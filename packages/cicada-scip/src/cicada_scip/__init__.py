"""
Cicada SCIP - SCIP-based language indexing for Cicada.

SCIP (Source Code Intelligence Protocol) is a language-agnostic protocol
created by Sourcegraph for code intelligence.
Learn more: https://github.com/sourcegraph/scip

This package provides:
- SCIPReader: Read .scip binary files
- SCIPConverter: Convert SCIP to Cicada's universal index format
- GenericSCIPIndexer: Base class for SCIP-based language indexers
"""

__version__ = "0.1.0"


# Lazy imports to avoid circular dependencies and speed up import time
def __getattr__(name):
    if name == "SCIPReader":
        from cicada_scip.reader import SCIPReader

        return SCIPReader
    elif name == "SCIPConverter":
        from cicada_scip.converter import SCIPConverter

        return SCIPConverter
    elif name == "GenericSCIPIndexer":
        from cicada_scip.indexer import GenericSCIPIndexer

        return GenericSCIPIndexer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["SCIPReader", "SCIPConverter", "GenericSCIPIndexer"]
