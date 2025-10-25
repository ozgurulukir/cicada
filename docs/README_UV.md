# Cicada Installation with UV

The fastest way to install and set up Cicada using [uv](https://github.com/astral-sh/uv).

## One-Command Install

Install directly from GitHub and run setup:

```bash
# Install from GitHub and run setup in current directory
uvx --from git+https://github.com/YOUR_USERNAME/cicada.git cicada-setup --repo .
```

Or install as a tool and use repeatedly:

```bash
# Install once
uv tool install git+https://github.com/YOUR_USERNAME/cicada.git

# Run setup in any Elixir project
cd /path/to/elixir/project
cicada-setup --repo .
```

## What This Does

The command will:
1. Download Cicada from GitHub
2. Install all dependencies (super fast with uv!)
3. Index your Elixir repository
4. Create `.cicada/index.json` with all modules and functions
5. Create `.mcp.json` for Claude Code

## Available Commands

After installation with `uv tool install`:

```bash
# Run setup in a project
cicada-setup --repo /path/to/project

# Re-index a project
cicada-index /path/to/project --output .cicada/index.json

# Run the MCP server directly
cicada-server
```

## Options

```bash
# Include PR information
cicada-setup --repo . --pr-info

# Use custom cicada directory
cicada-setup --repo . --cicada-dir ~/.cicada

# Skip dependency installation
cicada-setup --repo . --skip-install
```

## For Local Development

If you're developing Cicada locally:

```bash
# Install in editable mode
cd /path/to/cicada
uv pip install -e .

# Run setup
cicada-setup --repo /path/to/elixir/project
```

## Why UV?

- **Fast**: 10-100x faster than pip
- **Simple**: Single command installation
- **Isolated**: Tools don't interfere with system Python
- **Modern**: Better dependency resolution

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) installed

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Comparison

| Method | Speed | Command |
|--------|-------|---------|
| **UV (recommended)** | ⚡️ Fast | `uvx --from git+https://github.com/USER/cicada.git cicada-setup --repo .` |
| Traditional pip | 🐌 Slow | `python setup.py --repo .` |
| Manual | 🐌 Slowest | Multiple commands |
