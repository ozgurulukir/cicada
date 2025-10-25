#!/usr/bin/env python
"""
PR Indexer - Indexes pull requests and their commits for fast offline lookup.

Fetches all PRs from a GitHub repository and builds an index mapping commits to PRs.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class PRIndexer:
    """Indexes GitHub pull requests for fast offline lookup."""

    def __init__(self, repo_path: str = "."):
        """
        Initialize the PR indexer.

        Args:
            repo_path: Path to the git repository (defaults to current directory)
        """
        self.repo_path = Path(repo_path).resolve()
        self._validate_git_repo()
        self._validate_gh_cli()
        self.repo_owner = None
        self.repo_name = None
        self._get_repo_info()

    def _validate_git_repo(self):
        """Validate that the path is a git repository."""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def _validate_gh_cli(self):
        """Validate that GitHub CLI is installed and available."""
        try:
            subprocess.run(
                ["gh", "--version"], capture_output=True, check=True, cwd=self.repo_path
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "GitHub CLI (gh) is not installed or not available in PATH. "
                "Install it from https://cli.github.com/"
            )

    def _get_repo_info(self):
        """Get the repository owner and name from git remote."""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "repo",
                    "view",
                    "--json",
                    "nameWithOwner",
                    "-q",
                    ".nameWithOwner",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            name_with_owner = result.stdout.strip()
            if not name_with_owner or name_with_owner == "null":
                raise RuntimeError("Not a GitHub repository or no remote configured")

            self.repo_owner, self.repo_name = name_with_owner.split("/")

        except subprocess.CalledProcessError as e:
            raise RuntimeError("Not a GitHub repository or no remote configured")

    def fetch_all_prs(self, state: str = "all") -> List[Dict[str, Any]]:
        """
        Fetch all pull requests from GitHub using GraphQL for efficiency.

        Args:
            state: PR state filter ('all', 'open', 'closed', 'merged')

        Returns:
            List of PR dictionaries with full details including description and comments
        """
        print(f"Fetching PRs from {self.repo_owner}/{self.repo_name}...")

        try:
            # First, get the list of PR numbers using REST (fast, simple)
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    state,
                    "--json",
                    "number",
                    "--limit",
                    "10000",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            pr_list = json.loads(result.stdout)
            pr_numbers = [pr["number"] for pr in pr_list]
            print(f"Found {len(pr_numbers)} pull requests")

            # Fetch detailed PR info in batches using GraphQL
            detailed_prs = []
            batch_size = 10
            total_batches = (len(pr_numbers) + batch_size - 1) // batch_size

            try:
                for i in range(0, len(pr_numbers), batch_size):
                    batch = pr_numbers[i:i + batch_size]
                    print(f"  Fetching batch {i//batch_size + 1}/{total_batches} ({len(batch)} PRs)...")

                    batch_prs = self._fetch_prs_batch_graphql(batch)
                    detailed_prs.extend(batch_prs)

            except KeyboardInterrupt:
                print(f"\n\n⚠️  Interrupted by user. Fetched {len(detailed_prs)}/{len(pr_numbers)} PRs.")
                print("Saving partial index...")
                # Return what we have so far
                return detailed_prs

            return detailed_prs

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PRs: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR data: {e}")

    def _fetch_prs_batch_graphql(self, pr_numbers: List[int]) -> List[Dict[str, Any]]:
        """
        Fetch detailed PR information for a batch of PRs using GraphQL.

        Args:
            pr_numbers: List of PR numbers to fetch

        Returns:
            List of detailed PR dictionaries
        """
        if not pr_numbers:
            return []

        # Build GraphQL query for batch fetching
        # We'll query each PR individually within the same request
        pr_queries = []
        for i, num in enumerate(pr_numbers):
            pr_queries.append(f'''
                pr{i}: pullRequest(number: {num}) {{
                    number
                    title
                    url
                    state
                    mergedAt
                    bodyText
                    author {{ login }}
                    commits(first: 250) {{
                        nodes {{ commit {{ oid }} }}
                    }}
                    files(first: 100) {{
                        nodes {{ path }}
                    }}
                    reviewThreads(first: 100) {{
                        nodes {{
                            isResolved
                            comments(first: 10) {{
                                nodes {{
                                    id
                                    body
                                    createdAt
                                    author {{ login }}
                                    path
                                    position
                                    originalPosition
                                    line
                                    originalLine
                                    diffHunk
                                    commit {{ oid }}
                                }}
                            }}
                        }}
                    }}
                }}
            ''')

        query = f'''
            query {{
                repository(owner: "{self.repo_owner}", name: "{self.repo_name}") {{
                    {' '.join(pr_queries)}
                }}
            }}
        '''

        try:
            result = subprocess.run(
                ["gh", "api", "graphql", "-f", f"query={query}"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            data = json.loads(result.stdout)
            repo_data = data.get("data", {}).get("repository", {})

            detailed_prs = []
            for i in range(len(pr_numbers)):
                pr_data = repo_data.get(f"pr{i}")
                if not pr_data:
                    continue

                # Extract commits
                commits = [
                    node["commit"]["oid"]
                    for node in pr_data.get("commits", {}).get("nodes", [])
                ]

                # Extract files
                files = [
                    node["path"]
                    for node in pr_data.get("files", {}).get("nodes", [])
                ]

                # Extract and flatten review thread comments
                comments = []
                for thread in pr_data.get("reviewThreads", {}).get("nodes", []):
                    is_resolved = thread.get("isResolved", False)

                    for comment_node in thread.get("comments", {}).get("nodes", []):
                        # Map comment line to current file line
                        mapped_line = None
                        if comment_node.get("path") and comment_node.get("commit"):
                            # We'll map the line in a separate pass to avoid slowing down the fetch
                            # For now, just store the original data
                            mapped_line = comment_node.get("line")  # Will be updated later

                        comments.append({
                            "id": comment_node.get("id"),
                            "author": comment_node.get("author", {}).get("login", "unknown"),
                            "body": comment_node.get("body", ""),
                            "created_at": comment_node.get("createdAt"),
                            "path": comment_node.get("path"),
                            "line": mapped_line,  # Current line (to be mapped)
                            "original_line": comment_node.get("originalLine"),
                            "diff_hunk": comment_node.get("diffHunk"),
                            "resolved": is_resolved,  # Thread-level resolution status
                            "commit_sha": comment_node.get("commit", {}).get("oid"),
                        })

                detailed_pr = {
                    "number": pr_data["number"],
                    "title": pr_data["title"],
                    "url": pr_data["url"],
                    "state": pr_data["state"].lower(),
                    "merged": pr_data.get("mergedAt") is not None,
                    "merged_at": pr_data.get("mergedAt"),
                    "author": pr_data.get("author", {}).get("login", "unknown"),
                    "description": pr_data.get("bodyText", ""),
                    "commits": commits,
                    "files_changed": files,
                    "comments": comments,
                }

                detailed_prs.append(detailed_pr)

            return detailed_prs

        except subprocess.CalledProcessError as e:
            # Fall back to slower REST API if GraphQL fails
            print(f"  Warning: GraphQL failed, falling back to REST API: {e.stderr}")
            return [self._fetch_pr_rest(num) for num in pr_numbers]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Warning: Failed to parse GraphQL response: {e}")
            return [self._fetch_pr_rest(num) for num in pr_numbers]

    def _fetch_pr_rest(self, pr_number: int) -> Dict[str, Any]:
        """
        Fallback method to fetch a single PR using REST API.

        Args:
            pr_number: PR number to fetch

        Returns:
            PR dictionary
        """
        commits = self._fetch_pr_commits(pr_number)
        files = self._fetch_pr_files(pr_number)

        # Fetch PR metadata
        try:
            result = subprocess.run(
                ["gh", "pr", "view", str(pr_number), "--json", "number,title,url,state,mergedAt,author,body"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )
            pr_data = json.loads(result.stdout)

            return {
                "number": pr_number,
                "title": pr_data.get("title", ""),
                "url": pr_data.get("url", ""),
                "state": pr_data.get("state", "").lower(),
                "merged": pr_data.get("mergedAt") is not None,
                "merged_at": pr_data.get("mergedAt"),
                "author": pr_data.get("author", {}).get("login", "unknown"),
                "description": pr_data.get("body", ""),
                "commits": commits,
                "files_changed": files,
                "comments": [],  # REST fallback doesn't fetch comments
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            # Return minimal PR info if everything fails
            return {
                "number": pr_number,
                "title": f"PR #{pr_number}",
                "url": f"https://github.com/{self.repo_owner}/{self.repo_name}/pull/{pr_number}",
                "state": "unknown",
                "merged": False,
                "merged_at": None,
                "author": "unknown",
                "description": "",
                "commits": commits,
                "files_changed": files,
                "comments": [],
            }

    def _fetch_pr_commits(self, pr_number: int) -> List[str]:
        """
        Fetch all commit SHAs for a specific PR.

        Args:
            pr_number: PR number

        Returns:
            List of commit SHAs
        """
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    str(pr_number),
                    "--json",
                    "commits",
                    "-q",
                    ".commits[].oid",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            commits = [
                line.strip()
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            return commits

        except subprocess.CalledProcessError:
            # If we can't fetch commits, return empty list
            return []

    def _fetch_pr_files(self, pr_number: int) -> List[str]:
        """
        Fetch all files changed in a specific PR.

        Args:
            pr_number: PR number

        Returns:
            List of file paths
        """
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    str(pr_number),
                    "--json",
                    "files",
                    "-q",
                    ".files[].path",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            files = [
                line.strip()
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            return files

        except subprocess.CalledProcessError:
            # If we can't fetch files, return empty list
            return []

    def build_index(self, prs: List[Dict[str, Any]], preserve_last_pr: Optional[int] = None) -> Dict[str, Any]:
        """
        Build the index structure from PR data.

        Args:
            prs: List of PR dictionaries
            preserve_last_pr: If set, use this as last_pr_number instead of calculating from prs.
                             Used when building partial indexes from interrupted fetches.

        Returns:
            Index dictionary with metadata, prs, commit_to_pr mapping, and file_to_prs mapping
        """
        print("Building index...")

        # Build commit -> PR mapping
        commit_to_pr = {}
        for pr in prs:
            pr_number = pr["number"]
            for commit in pr["commits"]:
                commit_to_pr[commit] = pr_number

        # Build file -> PRs mapping
        file_to_prs = {}
        for pr in prs:
            pr_number = pr["number"]
            for file_path in pr.get("files_changed", []):
                if file_path not in file_to_prs:
                    file_to_prs[file_path] = []
                file_to_prs[file_path].append(pr_number)

        # Sort PR numbers for each file (newest first)
        for file_path in file_to_prs:
            file_to_prs[file_path].sort(reverse=True)

        # Count total comments
        total_comments = sum(len(pr.get("comments", [])) for pr in prs)

        # Build index structure
        index = {
            "metadata": {
                "repo_owner": self.repo_owner,
                "repo_name": self.repo_name,
                "last_indexed_at": datetime.now().isoformat(),
                "total_prs": len(prs),
                "total_commits_mapped": len(commit_to_pr),
                "total_comments": total_comments,
                "total_files": len(file_to_prs),
            },
            "prs": {str(pr["number"]): pr for pr in prs},
            "commit_to_pr": commit_to_pr,
            "file_to_prs": file_to_prs,
        }

        # Track last PR number for incremental updates
        if preserve_last_pr is not None:
            # Use preserved value (for partial/interrupted fetches)
            index["metadata"]["last_pr_number"] = preserve_last_pr
        elif prs:
            # Calculate from PRs (for complete fetches)
            index["metadata"]["last_pr_number"] = max(pr["number"] for pr in prs)

        print(f"Index built: {len(prs)} PRs, {len(commit_to_pr)} commits, {len(file_to_prs)} files, {total_comments} comments")
        return index

    def load_existing_index(self, index_path: str) -> Optional[Dict[str, Any]]:
        """
        Load existing index file if it exists.

        Args:
            index_path: Path to the index file

        Returns:
            Existing index dictionary or None if file doesn't exist
        """
        index_file = Path(index_path)
        if not index_file.exists():
            return None

        try:
            with open(index_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load existing index: {e}")
            return None

    def incremental_update(
        self, existing_index: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Fetch only new PRs since the last index.

        Args:
            existing_index: The existing index dictionary

        Returns:
            List of new PRs
        """
        last_pr_number = existing_index.get("metadata", {}).get("last_pr_number", 0)
        print(f"Performing incremental update (last PR: #{last_pr_number})...")

        # Fetch PR numbers (newest first) until we hit PRs we already have
        # Use a large limit to handle bulk updates, but stop early when we find indexed PRs
        new_pr_numbers = []
        fetch_limit = 1000  # Check up to 1000 most recent PRs

        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    "all",
                    "--json",
                    "number",
                    "--limit",
                    str(fetch_limit),
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            pr_list = json.loads(result.stdout)

            # PRs are returned newest-first by default
            for pr in pr_list:
                pr_num = pr["number"]
                if pr_num <= last_pr_number:
                    # Hit a PR we already have, stop here
                    break
                new_pr_numbers.append(pr_num)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PRs: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR data: {e}")

        if not new_pr_numbers:
            print(f"Found 0 new PRs")
            return []

        print(f"Found {len(new_pr_numbers)} new PRs")

        # Fetch detailed info for only the new PRs
        detailed_prs = []
        batch_size = 10
        total_batches = (len(new_pr_numbers) + batch_size - 1) // batch_size

        try:
            for i in range(0, len(new_pr_numbers), batch_size):
                batch = new_pr_numbers[i:i + batch_size]
                print(f"  Fetching batch {i//batch_size + 1}/{total_batches} ({len(batch)} PRs)...")

                batch_prs = self._fetch_prs_batch_graphql(batch)
                detailed_prs.extend(batch_prs)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user. Fetched {len(detailed_prs)}/{len(new_pr_numbers)} PRs.")
            print("Saving partial index...")
            return detailed_prs

        return detailed_prs

    def merge_indexes(
        self, existing_index: Dict[str, Any], new_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge new PRs into existing index.

        Args:
            existing_index: The existing index
            new_prs: List of new PR dictionaries

        Returns:
            Updated index dictionary
        """
        print("Merging new PRs into existing index...")

        # Update PR data
        for pr in new_prs:
            existing_index["prs"][str(pr["number"])] = pr

            # Update commit -> PR mapping
            for commit in pr["commits"]:
                existing_index["commit_to_pr"][commit] = pr["number"]

        # Rebuild file -> PRs mapping from scratch (most reliable)
        file_to_prs = {}
        for pr_num_str, pr in existing_index["prs"].items():
            pr_number = int(pr_num_str)
            for file_path in pr.get("files_changed", []):
                if file_path not in file_to_prs:
                    file_to_prs[file_path] = []
                file_to_prs[file_path].append(pr_number)

        # Sort PR numbers for each file (newest first)
        for file_path in file_to_prs:
            file_to_prs[file_path].sort(reverse=True)

        existing_index["file_to_prs"] = file_to_prs

        # Count total comments
        total_comments = sum(len(pr.get("comments", [])) for pr in existing_index["prs"].values())

        # Update metadata
        existing_index["metadata"]["last_indexed_at"] = datetime.now().isoformat()
        existing_index["metadata"]["total_prs"] = len(existing_index["prs"])
        existing_index["metadata"]["total_commits_mapped"] = len(
            existing_index["commit_to_pr"]
        )
        existing_index["metadata"]["total_comments"] = total_comments
        existing_index["metadata"]["total_files"] = len(file_to_prs)

        if new_prs:
            existing_index["metadata"]["last_pr_number"] = max(
                existing_index["metadata"].get("last_pr_number", 0),
                max(pr["number"] for pr in new_prs),
            )

        return existing_index

    def _map_comment_line_to_current(
        self, file_path: str, original_line: int, commit_sha: str
    ) -> Optional[int]:
        """
        Map a line number from a PR commit to the current HEAD.

        Args:
            file_path: Path to the file
            original_line: Line number in the PR commit
            commit_sha: The commit SHA where the comment was made

        Returns:
            Current line number, or None if line no longer exists
        """
        if not original_line or not commit_sha or not file_path:
            return None

        try:
            # Check if the file still exists
            result = subprocess.run(
                ["git", "ls-files", file_path],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
            )

            if not result.stdout.strip():
                # File doesn't exist in current HEAD
                return None

            # Use git blame to see what's at this line now
            # First, check if the line exists in the current file
            result = subprocess.run(
                ["git", "show", f"HEAD:{file_path}"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
            )

            current_lines = result.stdout.split("\n")
            if original_line > len(current_lines):
                # Line number exceeds file length
                return None

            # Try to get a unique context from the original line
            # to help track it even if line numbers changed
            result = subprocess.run(
                ["git", "show", f"{commit_sha}:{file_path}"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
            )

            original_lines = result.stdout.split("\n")
            if original_line > len(original_lines):
                return None

            # Get the actual line content from the original commit
            original_content = original_lines[original_line - 1].strip()

            if not original_content:
                # Empty line, can't track reliably
                return original_line  # Return original as best guess

            # Search for the same content in current file (best effort)
            # Look for exact match near the original line number
            search_range = 20  # Search +/- 20 lines
            start = max(1, original_line - search_range)
            end = min(len(current_lines), original_line + search_range)

            for i in range(start - 1, end):
                if current_lines[i].strip() == original_content:
                    return i + 1

            # If not found nearby, return None (line likely deleted/changed)
            return None

        except subprocess.CalledProcessError:
            # If any git command fails, return None
            return None
        except (IndexError, ValueError):
            return None

    def _map_all_comment_lines(self, prs: List[Dict[str, Any]]) -> None:
        """
        Map all comment lines in PRs to current line numbers.

        Args:
            prs: List of PR dictionaries to update in-place
        """
        print("Mapping comment lines to current file state...")

        total_comments = sum(len(pr.get("comments", [])) for pr in prs)
        if total_comments == 0:
            return

        mapped_count = 0
        unmapped_count = 0

        try:
            for pr in prs:
                for comment in pr.get("comments", []):
                    original_line = comment.get("original_line")
                    commit_sha = comment.get("commit_sha")
                    file_path = comment.get("path")

                    if original_line and commit_sha and file_path:
                        current_line = self._map_comment_line_to_current(
                            file_path, original_line, commit_sha
                        )
                        comment["line"] = current_line

                        if current_line is not None:
                            mapped_count += 1
                        else:
                            unmapped_count += 1
                    else:
                        comment["line"] = None
                        unmapped_count += 1

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Line mapping interrupted. Mapped {mapped_count}/{total_comments} comments.")
            print("Saving index with partial line mappings...")
            # Re-raise to let the outer handler save the index
            raise

        print(f"  Mapped {mapped_count} comments, {unmapped_count} unmappable/outdated")

    def save_index(self, index: Dict[str, Any], output_path: str):
        """
        Save index to file.

        Args:
            index: Index dictionary to save
            output_path: Path where the index will be saved
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(index, f, indent=2)

        print(f"Index saved to: {output_path}")

    def index_repository(
        self, output_path: str = ".cicada/pr_index.json", incremental: bool = False
    ):
        """
        Index the repository's PRs and save to file.

        Args:
            output_path: Path where the index will be saved
            incremental: If True, only fetch new PRs since last index
        """
        # Load existing index to preserve last_pr_number if clean build is interrupted
        existing_index = self.load_existing_index(output_path)
        old_last_pr = existing_index.get("metadata", {}).get("last_pr_number", 0) if existing_index else 0

        if incremental:
            if existing_index:
                # Fetch only new PRs
                new_prs = self.incremental_update(existing_index)

                if not new_prs:
                    print("No new PRs found. Index is up to date.")
                    return existing_index

                # Map comment lines to current file state
                self._map_all_comment_lines(new_prs)

                # Merge new PRs into existing index
                index = self.merge_indexes(existing_index, new_prs)
            else:
                print("No existing index found. Performing full index...")
                prs = self.fetch_all_prs()
                # Map comment lines to current file state
                self._map_all_comment_lines(prs)
                index = self.build_index(prs)
        else:
            # Full index (--clean)
            print(f"Starting clean rebuild (will preserve last_pr_number={old_last_pr} if interrupted)...")
            prs = self.fetch_all_prs()
            # Map comment lines to current file state
            self._map_all_comment_lines(prs)

            # If interrupted and we only got some PRs, preserve the old last_pr_number
            # This allows incremental updates to continue working for NEW PRs
            # User can run --clean again later to fill in the missing middle PRs
            total_prs_in_repo = self._get_total_pr_count()
            if len(prs) < total_prs_in_repo:
                print(f"⚠️  Partial index: got {len(prs)}/{total_prs_in_repo} PRs.")
                print(f"   Preserving last_pr_number={old_last_pr} for incremental updates.")
                index = self.build_index(prs, preserve_last_pr=old_last_pr)
            else:
                # Complete fetch
                index = self.build_index(prs)

        # Save index
        self.save_index(index, output_path)
        return index

    def _get_total_pr_count(self) -> int:
        """Get total number of PRs in the repository (quick count)."""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    "all",
                    "--json",
                    "number",
                    "--limit",
                    "1",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )
            # The API returns PRs in descending order, so the first PR's number
            # is approximately the total count (close enough for our purposes)
            pr_list = json.loads(result.stdout)
            if pr_list:
                return pr_list[0]["number"]
            return 0
        except:
            # If we can't determine, assume we got all PRs
            return 0


def main():
    """CLI entry point for pr_indexer."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Index GitHub pull requests for fast offline lookup"
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to git repository (default: current directory)",
    )
    parser.add_argument(
        "--output",
        default=".cicada/pr_index.json",
        help="Output path for the index file (default: .cicada/pr_index.json)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean and rebuild the entire index from scratch (default: incremental update)",
    )

    args = parser.parse_args()

    try:
        indexer = PRIndexer(repo_path=args.repo)
        # Incremental by default, unless --clean is specified
        indexer.index_repository(output_path=args.output, incremental=not args.clean)

        print(
            "\n✅ Indexing complete! You can now use the MCP tools for PR history lookups."
        )

    except KeyboardInterrupt:
        print("\n\n⚠️  Indexing interrupted by user.")
        print("Partial index may have been saved. Run again to continue or use --incremental.")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
