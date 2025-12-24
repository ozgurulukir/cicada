""".NET repository indexers using SCIP protocol.

This module provides indexers for C# and Visual Basic using scip-dotnet,
which supports both languages.
"""

from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer

# Shared excluded directories for .NET projects
_DOTNET_EXCLUDED_DIRS = {
    "bin",
    "obj",
    ".git",
    "node_modules",
    "packages",
    ".vs",
}


class _ScipDotnetIndexerBase(GenericSCIPIndexer):
    """Base class for .NET language indexers using scip-dotnet.

    This class contains the shared logic for C# and Visual Basic
    indexing since they both use the same underlying scip-dotnet tool.
    """

    def __init__(self, verbose: bool = False):
        """Initialize the SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = _DOTNET_EXCLUDED_DIRS

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-dotnet indexer."""
        cmd = ["scip-dotnet", "index", "--output", "index.scip"]
        scip_file = repo_path / "index.scip"

        return self._run_scip_command(
            repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
        )


class CSharpSCIPIndexer(_ScipDotnetIndexerBase):
    """Index C# repositories using scip-dotnet."""

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "csharp"

    def get_file_extensions(self) -> list[str]:
        """Return C# file extensions."""
        return [".cs"]


class VBSCIPIndexer(_ScipDotnetIndexerBase):
    """Index Visual Basic repositories using scip-dotnet."""

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "vb"

    def get_file_extensions(self) -> list[str]:
        """Return Visual Basic file extensions."""
        return [".vb"]
