# Cicada v0

**Elixir Module Search for Claude Code**

Cicada is an MCP (Model Context Protocol) server that enables Claude Code to search and explore Elixir codebases. It indexes your Elixir project and provides instant access to module and function information.

## Features

- **Fast Indexing**: Quickly indexes Elixir projects using tree-sitter AST parsing
- **Module Search**: Search for modules by exact name
- **Function Details**: Get complete function listings with arities, signatures, and line numbers
- **Public/Private Tracking**: Distinguishes between public (`def`) and private (`defp`) functions
- **MCP Integration**: Works seamlessly with Claude Code via MCP

## Quick Start

### 1. Setup

This project uses [asdf](https://asdf-vm.com/) for version management.

```bash
# Install Python
asdf install

# Install dependencies
pip install -r requirements.txt
```

### 2. Index Your Elixir Project

```bash
python indexer.py --repo /path/to/your/elixir/project
```

This creates `data/index.json` containing all modules and functions.

### 3. Configure

Edit `config.yaml` with your project path:

```yaml
repository:
  path: /path/to/your/elixir/project

storage:
  index_path: ./data/index.json
```

### 4. Configure Claude Code

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "cicada": {
      "command": "python",
      "args": ["/absolute/path/to/cicada/mcp_server.py"],
      "cwd": "/absolute/path/to/cicada"
    }
  }
}
```

### 5. Use with Claude Code

Ask Claude Code questions like:
- "What functions are in the AB.Generators module?"
- "Show me the User module"
- "What's in MyApp.Repo?"

## Architecture

```
┌─────────────────────┐
│   Claude Code       │
└──────────┬──────────┘
           │ MCP
┌──────────▼──────────┐
│   mcp_server.py     │
│   • search_module   │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   index.json        │
│   {modules: {...}}  │
└─────────────────────┘
```

## Components

### Parser (`parser.py`)
Uses tree-sitter to parse Elixir source files and extract:
- Module names
- Function names and arities
- Public vs private functions
- Line numbers and signatures

### Indexer (`indexer.py`)
Walks your Elixir repository and builds a complete index:
- Processes all `.ex` and `.exs` files
- Excludes `deps/`, `_build/`, etc.
- Generates `data/index.json`

### MCP Server (`mcp_server.py`)
Serves the `search_module` tool via MCP:
- Loads index into memory
- Handles exact module name lookups
- Returns formatted module data

## Index Structure

```json
{
  "modules": {
    "MyApp.User": {
      "file": "lib/myapp/user.ex",
      "line": 1,
      "functions": [
        {
          "name": "authenticate",
          "arity": 2,
          "full_name": "authenticate/2",
          "line": 42,
          "signature": "def authenticate",
          "type": "def"
        }
      ],
      "total_functions": 5,
      "public_functions": 3,
      "private_functions": 2
    }
  },
  "metadata": {
    "indexed_at": "2025-10-25T10:30:00",
    "total_modules": 45,
    "total_functions": 320,
    "repo_path": "/path/to/repo"
  }
}
```

## Testing

### Run Parser Tests
```bash
python test_parser.py
```

### Run End-to-End Tests
```bash
python test_e2e.py
```

### Test Parser on a File
```bash
python parser.py test_fixtures/sample.ex
```

## Development

### Re-index After Code Changes
```bash
python indexer.py --repo /path/to/your/elixir/project
```

### Custom Output Path
```bash
python indexer.py --repo /path/to/project --output custom/index.json
```

## Limitations (v0)

This is a minimal v0 implementation. It does NOT:
- Track function calls or call graphs
- Show git history
- Find tests
- Search documentation
- Provide fuzzy search (exact match only)

These features may come in future versions.

## Troubleshooting

### "Index file not found"
Run the indexer first: `python indexer.py --repo /path/to/project`

### "Module not found"
Use the exact module name as it appears in the code (e.g., `MyApp.User`, not `User`)

### MCP server won't connect
- Ensure absolute paths in MCP config
- Check that index.json exists
- Verify Python dependencies are installed

## Project Structure

```
cicada/
├── data/                  # Generated index files (gitignored)
├── test_fixtures/         # Test Elixir files
├── parser.py             # Tree-sitter Elixir parser
├── indexer.py            # Repository indexer
├── mcp_server.py         # MCP server
├── config.yaml           # Configuration
├── test_parser.py        # Parser unit tests
├── test_e2e.py           # Integration tests
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## License

MIT

---

**Version:** v0 - Bare Minimum Module Search
**Status:** Production Ready
**Lines of Code:** ~350
