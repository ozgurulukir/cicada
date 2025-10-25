"""
Elixir Parser using tree-sitter.

Parses Elixir source files to extract modules and functions.
"""

import tree_sitter_elixir as ts_elixir
from tree_sitter import Language, Parser


class ElixirParser:
    """Parser for extracting modules and functions from Elixir files."""

    def __init__(self):
        """Initialize the tree-sitter parser with Elixir grammar."""
        self.language = Language(ts_elixir.language())
        self.parser = Parser(self.language)

    def parse_file(self, file_path: str) -> dict:
        """
        Parse an Elixir file and extract module and function information.

        Args:
            file_path: Path to the .ex or .exs file to parse

        Returns:
            Dictionary containing module name and functions list, or None if parsing fails
        """
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()

            tree = self.parser.parse(source_code)
            root_node = tree.root_node

            # Check for parse errors
            if root_node.has_error:
                print(f"Parse error in {file_path}")
                return None

            # Find all defmodule nodes
            modules = self._extract_modules(root_node, source_code)

            return modules if modules else None

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_modules(self, node, source_code: bytes) -> list:
        """Extract all modules from the syntax tree."""
        modules = []
        self._find_modules_recursive(node, source_code, modules)
        return modules

    def _find_modules_recursive(self, node, source_code: bytes, modules: list):
        """Recursively find defmodule declarations."""
        # Check if this node is a function call (defmodule)
        if node.type == 'call':
            # Get the target, arguments, and do_block (all siblings)
            target = None
            arguments = None
            do_block = None

            for child in node.children:
                if child.type == 'identifier':
                    target = child
                elif child.type == 'arguments':
                    arguments = child
                elif child.type == 'do_block':
                    do_block = child

            # Check if this is a defmodule call
            if target and arguments:
                target_text = source_code[target.start_byte:target.end_byte].decode('utf-8')

                if target_text == 'defmodule':
                    # Extract module name from arguments
                    module_name = None

                    for arg_child in arguments.children:
                        if arg_child.type == 'alias':
                            module_name = source_code[arg_child.start_byte:arg_child.end_byte].decode('utf-8')
                            break

                    if module_name and do_block:
                        module_info = {
                            "module": module_name,
                            "line": node.start_point[0] + 1,
                            "functions": self._extract_functions(do_block, source_code)
                        }
                        modules.append(module_info)
                        return  # Don't recurse into module body

        # Recursively process children
        for child in node.children:
            self._find_modules_recursive(child, source_code, modules)

    def _extract_functions(self, node, source_code: bytes) -> list:
        """Extract all function definitions from a module body."""
        functions = []
        self._find_functions_recursive(node, source_code, functions)
        return functions

    def _find_functions_recursive(self, node, source_code: bytes, functions: list):
        """Recursively find def and defp declarations."""
        # Check if this node is a function call (def or defp)
        if node.type == 'call':
            # Get the target (function name)
            target = None
            arguments = None

            for child in node.children:
                if child.type == 'identifier':
                    target = child
                elif child.type == 'arguments':
                    arguments = child

            # Check if this is a def or defp call
            if target and arguments:
                target_text = source_code[target.start_byte:target.end_byte].decode('utf-8')

                if target_text in ['def', 'defp']:
                    # Extract function name and arity
                    func_info = self._parse_function_definition(arguments, source_code, target_text, node.start_point[0] + 1)
                    if func_info:
                        functions.append(func_info)
                        return  # Don't recurse into function body

        # Recursively process children
        for child in node.children:
            self._find_functions_recursive(child, source_code, functions)

    def _parse_function_definition(self, arguments_node, source_code: bytes, func_type: str, line: int) -> dict:
        """Parse a function definition to extract name and arity."""
        func_name = None
        arity = 0

        for arg_child in arguments_node.children:
            # The function signature can be either:
            # 1. A call node (function with params): func_name(param1, param2)
            # 2. An identifier (function with no params): func_name
            if arg_child.type == 'call':
                # Extract function name from call target
                for call_child in arg_child.children:
                    if call_child.type == 'identifier':
                        func_name = source_code[call_child.start_byte:call_child.end_byte].decode('utf-8')
                    elif call_child.type == 'arguments':
                        arity = self._calculate_arity(call_child, source_code)
                break
            elif arg_child.type == 'identifier':
                func_name = source_code[arg_child.start_byte:arg_child.end_byte].decode('utf-8')
                arity = 0
                break

        if func_name:
            return {
                "name": func_name,
                "arity": arity,
                "full_name": f"{func_name}/{arity}",
                "line": line,
                "signature": f"{func_type} {func_name}",
                "type": func_type
            }

        return None

    def _calculate_arity(self, params_node, source_code: bytes) -> int:
        """Calculate the arity (number of parameters) of a function."""
        # Count comma-separated parameters
        arity = 0

        # Simple approach: count immediate children that are not punctuation
        for child in params_node.children:
            if child.type not in [',', '(', ')', '[', ']']:
                arity += 1

        # If no children, might be a single param
        if arity == 0 and params_node.child_count > 0:
            arity = 1

        return arity


if __name__ == "__main__":
    # Simple test
    import sys

    if len(sys.argv) > 1:
        parser = ElixirParser()
        result = parser.parse_file(sys.argv[1])
        if result:
            import json
            print(json.dumps(result, indent=2))
        else:
            print("Failed to parse file")
    else:
        print("Usage: python parser.py <elixir_file.ex>")
