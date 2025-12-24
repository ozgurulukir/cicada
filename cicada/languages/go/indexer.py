"""Go repository indexer using SCIP protocol.

This indexer uses scip-go to generate type-aware semantic indexes
of Go codebases.
"""

from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer


class GoSCIPIndexer(GenericSCIPIndexer):
    """Index Go repositories using scip-go."""

    def __init__(self, verbose: bool = False):
        """Initialize the Go SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = {
            "vendor",
            ".git",
            "node_modules",
            "testdata",
        }

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "go"

    def get_file_extensions(self) -> list[str]:
        """Return Go file extensions."""
        return [".go"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-go indexer."""
        cmd = ["scip-go", "index", "--output", "index.scip"]
        scip_file = repo_path / "index.scip"

        return self._run_scip_command(
            repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
        )
