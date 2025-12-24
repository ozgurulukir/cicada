"""C/C++ repository indexers using SCIP protocol.

This module provides indexers for C and C++ using scip-clang,
which supports both languages.
"""

from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer

# Shared excluded directories for C/C++ projects
_CLANG_EXCLUDED_DIRS = {
    "build",
    ".git",
    "node_modules",
    "vendor",
    "third_party",
    "cmake-build-debug",
    "cmake-build-release",
}


class _ScipClangIndexerBase(GenericSCIPIndexer):
    """Base class for C/C++ indexers using scip-clang.

    This class contains the shared logic for C and C++ indexing
    since they both use the same underlying scip-clang tool.
    """

    def __init__(self, verbose: bool = False):
        """Initialize the SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = _CLANG_EXCLUDED_DIRS

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-clang indexer."""
        scip_file = repo_path / "index.scip"
        cmd = ["scip-clang", "--output", str(scip_file)]

        return self._run_scip_command(
            repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
        )


class CSCIPIndexer(_ScipClangIndexerBase):
    """Index C repositories using scip-clang."""

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "c"

    def get_file_extensions(self) -> list[str]:
        """Return C file extensions."""
        return [".c", ".h"]


class CppSCIPIndexer(_ScipClangIndexerBase):
    """Index C++ repositories using scip-clang."""

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "cpp"

    def get_file_extensions(self) -> list[str]:
        """Return C++ file extensions."""
        return [".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h"]
