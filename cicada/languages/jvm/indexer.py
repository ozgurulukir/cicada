"""JVM repository indexers using SCIP protocol.

This module provides indexers for Java and Scala using
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

    This class contains the shared logic for Java and Scala
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
        """Run scip-java indexer via coursier."""
        import shutil

        scip_file = repo_path / "index.scip"

        # Try to find scip-java in PATH first, then fall back to coursier
        if shutil.which("scip-java"):
            cmd = ["scip-java", "index", "--output", "index.scip"]
        elif shutil.which("coursier") or shutil.which("cs"):
            # Use coursier to launch scip-java (more reliable)
            launcher = "coursier" if shutil.which("coursier") else "cs"
            cmd = [
                launcher,
                "launch",
                "com.sourcegraph:scip-java_2.13:0.11.2",
                "--",
                "index",
                "--output",
                "index.scip",
            ]
        else:
            raise RuntimeError(
                "scip-java not found. Install via: brew install coursier/formulas/coursier"
            )

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
