# cicada-core

Core utilities and interfaces for Cicada code intelligence packages.

## Installation

```bash
pip install cicada-core
```

## Usage

```python
from cicada_core import BaseIndexer
from cicada_core.utils import get_storage_dir, compute_file_hash
```

## Components

- `BaseIndexer`: Abstract base class for all language indexers
- `utils.storage`: Storage path management (`~/.cicada/projects/`)
- `utils.hash_utils`: File hashing for incremental indexing

## License

MIT
