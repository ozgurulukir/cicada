"""
Elixir Repository Indexer.

Walks an Elixir repository and indexes all modules and functions.
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from cicada.parser import ElixirParser
from cicada.pr_finder import PRFinder


class ElixirIndexer:
    """Indexes Elixir repositories to extract module and function information."""

    def __init__(self, fetch_pr_info: bool = False):
        """
        Initialize the indexer with a parser.

        Args:
            fetch_pr_info: If True, fetch PR information for each module
        """
        self.parser = ElixirParser()
        self.excluded_dirs = {
            "deps",
            "_build",
            "node_modules",
            ".git",
            "assets",
            "priv",
        }
        self.fetch_pr_info = fetch_pr_info
        self.pr_finder = None
        self.pr_cache = {}  # Cache PR info by commit SHA to avoid redundant API calls

    def index_repository(self, repo_path: str, output_path: str = "data/index.json"):
        """
        Index an Elixir repository.

        Args:
            repo_path: Path to the Elixir repository root
            output_path: Path where the index JSON file will be saved

        Returns:
            Dictionary containing the index data
        """
        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        print(f"Indexing repository: {repo_path}")

        # Initialize PR finder if enabled
        if self.fetch_pr_info:
            try:
                self.pr_finder = PRFinder(repo_path=str(repo_path))
                print("PR information fetching enabled")
            except Exception as e:
                print(f"Warning: Could not initialize PR finder: {e}")
                print("Continuing without PR information...")
                self.fetch_pr_info = False

        # Find all Elixir files
        elixir_files = self._find_elixir_files(repo_path)
        total_files = len(elixir_files)

        print(f"Found {total_files} Elixir files")

        # Parse all files
        all_modules = {}
        total_functions = 0
        files_processed = 0

        for file_path in elixir_files:
            try:
                modules = self.parser.parse_file(str(file_path))

                if modules:
                    for module_data in modules:
                        module_name = module_data["module"]
                        functions = module_data["functions"]

                        # Calculate stats
                        public_count = sum(1 for f in functions if f["type"] == "def")
                        private_count = sum(1 for f in functions if f["type"] == "defp")

                        # Get PR information if enabled
                        pr_info = None
                        if self.fetch_pr_info:
                            relative_path = str(file_path.relative_to(repo_path))
                            pr_info = self._get_pr_info(
                                relative_path, module_data["line"]
                            )

                        # Store module info
                        module_info = {
                            "file": str(file_path.relative_to(repo_path)),
                            "line": module_data["line"],
                            "moduledoc": module_data.get("moduledoc"),
                            "functions": functions,
                            "total_functions": len(functions),
                            "public_functions": public_count,
                            "private_functions": private_count,
                            "aliases": module_data.get("aliases", {}),
                            "imports": module_data.get("imports", []),
                            "requires": module_data.get("requires", []),
                            "uses": module_data.get("uses", []),
                            "value_mentions": module_data.get("value_mentions", []),
                            "calls": module_data.get("calls", []),
                        }

                        # Add PR info if available
                        if pr_info:
                            module_info["pr_info"] = pr_info

                        all_modules[module_name] = module_info

                        total_functions += len(functions)

                files_processed += 1

                # Progress reporting
                if files_processed % 10 == 0:
                    print(f"  Processed {files_processed}/{total_files} files...")

            except Exception as e:
                print(f"  Skipping {file_path}: {e}")
                continue

        # Build final index
        index = {
            "modules": all_modules,
            "metadata": {
                "indexed_at": datetime.now().isoformat(),
                "total_modules": len(all_modules),
                "total_functions": total_functions,
                "repo_path": str(repo_path),
            },
        }

        # Save to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(index, f, indent=2)

        print(f"\nIndexing complete!")
        print(f"  Modules: {len(all_modules)}")
        print(f"  Functions: {total_functions}")
        print(f"\nIndex saved to: {output_path}")

        return index

    def _get_pr_info(self, file_path: str, line_number: int) -> dict:
        """
        Get PR information for a specific file and line number with caching.

        Args:
            file_path: Relative path to the file from repo root
            line_number: Line number where the module is defined

        Returns:
            Dictionary containing PR information, or None if not available
        """
        if not self.fetch_pr_info or self.pr_finder is None:
            return None

        try:
            result = self.pr_finder.find_pr_for_line(file_path, line_number)

            # Extract commit SHA for caching
            commit_sha = result.get("commit")

            if commit_sha:
                # Check cache first
                if commit_sha in self.pr_cache:
                    return self.pr_cache[commit_sha]

                # Cache the result
                pr_info = {
                    "commit": commit_sha,
                    "author_name": result.get("author_name"),
                    "author_email": result.get("author_email"),
                    "pr": result.get("pr"),
                }

                self.pr_cache[commit_sha] = pr_info
                return pr_info

            return None

        except Exception as e:
            # Silently fail on PR lookup errors to avoid breaking indexing
            print(
                f"  Warning: Could not fetch PR info for {file_path}:{line_number}: {e}"
            )
            return None

    def _find_elixir_files(self, repo_path: Path) -> list:
        """Find all Elixir source files in the repository."""
        elixir_files = []

        for root, dirs, files in os.walk(repo_path):
            # Remove excluded directories from the search
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            # Find .ex and .exs files
            for file in files:
                if file.endswith((".ex", ".exs")):
                    file_path = Path(root) / file
                    elixir_files.append(file_path)

        return sorted(elixir_files)


def main():
    """Main entry point for the indexer CLI."""
    parser = argparse.ArgumentParser(
        description="Index current Elixir repository to extract modules and functions"
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the Elixir repository to index (default: current directory)",
    )
    parser.add_argument(
        "--output",
        default=".cicada/index.json",
        help="Output path for the index file (default: .cicada/index.json)",
    )
    parser.add_argument(
        "--pr-info",
        action="store_true",
        help="Fetch PR information for each module (requires GitHub CLI and may be slow)",
    )

    args = parser.parse_args()

    indexer = ElixirIndexer(fetch_pr_info=args.pr_info)
    indexer.index_repository(args.repo, args.output)


if __name__ == "__main__":
    main()
