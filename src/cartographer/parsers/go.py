"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Go language parser.
"""

import re
from pathlib import Path
from typing import List

from ..database import ComponentData
from .base import BaseParser, ParseResult


class GoParser(BaseParser):
    """Parser for Go language."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse Go file."""
        result = ParseResult()
        lines = content.split('\n')

        # Extract imports
        self._extract_imports(content, file_path, result)

        # Extract components
        self._extract_structs(lines, file_path, result)
        self._extract_interfaces(lines, file_path, result)
        self._extract_functions(lines, file_path, result)
        self._extract_constants(content, lines, file_path, result)
        self._extract_type_aliases(lines, file_path, result)

        return result

    def _extract_imports(self, content: str, file_path: str, result: ParseResult):
        """Extract import statements."""
        pattern = r'import\s+(?:\(\s*)?(?:(\w+)\s+)?"([^"]+)"'
        file_stem = Path(file_path).stem

        for match in re.finditer(pattern, content):
            result.add_relationship(
                from_name=file_stem,
                to_name=match.group(2),
                rel_type='imports',
                line=content[:match.start()].count('\n') + 1
            )

    def _extract_structs(self, lines: List[str], file_path: str, result: ParseResult):
        """Extract Go structs."""
        pattern = r'^type\s+(\w+)\s+struct'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                is_exported = name[0].isupper()

                component = ComponentData(
                    name=name,
                    type='struct',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported=is_exported
                )
                result.add_component(component)

    def _extract_interfaces(self, lines: List[str], file_path: str, result: ParseResult):
        """Extract Go interfaces."""
        pattern = r'^type\s+(\w+)\s+interface'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                is_exported = name[0].isupper()

                component = ComponentData(
                    name=name,
                    type='interface',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported=is_exported
                )
                result.add_component(component)

    def _extract_functions(self, lines: List[str], file_path: str, result: ParseResult):
        """Extract Go functions and methods."""
        func_pattern = r'^func\s+(\w+)\s*\('
        method_pattern = r'^func\s+\((\w+)\s+\*?(\w+)\)\s+(\w+)\s*\('

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Method (with receiver)
            if match := re.match(method_pattern, stripped):
                receiver_type = match.group(2)
                name = match.group(3)
                is_exported = name[0].isupper()

                is_test = name.startswith('Test') or '_test.go' in file_path

                component = ComponentData(
                    name=name,
                    type='method',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=self._extract_go_signature(lines, i - 1),
                    parent=receiver_type,
                    exported=is_exported,
                    is_test=is_test
                )
                result.add_component(component)

            # Regular function
            elif match := re.match(func_pattern, stripped):
                name = match.group(1)
                is_exported = name[0].isupper()

                is_test = name.startswith('Test') or '_test.go' in file_path
                is_benchmark = name.startswith('Benchmark')
                is_example = name.startswith('Example')
                is_init = name == 'init'

                metadata = {}
                if is_benchmark:
                    metadata['subtype'] = 'benchmark'
                elif is_example:
                    metadata['subtype'] = 'example'
                elif is_init:
                    metadata['subtype'] = 'init'

                component = ComponentData(
                    name=name,
                    type='function',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=self._extract_go_signature(lines, i - 1),
                    exported=is_exported,
                    is_test=is_test or is_benchmark or is_example,
                    metadata=metadata
                )
                result.add_component(component)

    def _extract_go_signature(self, lines: List[str], start_idx: int) -> str:
        """Extract Go function signature."""
        sig_lines = []

        for i in range(start_idx, min(start_idx + 5, len(lines))):
            line = lines[i].strip()
            sig_lines.append(line)

            if '{' in line:
                break

        signature = ' '.join(sig_lines)
        signature = signature.split('{')[0].strip()
        return signature

    def _extract_constants(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract Go constants (const blocks and single constants)."""
        single_pattern = r'^const\s+(\w+)\s+(?:(\w+)\s+)?='

        in_const_block = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith('const ('):
                in_const_block = True
                continue

            if in_const_block and stripped == ')':
                in_const_block = False
                continue

            if in_const_block:
                const_match = re.match(r'(\w+)(?:\s+\w+)?\s*=', stripped)
                if const_match:
                    name = const_match.group(1)
                    is_exported = name[0].isupper()

                    component = ComponentData(
                        name=name,
                        type='constant',
                        file_path=file_path,
                        line_start=i,
                        line_end=i,
                        signature=stripped,
                        exported=is_exported
                    )
                    result.add_component(component)

            elif match := re.match(single_pattern, stripped):
                name = match.group(1)
                is_exported = name[0].isupper()

                component = ComponentData(
                    name=name,
                    type='constant',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=stripped,
                    exported=is_exported
                )
                result.add_component(component)

    def _extract_type_aliases(self, lines: List[str], file_path: str, result: ParseResult):
        """Extract Go type aliases (type Name = OtherType)."""
        pattern = r'^type\s+(\w+)\s+=\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                aliased_type = match.group(2)
                is_exported = name[0].isupper()

                component = ComponentData(
                    name=name,
                    type='type',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=line.strip(),
                    exported=is_exported,
                    metadata={'alias_of': aliased_type}
                )
                result.add_component(component)
