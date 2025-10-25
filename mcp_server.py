#!/usr/bin/env python
"""
Cicada MCP Server - Elixir Module Search.

Provides an MCP tool to search for Elixir modules and their functions.
"""

import json
import sys
from pathlib import Path

import yaml
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


class CicadaServer:
    """MCP server for Elixir module search."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the server with configuration."""
        self.config = self._load_config(config_path)
        self.index = self._load_index()
        self.server = Server("cicada")

        # Register handlers
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def _load_index(self) -> dict:
        """Load the index from JSON file."""
        index_path = Path(self.config['storage']['index_path'])

        if not index_path.exists():
            raise FileNotFoundError(
                f"Index file not found: {index_path}\n"
                f"Run 'python indexer.py --repo <path>' to create an index first."
            )

        with open(index_path, 'r') as f:
            return json.load(f)

    async def list_tools(self) -> list[Tool]:
        """List available MCP tools."""
        return [
            Tool(
                name="search_module",
                description=(
                    "Search for an Elixir module by exact name and return all its functions. "
                    "Provide the full module name (e.g., 'MyApp.User'). "
                    "Returns the module location, all public and private functions with "
                    "their signatures, arities, and line numbers."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "module_name": {
                            "type": "string",
                            "description": "Full module name to search (e.g., 'MyApp.User')"
                        }
                    },
                    "required": ["module_name"]
                }
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        if name == "search_module":
            return await self._search_module(arguments["module_name"])
        else:
            raise ValueError(f"Unknown tool: {name}")

    async def _search_module(self, module_name: str) -> list[TextContent]:
        """Search for a module and return its information."""
        # Exact match lookup
        if module_name in self.index['modules']:
            result = self._format_module(module_name)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # Module not found
        error_result = {
            "error": "Module not found",
            "query": module_name,
            "hint": "Use the exact module name as it appears in the code",
            "total_modules_available": self.index['metadata']['total_modules']
        }
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

    def _format_module(self, module_name: str) -> dict:
        """Format module data for response."""
        data = self.index['modules'][module_name]

        return {
            "module": module_name,
            "file": data['file'],
            "line": data['line'],
            "functions": data['functions'],
            "summary": {
                "total": data['total_functions'],
                "public": data['public_functions'],
                "private": data['private_functions']
            }
        }

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    try:
        server = CicadaServer()
        await server.run()
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
