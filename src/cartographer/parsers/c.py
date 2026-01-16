"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

C language parser.
"""

import re
from pathlib import Path
from typing import List

from ..database import ComponentData
from .base import BaseParser, ParseResult


class CParser(BaseParser):
    """Parser for C language."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse C file."""
        result = ParseResult()
        lines = content.split('\n')

        # Extract includes
        self._extract_includes(content, file_path, result)

        # Extract components
        self._extract_structs(content, lines, file_path, result)
        self._extract_typedefs(content, lines, file_path, result)
        self._extract_functions(content, lines, file_path, result)
        self._extract_macros(content, lines, file_path, result)
        self._extract_enums(content, lines, file_path, result)

        return result

    def _extract_includes(self, content: str, file_path: str, result: ParseResult):
        """Extract #include directives."""
        pattern = r'#include\s+[<"]([^>"]+)[>"]'
        file_stem = Path(file_path).stem

        for match in re.finditer(pattern, content):
            result.add_relationship(
                from_name=file_stem,
                to_name=match.group(1),
                rel_type='imports',
                line=content[:match.start()].count('\n') + 1
            )

    def _extract_structs(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract struct definitions."""
        pattern = r'^(?:typedef\s+)?struct\s+(\w+)?\s*\{'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                if name:
                    component = ComponentData(
                        name=name,
                        type='struct',
                        file_path=file_path,
                        line_start=i,
                        line_end=self._find_block_end(lines, i - 1),
                        signature=f"struct {name}",
                        exported=True
                    )
                    result.add_component(component)

    def _extract_typedefs(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract typedef declarations."""
        pattern = r'^typedef\s+(?!struct|enum|union)(.+?)\s+(\w+)\s*;'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(2)
                base_type = match.group(1)

                component = ComponentData(
                    name=name,
                    type='type',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"typedef {base_type} {name}",
                    exported=True
                )
                result.add_component(component)

    def _extract_functions(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract function definitions."""
        func_pattern = r'^(?:static\s+)?(?:inline\s+)?(?:extern\s+)?(\w+(?:\s*\*)*)\s+(\w+)\s*\(([^)]*)\)\s*\{'

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('#') or not line:
                i += 1
                continue

            if match := re.match(func_pattern, line):
                return_type = match.group(1).strip()
                func_name = match.group(2)
                params_str = match.group(3).strip()

                params = []
                if params_str and params_str != 'void':
                    for p in params_str.split(','):
                        p = p.strip()
                        if p:
                            parts = p.replace('*', ' * ').split()
                            if parts:
                                param_name = parts[-1].strip('*')
                                param_type = ' '.join(parts[:-1])
                                params.append({'name': param_name, 'type': param_type})

                is_static = 'static' in lines[i]
                is_test = func_name.startswith('test') or '_test' in file_path

                modifiers = []
                if is_static:
                    modifiers.append('static')
                if 'inline' in lines[i]:
                    modifiers.append('inline')

                component = ComponentData(
                    name=func_name,
                    type='function',
                    file_path=file_path,
                    line_start=i + 1,
                    line_end=self._find_block_end(lines, i),
                    signature=f"{return_type} {func_name}({params_str})",
                    params=params,
                    modifiers=modifiers,
                    exported=not is_static,
                    is_test=is_test
                )
                result.add_component(component)

            i += 1

    def _extract_macros(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract #define macros."""
        pattern = r'^#define\s+(\w+)(?:\(([^)]*)\))?\s*(.*)?'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                params_str = match.group(2)

                is_func_macro = params_str is not None

                signature = f"#define {name}"
                if is_func_macro:
                    signature += f"({params_str})"

                component = ComponentData(
                    name=name,
                    type='macro',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=signature,
                    exported=True,
                    metadata={'function_like': is_func_macro}
                )
                result.add_component(component)

    def _extract_enums(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract enum definitions."""
        pattern = r'^(?:typedef\s+)?enum\s+(\w+)?\s*\{'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                if name:
                    component = ComponentData(
                        name=name,
                        type='enum',
                        file_path=file_path,
                        line_start=i,
                        line_end=self._find_block_end(lines, i - 1),
                        signature=f"enum {name}",
                        exported=True
                    )
                    result.add_component(component)
