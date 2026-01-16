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

        # Extract security patterns
        self._extract_security_patterns(lines, file_path, result)

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

    def _extract_security_patterns(self, lines: List[str], file_path: str, result: ParseResult):
        """
        Extract security-relevant patterns for security auditing.
        Categories: input_source, output_sink, data_operation, security_control
        """
        # Input sources - dangerous input functions
        input_patterns = [
            (r'\bgets\s*\(', 'gets', 'input_source'),
            (r'\bscanf\s*\(', 'scanf', 'input_source'),
            (r'\bfscanf\s*\(', 'fscanf', 'input_source'),
            (r'\bsscanf\s*\(', 'sscanf', 'input_source'),
            (r'\bfgets\s*\(', 'fgets', 'input_source'),
            (r'\bread\s*\(', 'read', 'input_source'),
            (r'\brecv\s*\(', 'recv', 'input_source'),
            (r'\brecvfrom\s*\(', 'recvfrom', 'input_source'),
            (r'\bgetenv\s*\(', 'getenv', 'input_source'),
            (r'\bargv\[', 'argv', 'input_source'),
        ]

        # Output sinks - dangerous output/execution
        output_patterns = [
            (r'\bsystem\s*\(', 'system', 'output_sink'),
            (r'\bexec\w*\s*\(', 'exec', 'output_sink'),
            (r'\bpopen\s*\(', 'popen', 'output_sink'),
            (r'\bprintf\s*\(', 'printf', 'output_sink'),
            (r'\bsprintf\s*\(', 'sprintf', 'output_sink'),
            (r'\bfprintf\s*\(', 'fprintf', 'output_sink'),
            (r'\bvprintf\s*\(', 'vprintf', 'output_sink'),
            (r'\bvsprintf\s*\(', 'vsprintf', 'output_sink'),
        ]

        # Data operations - memory/buffer operations
        data_patterns = [
            (r'\bstrcpy\s*\(', 'strcpy', 'data_operation'),
            (r'\bstrcat\s*\(', 'strcat', 'data_operation'),
            (r'\bstrncpy\s*\(', 'strncpy', 'data_operation'),
            (r'\bstrncat\s*\(', 'strncat', 'data_operation'),
            (r'\bmemcpy\s*\(', 'memcpy', 'data_operation'),
            (r'\bmemmove\s*\(', 'memmove', 'data_operation'),
            (r'\bmalloc\s*\(', 'malloc', 'data_operation'),
            (r'\bcalloc\s*\(', 'calloc', 'data_operation'),
            (r'\brealloc\s*\(', 'realloc', 'data_operation'),
            (r'\bfree\s*\(', 'free', 'data_operation'),
            (r'\bfopen\s*\(', 'fopen', 'data_operation'),
            (r'\bfwrite\s*\(', 'fwrite', 'data_operation'),
            (r'\bfread\s*\(', 'fread', 'data_operation'),
        ]

        # Security controls - safer alternatives
        security_patterns = [
            (r'\bsnprintf\s*\(', 'snprintf', 'security_control'),
            (r'\bstrlcpy\s*\(', 'strlcpy', 'security_control'),
            (r'\bstrlcat\s*\(', 'strlcat', 'security_control'),
            (r'\bstrncmp\s*\(', 'strncmp', 'security_control'),
            (r'\bmemcmp\s*\(', 'memcmp', 'security_control'),
            (r'\bsecure_getenv\s*\(', 'secure_getenv', 'security_control'),
        ]

        all_patterns = input_patterns + output_patterns + data_patterns + security_patterns

        for i, line in enumerate(lines, 1):
            for pattern, subtype, category in all_patterns:
                if match := re.search(pattern, line):
                    context = match.group(0)[:40].replace('\n', ' ').strip()
                    name = f"{category}_{subtype}_L{i}"

                    component = ComponentData(
                        name=name,
                        type='security_pattern',
                        file_path=file_path,
                        line_start=i,
                        line_end=i,
                        signature=line.strip()[:100],
                        exported=False,
                        metadata={
                            'category': category,
                            'subtype': subtype,
                            'pattern': pattern,
                            'context': context
                        }
                    )
                    result.add_component(component)
