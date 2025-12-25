# Cicada Monorepo Split Plan

## Goal
Split cicada into a monorepo with separate packages for easier maintenance and development.

## Target Structure

```
cicada/                          # Monorepo root
├── packages/
│   ├── cicada-core/             # Shared foundation
│   │   ├── pyproject.toml
│   │   └── src/cicada_core/
│   │       ├── base_indexer.py  # Minimal ABC (no enrichment)
│   │       ├── schema.py        # Index schema types
│   │       └── utils/
│   │           ├── hash_utils.py
│   │           └── storage.py
│   │
│   ├── cicada-scip/             # SCIP-based indexing
│   │   ├── pyproject.toml       # depends on cicada-core
│   │   └── src/cicada_scip/
│   │       ├── reader.py
│   │       ├── converter.py
│   │       ├── indexer.py       # GenericSCIPIndexer
│   │       ├── formatter.py
│   │       └── languages/
│   │           ├── python/
│   │           ├── typescript/
│   │           ├── go/
│   │           ├── rust/
│   │           └── ... (11 new languages)
│   │
│   └── cicada/                  # Main package (MCP + CLI + queries)
│       ├── pyproject.toml       # depends on cicada-core, optionally cicada-scip
│       └── src/cicada/
│           ├── mcp/
│           ├── cli/
│           ├── git/             # Git helpers (used by queries + enrichment)
│           ├── extractors/      # Keyword/signature extractors
│           ├── enrichment/      # Enrichment pipeline (moved from base_indexer)
│           └── languages/
│               ├── elixir/      # Tree-sitter based (stays here for now)
│               └── erlang/
│
├── pyproject.toml               # Root workspace config
├── Makefile
└── README.md
```

## Principles

1. **One-way dependencies**: core ← scip ← main (never backwards)
2. **Incremental migration**: Keep tests passing at each step
3. **Feature flags**: Main cicada works without cicada-scip installed
4. **Minimal core**: cicada-core should be <500 lines total

## Phase 1: Setup Monorepo Structure (Day 1)

### 1.1 Create directory structure
```bash
mkdir -p packages/{cicada-core,cicada-scip,cicada}/src
```

### 1.2 Setup workspace tooling
- Use `uv` workspaces (pyproject.toml at root)
- Each package gets its own pyproject.toml
- Shared dev dependencies at root

### 1.3 Root pyproject.toml
```toml
[project]
name = "cicada-workspace"
version = "0.1.0"

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
cicada-core = { workspace = true }
cicada-scip = { workspace = true }
cicada = { workspace = true }
```

## Phase 2: Extract cicada-core (Day 1-2)

### 2.1 Files to move
| From | To |
|------|-----|
| `cicada/parsing/base_indexer.py` | `packages/cicada-core/src/cicada_core/base_indexer.py` |
| `cicada/utils/hash_utils.py` | `packages/cicada-core/src/cicada_core/utils/hash_utils.py` |
| `cicada/utils/storage.py` | `packages/cicada-core/src/cicada_core/utils/storage.py` |

### 2.2 Simplify base_indexer.py
**CRITICAL**: Strip enrichment pipeline from BaseIndexer
- Keep only: ABC interface, `get_language_name()`, `get_file_extensions()`, `get_excluded_dirs()`, `index_repository()`
- Remove: `_run_enrichment_pipeline()`, `_compute_timestamps()`, `_extract_cochange()`, etc.
- These move to main cicada as post-processing

### 2.3 Create cicada-core pyproject.toml
```toml
[project]
name = "cicada-core"
version = "0.1.0"
dependencies = []  # Zero external deps!

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 2.4 Verify
```bash
cd packages/cicada-core && uv run python -c "from cicada_core import BaseIndexer"
```

## Phase 3: Extract cicada-scip (Day 2-3)

### 3.1 Files to move
| From | To |
|------|-----|
| `cicada/languages/scip/` | `packages/cicada-scip/src/cicada_scip/` |
| `cicada/languages/python/` | `packages/cicada-scip/src/cicada_scip/languages/python/` |
| `cicada/languages/typescript/` | `packages/cicada-scip/src/cicada_scip/languages/typescript/` |
| `cicada/languages/go/` | `packages/cicada-scip/src/cicada_scip/languages/go/` |
| ... all SCIP languages | ... |

### 3.2 Update imports
```python
# Before
from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.hash_utils import compute_file_hash

