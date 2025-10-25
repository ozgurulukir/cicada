#!/usr/bin/env python
"""
Formatter Module - Formats module search results in various formats.

This module provides formatting utilities for Cicada MCP server responses,
supporting both Markdown and JSON output formats.
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import argparse


class ModuleFormatter:
    """Formats Cicada module data in various output formats."""

    @staticmethod
    def _format_function_signature(func: Dict[str, Any]) -> str:
        """
        Format function signature with arguments and types.

        Args:
            func: Function dictionary with name, args, and optionally args_with_types

        Returns:
            Formatted signature like "func_name(arg1: type1, arg2: type2)" or "func_name/arity"
        """
        func_name = func["name"]

        # If we have args_with_types, use that
        if "args_with_types" in func and func["args_with_types"]:
            args_str = ", ".join(
                [
                    f"{arg['name']}: {arg['type']}" if arg["type"] else arg["name"]
                    for arg in func["args_with_types"]
                ]
            )
            return f"{func_name}({args_str})"

        # Otherwise, fallback to args without types
        elif "args" in func and func["args"]:
            args_str = ", ".join(func["args"])
            return f"{func_name}({args_str})"

        # No args, just show function name with empty parens or /0
        elif func["arity"] == 0:
            return f"{func_name}()"

        # Fallback to name/arity
        return f"{func_name}/{func['arity']}"

    @staticmethod
    def _group_functions_by_name_arity(
        funcs: list[Dict[str, Any]],
    ) -> Dict[tuple, list[Dict[str, Any]]]:
        """
        Group functions by their name and arity.

        Args:
            funcs: List of function dictionaries

        Returns:
            Dictionary mapping (name, arity) tuples to lists of function clauses
        """
        grouped = {}
        for func in funcs:
            key = (func["name"], func["arity"])
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(func)
        return grouped

    @staticmethod
    def format_module_markdown(module_name: str, data: Dict[str, Any], private_functions: str = "exclude") -> str:
        """
        Format module data as Markdown.

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index
            private_functions: How to handle private functions: 'exclude' (hide), 'include' (show all), or 'only' (show only private)

        Returns:
            Formatted Markdown string
        """
        # Group functions by type (def = public, defp = private)
        public_funcs = [f for f in data["functions"] if f["type"] == "def"]
        private_funcs = [f for f in data["functions"] if f["type"] == "defp"]

        # Group by name/arity to deduplicate function clauses
        public_grouped = ModuleFormatter._group_functions_by_name_arity(public_funcs)
        private_grouped = ModuleFormatter._group_functions_by_name_arity(private_funcs)

        # Count unique functions, not function clauses
        public_count = len(public_grouped)
        private_count = len(private_grouped)

        # Build the markdown output - compact format
        lines = [
            module_name,
            "",
            f"{data['file']}:{data['line']} • {public_count} public • {private_count} private",
        ]

        # Add moduledoc if present (first paragraph only for brevity)
        if data.get("moduledoc"):
            doc = data["moduledoc"].strip()
            # Get first paragraph (up to double newline or first 200 chars)
            first_para = doc.split("\n\n")[0].strip()
            if len(first_para) > 200:
                first_para = first_para[:200] + "..."
            lines.extend(["", first_para])

        # Show public functions (unless private_functions == "only")
        if public_grouped and private_functions != "only":
            lines.extend(["", "Public:", ""])
            for (name, arity), clauses in sorted(public_grouped.items()):
                # Use the first clause for display (they all have same name/arity)
                func = clauses[0]
                func_sig = ModuleFormatter._format_function_signature(func)
                lines.append(f"{func_sig} — :{func['line']}")

        # Show private functions (if private_functions == "include" or "only")
        if private_grouped and private_functions in ["include", "only"]:
            lines.extend(["", "Private:", ""])
            for (name, arity), clauses in sorted(private_grouped.items()):
                # Use the first clause for display (they all have same name/arity)
                func = clauses[0]
                func_sig = ModuleFormatter._format_function_signature(func)
                lines.append(f"{func_sig} — :{func['line']}")

        # Check if there are no functions to display based on the filter
        has_functions_to_show = (
            (private_functions != "only" and public_grouped) or
            (private_functions in ["include", "only"] and private_grouped)
        )

        if not has_functions_to_show:
            if private_functions == "only" and not private_grouped:
                lines.extend(["", "*No private functions found*"])
            elif not data["functions"]:
                lines.extend(["", "*No functions found*"])

        return "\n".join(lines)

    @staticmethod
    def format_module_json(module_name: str, data: Dict[str, Any], private_functions: str = "exclude") -> str:
        """
        Format module data as JSON.

        Args:
            module_name: The name of the module
            data: The module data dictionary from the index
            private_functions: How to handle private functions: 'exclude' (hide), 'include' (show all), or 'only' (show only private)

        Returns:
            Formatted JSON string
        """
        # Filter functions based on private_functions parameter
        if private_functions == "exclude":
            # Only public functions
            filtered_funcs = [f for f in data["functions"] if f["type"] == "def"]
        elif private_functions == "only":
            # Only private functions
            filtered_funcs = [f for f in data["functions"] if f["type"] == "defp"]
        else:  # "include"
            # All functions
            filtered_funcs = data["functions"]

        # Group functions by name/arity to deduplicate function clauses
        grouped = ModuleFormatter._group_functions_by_name_arity(filtered_funcs)

        # Compact function format - one entry per unique name/arity
        functions = [
            {
                "signature": ModuleFormatter._format_function_signature(clauses[0]),
                "line": clauses[0]["line"],
                "type": clauses[0]["type"],
            }
            for (name, arity), clauses in sorted(grouped.items())
        ]

        result = {
            "module": module_name,
            "location": f"{data['file']}:{data['line']}",
            "moduledoc": data.get("moduledoc"),
            "counts": {
                "public": data["public_functions"],
                "private": data["private_functions"],
            },
            "functions": functions,
        }
        return json.dumps(result, indent=2)

    @staticmethod
    def format_error_markdown(module_name: str, total_modules: int) -> str:
        """
        Format error message as Markdown.

        Args:
            module_name: The queried module name
            total_modules: Total number of modules in the index

        Returns:
            Formatted Markdown error message
        """
        return f"""# Module Not Found

