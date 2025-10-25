#!/usr/bin/env python
"""
Cicada One-Command Setup Script.

Downloads the tool, indexes the repository, and creates .mcp.json configuration.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, cwd=cwd, capture_output=True, text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}", file=sys.stderr)
        print(f"Error: {e.stderr}", file=sys.stderr)
        raise


def check_python():
    """Check if Python 3.10+ is available."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(
            f"Error: Python 3.10+ required. Current: {version.major}.{version.minor}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"✓ Python {version.major}.{version.minor} detected")


def install_cicada(target_dir, github_url=None):
    """
    Install cicada from GitHub or use existing installation.

    Args:
        target_dir: Directory where cicada will be installed
        github_url: GitHub URL to clone from (optional)

    Returns:
        Path to the cicada installation
    """
    target_path = Path(target_dir).resolve()

    # If we're already in the cicada directory, use it
    current_dir = Path.cwd()
    if (current_dir / "cicada" / "mcp_server.py").exists():
        print(f"✓ Using existing cicada installation at {current_dir}")
        return current_dir

    # Check if target directory already has cicada
    if (target_path / "cicada" / "mcp_server.py").exists():
        print(f"✓ Using existing cicada installation at {target_path}")
        return target_path

    # Download from GitHub
    if github_url:
        print(f"Downloading cicada from {github_url}...")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        run_command(f"git clone {github_url} {target_path}")
        print(f"✓ Downloaded cicada to {target_path}")
    else:
        print("Error: cicada not found and no GitHub URL provided", file=sys.stderr)
        sys.exit(1)

    return target_path


def check_uv_available():
    """Check if uv is available on the system."""
    try:
        result = run_command("uv --version", check=False)
        return result.returncode == 0
    except Exception:
        return False


def install_dependencies_uv(cicada_dir):
    """Install Python dependencies using uv (fast!)."""
    print("Installing dependencies with uv...")

    # Use uv to sync dependencies
    # uv will automatically create a venv and install everything
    run_command(f"uv sync", cwd=cicada_dir)

    # Find the python binary uv created
    venv_path = cicada_dir / ".venv"
    python_bin = venv_path / "bin" / "python"

    if not python_bin.exists():
        # Try alternative venv location
        venv_path = cicada_dir / "venv"
        python_bin = venv_path / "bin" / "python"

    print("✓ Dependencies installed with uv")
    return python_bin


def install_dependencies_pip(cicada_dir):
    """Install Python dependencies using traditional pip."""
    print("Installing dependencies with pip...")

    # Check if venv exists
    venv_path = cicada_dir / "venv"
    python_bin = venv_path / "bin" / "python"

    if not venv_path.exists():
        print("Creating virtual environment...")
        run_command(f"python -m venv {venv_path}")

    # Install dependencies
    requirements_file = cicada_dir / "requirements.txt"
    if requirements_file.exists():
        run_command(f"{python_bin} -m pip install -r {requirements_file}")

    # Install package in editable mode
    run_command(f"{python_bin} -m pip install -e {cicada_dir}")

    print("✓ Dependencies installed with pip")
    return python_bin


def install_dependencies(cicada_dir, use_uv=None):
    """
    Install Python dependencies for cicada.

    Args:
        cicada_dir: Directory where cicada is installed
        use_uv: If True, use uv; if False, use pip; if None, auto-detect

    Returns:
        Path to python binary
    """
    # Auto-detect uv if not specified
    if use_uv is None:
        use_uv = check_uv_available()
        if use_uv:
            print("✓ Detected uv - will use it for faster installation")

    if use_uv:
        return install_dependencies_uv(cicada_dir)
    else:
        return install_dependencies_pip(cicada_dir)


def index_repository(cicada_dir, python_bin, repo_path, fetch_pr_info=False):
    """Index the Elixir repository."""
    print(f"Indexing repository at {repo_path}...")

    repo_path = Path(repo_path).resolve()
    output_path = repo_path / ".cicada" / "index.json"

    # Create .cicada directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Run indexer
    indexer_script = cicada_dir / "cicada" / "indexer.py"
    cmd = f"{python_bin} {indexer_script} {repo_path} --output {output_path}"

    if fetch_pr_info:
        cmd += " --pr-info"

    run_command(cmd)

    print(f"✓ Repository indexed at {output_path}")
    return output_path


