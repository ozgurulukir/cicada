# PR Indexing - Fast Offline PR Lookups

The PR indexing system allows you to find which pull request introduced any line of code without making network requests at query time.

## How It Works

1. **Indexing** (one-time or periodic):
   - Fetches all PRs from GitHub via `gh` CLI
   - For each PR, stores commits and files changed
   - Builds a commit → PR lookup table
   - Saves everything to `data/pr_index.json`

2. **Lookup** (fast, offline):
   - Runs `git blame` to find commit SHA (local, fast)
   - Looks up commit in the index
   - Returns PR info instantly (no network!)

## Quick Start

### 1. Index Your Repository

```bash
# Full index (first time)
python cicada/pr_indexer.py /path/to/your/repo

# Incremental update (faster, only new PRs)
python cicada/pr_indexer.py /path/to/your/repo --incremental
```

### 2. Find PR for a Line

```bash
# Uses index by default (fast, no network)
python cicada/pr_finder.py README.md 1

# Different output formats
python cicada/pr_finder.py README.md 1 --format markdown
python cicada/pr_finder.py README.md 1 --format json

# Disable index and use network instead
python cicada/pr_finder.py README.md 1 --no-index
```

## Index Structure

The index file (`data/pr_index.json`) contains:

```json
{
  "metadata": {
    "repo_owner": "wende",
    "repo_name": "cicada",
    "last_indexed_at": "2025-10-25T13:00:00Z",
    "total_prs": 50,
    "total_commits_mapped": 250,
    "last_pr_number": 123
  },
  "prs": {
    "42": {
      "number": 42,
      "title": "Add new feature",
      "url": "https://github.com/wende/cicada/pull/42",
      "state": "closed",
      "merged": true,
      "author": "wende",
      "commits": ["c1f9203...", "abc123..."],
      "files_changed": ["README.md", "src/main.py"]
    }
  },
  "commit_to_pr": {
    "c1f9203cb832203f84da0f9766bde205f60a7aa3": 42
  }
}
```

## CLI Reference

### pr_indexer.py

Index all pull requests from a GitHub repository.

**Arguments:**
- `repo` - Path to git repository (default: current directory)

**Options:**
- `--output PATH` - Output path for index file (default: data/pr_index.json)
- `--incremental` - Only fetch new PRs since last index (faster)

**Examples:**
```bash
# Full index
python cicada/pr_indexer.py .

# Incremental update
python cicada/pr_indexer.py . --incremental

# Custom output path
python cicada/pr_indexer.py . --output /path/to/pr_index.json
```

### pr_finder.py

Find the PR that introduced a specific line of code.

**Arguments:**
- `file` - Path to the file
- `line` - Line number (1-indexed)

**Options:**
- `--format {text,json,markdown}` - Output format (default: text)
- `--no-index` - Disable index and use network instead
- `--index-path PATH` - Path to PR index file (default: data/pr_index.json)

**Examples:**
```bash
# Basic usage (uses index)
python cicada/pr_finder.py README.md 1

# Markdown output
python cicada/pr_finder.py README.md 68 --format markdown

# Use network instead of index
python cicada/pr_finder.py README.md 1 --no-index

# Custom index path
python cicada/pr_finder.py README.md 1 --index-path /custom/path/pr_index.json
```

## Performance

- **Indexing**: ~10 PRs/second (GitHub API rate limited)
- **Lookup**: ~0.1 seconds (git blame + index lookup, no network!)
- **Index size**: ~1KB per PR on average

## Incremental Updates

The indexer supports incremental updates to minimize API calls:

```bash
# First time: index all PRs
python cicada/pr_indexer.py .

# Later: only fetch new PRs since last index
python cicada/pr_indexer.py . --incremental
```

The index tracks `last_pr_number` and only fetches PRs with higher numbers.

## Use as a Library

### Indexing

```python
from cicada.pr_indexer import PRIndexer

indexer = PRIndexer(repo_path="/path/to/repo")
index = indexer.index_repository(
    output_path="data/pr_index.json",
    incremental=True
)
```

### Lookup

```python
from cicada.pr_finder import PRFinder

# With index (fast, offline)
finder = PRFinder(repo_path=".", use_index=True)
result = finder.find_pr_for_line("README.md", 68)

# Without index (network, slower)
finder = PRFinder(repo_path=".", use_index=False)
result = finder.find_pr_for_line("README.md", 68)

# Format output
print(finder.format_result(result, "markdown"))
```

## Requirements

- GitHub CLI (`gh`) installed and authenticated
- Git repository with GitHub remote
- Python 3.7+

## Troubleshooting

**"Not a GitHub repository"**
- Ensure the repository has a GitHub remote configured
- Run `gh repo view` to verify GitHub CLI can access the repo

**"PR index not found"**
- Run `python cicada/pr_indexer.py .` to create the index
- Check that `data/pr_index.json` exists

**"GitHub CLI not found"**
- Install GitHub CLI: https://cli.github.com/
- Authenticate: `gh auth login`

## Rate Limits

GitHub API has rate limits:
- Authenticated: 5,000 requests/hour
- The indexer fetches ~3 requests per PR (list + commits + files)
- Use `--incremental` for subsequent updates to minimize API calls