**Query:** `{module_name}`

The module `{module_name}` was not found in the index.

## Suggestions

- Verify the exact module name as it appears in the code
- Check that the module is part of the indexed codebase
- Total modules available in index: **{total_modules}**

## Note

Module names are case-sensitive and must match exactly (e.g., `MyApp.User`, not `myapp.user`).
"""

    @staticmethod
    def format_error_json(module_name: str, total_modules: int) -> str:
        """
        Format error message as JSON.

        Args:
            module_name: The queried module name
            total_modules: Total number of modules in the index

        Returns:
            Formatted JSON error message
        """
        error_result = {
            "error": "Module not found",
            "query": module_name,
            "hint": "Use the exact module name as it appears in the code",
            "total_modules_available": total_modules,
        }
        return json.dumps(error_result, indent=2)

    @staticmethod
    def format_function_results_markdown(
        function_name: str, results: list[Dict[str, Any]]
    ) -> str:
        """
        Format function search results as Markdown.

        Args:
            function_name: The searched function name
            results: List of function matches with module context

        Returns:
            Formatted Markdown string
        """
        if not results:
            return f"""# Function Not Found

**Query:** `{function_name}`

No functions matching `{function_name}` were found in the index.

## Suggestions

- Verify the function name spelling
- Try searching without arity (e.g., 'create_user' instead of 'create_user/2')
- Check that the function is part of the indexed codebase
"""

        # For single results (e.g., MFA search), use simpler header
        if len(results) == 1:
            lines = [
                f"⎿ # `{results[0]['module']}.{results[0]['function']['name']}/{results[0]['function']['arity']}`"
            ]
        else:
            lines = [
                f"# Functions matching `{function_name}`",
                f"",
                f"Found **{len(results)}** match(es):",
            ]

        for result in results:
            module_name = result["module"]
            func = result["function"]
            file_path = result["file"]

            # Skip the section header for single results
            if len(results) == 1:
                lines.extend(["", f"  `{file_path}:{func['line']}`"])
            else:
                lines.extend(
                    [
                        "",
                        "---",
                        "",
                        f"## `{module_name}.{func['name']}/{func['arity']}`",
                    ]
                )
                lines.append(f"`{file_path}:{func['line']}` • {func['type']}")

            # Add documentation if present
            if func.get("doc"):
                lines.extend(["", "**Documentation:**", "", func["doc"]])

            # Add signature
            sig = ModuleFormatter._format_function_signature(func)
            if len(results) == 1:
                lines.extend([f"  {func['type']} {sig}", ""])
            else:
                lines.extend(["", "**Signature:**", "", f"```", f"{sig}", "```"])

            # Add call sites
            call_sites = result.get("call_sites", [])
            indent = "  " if len(results) == 1 else ""

            if call_sites:
                # Check if we have usage examples (code lines)
                has_examples = any("code_line" in site for site in call_sites)

                if has_examples:
                    # Separate into code and test call sites
                    code_sites = [
                        s for s in call_sites if "test" not in s["file"].lower()
                    ]
                    test_sites = [s for s in call_sites if "test" in s["file"].lower()]

                    lines.append(f"{indent}**Usage Examples:**")

                    if code_sites:
                        lines.append(f"{indent}  Code ({len(code_sites)}):")
                        for site in code_sites:
                            # Format calling location with function if available
                            calling_func = site.get("calling_function")
                            if calling_func:
                                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
                            else:
                                caller = site["calling_module"]

                            lines.append(
                                f"{indent}  - `{caller}` at `{site['file']}:{site['line']}`"
                            )

                            # Add the actual code line if available
                            if "code_line" in site:
                                lines.append(f"{indent}    ```")
                                lines.append(f"{indent}    {site['code_line']}")
                                lines.append(f"{indent}    ```")

                    if test_sites:
                        if code_sites:
                            lines.append("")  # Blank line between sections
                        lines.append(f"{indent}  Test ({len(test_sites)}):")
                        for site in test_sites:
                            # Format calling location with function if available
                            calling_func = site.get("calling_function")
                            if calling_func:
                                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
                            else:
                                caller = site["calling_module"]

                            lines.append(
                                f"{indent}  - `{caller}` at `{site['file']}:{site['line']}`"
                            )

                            # Add the actual code line if available
                            if "code_line" in site:
                                lines.append(f"{indent}    ```")
                                lines.append(f"{indent}    {site['code_line']}")
                                lines.append(f"{indent}    ```")
                else:
                    # Separate into code and test call sites
                    code_sites = [
                        s for s in call_sites if "test" not in s["file"].lower()
                    ]
                    test_sites = [s for s in call_sites if "test" in s["file"].lower()]

                    call_count = len(call_sites)
                    lines.append(f"{indent}**Called {call_count} times:**")

                    if code_sites:
                        lines.append(f"{indent}  Code ({len(code_sites)}):")
                        for site in code_sites:
                            # Format calling location with function if available
                            calling_func = site.get("calling_function")
                            if calling_func:
                                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
                            else:
                                caller = site["calling_module"]

                            lines.append(
                                f"{indent}  - `{caller}` at `{site['file']}:{site['line']}`"
                            )

                    if test_sites:
                        if code_sites:
                            lines.append("")  # Blank line between sections
                        lines.append(f"{indent}  Test ({len(test_sites)}):")
                        for site in test_sites:
                            # Format calling location with function if available
                            calling_func = site.get("calling_function")
                            if calling_func:
                                caller = f"{site['calling_module']}.{calling_func['name']}/{calling_func['arity']}"
                            else:
                                caller = site["calling_module"]

                            lines.append(
                                f"{indent}  - `{caller}` at `{site['file']}:{site['line']}`"
                            )
            else:
                lines.extend([f"{indent}*No call sites found*"])

        return "\n".join(lines)

    @staticmethod
    def format_function_results_json(
        function_name: str, results: list[Dict[str, Any]]
    ) -> str:
        """
        Format function search results as JSON.

        Args:
            function_name: The searched function name
            results: List of function matches with module context

        Returns:
            Formatted JSON string
        """
        if not results:
            error_result = {
                "error": "Function not found",
                "query": function_name,
                "hint": "Verify the function name spelling or try without arity",
            }
            return json.dumps(error_result, indent=2)

        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "module": result["module"],
                    "function": result["function"]["name"],
                    "arity": result["function"]["arity"],
                    "full_name": f"{result['module']}.{result['function']['name']}/{result['function']['arity']}",
                    "signature": ModuleFormatter._format_function_signature(
                        result["function"]
                    ),
                    "location": f"{result['file']}:{result['function']['line']}",
                    "type": result["function"]["type"],
                    "doc": result["function"].get("doc"),
                    "call_sites": result.get("call_sites", []),
                }
            )

        output = {
            "query": function_name,
            "total_matches": len(results),
            "results": formatted_results,
        }
        return json.dumps(output, indent=2)

    @staticmethod
    def format_module_usage_markdown(
        module_name: str, usage_results: Dict[str, Any]
    ) -> str:
        """
        Format module usage results as Markdown.

        Args:
            module_name: The module being searched for
            usage_results: Dictionary with usage category keys

        Returns:
            Formatted Markdown string
        """
        aliases = usage_results.get("aliases", [])
        imports = usage_results.get("imports", [])
        requires = usage_results.get("requires", [])
        uses = usage_results.get("uses", [])
        value_mentions = usage_results.get("value_mentions", [])
        function_calls = usage_results.get("function_calls", [])

        lines = [f"# Usage of `{module_name}`", ""]

        # Show aliases section
        if aliases:
            lines.extend([f"## Aliases ({len(aliases)} module(s)):", ""])
            for imp in aliases:
                alias_info = (
                    f" as `{imp['alias_name']}`"
                    if imp["alias_name"] != module_name.split(".")[-1]
                    else ""
                )
                lines.append(
                    f"- `{imp['importing_module']}` {alias_info} — `{imp['file']}`"
                )
            lines.append("")

        # Show imports section
        if imports:
            lines.extend([f"## Imports ({len(imports)} module(s)):", ""])
            for imp in imports:
                lines.append(
                    f"- `{imp['importing_module']}` — `{imp['file']}`"
                )
            lines.append("")

        # Show requires section
        if requires:
            lines.extend([f"## Requires ({len(requires)} module(s)):", ""])
            for req in requires:
                lines.append(
                    f"- `{req['importing_module']}` — `{req['file']}`"
                )
            lines.append("")

        # Show uses section
        if uses:
            lines.extend([f"## Uses ({len(uses)} module(s)):", ""])
            for use in uses:
                lines.append(
                    f"- `{use['importing_module']}` — `{use['file']}`"
                )
            lines.append("")

        # Show value mentions section
        if value_mentions:
            lines.extend([f"## As Value ({len(value_mentions)} module(s)):", ""])
            for vm in value_mentions:
                lines.append(
                    f"- `{vm['importing_module']}` — `{vm['file']}`"
                )
            lines.append("")

        # Show function calls section
        if function_calls:
            # Count total calls
            total_calls = sum(len(fc["calls"]) for fc in function_calls)
            lines.extend(
                [
                    f"## Function Calls ({len(function_calls)} module(s), {total_calls} function(s)):",
                    "",
                ]
            )

            for fc in function_calls:
                lines.append(f"### `{fc['calling_module']}`")
                lines.append(f"  `{fc['file']}`")
                lines.append("")

                for call in fc["calls"]:
                    alias_info = (
                        f" (via `{call['alias_used']}`)" if call["alias_used"] else ""
                    )
                    # Show unique line numbers for this function
                    line_list = ", ".join(f":{line}" for line in sorted(call["lines"]))
                    lines.append(
                        f"  - `{call['function']}/{call['arity']}`{alias_info} — {line_list}"
                    )

                lines.append("")

        # Show message if no usage found at all
        if not any([aliases, imports, requires, uses, value_mentions, function_calls]):
            lines.extend(["*No usage found for this module*"])

        return "\n".join(lines)

    @staticmethod
    def format_module_usage_json(
        module_name: str, usage_results: Dict[str, Any]
    ) -> str:
        """
        Format module usage results as JSON.

        Args:
            module_name: The module being searched for
            usage_results: Dictionary with usage category keys

        Returns:
            Formatted JSON string
        """
        output = {
            "module": module_name,
            "aliases": usage_results.get("aliases", []),
            "imports": usage_results.get("imports", []),
            "requires": usage_results.get("requires", []),
            "uses": usage_results.get("uses", []),
            "value_mentions": usage_results.get("value_mentions", []),
            "function_calls": usage_results.get("function_calls", []),
            "summary": {
                "aliased_by": len(usage_results.get("aliases", [])),
                "imported_by": len(usage_results.get("imports", [])),
                "required_by": len(usage_results.get("requires", [])),
                "used_by": len(usage_results.get("uses", [])),
                "mentioned_as_value_by": len(usage_results.get("value_mentions", [])),
                "called_by": len(usage_results.get("function_calls", [])),
            },
        }
        return json.dumps(output, indent=2)


class JSONFormatter:
    """Formats JSON data with customizable options."""

    def __init__(self, indent: int = 2, sort_keys: bool = False):
        """
        Initialize the formatter.

        Args:
            indent: Number of spaces for indentation (default: 2)
            sort_keys: Whether to sort dictionary keys alphabetically (default: False)
        """
        self.indent = indent
        self.sort_keys = sort_keys

    def format_string(self, json_string: str) -> str:
        """
        Format a JSON string.

        Args:
            json_string: Raw JSON string to format

        Returns:
            Formatted JSON string

        Raises:
            ValueError: If the input is not valid JSON
        """
        try:
            data = json.loads(json_string)
            return json.dumps(data, indent=self.indent, sort_keys=self.sort_keys)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def format_file(self, input_path: Path, output_path: Optional[Path] = None) -> str:
        """
        Format a JSON file.

        Args:
            input_path: Path to the input JSON file
            output_path: Optional path to write formatted output (default: stdout)

        Returns:
            Formatted JSON string

        Raises:
            FileNotFoundError: If the input file doesn't exist
            ValueError: If the input file contains invalid JSON
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Read the input file
        with open(input_path, "r") as f:
            json_string = f.read()

        # Format the JSON
        formatted = self.format_string(json_string)

        # Write to output file if specified, otherwise return for stdout
        if output_path:
            with open(output_path, "w") as f:
                f.write(formatted)
                f.write("\n")  # Add trailing newline
            print(f"Formatted JSON written to: {output_path}", file=sys.stderr)

        return formatted

    def format_dict(self, data: dict) -> str:
        """
        Format a Python dictionary as JSON.

        Args:
            data: Dictionary to format

        Returns:
            Formatted JSON string
        """
        return json.dumps(data, indent=self.indent, sort_keys=self.sort_keys)


def main():
    """Main entry point for the formatter CLI."""
    parser = argparse.ArgumentParser(
        description="Pretty print JSON files with customizable formatting"
    )
    parser.add_argument("input", type=Path, help="Input JSON file to format")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output file (default: print to stdout)"
    )
    parser.add_argument(
        "-i",
        "--indent",
        type=int,
        default=2,
        help="Number of spaces for indentation (default: 2)",
    )
    parser.add_argument(
        "-s",
        "--sort-keys",
        action="store_true",
        help="Sort dictionary keys alphabetically",
    )
    parser.add_argument(
        "--compact", action="store_true", help="Use compact formatting (no indentation)"
    )

    args = parser.parse_args()

    # Create formatter with specified options
    indent = None if args.compact else args.indent
    formatter = JSONFormatter(indent=indent, sort_keys=args.sort_keys)

    try:
        # Format the file
        formatted = formatter.format_file(args.input, args.output)

        # Print to stdout if no output file specified
        if not args.output:
            print(formatted)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
