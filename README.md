<div align="center">

<img src="cicada.png" alt="CICADA Logo" width="400"/>

# CICADA

### **C**ode **I**ntelligence: **C**ontextual **A**nalysis, **D**iscovery, and **A**ttribution

*Claude searches blindly. Be its guide.*

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Elixir](https://img.shields.io/badge/Elixir-Support-purple.svg)](https://elixir-lang.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

[Features](#features) •
[Installation](#installation) •
[Usage](#usage) •
[Documentation](#documentation) •
[Contributing](#contributing)

</div>

---

## Overview

CICADA is a Model Context Protocol (MCP) server that provides Claude Code with code intelligence for Elixir projects. It indexes your codebase using tree-sitter AST parsing and provides instant access to modules, functions, call sites, and PR attribution.

### Key Features

- Fast module and function search
- Call site tracking with line numbers
- PR attribution via git blame and GitHub CLI
- Tree-sitter based parsing
- MCP integration for Claude Code

---

## Installation

### Quick Install with UV (Recommended)

**Installing UV:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv
```

Using [uv](https://github.com/astral-sh/uv) (10-100x faster than pip):

```bash
# Install and configure in one command
cd /path/to/your/elixir/project
uvx --from git+https://github.com/wende/cicada.git cicada-setup --repo .
```

Or install as a persistent tool:

```bash
# Install once
uv tool install git+https://github.com/wende/cicada.git

# Use in any project
cd /path/to/elixir/project
cicada-setup --repo .
```

### Traditional Install

Without uv:

```bash
cd /path/to/your/elixir/project
python3 /path/to/cicada/install.py --repo .
```

### Manual Setup

For full control:

```bash
# Clone the repository
git clone https://github.com/wende/cicada.git
cd cicada

# Install dependencies
pip install -r requirements.txt

# Index your Elixir project
python -m cicada.indexer --repo /path/to/your/elixir/project

# Configure for Claude Code (see Configuration section)
```

---

## Quick Start

After installation, ask Claude Code:

```
"What functions are in the MyApp.User module?"
"Show me where authenticate/2 is called"
"Which PR introduced the Accounts module?"
"Find all usages of Repo.insert/2"
```

---

## MCP Tools

### `search_module`
Search for a module by exact name and retrieve all its functions.

**Parameters:**
- `module_name` (string, optional): Full module name (e.g., `"MyApp.User"`)
- `file_path` (string, optional): Path to Elixir file (e.g., `"lib/my_app/user.ex"`)
  - *Provide either `module_name` or `file_path`*
- `format` (string, default: `"markdown"`): Output format (`"markdown"` or `"json"`)
- `private_functions` (string, default: `"exclude"`): Control private function display
  - `"exclude"`: Hide private functions
  - `"include"`: Show all functions
  - `"only"`: Show only private functions

**Returns (Markdown):**
```
MyApp.User

lib/my_app/user.ex:1 • 12 public • 3 private

Public:

create_user(attrs: map) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()} — :42
get_user(id: integer) :: User.t() | nil — :58
...
```

**Returns (JSON):**
```json
{
  "module": "MyApp.User",
  "location": "lib/my_app/user.ex:1",
  "moduledoc": "User management module...",
  "counts": {"public": 12, "private": 3},
  "functions": [
    {
      "signature": "create_user(attrs: map) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}",
      "line": 42,
      "type": "def"
    }
  ]
}
```

### `search_function`
Find function definitions and see where they're called across the codebase.

**Parameters:**
- `function_name` (string, required): Function to search for
  - `"create_user"` - Search all modules
  - `"create_user/2"` - Search specific arity
  - `"MyApp.User.create_user"` - Search specific module
  - `"MyApp.User.create_user/2"` - Module + arity
- `format` (string, default: `"markdown"`): Output format (`"markdown"` or `"json"`)
- `include_usage_examples` (boolean, default: `false`): Include actual code lines showing usage
- `max_examples` (integer, default: `5`): Maximum usage examples to show (1-20)
- `test_files_only` (boolean, default: `false`): Only show calls from test files

**Returns (Markdown):**
```
# create_user/2

## MyApp.User.create_user/2
lib/my_app/user.ex:42

create_user(attrs: map, opts: keyword) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}

Creates a new user with the given attributes.

Called from 8 locations:
- MyApp.UserController.create/2 (lib/my_app_web/controllers/user_controller.ex:23)
- MyApp.Accounts.register/1 (lib/my_app/accounts.ex:15)
...
```

**Returns (JSON):**
```json
{
  "function_name": "create_user/2",
  "results": [
    {
      "module": "MyApp.User",
      "function": {
        "name": "create_user",
        "arity": 2,
        "line": 42,
        "signature": "create_user(attrs: map, opts: keyword)"
      },
      "file": "lib/my_app/user.ex",
      "call_sites": [
        {
          "calling_module": "MyApp.UserController",
          "calling_function": {"name": "create", "arity": 2},
          "file": "lib/my_app_web/controllers/user_controller.ex",
          "line": 23
        }
      ]
    }
  ]
}
```

### `search_module_usage`
Find everywhere a module is used in the codebase (aliases, imports, and function calls).

**Parameters:**
- `module_name` (string, required): Full module name (e.g., `"MyApp.User"`)
- `format` (string, default: `"markdown"`): Output format (`"markdown"` or `"json"`)

**Returns (Markdown):**
```
# MyApp.User Usage

## Aliases (5)
- MyApp.UserController (lib/my_app_web/controllers/user_controller.ex)
  alias MyApp.User
- MyApp.Accounts (lib/my_app/accounts.ex)
  alias MyApp.User

## Function Calls (3 modules)
- MyApp.UserController (lib/my_app_web/controllers/user_controller.ex)
  • create_user/2 at lines: 23, 45
  • get_user/1 at lines: 12
...
```

**Returns (JSON):**
```json
{
  "module": "MyApp.User",
  "usage": {
    "aliases": [
      {
        "importing_module": "MyApp.UserController",
        "alias_name": "User",
        "file": "lib/my_app_web/controllers/user_controller.ex"
      }
    ],
    "function_calls": [
      {
        "calling_module": "MyApp.UserController",
        "file": "lib/my_app_web/controllers/user_controller.ex",
        "calls": [
          {
            "function": "create_user",
            "arity": 2,
            "lines": [23, 45]
          }
        ]
      }
    ]
  }
}
```

### `find_pr_for_line`
Discover which pull request introduced a specific line of code.

**Parameters:**
- `file_path` (string, required): Path to file (relative to repo root or absolute)
- `line_number` (integer, required): Line number (1-indexed, minimum: 1)
- `format` (string, default: `"text"`): Output format (`"text"`, `"json"`, or `"markdown"`)

**Returns (Text):**
```
PR #123: Add user authentication
Author: John Doe <john@example.com>
Commit: abc123def456
Date: 2024-01-15
URL: https://github.com/org/repo/pull/123
```

**Returns (JSON):**
```json
{
  "pr_number": 123,
  "pr_title": "Add user authentication",
  "author": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "commit": {
    "sha": "abc123def456",
    "message": "Add user authentication module"
  },
  "date": "2024-01-15",
  "url": "https://github.com/org/repo/pull/123"
}
```

---

## Configuration

### Project Configuration (`.mcp.json`)

Created automatically by the setup script:

```json
{
  "mcpServers": {
    "cicada": {
      "command": "python",
      "args": ["/absolute/path/to/cicada/cicada/mcp_server.py"],
      "cwd": "/absolute/path/to/cicada",
      "env": {
        "CICADA_INDEX_PATH": "/path/to/project/.cicada/index.json"
      }
    }
  }
}
```

### Setup Options

```bash
# Basic setup
cicada-setup --repo .

# Include PR information (requires GitHub CLI)
cicada-setup --repo . --pr-info

# Skip dependency installation
cicada-setup --repo . --skip-install

# Custom installation directory
cicada-setup --repo . --cicada-dir /custom/path
```

### Re-indexing

After code changes, re-index your project:

```bash
# Quick re-index (uses existing installation)
cicada-setup --repo . --skip-install

# Or use the indexer directly
cicada-index --repo . --output .cicada/index.json
```

---

## Roadmap

### v0 (Current)
- Module and function search
- Call site tracking
- PR attribution
- Basic MCP integration

### v0.1 (Planned)
- Enhanced test detection with confidence scoring
- Documentation search in markdown files
- Git commit history integration
- Usage pattern extraction

### v0.2 (Future)
- Comprehensive context aggregation
- Implementation guidance (error patterns, conventions)
- Improved fuzzy search capabilities
- Multi-repository support

### Long Term
- Multi-language support (Python, TypeScript, Rust)
- Semantic code search
- Real-time incremental indexing
- Web UI for exploration

---

## Limitations (v0)

Current limitations:
- Exact match only (no fuzzy search)
- Direct call tracking only (not comprehensive call graphs)
- No automatic documentation file search
- No function similarity suggestions
- No usage convention extraction

These features may be added in future versions.

---

## Contributing

### Development Setup

```bash
# Clone your fork
git clone https://github.com/wende/cicada.git
cd cicada

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with test dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Testing

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_parser.py
pytest tests/test_search_function.py

# Run with coverage
pytest --cov=cicada --cov-report=html
```

### Code Style

This project uses:
- **black** for code formatting
- **pytest** for testing
- **type hints** where appropriate

Before submitting a PR:
```bash
# Format code
black cicada tests

# Run tests
pytest

# Check types (if using mypy)
mypy cicada
```

### Reporting Issues

When reporting bugs or requesting features:

1. Check existing [Issues](https://github.com/wende/cicada/issues)
2. If not found, create a new issue with:
   - Clear description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Your environment (OS, Python version, Elixir version)

---

## Troubleshooting

### "Index file not found"

Run the indexer first:
```bash
cicada-index --repo /path/to/project
```

### "Module not found"

Use the exact module name as it appears in code (e.g., `MyApp.User`, not `User`).

### MCP Server Won't Connect

1. Verify `.mcp.json` exists in your project root
2. Check that all paths in `.mcp.json` are absolute
3. Ensure `index.json` was created successfully
4. Restart Claude Code
5. Check Claude Code logs for errors

### PR Information Not Working

PR attribution requires GitHub CLI:
```bash
# Install GitHub CLI
brew install gh  # macOS
# or visit https://cli.github.com/

# Authenticate
gh auth login

# Re-run indexer with PR info
cicada-index --repo . --fetch-pr-info
```

#### Uninstall

Remove CICADA from a project:

```bash
rm -rf .cicada/ .mcp.json
# Restart Claude Code
```

---

## Credits

### Built With

- [Tree-sitter](https://tree-sitter.github.io/) - Incremental parsing system
- [tree-sitter-elixir](https://github.com/elixir-lang/tree-sitter-elixir) - Elixir grammar
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [GitHub CLI](https://cli.github.com/) - PR attribution

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- The Anthropic team for Claude Code and MCP
- The Elixir community for tree-sitter-elixir
- All contributors who help improve CICADA

---

<div align="center">

**[⬆ back to top](#cicada)**

</div>
