"""JVM repository indexers using SCIP protocol.

This module provides indexers for Java, Kotlin, and Scala using
scip-java, which supports all JVM languages.
"""

from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer

# Shared excluded directories for JVM projects
_JVM_EXCLUDED_DIRS = {
    "build",
    "target",
    ".gradle",
    ".git",
    "node_modules",
    "out",
    "bin",
    ".idea",
}


class _ScipJavaIndexerBase(GenericSCIPIndexer):
    """Base class for JVM language indexers using scip-java.

    This class contains the shared logic for Java, Kotlin, and Scala
    indexing since they all use the same underlying scip-java tool.
    """

    def __init__(self, verbose: bool = False):
        """Initialize the SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = _JVM_EXCLUDED_DIRS

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-java indexer."""
        cmd = ["scip-java", "index", "--output", "index.scip"]
        scip_file = repo_path / "index.scip"

        return self._run_scip_command(
            repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
        )


class JavaSCIPIndexer(_ScipJavaIndexerBase):
    """Index Java repositories using scip-java."""

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "java"

    def get_file_extensions(self) -> list[str]:
        """Return Java file extensions."""
        return [".java"]


class KotlinSCIPIndexer(_ScipJavaIndexerBase):
    """Index Kotlin repositories using scip-java."""

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "kotlin"

    def get_file_extensions(self) -> list[str]:
        """Return Kotlin file extensions."""
        return [".kt", ".kts"]


class ScalaSCIPIndexer(_ScipJavaIndexerBase):
    """Index Scala repositories using scip-java."""

    def __init__(self, verbose: bool = False):
        """Initialize the Scala SCIP indexer with additional exclusions."""
        super().__init__(verbose)
        self.excluded_dirs = self.excluded_dirs | {".bloop", ".metals", "project/target"}

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "scala"

    def get_file_extensions(self) -> list[str]:
        """Return Scala file extensions."""
        return [".scala", ".sc"]
