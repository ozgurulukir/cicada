"""
Git integration - extract commit history and file changes

This module provides access to git commit history using GitPython.
It complements pr_finder.py (which provides PR attribution) by
offering comprehensive commit history for files and functions.
"""

import git
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class GitHelper:
    """Helper class for extracting git commit history"""

    def __init__(self, repo_path: str):
        """
        Initialize GitHelper with a repository path

        Args:
            repo_path: Path to git repository

        Raises:
            git.InvalidGitRepositoryError: If path is not a git repository
        """
        self.repo = git.Repo(repo_path)
        self.repo_path = Path(repo_path)

    def get_file_history(self, file_path: str, max_commits: int = 10) -> List[Dict]:
        """
        Get commit history for a specific file

        Args:
            file_path: Relative path to file from repo root
            max_commits: Maximum number of commits to return

        Returns:
            List of commit information dictionaries with keys:
            - sha: Short commit SHA (8 chars)
            - full_sha: Full commit SHA
            - author: Author name
            - author_email: Author email
            - date: Commit date in ISO format
            - message: Full commit message
            - summary: First line of commit message
        """
        commits = []

        try:
            # Get commits that touched this file
            for commit in self.repo.iter_commits(paths=file_path, max_count=max_commits):
                commits.append({
                    'sha': commit.hexsha[:8],  # Short SHA
                    'full_sha': commit.hexsha,
                    'author': str(commit.author),
                    'author_email': commit.author.email,
                    'date': commit.committed_datetime.isoformat(),
                    'message': commit.message.strip(),
                    'summary': commit.summary
                })
        except Exception as e:
            print(f"Error getting history for {file_path}: {e}")

        return commits

    def get_function_history(
        self,
        file_path: str,
        function_name: str,
        line_number: int,
        max_commits: int = 5
    ) -> List[Dict]:
        """
        Get commit history for a specific function

        This is a heuristic-based approach that returns commits that:
        1. Modified the file near the function's location, OR
        2. Mention the function name in the commit message

        A more sophisticated version would use git blame to track
        exact line changes over time.

        Args:
            file_path: Relative path to file
            function_name: Name of the function
            line_number: Line number where function is defined
            max_commits: Maximum commits to return

        Returns:
            List of relevant commits with 'relevance' field:
            - 'mentioned': Function name in commit message
            - 'file_change': Recent change to the file
        """
        # Get file history with more commits than requested
        file_commits = self.get_file_history(file_path, max_commits * 2)

        # Filter for commits mentioning the function or likely relevant
        relevant_commits = []
        for commit in file_commits:
            # Include if function name in commit message
            if function_name.lower() in commit['message'].lower():
                commit['relevance'] = 'mentioned'
                relevant_commits.append(commit)
            # Or if it's a recent commit to the file
            elif len(relevant_commits) < max_commits:
                commit['relevance'] = 'file_change'
                relevant_commits.append(commit)

            if len(relevant_commits) >= max_commits:
                break

        return relevant_commits

    def get_recent_commits(self, max_count: int = 20) -> List[Dict]:
        """
        Get recent commits in the repository

        Args:
            max_count: Maximum number of commits to return

        Returns:
            List of recent commits with summary information
        """
        commits = []

        for commit in self.repo.iter_commits(max_count=max_count):
            # Try to get stats, but handle errors for initial/incomplete commits
            try:
                files_changed = len(commit.stats.files)
            except Exception:
                # Can't get stats (e.g., initial commit, shallow clone)
                files_changed = 0

            commits.append({
                'sha': commit.hexsha[:8],
                'full_sha': commit.hexsha,
                'author': str(commit.author),
                'date': commit.committed_datetime.isoformat(),
                'message': commit.summary,
                'files_changed': files_changed
            })

        return commits

    def get_commit_details(self, commit_sha: str) -> Optional[Dict]:
        """
        Get detailed information about a specific commit

        Args:
            commit_sha: Commit SHA (can be short or full)

        Returns:
            Detailed commit information or None if not found:
            - sha: Short SHA
            - full_sha: Full SHA
            - author: Author name
            - author_email: Author email
            - date: Commit date
            - message: Full commit message
            - files_changed: List of files modified
            - insertions: Number of lines inserted
            - deletions: Number of lines deleted
        """
        try:
            commit = self.repo.commit(commit_sha)

            # Try to get stats, but handle errors for initial/incomplete commits
            try:
                files_changed = list(commit.stats.files.keys())
                insertions = commit.stats.total['insertions']
                deletions = commit.stats.total['deletions']
            except Exception:
                # Can't get stats (e.g., initial commit, shallow clone)
                files_changed = []
                insertions = 0
                deletions = 0

            return {
                'sha': commit.hexsha[:8],
                'full_sha': commit.hexsha,
                'author': str(commit.author),
                'author_email': commit.author.email,
                'date': commit.committed_datetime.isoformat(),
                'message': commit.message.strip(),
                'files_changed': files_changed,
                'insertions': insertions,
                'deletions': deletions
            }
        except Exception as e:
            print(f"Error getting commit {commit_sha}: {e}")
            return None

    def search_commits(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search commit messages for a query string

        Args:
            query: Search term to find in commit messages
            max_results: Maximum results to return

        Returns:
            List of matching commits
        """
        results = []
        query_lower = query.lower()

        # Search through the last 500 commits
        for commit in self.repo.iter_commits(max_count=500):
            if query_lower in commit.message.lower():
                results.append({
                    'sha': commit.hexsha[:8],
                    'full_sha': commit.hexsha,
                    'author': str(commit.author),
                    'date': commit.committed_datetime.isoformat(),
                    'message': commit.summary
                })

                if len(results) >= max_results:
                    break

        return results


def main():
    """Test git helper functions"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m cicada.git_helper /path/to/repo")
        print("\nExample:")
        print("  python -m cicada.git_helper .")
        return

    repo_path = sys.argv[1]

    try:
        helper = GitHelper(repo_path)

        print("=" * 60)
        print("Git Helper Test")
        print("=" * 60)

        print("\n📋 Recent commits (last 5):")
        for commit in helper.get_recent_commits(5):
            print(f"  {commit['sha']} - {commit['message']}")
            print(f"    by {commit['author']} ({commit['files_changed']} files)")

        print("\n🔍 Searching for 'README' in commits:")
        for commit in helper.search_commits('README', 3):
            print(f"  {commit['sha']} - {commit['message']}")

        # Try to get history for a known file
        print("\n📁 Testing file history:")
        test_files = ['README.md', 'pyproject.toml', 'cicada/mcp_server.py']
        for test_file in test_files:
            history = helper.get_file_history(test_file, max_commits=3)
            if history:
                print(f"\n  {test_file} (last 3 commits):")
                for commit in history:
                    print(f"    {commit['sha']} - {commit['summary']}")
                break

        print("\n✅ Git helper is working correctly!")

    except git.InvalidGitRepositoryError:
        print(f"❌ Error: {repo_path} is not a git repository")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