def create_mcp_config(repo_path, cicada_dir, python_bin):
    """Create .mcp.json configuration file."""
    print("Creating .mcp.json configuration...")

    repo_path = Path(repo_path).resolve()
    mcp_config_path = repo_path / ".mcp.json"

    # Create configuration
    config = {
        "mcpServers": {
            "cicada": {
                "command": str(python_bin),
                "args": [str(cicada_dir / "cicada" / "mcp_server.py")],
                "cwd": str(cicada_dir),
                "env": {"CICADA_REPO_PATH": str(repo_path)},
            }
        }
    }

    # Write config file
    with open(mcp_config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✓ MCP configuration created at {mcp_config_path}")
    return mcp_config_path


def create_config_yaml(cicada_dir, repo_path, index_path):
    """Create or update config.yaml in cicada directory."""
    config_path = cicada_dir / "config.yaml"

    config_content = f"""repository:
  path: {repo_path}

storage:
  index_path: {index_path}
"""

    with open(config_path, "w") as f:
        f.write(config_content)

    print(f"✓ Config file created at {config_path}")


def main():
    """Main entry point for the setup script."""
    parser = argparse.ArgumentParser(
        description="One-command setup for Cicada MCP server",
        epilog="Example: python setup.py --repo /path/to/elixir/project",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the Elixir repository to index (default: current directory)",
    )
    parser.add_argument(
        "--cicada-dir",
        help="Directory where cicada is or will be installed (default: ~/.cicada)",
    )
    parser.add_argument(
        "--github-url",
        help="GitHub URL to clone cicada from (if not already installed)",
    )
    parser.add_argument(
        "--pr-info",
        action="store_true",
        help="Fetch PR information during indexing (requires GitHub CLI and may be slow)",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip installing dependencies (use if already installed)",
    )
    parser.add_argument(
        "--use-uv",
        action="store_true",
        help="Force use of uv for dependency installation (faster)",
    )
    parser.add_argument(
        "--use-pip",
        action="store_true",
        help="Force use of pip for dependency installation (traditional)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Cicada MCP Setup")
    print("=" * 60)

    # Check Python version
    check_python()

    # Determine cicada directory
    if args.cicada_dir:
        cicada_dir = Path(args.cicada_dir).resolve()
    else:
        # Use current directory if we're in cicada, otherwise use ~/.cicada
        current_dir = Path.cwd()
        if (current_dir / "cicada" / "mcp_server.py").exists():
            cicada_dir = current_dir
        else:
            cicada_dir = Path.home() / ".cicada"

    # Install or locate cicada
    cicada_dir = install_cicada(cicada_dir, args.github_url)

    # Install dependencies
    if not args.skip_install:
        # Determine which package manager to use
        use_uv = None
        if args.use_uv:
            use_uv = True
        elif args.use_pip:
            use_uv = False
        # Otherwise use_uv=None for auto-detect

        python_bin = install_dependencies(cicada_dir, use_uv=use_uv)
    else:
        # Try to find existing python binary
        python_bin = cicada_dir / ".venv" / "bin" / "python"
        if not python_bin.exists():
            python_bin = cicada_dir / "venv" / "bin" / "python"
        if not python_bin.exists():
            python_bin = sys.executable
        print(f"✓ Skipping dependency installation, using {python_bin}")

    # Index repository
    index_path = index_repository(cicada_dir, python_bin, args.repo, args.pr_info)

    # Create config.yaml
    create_config_yaml(cicada_dir, args.repo, index_path)

    # Create .mcp.json
    mcp_config_path = create_mcp_config(args.repo, cicada_dir, python_bin)

    print()
    print("=" * 60)
    print("✓ Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Configure Claude Code to use the MCP server:")
    print(f"   Add {mcp_config_path} to your Claude Code settings")
    print()
    print("2. Restart Claude Code")
    print()
    print("3. Try asking Claude Code:")
    print("   - 'What modules are in this project?'")
    print("   - 'Show me the functions in [ModuleName]'")
    print()


if __name__ == "__main__":
    main()
