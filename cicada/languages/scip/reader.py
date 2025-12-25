"""SCIP reader - re-export from cicada_scip for backward compatibility."""

__all__ = []

try:
    from cicada_scip.reader import SCIPReader

    __all__ = ["SCIPReader"]
except ImportError:
    pass