# After
from cicada_core import BaseIndexer
from cicada_core.utils.hash_utils import compute_file_hash
```

### 3.3 Remove enrichment from GenericSCIPIndexer
- `incremental_index_repository()` returns raw index (no keywords, timestamps, cochange)
- Enrichment becomes caller's responsibility
- This makes cicada-scip **pure parsing** with no ML/git deps

### 3.4 Create cicada-scip pyproject.toml
```toml
[project]
name = "cicada-scip"
version = "0.1.0"
dependencies = [
    "cicada-core",
    "protobuf>=4.0.0",
]

[project.optional-dependencies]
python = ["scip-python"]  # Optional per-language deps
typescript = ["scip-typescript"]
```

### 3.5 Tests
- Move `tests/languages/scip/` to `packages/cicada-scip/tests/`
- Update test imports
- Run: `cd packages/cicada-scip && uv run pytest`

## Phase 4: Refactor Main cicada (Day 3-4)

### 4.1 Move enrichment pipeline
Create new module: `packages/cicada/src/cicada/enrichment/pipeline.py`
```python
def enrich_index(
    index: dict,
    repo_path: Path,
    *,
    extract_keywords: bool = False,
    compute_timestamps: bool = False,
    extract_cochange: bool = False,
) -> dict:
    """Post-process a raw index with enrichments."""
    ...
```

### 4.2 Update LanguageRegistry
```python
# Make SCIP languages optional
try:
    from cicada_scip.languages import register_scip_languages
    register_scip_languages()
except ImportError:
    pass  # cicada-scip not installed
```

### 4.3 Update MCP handlers
```python
# index_manager.py
def refresh_index(...):
    indexer = get_indexer(language)
    raw_index = indexer.index_repository(repo_path, output_path)

    # Enrichment is now separate
    enriched = enrich_index(
        raw_index,
        repo_path,
        extract_keywords=True,
        compute_timestamps=True,
    )
    save_index(enriched, output_path)
```

### 4.4 Main cicada pyproject.toml
```toml
[project]
name = "cicada"
version = "0.1.0"
dependencies = [
    "cicada-core",
    # ... existing deps (mcp, gitpython, etc.)
]

[project.optional-dependencies]
scip = ["cicada-scip"]
all = ["cicada-scip", "keybert", ...]
```

## Phase 5: Update Build & CI (Day 4)

### 5.1 Root Makefile
```makefile
.PHONY: install test lint

install:
	uv sync --all-packages

test:
	uv run pytest packages/cicada-core/tests
	uv run pytest packages/cicada-scip/tests
	uv run pytest packages/cicada/tests

lint:
	uv run ruff check packages/
```

### 5.2 GitHub Actions
```yaml
jobs:
  test:
    strategy:
      matrix:
        package: [cicada-core, cicada-scip, cicada]
    steps:
      - run: cd packages/${{ matrix.package }} && uv run pytest
```

### 5.3 Publishing
- Each package published separately to PyPI
- Use `uv publish` or standard twine

## Phase 6: Cleanup (Day 5)

### 6.1 Remove old structure
```bash
rm -rf cicada/languages/scip
rm -rf cicada/languages/python  # SCIP version
rm -rf cicada/languages/typescript
# etc.
```

### 6.2 Update documentation
- README.md for each package
- Installation instructions: `pip install cicada[scip]`

### 6.3 Migration guide
Document for users:
```bash
# Before
pip install cicada-mcp

# After (with SCIP support)
pip install cicada[scip]

# Or minimal (no language indexing)
pip install cicada
```

## Risk Mitigation

### Keep escape hatch
During migration, keep old imports working via re-exports:
```python
# cicada/languages/scip/__init__.py (temporary)
from cicada_scip import SCIPReader, SCIPConverter  # Re-export
import warnings
warnings.warn("Import from cicada_scip directly", DeprecationWarning)
```

### Feature branch
Do all work on `feat/monorepo-split` branch, merge only when stable.

### Incremental PRs
1. PR1: Setup monorepo structure + cicada-core
2. PR2: Extract cicada-scip
3. PR3: Refactor main cicada + enrichment
4. PR4: CI/CD + publishing
5. PR5: Cleanup + docs

## Success Criteria

- [ ] `uv run pytest` passes for all packages
- [ ] `pip install cicada-core` works standalone
- [ ] `pip install cicada-scip` works with just cicada-core
- [ ] `pip install cicada[scip]` gives full functionality
- [ ] CI runs <5 minutes (parallel package testing)
- [ ] Each package <2000 lines (excluding tests)

## Timeline

| Day | Task |
|-----|------|
| 1 | Monorepo setup + cicada-core extraction |
| 2 | cicada-scip extraction (files + imports) |
| 3 | cicada-scip tests passing |
| 4 | Main cicada refactor (enrichment separation) |
| 5 | CI/CD + cleanup + docs |

Total: ~1 week for clean split
