"""SCIP indexer - re-export from cicada_scip for backward compatibility."""

__all__ = []

try:
    from cicada_scip.indexer import GenericSCIPIndexer

    __all__ = ["GenericSCIPIndexer"]
except ImportError:
    pass
