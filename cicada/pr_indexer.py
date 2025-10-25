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
        Fetch all pull requests from GitHub.

        Args:
            state: PR state filter ('all', 'open', 'closed', 'merged')

        Returns:
            List of PR dictionaries with full details
        """
        print(f"Fetching PRs from {self.repo_owner}/{self.repo_name}...")

        try:
            # Fetch PR list with basic info
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    state,
                    "--json",
                    "number,title,url,state,mergedAt,author,headRefOid",
                    "--limit",
                    "10000",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            prs = json.loads(result.stdout)
            print(f"Found {len(prs)} pull requests")

            # Fetch detailed information for each PR (commits and files)
            detailed_prs = []
            for i, pr in enumerate(prs, 1):
                if i % 10 == 0:
                    print(f"  Processing PR details {i}/{len(prs)}...")

                pr_number = pr["number"]

                # Fetch commits for this PR
                commits = self._fetch_pr_commits(pr_number)

                # Fetch files changed in this PR
                files = self._fetch_pr_files(pr_number)

                detailed_pr = {
                    "number": pr_number,
                    "title": pr["title"],
                    "url": pr["url"],
                    "state": pr["state"],
                    "merged": pr.get("mergedAt") is not None,
                    "merged_at": pr.get("mergedAt"),
                    "author": pr["author"]["login"] if pr.get("author") else "unknown",
                    "commits": commits,
                    "files_changed": files,
                }

                detailed_prs.append(detailed_pr)

            return detailed_prs

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PRs: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR data: {e}")

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

    def build_index(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build the index structure from PR data.

        Args:
            prs: List of PR dictionaries

        Returns:
            Index dictionary with metadata, prs, and commit_to_pr mapping
        """
        print("Building index...")

        # Build commit -> PR mapping
        commit_to_pr = {}
        for pr in prs:
            pr_number = pr["number"]
            for commit in pr["commits"]:
                commit_to_pr[commit] = pr_number

        # Build index structure
        index = {
            "metadata": {
                "repo_owner": self.repo_owner,
                "repo_name": self.repo_name,
                "last_indexed_at": datetime.now().isoformat(),
                "total_prs": len(prs),
                "total_commits_mapped": len(commit_to_pr),
            },
            "prs": {str(pr["number"]): pr for pr in prs},
            "commit_to_pr": commit_to_pr,
        }

        # Track last PR number for incremental updates
        if prs:
            index["metadata"]["last_pr_number"] = max(pr["number"] for pr in prs)

        print(f"Index built: {len(prs)} PRs, {len(commit_to_pr)} commits mapped")
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

        # Fetch all PRs and filter for new ones
        all_prs = self.fetch_all_prs()
        new_prs = [pr for pr in all_prs if pr["number"] > last_pr_number]

        print(f"Found {len(new_prs)} new PRs")
        return new_prs

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

        # Update metadata
        existing_index["metadata"]["last_indexed_at"] = datetime.now().isoformat()
        existing_index["metadata"]["total_prs"] = len(existing_index["prs"])
        existing_index["metadata"]["total_commits_mapped"] = len(
            existing_index["commit_to_pr"]
        )

        if new_prs:
            existing_index["metadata"]["last_pr_number"] = max(
                existing_index["metadata"].get("last_pr_number", 0),
                max(pr["number"] for pr in new_prs),
            )

        return existing_index

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
        self, output_path: str = "data/pr_index.json", incremental: bool = False
    ):
        """
        Index the repository's PRs and save to file.

        Args:
            output_path: Path where the index will be saved
            incremental: If True, only fetch new PRs since last index
        """
        if incremental:
            # Load existing index
            existing_index = self.load_existing_index(output_path)

            if existing_index:
                # Fetch only new PRs
                new_prs = self.incremental_update(existing_index)

                if not new_prs:
                    print("No new PRs found. Index is up to date.")
                    return existing_index

                # Merge new PRs into existing index
                index = self.merge_indexes(existing_index, new_prs)
            else:
                print("No existing index found. Performing full index...")
                prs = self.fetch_all_prs()
                index = self.build_index(prs)
        else:
            # Full index
            prs = self.fetch_all_prs()
            index = self.build_index(prs)

        # Save index
        self.save_index(index, output_path)
        return index


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
        default="data/pr_index.json",
        help="Output path for the index file (default: data/pr_index.json)",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only fetch new PRs since last index (faster)",
    )

    args = parser.parse_args()

    try:
        indexer = PRIndexer(repo_path=args.repo)
        indexer.index_repository(output_path=args.output, incremental=args.incremental)

        print(
            "\nIndexing complete! You can now use pr_finder.py for fast offline lookups."
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
