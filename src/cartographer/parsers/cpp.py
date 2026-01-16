"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

C++ language parser.
"""

import re
from pathlib import Path
from typing import List

from ..database import ComponentData
from .base import BaseParser, ParseResult


class CppParser(BaseParser):
    """Parser for C++ language."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse C++ file."""
        result = ParseResult()
        lines = content.split('\n')

        # Extract includes
        self._extract_includes(content, file_path, result)

        # Extract components
        self._extract_namespaces(content, lines, file_path, result)
        self._extract_classes(content, lines, file_path, result)
        self._extract_structs(content, lines, file_path, result)
        self._extract_functions(content, lines, file_path, result)
        self._extract_templates(content, lines, file_path, result)
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

    def _extract_namespaces(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract namespace definitions."""
        pattern = r'^namespace\s+(\w+)(?:\s*=\s*(\w+))?'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                alias_of = match.group(2)

                if alias_of:
                    component = ComponentData(
                        name=name,
                        type='namespace_alias',
                        file_path=file_path,
                        line_start=i,
                        line_end=i,
                        signature=f"namespace {name} = {alias_of}",
                        exported=True
                    )
                else:
                    component = ComponentData(
                        name=name,
                        type='namespace',
                        file_path=file_path,
                        line_start=i,
                        line_end=self._find_block_end(lines, i - 1),
                        signature=f"namespace {name}",
                        exported=True
                    )
                result.add_component(component)

    def _extract_classes(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract class definitions."""
        pattern = r'^(?:template\s*<[^>]+>\s*)?class\s+(\w+)(?:\s*:\s*(?:public|private|protected)?\s*(\w+))?'

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if match := re.match(pattern, stripped):
                if ';' in stripped and '{' not in stripped:
                    continue

                name = match.group(1)
                base_class = match.group(2)

                modifiers = []
                if 'template' in stripped:
                    modifiers.append('template')

                component = ComponentData(
                    name=name,
                    type='class',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=stripped.rstrip('{').strip(),
                    exported=True,
                    modifiers=modifiers
                )
                result.add_component(component)

                if base_class:
                    result.add_relationship(
                        from_name=name,
                        to_name=base_class,
                        rel_type='extends',
                        line=i
                    )

    def _extract_structs(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract struct definitions."""
        pattern = r'^(?:template\s*<[^>]+>\s*)?struct\s+(\w+)'

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if match := re.match(pattern, stripped):
                if ';' in stripped and '{' not in stripped:
                    continue

                name = match.group(1)

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

    def _extract_functions(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract function definitions (including methods)."""
        func_pattern = r'^(?!.*class\s)(?!.*struct\s)(?:(?:static|inline|virtual|explicit|constexpr|extern)\s+)*(\w+(?:\s*[*&])*(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)\s*(?:const)?\s*(?:override)?\s*(?:final)?\s*\{'

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith('class ') or stripped.startswith('struct '):
                continue

            if match := re.match(func_pattern, stripped):
                return_type = match.group(1).strip()
                func_name = match.group(2)
                params_str = match.group(3).strip()

                if func_name.startswith('~') or return_type == func_name:
                    continue

                params = []
                if params_str:
                    for p in params_str.split(','):
                        p = p.strip()
                        if p and p != 'void':
                            parts = p.replace('*', ' * ').replace('&', ' & ').split()
                            if parts:
                                param_name = parts[-1].strip('*&')
                                param_type = ' '.join(parts[:-1])
                                params.append({'name': param_name, 'type': param_type})

                modifiers = []
                if 'static' in stripped:
                    modifiers.append('static')
                if 'inline' in stripped:
                    modifiers.append('inline')
                if 'virtual' in stripped:
                    modifiers.append('virtual')
                if 'constexpr' in stripped:
                    modifiers.append('constexpr')

                component = ComponentData(
                    name=func_name,
                    type='function',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=f"{return_type} {func_name}({params_str})",
                    params=params,
                    modifiers=modifiers,
                    exported=True
                )
                result.add_component(component)

    def _extract_templates(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract template function specializations."""
        pattern = r'^template\s*<([^>]+)>'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                template_params = match.group(1)

                if i < len(lines):
                    next_line = lines[i].strip()
                    func_match = re.match(r'(\w+(?:\s*[*&])*)\s+(\w+)\s*\(', next_line)
                    if func_match:
                        func_name = func_match.group(2)
                        component = ComponentData(
                            name=func_name,
                            type='template_function',
                            file_path=file_path,
                            line_start=i,
                            line_end=self._find_block_end(lines, i),
                            signature=f"template<{template_params}> {next_line.rstrip('{')}",
                            exported=True,
                            metadata={'template_params': template_params}
                        )
                        result.add_component(component)

    def _extract_enums(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract enum definitions (including enum class)."""
        pattern = r'^enum\s+(?:class\s+)?(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                is_enum_class = 'enum class' in line

                component = ComponentData(
                    name=name,
                    type='enum',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=f"enum {'class ' if is_enum_class else ''}{name}",
                    exported=True,
                    metadata={'scoped': is_enum_class}
                )
                result.add_component(component)

    def _extract_security_patterns(self, lines: List[str], file_path: str, result: ParseResult):
        """
        Extract security-relevant patterns for security auditing.
        Categories: input_source, output_sink, data_operation, security_control
        """
        # Input sources
        input_patterns = [
            # C-style input (also valid in C++)
            (r'\bgets\s*\(', 'gets', 'input_source'),
            (r'\bscanf\s*\(', 'scanf', 'input_source'),
            (r'\bfscanf\s*\(', 'fscanf', 'input_source'),
            (r'\bfgets\s*\(', 'fgets', 'input_source'),
            (r'\bgetenv\s*\(', 'getenv', 'input_source'),
            (r'\bargv\[', 'argv', 'input_source'),
            # C++ streams
            (r'\bcin\s*>>', 'cin', 'input_source'),
            (r'\bgetline\s*\(', 'getline', 'input_source'),
            (r'std::cin\s*>>', 'cin', 'input_source'),
        ]

        # Output sinks
        output_patterns = [
            # C-style
            (r'\bsystem\s*\(', 'system', 'output_sink'),
            (r'\bexec\w*\s*\(', 'exec', 'output_sink'),
            (r'\bpopen\s*\(', 'popen', 'output_sink'),
            (r'\bsprintf\s*\(', 'sprintf', 'output_sink'),
            (r'\bvsprintf\s*\(', 'vsprintf', 'output_sink'),
            # C++ streams
            (r'\bcout\s*<<', 'cout', 'output_sink'),
            (r'std::cout\s*<<', 'cout', 'output_sink'),
        ]

        # Data operations
        data_patterns = [
            # C-style memory
            (r'\bstrcpy\s*\(', 'strcpy', 'data_operation'),
            (r'\bstrcat\s*\(', 'strcat', 'data_operation'),
            (r'\bmemcpy\s*\(', 'memcpy', 'data_operation'),
            (r'\bmalloc\s*\(', 'malloc', 'data_operation'),
            (r'\bfree\s*\(', 'free', 'data_operation'),
            # C++ memory
            (r'\bnew\s+', 'new', 'data_operation'),
            (r'\bdelete\s+', 'delete', 'data_operation'),
            (r'\bdelete\[\]', 'delete_array', 'data_operation'),
            # Smart pointers (safer)
            (r'std::unique_ptr', 'unique_ptr', 'data_operation'),
            (r'std::shared_ptr', 'shared_ptr', 'data_operation'),
            (r'std::make_unique', 'make_unique', 'data_operation'),
            (r'std::make_shared', 'make_shared', 'data_operation'),
        ]

        # Security controls
        security_patterns = [
            (r'\bsnprintf\s*\(', 'snprintf', 'security_control'),
            (r'\bstd::string\b', 'std_string', 'security_control'),
            (r'\bstd::vector\b', 'std_vector', 'security_control'),
            (r'\bstd::array\b', 'std_array', 'security_control'),
            (r'static_cast<', 'static_cast', 'security_control'),
            (r'dynamic_cast<', 'dynamic_cast', 'security_control'),
            (r'reinterpret_cast<', 'reinterpret_cast', 'security_control'),
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
