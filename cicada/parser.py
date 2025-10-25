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
            with open(file_path, "rb") as f:
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
        if node.type == "call":
            # Get the target, arguments, and do_block (all siblings)
            target = None
            arguments = None
            do_block = None

            for child in node.children:
                if child.type == "identifier":
                    target = child
                elif child.type == "arguments":
                    arguments = child
                elif child.type == "do_block":
                    do_block = child

            # Check if this is a defmodule call
            if target and arguments:
                target_text = source_code[target.start_byte : target.end_byte].decode(
                    "utf-8"
                )

                if target_text == "defmodule":
                    # Extract module name from arguments
                    module_name = None

                    for arg_child in arguments.children:
                        if arg_child.type == "alias":
                            module_name = source_code[
                                arg_child.start_byte : arg_child.end_byte
                            ].decode("utf-8")
                            break

                    if module_name and do_block:
                        # Extract functions and specs
                        functions = self._extract_functions(do_block, source_code)
                        specs = self._extract_specs(do_block, source_code)

                        # Match specs with functions
                        functions_with_specs = self._match_specs_to_functions(
                            functions, specs
                        )

                        # Extract aliases, imports, requires, uses, value mentions, and function calls
                        aliases = self._extract_aliases(do_block, source_code)
                        imports = self._extract_imports(do_block, source_code)
                        requires = self._extract_requires(do_block, source_code)
                        uses = self._extract_uses(do_block, source_code)
                        value_mentions = self._extract_value_mentions(do_block, source_code)
                        function_calls = self._extract_function_calls(
                            do_block, source_code
                        )

                        module_info = {
                            "module": module_name,
                            "line": node.start_point[0] + 1,
                            "moduledoc": self._extract_moduledoc(do_block, source_code),
                            "functions": functions_with_specs,
                            "aliases": aliases,
                            "imports": imports,
                            "requires": requires,
                            "uses": uses,
                            "value_mentions": value_mentions,
                            "calls": function_calls,
                        }
                        modules.append(module_info)
                        return  # Don't recurse into module body

        # Recursively process children
        for child in node.children:
            self._find_modules_recursive(child, source_code, modules)

    def _extract_moduledoc(self, node, source_code: bytes) -> str | None:
        """Extract the @moduledoc attribute from a module's do_block."""
        return self._find_moduledoc_recursive(node, source_code)

    def _find_moduledoc_recursive(self, node, source_code: bytes) -> str | None:
        """Recursively search for @moduledoc attribute."""
        # Look for unary_operator nodes (which represent @ attributes)
        if node.type == "unary_operator":
            operator = None
            operand = None

            for child in node.children:
                if child.type == "@":
                    operator = child
                elif child.type == "call":
                    # @moduledoc "..." is represented as a call
                    operand = child

            if operator and operand:
                # Check if this is a moduledoc attribute
                for call_child in operand.children:
                    if call_child.type == "identifier":
                        attr_name = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")

                        if attr_name == "moduledoc":
                            # Extract the documentation string from the arguments
                            for arg_child in operand.children:
                                if arg_child.type == "arguments":
                                    doc_string = self._extract_string_from_arguments(
                                        arg_child, source_code
                                    )
                                    if doc_string:
                                        return doc_string

        # Recursively search children (only in the immediate do_block, not nested modules)
        for child in node.children:
            # Don't recurse into nested defmodule
            if child.type == "call":
                # Check if it's a defmodule
                is_defmodule = False
                for call_child in child.children:
                    if call_child.type == "identifier":
                        target_text = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")
                        if target_text == "defmodule":
                            is_defmodule = True
                            break

                if is_defmodule:
                    continue

            result = self._find_moduledoc_recursive(child, source_code)
            if result:
                return result

        return None

    def _extract_string_from_arguments(
        self, arguments_node, source_code: bytes
    ) -> str | None:
        """Extract string value from function arguments."""
        for child in arguments_node.children:
            # Handle string literals
            if child.type == "string":
                # Get the string content (without quotes)
                string_content = []
                for string_child in child.children:
                    if string_child.type == "quoted_content":
                        content = source_code[
                            string_child.start_byte : string_child.end_byte
                        ].decode("utf-8")
                        string_content.append(content)

                if string_content:
                    return "".join(string_content)

            # Handle false (for @moduledoc false)
            elif child.type == "boolean" or child.type == "atom":
                value = source_code[child.start_byte : child.end_byte].decode("utf-8")
                if value == "false":
                    return None

        return None

    def _extract_functions(self, node, source_code: bytes) -> list:
        """Extract all function definitions from a module body."""
        functions = []
        docs = {}
        # First extract all @doc attributes
        self._find_docs_recursive(node, source_code, docs)
        # Then extract functions
        self._find_functions_recursive(node, source_code, functions)
        # Match docs to functions
        self._match_docs_to_functions(functions, docs)
        return functions

    def _extract_specs(self, node, source_code: bytes) -> dict:
        """Extract all @spec attributes from a module body."""
        specs = {}
        self._find_specs_recursive(node, source_code, specs)
        return specs

    def _find_specs_recursive(self, node, source_code: bytes, specs: dict):
        """Recursively find @spec declarations."""
        # Look for unary_operator nodes (which represent @ attributes)
        if node.type == "unary_operator":
            operator = None
            operand = None

            for child in node.children:
                if child.type == "@":
                    operator = child
                elif child.type == "call":
                    operand = child

            if operator and operand:
                # Check if this is a spec attribute
                for call_child in operand.children:
                    if call_child.type == "identifier":
                        attr_name = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")

                        if attr_name == "spec":
                            # Extract the spec definition
                            spec_info = self._parse_spec(operand, source_code)
                            if spec_info:
                                key = f"{spec_info['name']}/{spec_info['arity']}"
                                specs[key] = spec_info

        # Recursively search children
        for child in node.children:
            # Don't recurse into nested defmodule or function definitions
            if child.type == "call":
                is_defmodule_or_def = False
                for call_child in child.children:
                    if call_child.type == "identifier":
                        target_text = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")
                        if target_text in ["defmodule", "def", "defp"]:
                            is_defmodule_or_def = True
                            break

                if is_defmodule_or_def:
                    continue

            self._find_specs_recursive(child, source_code, specs)

    def _parse_spec(self, spec_node, source_code: bytes) -> dict | None:
        """Parse a @spec attribute to extract function name, arity, parameter types, and return type."""
        # @spec is represented as: spec(function_signature)
        # We need to find the arguments node and parse the typespec

        for child in spec_node.children:
            if child.type == "arguments":
                # The typespec is in the arguments
                for arg in child.children:
                    if arg.type == "binary_operator":
                        # This is the :: operator separating params from return type
                        # Left side has the function call with params
                        # Right side has the return type
                        func_call = None
                        return_type = None
                        found_call = False

                        for op_child in arg.children:
                            if op_child.type == "call":
                                func_call = op_child
                                found_call = True
                            elif found_call and op_child.type not in ["::", "operator"]:
                                # This is the return type node (after :: operator)
                                return_type = source_code[
                                    op_child.start_byte : op_child.end_byte
                                ].decode("utf-8")

                        if func_call:
                            func_name = None
                            param_types = []

                            for fc_child in func_call.children:
                                if fc_child.type == "identifier":
                                    func_name = source_code[
                                        fc_child.start_byte : fc_child.end_byte
                                    ].decode("utf-8")
                                elif fc_child.type == "arguments":
                                    param_types = self._extract_param_types(
                                        fc_child, source_code
                                    )

                            if func_name:
                                return {
                                    "name": func_name,
                                    "arity": len(param_types),
                                    "param_types": param_types,
                                    "return_type": return_type,
                                }

        return None

    def _extract_param_types(self, params_node, source_code: bytes) -> list[str]:
        """Extract parameter type strings from @spec arguments."""
        param_types = []

        for child in params_node.children:
            if child.type in [",", "(", ")", "[", "]"]:
                continue

            # Get the type as a string
            type_str = source_code[child.start_byte : child.end_byte].decode("utf-8")
            param_types.append(type_str)

        return param_types

    def _match_specs_to_functions(self, functions: list, specs: dict) -> list:
        """Match specs with functions and add type information to function args and return type."""
        for func in functions:
            key = f"{func['name']}/{func['arity']}"
            if key in specs:
                spec = specs[key]
                # Add types to arguments
                if "args" in func and "param_types" in spec:
                    # Create args_with_types list
                    args_with_types = []
                    for i, arg_name in enumerate(func["args"]):
                        if i < len(spec["param_types"]):
                            args_with_types.append(
                                {"name": arg_name, "type": spec["param_types"][i]}
                            )
                        else:
                            args_with_types.append({"name": arg_name, "type": None})
                    func["args_with_types"] = args_with_types

                # Add return type from spec
                if "return_type" in spec and spec["return_type"]:
                    func["return_type"] = spec["return_type"]

        return functions

    def _find_docs_recursive(self, node, source_code: bytes, docs: dict):
        """Recursively find @doc declarations."""
        # Look for unary_operator nodes (which represent @ attributes)
        if node.type == "unary_operator":
            operator = None
            operand = None

            for child in node.children:
                if child.type == "@":
                    operator = child
                elif child.type == "call":
                    operand = child

            if operator and operand:
                # Check if this is a doc attribute
                for call_child in operand.children:
                    if call_child.type == "identifier":
                        attr_name = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")

                        if attr_name == "doc":
                            # Extract the doc definition
                            doc_info = self._parse_doc(
                                operand, source_code, node.start_point[0] + 1
                            )
                            if doc_info:
                                # Store by line number to match with function later
                                docs[doc_info["line"]] = doc_info["text"]

        # Recursively search children
        for child in node.children:
            # Don't recurse into nested defmodule or function definitions
            if child.type == "call":
                is_defmodule_or_def = False
                for call_child in child.children:
                    if call_child.type == "identifier":
                        target_text = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")
                        if target_text in ["defmodule", "def", "defp"]:
                            is_defmodule_or_def = True
                            break

                if is_defmodule_or_def:
                    continue

            self._find_docs_recursive(child, source_code, docs)

    def _parse_doc(self, doc_node, source_code: bytes, line: int) -> dict | None:
        """Parse a @doc attribute to extract its text."""
        # @doc is represented as: doc("text") or doc(false)
        for child in doc_node.children:
            if child.type == "arguments":
                doc_text = self._extract_string_from_arguments(child, source_code)
                if doc_text:
                    return {"line": line, "text": doc_text}
        return None

    def _match_docs_to_functions(self, functions: list, docs: dict):
        """Match @doc attributes to functions based on proximity."""
        # @doc appears right before the function, usually 1-2 lines before
        for func in functions:
            func_line = func["line"]
            # Look for @doc in the 5 lines before the function
            for offset in range(1, 6):
                doc_line = func_line - offset
                if doc_line in docs:
                    func["doc"] = docs[doc_line]
                    break

    def _find_functions_recursive(self, node, source_code: bytes, functions: list):
        """Recursively find def and defp declarations."""
        # Check if this node is a function call (def or defp)
        if node.type == "call":
            # Get the target (function name)
            target = None
            arguments = None

            for child in node.children:
                if child.type == "identifier":
                    target = child
                elif child.type == "arguments":
                    arguments = child

            # Check if this is a def or defp call
            if target and arguments:
                target_text = source_code[target.start_byte : target.end_byte].decode(
                    "utf-8"
                )

                if target_text in ["def", "defp"]:
                    # Extract function name and arity
                    func_info = self._parse_function_definition(
                        arguments, source_code, target_text, node.start_point[0] + 1
                    )
                    if func_info:
                        functions.append(func_info)
                        return  # Don't recurse into function body

        # Recursively process children
        for child in node.children:
            self._find_functions_recursive(child, source_code, functions)

    def _parse_function_definition(
        self, arguments_node, source_code: bytes, func_type: str, line: int
    ) -> dict:
        """Parse a function definition to extract name, arity, argument names, and guards."""
        func_name = None
        arity = 0
        arg_names = []
        guards = []

        for arg_child in arguments_node.children:
            # The function signature can be either:
            # 1. A call node (function with params): func_name(param1, param2)
            # 2. An identifier (function with no params): func_name
            # 3. A binary_operator (when guards are present): func_name(params) when guard
            if arg_child.type == "call":
                # Extract function name from call target
                for call_child in arg_child.children:
                    if call_child.type == "identifier":
                        func_name = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")
                    elif call_child.type == "arguments":
                        arg_names = self._extract_argument_names(
                            call_child, source_code
                        )
                        arity = len(arg_names)
                break
            elif arg_child.type == "binary_operator":
                # This handles guards: func_name(params) when guard_expr
                # The binary_operator contains the call as its first child
                for op_child in arg_child.children:
                    if op_child.type == "call":
                        # Extract function name and args from the call
                        for call_child in op_child.children:
                            if call_child.type == "identifier":
                                func_name = source_code[
                                    call_child.start_byte : call_child.end_byte
                                ].decode("utf-8")
                            elif call_child.type == "arguments":
                                arg_names = self._extract_argument_names(
                                    call_child, source_code
                                )
                                arity = len(arg_names)
                        break
                break
            elif arg_child.type == "identifier":
                func_name = source_code[
                    arg_child.start_byte : arg_child.end_byte
                ].decode("utf-8")
                arity = 0
                arg_names = []
                break

        # Extract guard clauses
        guards = self._extract_guards(arguments_node, source_code)

        if func_name:
            return {
                "name": func_name,
                "arity": arity,
                "args": arg_names,
                "guards": guards,
                "full_name": f"{func_name}/{arity}",
                "line": line,
                "signature": f"{func_type} {func_name}",
                "type": func_type,
            }

        return None

    def _extract_guards(self, arguments_node, source_code: bytes) -> list[str]:
        """
        Extract guard clauses from function definition arguments.

        Example:
            def abs_value(n) when n < 0, do: -n
            Returns: ["n < 0"]

        Tree structure:
            arguments:
              binary_operator:  # This contains function_call WHEN guard_expr
                call: abs_value(n)
                when: 'when'
                binary_operator: n < 0  # This is the guard expression
        """
        guards = []

        for arg_child in arguments_node.children:
            # Guards appear as binary_operator nodes containing 'when'
            if arg_child.type == "binary_operator":
                # Look for 'when' keyword and the guard expression after it
                has_when = False
                guard_node = None

                for op_child in arg_child.children:
                    if op_child.type == "when":
                        has_when = True
                    elif has_when:
                        # This is the guard expression node (comes after 'when')
                        # It's typically a binary_operator (like n < 0)
                        guard_expr = source_code[op_child.start_byte:op_child.end_byte].decode("utf-8")
                        guards.append(guard_expr)
                        break

        return guards

    def _extract_argument_names(self, params_node, source_code: bytes) -> list[str]:
        """Extract parameter names from function arguments."""
        arg_names = []

        for child in params_node.children:
            if child.type in [",", "(", ")", "[", "]"]:
                continue

            # Extract the argument name (simplified - handles basic cases)
            arg_name = self._get_param_name(child, source_code)
            if arg_name:
                arg_names.append(arg_name)

        return arg_names

    def _get_param_name(self, node, source_code: bytes) -> str | None:
        """Get parameter name from a parameter node."""
        # Handle simple identifier: my_arg
        if node.type == "identifier":
            return source_code[node.start_byte : node.end_byte].decode("utf-8")

        # Handle pattern match with default: my_arg \\ default_value
        elif node.type == "binary_operator":
            for child in node.children:
                if child.type == "identifier":
                    return source_code[child.start_byte : child.end_byte].decode(
                        "utf-8"
                    )

        # Handle destructuring: {key, value} or [head | tail]
        elif node.type in ["tuple", "list", "map"]:
            # For complex patterns, return the whole pattern as string
            return source_code[node.start_byte : node.end_byte].decode("utf-8")

        # Handle call patterns (e.g., %Struct{} = arg)
        elif node.type == "call":
            # Try to find the actual variable name
            for child in node.children:
                if child.type == "identifier":
                    return source_code[child.start_byte : child.end_byte].decode(
                        "utf-8"
                    )

        # Fallback: return the whole node as string
        return source_code[node.start_byte : node.end_byte].decode("utf-8")

    def _calculate_arity(self, params_node, source_code: bytes) -> int:
        """Calculate the arity (number of parameters) of a function."""
        # Count comma-separated parameters
        arity = 0

        # Simple approach: count immediate children that are not punctuation
        for child in params_node.children:
            if child.type not in [",", "(", ")", "[", "]"]:
                arity += 1

        # If no children, might be a single param
        if arity == 0 and params_node.child_count > 0:
            arity = 1

        return arity

    def _extract_aliases(self, node, source_code: bytes) -> dict:
        """Extract all alias declarations from a module body."""
        aliases = {}
        self._find_aliases_recursive(node, source_code, aliases)
        return aliases

    def _find_aliases_recursive(self, node, source_code: bytes, aliases: dict):
        """Recursively find alias declarations."""
        if node.type == "call":
            target = None
            arguments = None

            for child in node.children:
                if child.type == "identifier":
                    target = child
                elif child.type == "arguments":
                    arguments = child

            if target and arguments:
                target_text = source_code[target.start_byte : target.end_byte].decode(
                    "utf-8"
                )

                if target_text == "alias":
                    # Parse the alias
                    alias_info = self._parse_alias(arguments, source_code)
                    if alias_info:
                        # alias_info is a dict of {short_name: full_name}
                        aliases.update(alias_info)

        # Recursively search children, but skip function bodies
        for child in node.children:
            if child.type == "call":
                is_function_def = False
                for call_child in child.children:
                    if call_child.type == "identifier":
                        target_text = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")
                        if target_text in ["def", "defp", "defmodule"]:
                            is_function_def = True
                            break

                if is_function_def:
                    continue

            self._find_aliases_recursive(child, source_code, aliases)

    def _parse_alias(self, arguments_node, source_code: bytes) -> dict | None:
        """
        Parse an alias declaration.

        Handles:
        - alias MyApp.User -> {User: MyApp.User}
        - alias MyApp.User, as: U -> {U: MyApp.User}
        - alias MyApp.{User, Post} -> {User: MyApp.User, Post: MyApp.Post}
        """
        result = {}

        for arg_child in arguments_node.children:
            # Simple alias: alias MyApp.User
            if arg_child.type == "alias":
                full_name = source_code[
                    arg_child.start_byte : arg_child.end_byte
                ].decode("utf-8")
                # Get the last part as the short name
                short_name = full_name.split(".")[-1]
                result[short_name] = full_name

            # Alias with tuple: alias MyApp.{User, Post}
            elif arg_child.type == "dot":
                # The dot node contains: alias (module prefix), dot, and tuple
                module_prefix = None
                tuple_node = None

                for dot_child in arg_child.children:
                    if dot_child.type == "alias":
                        module_prefix = source_code[
                            dot_child.start_byte : dot_child.end_byte
                        ].decode("utf-8")
                    elif dot_child.type == "tuple":
                        tuple_node = dot_child

                if module_prefix and tuple_node:
                    # Extract each alias from the tuple
                    for tuple_child in tuple_node.children:
                        if tuple_child.type == "alias":
                            short_name = source_code[
                                tuple_child.start_byte : tuple_child.end_byte
                            ].decode("utf-8")
                            full_name = f"{module_prefix}.{short_name}"
                            result[short_name] = full_name

            # Keyword list for 'as:' option
            elif arg_child.type == "keywords":
                # Find the 'as:' keyword
                for kw_child in arg_child.children:
                    if kw_child.type == "pair":
                        key_text = None
                        alias_name = None
                        for pair_child in kw_child.children:
                            if pair_child.type == "keyword":
                                # Get keyword text (e.g., "as:")
                                key_text = source_code[
                                    pair_child.start_byte : pair_child.end_byte
                                ].decode("utf-8")
                            elif pair_child.type == "alias":
                                alias_name = source_code[
                                    pair_child.start_byte : pair_child.end_byte
                                ].decode("utf-8")

                        # If we found 'as:', update the result to use custom name
                        if key_text and "as" in key_text and alias_name:
                            # Get the full module name from previous arg
                            for prev_arg in arguments_node.children:
                                if prev_arg.type == "alias":
                                    full_name = source_code[
                                        prev_arg.start_byte : prev_arg.end_byte
                                    ].decode("utf-8")
                                    # Remove the default short name and add custom one
                                    result.clear()
                                    result[alias_name] = full_name
                                    break

        return result if result else None

    def _extract_imports(self, node, source_code: bytes) -> list:
        """Extract all import declarations from a module body."""
        imports = []
        self._find_imports_recursive(node, source_code, imports)
        return imports

    def _find_imports_recursive(self, node, source_code: bytes, imports: list):
        """Recursively find import declarations."""
        if node.type == "call":
            target = None
            arguments = None

            for child in node.children:
                if child.type == "identifier":
                    target = child
                elif child.type == "arguments":
                    arguments = child

            if target and arguments:
                target_text = source_code[target.start_byte : target.end_byte].decode(
                    "utf-8"
                )

                if target_text == "import":
                    # Parse the import - imports are simpler than aliases
                    # import MyModule or import MyModule, only: [func: 1]
                    for arg_child in arguments.children:
                        if arg_child.type == "alias":
                            module_name = source_code[
                                arg_child.start_byte : arg_child.end_byte
                            ].decode("utf-8")
                            imports.append(module_name)

        # Recursively search children, but skip function bodies
        for child in node.children:
            if child.type == "call":
                is_function_def = False
                for call_child in child.children:
                    if call_child.type == "identifier":
                        target_text = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")
                        if target_text in ["def", "defp", "defmodule"]:
                            is_function_def = True
                            break

                if is_function_def:
                    continue

            self._find_imports_recursive(child, source_code, imports)

    def _extract_requires(self, node, source_code: bytes) -> list:
        """Extract all require declarations from a module body."""
        requires = []
        self._find_requires_recursive(node, source_code, requires)
        return requires

    def _find_requires_recursive(self, node, source_code: bytes, requires: list):
        """Recursively find require declarations."""
        if node.type == "call":
            target = None
            arguments = None

            for child in node.children:
                if child.type == "identifier":
                    target = child
                elif child.type == "arguments":
                    arguments = child

            if target and arguments:
                target_text = source_code[target.start_byte : target.end_byte].decode(
                    "utf-8"
                )

                if target_text == "require":
                    # Parse the require
                    for arg_child in arguments.children:
                        if arg_child.type == "alias":
                            module_name = source_code[
                                arg_child.start_byte : arg_child.end_byte
                            ].decode("utf-8")
                            requires.append(module_name)

        # Recursively search children, but skip function bodies
        for child in node.children:
            if child.type == "call":
                is_function_def = False
                for call_child in child.children:
                    if call_child.type == "identifier":
                        target_text = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")
                        if target_text in ["def", "defp", "defmodule"]:
                            is_function_def = True
                            break

                if is_function_def:
                    continue

            self._find_requires_recursive(child, source_code, requires)

    def _extract_uses(self, node, source_code: bytes) -> list:
        """Extract all use declarations from a module body."""
        uses = []
        self._find_uses_recursive(node, source_code, uses)
        return uses

    def _find_uses_recursive(self, node, source_code: bytes, uses: list):
        """Recursively find use declarations."""
        if node.type == "call":
            target = None
            arguments = None

            for child in node.children:
                if child.type == "identifier":
                    target = child
                elif child.type == "arguments":
                    arguments = child

            if target and arguments:
                target_text = source_code[target.start_byte : target.end_byte].decode(
                    "utf-8"
                )

                if target_text == "use":
                    # Parse the use
                    for arg_child in arguments.children:
                        if arg_child.type == "alias":
                            module_name = source_code[
                                arg_child.start_byte : arg_child.end_byte
                            ].decode("utf-8")
                            uses.append(module_name)

        # Recursively search children, but skip function bodies
        for child in node.children:
            if child.type == "call":
                is_function_def = False
                for call_child in child.children:
                    if call_child.type == "identifier":
                        target_text = source_code[
                            call_child.start_byte : call_child.end_byte
                        ].decode("utf-8")
                        if target_text in ["def", "defp", "defmodule"]:
                            is_function_def = True
                            break

                if is_function_def:
                    continue

            self._find_uses_recursive(child, source_code, uses)

    def _extract_value_mentions(self, node, source_code: bytes) -> list:
        """Extract all module mentions as values (e.g., module passed as argument)."""
        value_mentions = []
        self._find_value_mentions_recursive(node, source_code, value_mentions)
        # Return unique module names
        return list(set(value_mentions))

    def _find_value_mentions_recursive(self, node, source_code: bytes, value_mentions: list):
        """Recursively find module value mentions."""
        # Look for alias nodes that are NOT part of alias/import/require/use declarations
        # and are NOT part of module function calls (which are already tracked in calls)

        if node.type == "alias":
            # Check if this is a standalone alias (value mention)
            # Skip if parent is a specific call type
            parent = node.parent if hasattr(node, 'parent') else None

            # Get the module name
            module_name = source_code[node.start_byte : node.end_byte].decode("utf-8")

            # We need to check if this alias is part of a call with dot notation
            # If it has a dot parent, it's a module function call, not a value mention
            is_in_call = False
            current = node

            # Check ancestors to see if we're in a special context
            for i in range(3):  # Check up to 3 levels up
                if current.parent:
                    current = current.parent
                    if current.type == "call":
                        # Check if this is alias/import/require/use/defmodule
                        for child in current.children:
                            if child.type == "identifier":
                                func_text = source_code[child.start_byte : child.end_byte].decode("utf-8")
                                if func_text in ["alias", "import", "require", "use", "defmodule"]:
                                    is_in_call = True
                                    break
                    elif current.type == "dot":
                        # This alias is part of a Module.function call
                        is_in_call = True
                        break

            if not is_in_call:
                value_mentions.append(module_name)

        # Recursively search all children
        for child in node.children:
            self._find_value_mentions_recursive(child, source_code, value_mentions)

    def _extract_function_calls(self, node, source_code: bytes) -> list:
        """Extract all function calls from a module body."""
        calls = []
        self._find_function_calls_recursive(node, source_code, calls)
        return calls

    def _find_function_calls_recursive(self, node, source_code: bytes, calls: list):
        """Recursively find function calls."""
        if node.type == "call":
            # Check if this is a function definition (def/defp)
            is_function_def = False
            for child in node.children:
                if child.type == "identifier":
                    func_text = source_code[child.start_byte : child.end_byte].decode(
                        "utf-8"
                    )
                    if func_text in ["def", "defp", "defmodule"]:
                        is_function_def = True
                        break

            if is_function_def:
                # Skip the arguments (which contain the function signature)
                # but still process the do_block to find calls within the function body
                for child in node.children:
                    if child.type == "do_block":
                        self._find_function_calls_recursive(child, source_code, calls)
                return  # Don't process other children

            # Try to extract the function call information
            call_info = self._parse_function_call(node, source_code)
            if call_info:
                calls.append(call_info)

        # Recursively search all children
        for child in node.children:
            self._find_function_calls_recursive(child, source_code, calls)

    def _parse_function_call(self, call_node, source_code: bytes) -> dict | None:
        """
        Parse a function call to extract the module, function name, arity, and location.

        Handles:
        - Local calls: func(arg1, arg2)
        - Module calls: MyModule.func(arg1, arg2)
        - Aliased calls: User.create(name, email)
        """
        line = call_node.start_point[0] + 1

        # Check for dot notation (Module.function)
        has_dot = False
        module_name = None
        function_name = None
        arguments_node = None

        for child in call_node.children:
            if child.type == "dot":
                has_dot = True
                # Extract module and function from dot
                for dot_child in child.children:
                    if dot_child.type == "alias":
                        module_name = source_code[
                            dot_child.start_byte : dot_child.end_byte
                        ].decode("utf-8")
                    elif dot_child.type == "identifier":
                        function_name = source_code[
                            dot_child.start_byte : dot_child.end_byte
                        ].decode("utf-8")
            elif child.type == "identifier" and not has_dot:
                # Local function call
                function_name = source_code[child.start_byte : child.end_byte].decode(
                    "utf-8"
                )
            elif child.type == "arguments":
                arguments_node = child

        # Skip certain special forms and macros
        if function_name in [
            "alias",
            "import",
            "require",
            "use",
            "def",
            "defp",
            "defmodule",
            "if",
            "unless",
            "case",
            "cond",
            "with",
            "for",
            "try",
            "receive",
        ]:
            return None

        # Calculate arity
        arity = 0
        if arguments_node:
            arity = self._count_arguments(arguments_node)

        if function_name:
            return {
                "module": module_name,  # None for local calls
                "function": function_name,
                "arity": arity,
                "line": line,
            }

        return None

    def _count_arguments(self, arguments_node) -> int:
        """Count the number of arguments in a function call."""
        count = 0
        for child in arguments_node.children:
            if child.type not in [",", "(", ")"]:
                count += 1
        return count


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
