"""Dart repository indexer using SCIP protocol.

This indexer uses scip-dart to generate type-aware semantic indexes
of Dart codebases.
"""

from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer


class DartSCIPIndexer(GenericSCIPIndexer):
    """Index Dart repositories using scip-dart."""

    def __init__(self, verbose: bool = False):
        """Initialize the Dart SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = {
            "build",
            ".dart_tool",
            ".git",
            "node_modules",
            ".pub-cache",
        }

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "dart"

    def get_file_extensions(self) -> list[str]:
        """Return Dart file extensions."""
        return [".dart"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-dart indexer."""
        cmd = ["scip-dart", "index", "--output", "index.scip"]
        scip_file = repo_path / "index.scip"

        return self._run_scip_command(
            repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
        )
