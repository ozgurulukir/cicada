"""Language adapters - re-export from cicada_scip for backward compatibility."""

__all__ = []

try:
    from cicada_scip.language_adapters import (
        BaseSCIPLanguageAdapter,
        PythonSCIPAdapter,
        RustSCIPAdapter,
        get_language_adapter,
        register_language_adapter,
    )

    __all__ = [
        "BaseSCIPLanguageAdapter",
        "PythonSCIPAdapter",
        "RustSCIPAdapter",
        "register_language_adapter",
        "get_language_adapter",
    ]
except ImportError:
    pass
