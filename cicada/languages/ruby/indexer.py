"""Ruby repository indexer using SCIP protocol.

This indexer uses scip-ruby to generate type-aware semantic indexes
of Ruby codebases.
"""

from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer


class RubySCIPIndexer(GenericSCIPIndexer):
    """Index Ruby repositories using scip-ruby."""

    def __init__(self, verbose: bool = False):
        """Initialize the Ruby SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = {
            "vendor",
            ".git",
            "node_modules",
            "tmp",
            "log",
            ".bundle",
        }

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "ruby"

    def get_file_extensions(self) -> list[str]:
        """Return Ruby file extensions."""
        return [".rb", ".rake"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-ruby indexer."""
        cmd = ["scip-ruby", "index", "--output", "index.scip"]
        scip_file = repo_path / "index.scip"

        return self._run_scip_command(
            repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
        )
