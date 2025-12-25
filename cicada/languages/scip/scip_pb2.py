"""SCIP protobuf - re-export from cicada_scip for backward compatibility."""

__all__ = []

try:
    from cicada_scip.scip_pb2 import *  # noqa: F401, F403
    from cicada_scip import scip_pb2 as _scip_pb2

    # Re-export all public names
    __all__ = [name for name in dir(_scip_pb2) if not name.startswith("_")]
except ImportError:
    pass
