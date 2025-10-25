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

from cicada.formatter import ModuleFormatter
from cicada.pr_finder import PRFinder


class CicadaServer:
    """MCP server for Elixir module search."""

    def __init__(self, config_path: str = ".cicada/config.yaml"):
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

        with open(config_file, "r") as f:
            return yaml.safe_load(f)

    def _load_index(self) -> dict:
        """Load the index from JSON file."""
        index_path = Path(self.config["storage"]["index_path"])

        if not index_path.exists():
            raise FileNotFoundError(
                f"Index file not found: {index_path}\n"
                f"Run 'python indexer.py --repo <path>' to create an index first."
            )

        with open(index_path, "r") as f:
            return json.load(f)

    async def list_tools(self) -> list[Tool]:
        """List available MCP tools."""
        return [
            Tool(
                name="search_module",
                description=(
                    "Search for an Elixir module by exact name or file path and return all its functions. "
                    "Provide either the full module name (e.g., 'MyApp.User') or a file path (e.g., 'lib/my_app/user.ex'). "
                    "Returns the module location, all public and private functions with "
                    "their signatures, argument names, types, and line numbers. "
                    "Output format defaults to Markdown with JSON as fallback."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "module_name": {
                            "type": "string",
                            "description": "Full module name to search (e.g., 'MyApp.User'). Provide either this or file_path.",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to an Elixir file (e.g., 'lib/my_app/user.ex'). Provide either this or module_name.",
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format: 'markdown' (default) or 'json'",
                            "enum": ["markdown", "json"],
                            "default": "markdown",
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="search_function",
                description=(
                    "Search for an Elixir function by name across all modules or in a specific module. "
                    "Supports multiple formats: 'function_name', 'function_name/arity' (searches all modules), "
                    "or 'Module.function_name', 'Module.function_name/arity' (searches specific module only). "
                    "Returns matching functions with their documentation, signatures, types, location, and call sites. "
                    "Output format defaults to Markdown with JSON as fallback."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "description": "Function name to search. Formats: 'create_user', 'create_user/2' (all modules), or 'MyApp.User.create_user', 'MyApp.User.create_user/2' (specific module)",
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format: 'markdown' (default) or 'json'",
                            "enum": ["markdown", "json"],
                            "default": "markdown",
                        },
                        "include_usage_examples": {
                            "type": "boolean",
                            "description": "Include actual code lines showing how the function is called (default: false)",
                            "default": False,
                        },
                        "max_examples": {
                            "type": "integer",
                            "description": "Maximum number of usage examples to show per function (default: 5)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                        },
                        "test_files_only": {
                            "type": "boolean",
                            "description": "Only show calls from test files (files with 'test' in their path) (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["function_name"],
                },
            ),
            Tool(
                name="search_module_usage",
                description=(
                    "Find where an Elixir module is used throughout the codebase. "
                    "Searches for all locations where the module is aliased/imported and called. "
                    "Returns the modules that import/alias the target module and the locations where its functions are called. "
                    "Output format defaults to Markdown with JSON as fallback."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "module_name": {
                            "type": "string",
                            "description": "Full module name to search for usage (e.g., 'MyApp.User')",
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format: 'markdown' (default) or 'json'",
                            "enum": ["markdown", "json"],
                            "default": "markdown",
                        },
                    },
                    "required": ["module_name"],
                },
            ),
            Tool(
                name="find_pr_for_line",
                description=(
                    "Find the pull request that introduced a specific line of code. "
                    "Provide a file path and line number to discover which PR created or modified that line. "
                    "Returns commit information, author details, and associated PR metadata. "
                    "Uses cached PR index for fast offline lookup when available."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (relative to repo root or absolute)",
                        },
                        "line_number": {
                            "type": "integer",
                            "description": "Line number (1-indexed)",
                            "minimum": 1,
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format: 'text' (default), 'json', or 'markdown'",
                            "enum": ["text", "json", "markdown"],
                            "default": "text",
                        },
                    },
                    "required": ["file_path", "line_number"],
                },
            ),
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        if name == "search_module":
            module_name = arguments.get("module_name")
            file_path = arguments.get("file_path")
            output_format = arguments.get("format", "markdown")

            # Validate that at least one is provided
            if not module_name and not file_path:
                error_msg = "Either 'module_name' or 'file_path' must be provided"
                return [TextContent(type="text", text=error_msg)]

            # If file_path is provided, resolve it to module_name
            if file_path:
                module_name = self._resolve_file_to_module(file_path)
                if not module_name:
                    error_msg = f"Could not find module in file: {file_path}"
                    return [TextContent(type="text", text=error_msg)]

            return await self._search_module(module_name, output_format)
        elif name == "search_function":
            function_name = arguments.get("function_name")
            output_format = arguments.get("format", "markdown")
            include_usage_examples = arguments.get("include_usage_examples", False)
            max_examples = arguments.get("max_examples", 5)
            test_files_only = arguments.get("test_files_only", False)

            if not function_name:
                error_msg = "'function_name' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self._search_function(
                function_name,
                output_format,
                include_usage_examples,
                max_examples,
                test_files_only,
            )
        elif name == "search_module_usage":
            module_name = arguments.get("module_name")
            output_format = arguments.get("format", "markdown")

            if not module_name:
                error_msg = "'module_name' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self._search_module_usage(module_name, output_format)
        elif name == "find_pr_for_line":
            file_path = arguments.get("file_path")
            line_number = arguments.get("line_number")
            output_format = arguments.get("format", "text")

            if not file_path:
                error_msg = "'file_path' is required"
                return [TextContent(type="text", text=error_msg)]

            if not line_number:
                error_msg = "'line_number' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self._find_pr_for_line(file_path, line_number, output_format)
        else:
            raise ValueError(f"Unknown tool: {name}")

    def _resolve_file_to_module(self, file_path: str) -> str | None:
        """Resolve a file path to a module name by searching the index."""
        # Normalize the file path (remove leading ./ and trailing whitespace)
        normalized_path = file_path.strip().lstrip("./")

        # Search through all modules to find one matching this file path
        for module_name, module_data in self.index["modules"].items():
            module_file = module_data["file"]

            # Check for exact match
            if module_file == normalized_path:
                return module_name

            # Also check if the provided path ends with the module file
            # (handles cases where user provides absolute path)
            if normalized_path.endswith(module_file):
                return module_name

            # Check if the module file ends with the provided path
            # (handles cases where user provides just filename or partial path)
            if module_file.endswith(normalized_path):
                return module_name

        return None

    async def _search_module(
        self, module_name: str, output_format: str = "markdown"
    ) -> list[TextContent]:
        """Search for a module and return its information."""
        # Exact match lookup
        if module_name in self.index["modules"]:
            data = self.index["modules"][module_name]

            if output_format == "json":
                result = ModuleFormatter.format_module_json(module_name, data)
            else:
                result = ModuleFormatter.format_module_markdown(module_name, data)

            return [TextContent(type="text", text=result)]

        # Module not found
        total_modules = self.index["metadata"]["total_modules"]

        if output_format == "json":
            error_result = ModuleFormatter.format_error_json(module_name, total_modules)
        else:
            error_result = ModuleFormatter.format_error_markdown(
                module_name, total_modules
            )

        return [TextContent(type="text", text=error_result)]

    async def _search_function(
        self,
        function_name: str,
        output_format: str = "markdown",
        include_usage_examples: bool = False,
        max_examples: int = 5,
        test_files_only: bool = False,
    ) -> list[TextContent]:
        """Search for a function across all modules and return matches with call sites."""
        # Parse the function name - supports multiple formats:
        # - "func_name" or "func_name/arity" (search all modules)
        # - "Module.func_name" or "Module.func_name/arity" (search specific module)
        target_module = None
        target_name = function_name
        target_arity = None

        # Check for Module.function format
        if "." in function_name:
            # Split on last dot to separate module from function
            parts = function_name.rsplit(".", 1)
            if len(parts) == 2:
                target_module = parts[0]
                target_name = parts[1]

        # Check for arity
        if "/" in target_name:
            parts = target_name.split("/")
            target_name = parts[0]
            try:
                target_arity = int(parts[1])
            except (ValueError, IndexError):
                pass

        # Search across all modules for function definitions
        results = []
        for module_name, module_data in self.index["modules"].items():
            # If target_module is specified, only search in that module
            if target_module and module_name != target_module:
                continue

            for func in module_data["functions"]:
                # Match by name and optionally arity
                if func["name"] == target_name:
                    if target_arity is None or func["arity"] == target_arity:
                        # Find call sites for this function
                        call_sites = self._find_call_sites(
                            target_module=module_name,
                            target_function=target_name,
                            target_arity=func["arity"],
                        )

                        # Filter for test files only if requested
                        if test_files_only:
                            call_sites = self._filter_test_call_sites(call_sites)

                        # Optionally include usage examples (actual code lines)
                        if include_usage_examples and call_sites:
                            # Consolidate call sites by calling module (one example per module)
                            consolidated_sites = self._consolidate_call_sites_by_module(
                                call_sites
                            )
                            # Limit the number of examples
                            limited_call_sites = consolidated_sites[:max_examples]
                            # Extract code lines for each call site
                            self._add_code_examples(limited_call_sites)
                        else:
                            limited_call_sites = call_sites

                        results.append(
                            {
                                "module": module_name,
                                "function": func,
                                "file": module_data["file"],
                                "call_sites": (
                                    limited_call_sites
                                    if include_usage_examples
                                    else call_sites
                                ),
                            }
                        )

        # Format results
        if output_format == "json":
            result = ModuleFormatter.format_function_results_json(
                function_name, results
            )
        else:
            result = ModuleFormatter.format_function_results_markdown(
                function_name, results
            )

        return [TextContent(type="text", text=result)]

    async def _search_module_usage(
        self, module_name: str, output_format: str = "markdown"
    ) -> list[TextContent]:
        """
        Search for all locations where a module is used (aliased/imported and called).

        Args:
            module_name: The module to search for (e.g., "MyApp.User")
            output_format: Output format ('markdown' or 'json')

        Returns:
            TextContent with usage information
        """
        # Check if the module exists in the index
        if module_name not in self.index["modules"]:
            error_msg = f"Module '{module_name}' not found in index."
            return [TextContent(type="text", text=error_msg)]

        usage_results = {
            "imports": [],  # Modules that alias/import the target module
            "function_calls": [],  # Direct function calls to the target module
        }

        # Search through all modules to find usage
        for caller_module, module_data in self.index["modules"].items():
            # Skip the module itself
            if caller_module == module_name:
                continue

            # Check aliases for imports
            aliases = module_data.get("aliases", {})
            for alias_name, full_module in aliases.items():
                if full_module == module_name:
                    usage_results["imports"].append(
                        {
                            "importing_module": caller_module,
                            "alias_name": alias_name,
                            "full_module": full_module,
                            "file": module_data["file"],
                        }
                    )

            # Check function calls
            calls = module_data.get("calls", [])
            module_calls = {}  # Track calls grouped by function

            for call in calls:
                call_module = call.get("module")

                # Resolve the call's module name using aliases
                if call_module:
                    resolved_module = aliases.get(call_module, call_module)

                    if resolved_module == module_name:
                        # Track which function is being called
                        func_key = f"{call['function']}/{call['arity']}"

                        if func_key not in module_calls:
                            module_calls[func_key] = {
                                "function": call["function"],
                                "arity": call["arity"],
                                "lines": [],
                                "alias_used": call_module if call_module != resolved_module else None,
                            }

                        module_calls[func_key]["lines"].append(call["line"])

            # Add call information if there are any calls
            if module_calls:
                usage_results["function_calls"].append(
                    {
                        "calling_module": caller_module,
                        "file": module_data["file"],
                        "calls": list(module_calls.values()),
                    }
                )

        # Format results
        if output_format == "json":
            result = ModuleFormatter.format_module_usage_json(module_name, usage_results)
        else:
            result = ModuleFormatter.format_module_usage_markdown(
                module_name, usage_results
            )

        return [TextContent(type="text", text=result)]

    def _add_code_examples(self, call_sites: list):
        """
        Add actual code lines to call sites.

        Args:
            call_sites: List of call site dictionaries to enhance with code examples

        Modifies call_sites in-place by adding 'code_line' key with the actual source code.
        Extracts complete function calls from opening '(' to closing ')'.
        """
        # Get the repo path from the index metadata (fallback to config if not available)
        repo_path_str = self.index.get("metadata", {}).get("repo_path")
        if not repo_path_str:
            # Fallback to config if available
            repo_path_str = self.config.get("repository", {}).get("path")

        if not repo_path_str:
            # Can't add examples without repo path
            return

        repo_path = Path(repo_path_str)

        for site in call_sites:
            file_path = repo_path / site["file"]
            line_number = site["line"]

            try:
                # Read all lines from the file
                with open(file_path, "r") as f:
                    lines = f.readlines()

                # Extract complete function call
                code_lines = self._extract_complete_call(lines, line_number)
                if code_lines:
                    site["code_line"] = code_lines
            except (FileNotFoundError, IOError, IndexError) as e:
                # If we can't read the file/line, just skip adding the code example
                pass

    def _extract_complete_call(self, lines: list[str], start_line: int) -> str | None:
        """
        Extract a complete function call starting from the given line.

        Args:
            lines: All lines from the file
            start_line: Line number where the call starts (1-indexed)

        Returns:
            Complete function call as a string, or None if extraction fails
        """
        if start_line < 1 or start_line > len(lines):
            return None

        # Start from the line where the call occurs (convert to 0-indexed)
        start_idx = start_line - 1

        # Collect lines for the complete call
        collected_lines = []
        paren_count = 0
        found_opening = False

        # Read lines starting from the call line
        for i in range(start_idx, len(lines)):
            line = lines[i].rstrip("\n")
            collected_lines.append(line)

            # Count parentheses to find the complete call
            for char in line:
                if char == "(":
                    paren_count += 1
                    found_opening = True
                elif char == ")":
                    paren_count -= 1

            # If we found an opening paren and count is back to 0, we have the complete call
            if found_opening and paren_count == 0:
                # Join the lines and return
                return "\n".join(collected_lines)

            # Safety limit: don't read more than 20 lines for a single call
            if len(collected_lines) >= 20:
                break

        # If we couldn't find a complete call, return what we have
        return "\n".join(collected_lines) if collected_lines else None

    def _find_call_sites(
        self, target_module: str, target_function: str, target_arity: int
    ) -> list:
        """
        Find all locations where a function is called.

        Args:
            target_module: The module containing the function (e.g., "MyApp.User")
            target_function: The function name (e.g., "create_user")
            target_arity: The function arity

        Returns:
            List of call sites with resolved module names
        """
        call_sites = []

        # Find the function definition line to filter out @spec/@doc
        function_def_line = None
        if target_module in self.index["modules"]:
            for func in self.index["modules"][target_module]["functions"]:
                if func["name"] == target_function and func["arity"] == target_arity:
                    function_def_line = func["line"]
                    break

        for caller_module, module_data in self.index["modules"].items():
            # Get aliases for this module to resolve calls
            aliases = module_data.get("aliases", {})

            # Check all calls in this module
            for call in module_data.get("calls", []):
                if call["function"] != target_function:
                    continue

                if call["arity"] != target_arity:
                    continue

                # Resolve the call's module name using aliases
                call_module = call.get("module")

                if call_module is None:
                    # Local call - check if it's in the same module
                    if caller_module == target_module:
                        # Filter out calls that are part of the function definition
                        # (@spec, @doc appear 1-5 lines before the def)
                        if (
                            function_def_line
                            and abs(call["line"] - function_def_line) <= 5
                        ):
                            continue

                        # Find the calling function
                        calling_function = self._find_function_at_line(
                            caller_module, call["line"]
                        )

                        call_sites.append(
                            {
                                "calling_module": caller_module,
                                "calling_function": calling_function,
                                "file": module_data["file"],
                                "line": call["line"],
                                "call_type": "local",
                            }
                        )
                else:
                    # Qualified call - resolve the module name
                    resolved_module = aliases.get(call_module, call_module)

                    # Check if this resolves to our target module
                    if resolved_module == target_module:
                        # Find the calling function
                        calling_function = self._find_function_at_line(
                            caller_module, call["line"]
                        )

                        call_sites.append(
                            {
                                "calling_module": caller_module,
                                "calling_function": calling_function,
                                "file": module_data["file"],
                                "line": call["line"],
                                "call_type": "qualified",
                                "alias_used": (
                                    call_module
                                    if call_module != resolved_module
                                    else None
                                ),
                            }
                        )

        return call_sites

    def _find_function_at_line(self, module_name: str, line: int) -> dict | None:
        """
        Find the function that contains a specific line number.

        Args:
            module_name: The module to search in
            line: The line number

        Returns:
            Dictionary with 'name' and 'arity', or None if not found
        """
        if module_name not in self.index["modules"]:
            return None

        module_data = self.index["modules"][module_name]

        # Find the function whose definition line is closest before the target line
        best_match = None
        for func in module_data["functions"]:
            func_line = func["line"]
            # The function must be defined before or at the line
            if func_line <= line:
                # Keep the closest one
                if best_match is None or func_line > best_match["line"]:
                    best_match = {
                        "name": func["name"],
                        "arity": func["arity"],
                        "line": func_line,
                    }

        return best_match

    def _consolidate_call_sites_by_module(self, call_sites: list) -> list:
        """
        Consolidate call sites by calling module, keeping only one example per module.
        Prioritizes keeping test files separate from regular code files.

        Args:
            call_sites: List of call site dictionaries

        Returns:
            Consolidated list with one call site per unique calling module
        """
        seen_modules = {}
        consolidated = []

        for site in call_sites:
            module = site["calling_module"]

            # If we haven't seen this module yet, add it
            if module not in seen_modules:
                seen_modules[module] = site
                consolidated.append(site)

        return consolidated

    def _filter_test_call_sites(self, call_sites: list) -> list:
        """
        Filter call sites to only include calls from test files.

        A file is considered a test file if 'test' appears anywhere in its path.

        Args:
            call_sites: List of call site dictionaries

        Returns:
            Filtered list containing only call sites from test files
        """
        return [site for site in call_sites if "test" in site["file"].lower()]

    async def _find_pr_for_line(
        self, file_path: str, line_number: int, output_format: str = "text"
    ) -> list[TextContent]:
        """
        Find the PR that introduced a specific line of code.

        Args:
            file_path: Path to the file
            line_number: Line number (1-indexed)
            output_format: Output format ('text', 'json', or 'markdown')

        Returns:
            TextContent with PR information
        """
        try:
            # Get repo path from config
            repo_path = self.config.get("repository", {}).get("path", ".")

            # Initialize PRFinder with index enabled by default
            pr_finder = PRFinder(
                repo_path=repo_path,
                use_index=True,
                index_path="data/pr_index.json",
                verbose=False,
            )

            # Find PR for the line
            result = pr_finder.find_pr_for_line(file_path, line_number)

            # Format the result
            formatted_result = pr_finder.format_result(result, output_format)

            return [TextContent(type="text", text=formatted_result)]

        except Exception as e:
            error_msg = f"Error finding PR: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
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
