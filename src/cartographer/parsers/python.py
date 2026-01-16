"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Python language parser using AST.
"""

import ast as python_ast
from pathlib import Path
from typing import List, Dict, Optional, Any

from ..database import ComponentData
from .base import BaseParser, ParseResult


class PythonParser(BaseParser):
    """Parser for Python using AST."""

    # Decorator patterns that indicate route handlers
    ROUTE_DECORATORS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'route', 'api_route'}

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse Python file."""
        result = ParseResult()

        try:
            tree = python_ast.parse(content)
            lines = content.split('\n')

            # Extract __all__ for exports
            exports = self._extract_all_exports(tree)

            # Extract imports
            self._extract_imports(tree, file_path, result)

            # Extract top-level components
            for node in tree.body:
                if isinstance(node, python_ast.ClassDef):
                    self._parse_class(node, lines, file_path, result, exports)
                elif isinstance(node, (python_ast.FunctionDef, python_ast.AsyncFunctionDef)):
                    self._parse_function(node, lines, file_path, result, exports)
                elif isinstance(node, python_ast.Assign):
                    self._parse_assignment(node, lines, file_path, result, exports)
                elif isinstance(node, python_ast.AnnAssign):
                    self._parse_annotated_assignment(node, lines, file_path, result, exports)

        except SyntaxError:
            pass  # Skip files with syntax errors
        except Exception:
            pass  # Skip files that can't be parsed

        return result

    def _extract_all_exports(self, tree) -> set:
        """Extract names from __all__ list."""
        exports = set()
        for node in tree.body:
            if isinstance(node, python_ast.Assign):
                for target in node.targets:
                    if isinstance(target, python_ast.Name) and target.id == '__all__':
                        if isinstance(node.value, (python_ast.List, python_ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, python_ast.Constant):
                                    exports.add(elt.value)
        return exports

    def _extract_imports(self, tree, file_path: str, result: ParseResult):
        """Extract import statements."""
        file_stem = Path(file_path).stem

        for node in python_ast.walk(tree):
            if isinstance(node, python_ast.Import):
                for alias in node.names:
                    result.add_relationship(
                        from_name=file_stem,
                        to_name=alias.name,
                        rel_type='imports',
                        line=node.lineno
                    )

            elif isinstance(node, python_ast.ImportFrom):
                if node.module:
                    result.add_relationship(
                        from_name=file_stem,
                        to_name=node.module,
                        rel_type='imports',
                        line=node.lineno
                    )

    def _parse_class(
        self,
        node: python_ast.ClassDef,
        lines: List[str],
        file_path: str,
        result: ParseResult,
        exports: set,
        parent: Optional[str] = None
    ):
        """Parse class definition."""
        # Decorators
        decorators = [self._get_name(dec) for dec in node.decorator_list]

        # Base classes
        bases = [self._get_name(base) for base in node.bases]

        # Exported check
        is_exported = node.name in exports or (not node.name.startswith('_') and not exports)

        # Docstring
        docstring = python_ast.get_docstring(node)

        # Determine class subtype based on decorators and base classes
        class_subtype = None
        if 'dataclass' in decorators or 'dataclasses.dataclass' in decorators:
            class_subtype = 'dataclass'
        elif any(b in ('BaseModel', 'pydantic.BaseModel') for b in bases):
            class_subtype = 'pydantic_model'
        elif any(b in ('Protocol', 'typing.Protocol') for b in bases):
            class_subtype = 'protocol'
        elif any(b in ('ABC', 'abc.ABC') for b in bases):
            class_subtype = 'abstract'
        elif any(b in ('NamedTuple', 'typing.NamedTuple') for b in bases):
            class_subtype = 'namedtuple'
        elif any(b in ('Enum', 'enum.Enum', 'IntEnum', 'StrEnum') for b in bases):
            class_subtype = 'enum'
        elif any(b in ('TypedDict', 'typing.TypedDict') for b in bases):
            class_subtype = 'typeddict'
        elif any(b in ('Exception', 'BaseException') for b in bases):
            class_subtype = 'exception'

        # Build signature
        base_str = f"({', '.join(bases)})" if bases else ""
        signature = f"class {node.name}{base_str}"

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, (python_ast.FunctionDef, python_ast.AsyncFunctionDef)):
                methods.append(item.name)

        # Check if test
        is_test = node.name.startswith('Test') or 'test' in file_path.lower()

        # Build metadata
        metadata = {}
        if class_subtype:
            metadata['subtype'] = class_subtype

        # Create component
        component = ComponentData(
            name=node.name,
            type='class',
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            signature=signature,
            docstring=docstring,
            decorators=decorators,
            parent=parent,
            exported=is_exported,
            methods=methods,
            is_test=is_test,
            metadata=metadata
        )

        result.add_component(component)

        # Add inheritance relationships
        for base in bases:
            result.add_relationship(
                from_name=node.name,
                to_name=base,
                rel_type='extends',
                line=node.lineno
            )

        # Parse methods
        for item in node.body:
            if isinstance(item, (python_ast.FunctionDef, python_ast.AsyncFunctionDef)):
                self._parse_function(item, lines, file_path, result, exports, parent=node.name)

    def _parse_function(
        self,
        node,
        lines: List[str],
        file_path: str,
        result: ParseResult,
        exports: set,
        parent: Optional[str] = None
    ):
        """Parse function or method."""
        # Decorators
        decorators = [self._get_name(dec) for dec in node.decorator_list]

        # Check for route decorators (FastAPI, Flask, etc.)
        route_info = None
        for dec in node.decorator_list:
            route_info = self._is_route_decorator(dec)
            if route_info:
                break

        # Parameters
        params = []
        if hasattr(node.args, 'args'):
            for arg in node.args.args:
                if arg.arg == 'self' or arg.arg == 'cls':
                    continue
                param = {'name': arg.arg}
                if arg.annotation:
                    param['type'] = self._get_name(arg.annotation)
                params.append(param)

        # Build signature
        param_strs = []
        for p in params:
            if 'type' in p:
                param_strs.append(f"{p['name']}: {p['type']}")
            else:
                param_strs.append(p['name'])

        returns = ""
        if node.returns:
            returns = f" -> {self._get_name(node.returns)}"

        is_async = isinstance(node, python_ast.AsyncFunctionDef)
        async_prefix = "async " if is_async else ""
        signature = f"{async_prefix}def {node.name}({', '.join(param_strs)}){returns}"

        # Modifiers
        modifiers = []
        if is_async:
            modifiers.append('async')
        if node.name.startswith('_') and not node.name.startswith('__'):
            modifiers.append('protected')
        elif node.name.startswith('__') and not node.name.endswith('__'):
            modifiers.append('private')
        if 'staticmethod' in decorators:
            modifiers.append('static')
        if 'classmethod' in decorators:
            modifiers.append('classmethod')
        if 'property' in decorators:
            modifiers.append('property')

        # Export check
        is_exported = (
            node.name in exports or
            (not node.name.startswith('_') and not exports and parent is None)
        )

        # Check if test
        is_test = (
            node.name.startswith('test') or
            'test' in file_path.lower() or
            any(d in ('pytest.fixture', 'fixture') for d in decorators)
        )

        # Determine component type
        if route_info:
            comp_type = 'route'
            # Override name for routes to include method
            comp_name = f"{route_info['method']}_{node.name}"
        else:
            comp_type = 'method' if parent else 'function'
            comp_name = node.name

        # Create component
        component = ComponentData(
            name=comp_name,
            type=comp_type,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            signature=signature,
            docstring=python_ast.get_docstring(node),
            params=params,
            decorators=decorators,
            modifiers=modifiers,
            parent=parent,
            exported=is_exported,
            is_async=is_async,
            is_test=is_test,
            metadata=route_info if route_info else {}
        )

        result.add_component(component)

        # Extract function calls
        for child in python_ast.walk(node):
            if isinstance(child, python_ast.Call):
                callee = self._get_name(child.func)
                if callee and callee != 'Unknown':
                    result.add_relationship(
                        from_name=node.name,
                        to_name=callee,
                        rel_type='calls',
                        line=child.lineno if hasattr(child, 'lineno') else node.lineno
                    )

    def _get_name(self, node) -> str:
        """Extract name from AST node."""
        if isinstance(node, python_ast.Name):
            return node.id
        elif isinstance(node, python_ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, python_ast.Subscript):
            value = self._get_name(node.value)
            slice_val = self._get_name(node.slice)
            return f"{value}[{slice_val}]"
        elif isinstance(node, python_ast.Constant):
            return str(node.value)
        elif isinstance(node, python_ast.Call):
            return self._get_name(node.func)
        return "Unknown"

    def _parse_assignment(
        self,
        node: python_ast.Assign,
        lines: List[str],
        file_path: str,
        result: ParseResult,
        exports: set
    ):
        """Parse module-level assignments (constants, type aliases)."""
        for target in node.targets:
            if isinstance(target, python_ast.Name):
                name = target.id
                # Skip private/dunder names and __all__
                if name.startswith('_') or name == '__all__':
                    continue

                # Determine type based on naming convention and value
                is_constant = name.isupper()  # SCREAMING_SNAKE_CASE
                is_type_alias = (
                    isinstance(node.value, python_ast.Subscript) or
                    (isinstance(node.value, python_ast.Name) and node.value.id in ('List', 'Dict', 'Set', 'Tuple', 'Optional', 'Union'))
                )

                if is_constant or is_type_alias:
                    comp_type = 'constant' if is_constant else 'type'
                    is_exported = name in exports or (not name.startswith('_') and not exports)

                    # Get line content for signature
                    line_content = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""

                    component = ComponentData(
                        name=name,
                        type=comp_type,
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        signature=line_content,
                        exported=is_exported
                    )
                    result.add_component(component)

    def _parse_annotated_assignment(
        self,
        node: python_ast.AnnAssign,
        lines: List[str],
        file_path: str,
        result: ParseResult,
        exports: set
    ):
        """Parse annotated assignments (typed constants, TypeAlias)."""
        if isinstance(node.target, python_ast.Name):
            name = node.target.id
            if name.startswith('_'):
                return

            # Check if it's a TypeAlias
            is_type_alias = (
                isinstance(node.annotation, python_ast.Name) and
                node.annotation.id == 'TypeAlias'
            )
            is_constant = name.isupper()

            if is_type_alias or is_constant:
                comp_type = 'type' if is_type_alias else 'constant'
                is_exported = name in exports or (not name.startswith('_') and not exports)

                line_content = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""

                component = ComponentData(
                    name=name,
                    type=comp_type,
                    file_path=file_path,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    signature=line_content,
                    exported=is_exported
                )
                result.add_component(component)

    def _is_route_decorator(self, decorator) -> Optional[Dict[str, Any]]:
        """Check if decorator is a route decorator and extract route info."""
        if isinstance(decorator, python_ast.Call):
            func = decorator.func
            # @app.get("/path") or @router.post("/path")
            if isinstance(func, python_ast.Attribute):
                method = func.attr.lower()
                if method in self.ROUTE_DECORATORS:
                    # Extract path from first argument
                    path = None
                    if decorator.args and isinstance(decorator.args[0], python_ast.Constant):
                        path = decorator.args[0].value
                    return {'method': method.upper(), 'path': path or '/'}
        elif isinstance(decorator, python_ast.Attribute):
            # @app.get (without call) - less common
            method = decorator.attr.lower()
            if method in self.ROUTE_DECORATORS:
                return {'method': method.upper(), 'path': '/'}
        return None
