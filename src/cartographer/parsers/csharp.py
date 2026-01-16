"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

C# language parser.
"""

import re
from pathlib import Path
from typing import List

from ..database import ComponentData
from .base import BaseParser, ParseResult


class CSharpParser(BaseParser):
    """Parser for C# language."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse C# file."""
        result = ParseResult()
        lines = content.split('\n')

        # Extract using statements
        self._extract_usings(content, file_path, result)

        # Extract namespace
        self._extract_namespaces(content, lines, file_path, result)

        # Extract components
        self._extract_classes(content, lines, file_path, result)
        self._extract_interfaces(content, lines, file_path, result)
        self._extract_structs(content, lines, file_path, result)
        self._extract_enums(content, lines, file_path, result)
        self._extract_records(content, lines, file_path, result)
        self._extract_delegates(content, lines, file_path, result)

        # Extract security patterns
        self._extract_security_patterns(lines, file_path, result)

        return result

    def _extract_usings(self, content: str, file_path: str, result: ParseResult):
        """Extract using statements."""
        pattern = r'^using\s+(?:static\s+)?([^;=]+);'
        file_stem = Path(file_path).stem

        for match in re.finditer(pattern, content, re.MULTILINE):
            using = match.group(1).strip()
            if '=' not in using:
                result.add_relationship(
                    from_name=file_stem,
                    to_name=using,
                    rel_type='imports',
                    line=content[:match.start()].count('\n') + 1
                )

    def _extract_namespaces(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract namespace declarations."""
        pattern = r'^namespace\s+([\w.]+)\s*[{;]'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                is_file_scoped = line.strip().endswith(';')

                component = ComponentData(
                    name=name,
                    type='namespace',
                    file_path=file_path,
                    line_start=i,
                    line_end=len(lines) if is_file_scoped else self._find_block_end(lines, i - 1),
                    signature=f"namespace {name}",
                    exported=True,
                    metadata={'file_scoped': is_file_scoped}
                )
                result.add_component(component)

    def _extract_classes(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract class definitions."""
        pattern = r'^(?:\[[\w\(\),\s]+\]\s*)?(?:public|private|protected|internal|sealed|abstract|static|partial|\s)+class\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*([^{]+))?'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                base_types = match.group(2)

                modifiers = []
                if 'public' in line:
                    modifiers.append('public')
                if 'private' in line:
                    modifiers.append('private')
                if 'protected' in line:
                    modifiers.append('protected')
                if 'internal' in line:
                    modifiers.append('internal')
                if 'sealed' in line:
                    modifiers.append('sealed')
                if 'abstract' in line:
                    modifiers.append('abstract')
                if 'static' in line:
                    modifiers.append('static')
                if 'partial' in line:
                    modifiers.append('partial')

                generic_match = re.search(r'<([^>]+)>', line)
                generic_params = generic_match.group(1) if generic_match else None

                component = ComponentData(
                    name=name,
                    type='class',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    modifiers=modifiers,
                    exported='public' in modifiers or 'internal' in modifiers,
                    metadata={'generic_params': generic_params} if generic_params else {}
                )
                result.add_component(component)

                if base_types:
                    for base in base_types.split(','):
                        base = base.strip().split('<')[0].strip()
                        if base and base != 'where':
                            result.add_relationship(
                                from_name=name,
                                to_name=base,
                                rel_type='extends',
                                line=i
                            )

                self._extract_class_members(lines, i, self._find_block_end(lines, i - 1), name, file_path, result)

    def _extract_class_members(self, lines: List[str], start: int, end: int, class_name: str, file_path: str, result: ParseResult):
        """Extract methods and properties within a class."""
        method_pattern = r'^(?:\[[\w\(\),\s]+\]\s*)?(?:public|private|protected|internal|virtual|override|abstract|static|async|sealed|\s)+(?:(\w+(?:<[^>]+>)?(?:\[\])?)\s+)?(\w+)\s*\(([^)]*)\)'
        prop_pattern = r'^(?:public|private|protected|internal|virtual|override|abstract|static|\s)+(\w+(?:<[^>]+>)?(?:\[\]|\?)?)\s+(\w+)\s*\{'

        for i in range(start, min(end, len(lines))):
            line = lines[i].strip()

            if re.match(r'(?:public|private|protected|internal|\s)*class\s', line):
                continue

            if match := re.match(method_pattern, line):
                return_type = match.group(1) or 'void'
                method_name = match.group(2)
                params_str = match.group(3)

                if method_name == class_name or method_name == f'~{class_name}':
                    continue

                modifiers = []
                if 'public' in line:
                    modifiers.append('public')
                if 'private' in line:
                    modifiers.append('private')
                if 'protected' in line:
                    modifiers.append('protected')
                if 'async' in line:
                    modifiers.append('async')
                if 'static' in line:
                    modifiers.append('static')
                if 'virtual' in line:
                    modifiers.append('virtual')
                if 'override' in line:
                    modifiers.append('override')
                if 'abstract' in line:
                    modifiers.append('abstract')

                params = []
                if params_str.strip():
                    for p in params_str.split(','):
                        p = p.strip()
                        if p:
                            parts = p.split()
                            if len(parts) >= 2:
                                param_type = ' '.join(parts[:-1])
                                param_name = parts[-1]
                                params.append({'name': param_name, 'type': param_type})

                component = ComponentData(
                    name=method_name,
                    type='method',
                    file_path=file_path,
                    line_start=i + 1,
                    line_end=self._find_block_end(lines, i),
                    signature=f"{return_type} {method_name}({params_str})",
                    params=params,
                    parent=class_name,
                    modifiers=modifiers,
                    exported='public' in modifiers,
                    is_async='async' in modifiers
                )
                result.add_component(component)

            elif match := re.match(prop_pattern, line):
                prop_type = match.group(1)
                prop_name = match.group(2)

                modifiers = []
                if 'public' in line:
                    modifiers.append('public')
                if 'private' in line:
                    modifiers.append('private')
                if 'protected' in line:
                    modifiers.append('protected')
                if 'static' in line:
                    modifiers.append('static')

                component = ComponentData(
                    name=prop_name,
                    type='property',
                    file_path=file_path,
                    line_start=i + 1,
                    line_end=i + 1,
                    signature=f"{prop_type} {prop_name}",
                    parent=class_name,
                    modifiers=modifiers,
                    exported='public' in modifiers
                )
                result.add_component(component)

    def _extract_interfaces(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract interface definitions."""
        pattern = r'^(?:\[[\w\(\),\s]+\]\s*)?(?:public|private|protected|internal|\s)+interface\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*([^{]+))?'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                base_interfaces = match.group(2)

                component = ComponentData(
                    name=name,
                    type='interface',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported='public' in line
                )
                result.add_component(component)

                if base_interfaces:
                    for base in base_interfaces.split(','):
                        base = base.strip().split('<')[0]
                        if base:
                            result.add_relationship(
                                from_name=name,
                                to_name=base,
                                rel_type='extends',
                                line=i
                            )

    def _extract_structs(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract struct definitions."""
        pattern = r'^(?:\[[\w\(\),\s]+\]\s*)?(?:public|private|protected|internal|readonly|\s)+struct\s+(\w+)(?:<[^>]+>)?'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)

                modifiers = []
                if 'readonly' in line:
                    modifiers.append('readonly')

                component = ComponentData(
                    name=name,
                    type='struct',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    modifiers=modifiers,
                    exported='public' in line
                )
                result.add_component(component)

    def _extract_enums(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract enum definitions."""
        pattern = r'^(?:\[[\w\(\),\s]+\]\s*)?(?:public|private|protected|internal|\s)+enum\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)

                component = ComponentData(
                    name=name,
                    type='enum',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported='public' in line
                )
                result.add_component(component)

    def _extract_records(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract record definitions (C# 9+)."""
        pattern = r'^(?:\[[\w\(\),\s]+\]\s*)?(?:public|private|protected|internal|sealed|abstract|\s)+record\s+(?:struct\s+|class\s+)?(\w+)(?:<[^>]+>)?'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)

                component = ComponentData(
                    name=name,
                    type='record',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1) if '{' in line else i,
                    signature=line.strip().rstrip('{;').strip(),
                    exported='public' in line
                )
                result.add_component(component)

    def _extract_delegates(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract delegate definitions."""
        pattern = r'^(?:public|private|protected|internal|\s)+delegate\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*\('

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                return_type = match.group(1)
                name = match.group(2)

                component = ComponentData(
                    name=name,
                    type='delegate',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=line.strip().rstrip(';'),
                    exported='public' in line
                )
                result.add_component(component)

    def _extract_security_patterns(self, lines: List[str], file_path: str, result: ParseResult):
        """
        Extract security-relevant patterns for security auditing.
        Categories: input_source, output_sink, data_operation, security_control
        """
        # Input sources
        input_patterns = [
            # ASP.NET request access
            (r'Request\.(Form|QueryString|Headers|Cookies)\[', 'request_data', 'input_source'),
            (r'Request\.Form\[', 'form_data', 'input_source'),
            (r'Request\.QueryString\[', 'query_string', 'input_source'),
            (r'Request\.Headers\[', 'http_header', 'input_source'),
            (r'Request\.Cookies\[', 'cookie', 'input_source'),
            (r'HttpContext\.Request', 'http_request', 'input_source'),
            # Model binding
            (r'\[FromBody\]', 'from_body', 'input_source'),
            (r'\[FromQuery\]', 'from_query', 'input_source'),
            (r'\[FromForm\]', 'from_form', 'input_source'),
            (r'\[FromHeader\]', 'from_header', 'input_source'),
            (r'\[FromRoute\]', 'from_route', 'input_source'),
            # Environment
            (r'Environment\.GetEnvironmentVariable\s*\(', 'env_var', 'input_source'),
            # Console input
            (r'Console\.ReadLine\s*\(', 'console_read', 'input_source'),
            (r'Console\.Read\s*\(', 'console_read', 'input_source'),
        ]

        # Output sinks
        output_patterns = [
            # HTML rendering
            (r'Html\.Raw\s*\(', 'html_raw', 'output_sink'),
            (r'@Html\.Raw\s*\(', 'html_raw', 'output_sink'),
            (r'HtmlString\s*\(', 'html_string', 'output_sink'),
            # Code execution
            (r'Process\.Start\s*\(', 'process_start', 'output_sink'),
            (r'Assembly\.Load', 'assembly_load', 'output_sink'),
            (r'Activator\.CreateInstance', 'activator', 'output_sink'),
            (r'Type\.InvokeMember', 'invoke_member', 'output_sink'),
            # Deserialization
            (r'BinaryFormatter\.Deserialize', 'binary_deserialize', 'output_sink'),
            (r'JsonConvert\.DeserializeObject', 'json_deserialize', 'output_sink'),
            (r'XmlSerializer\.Deserialize', 'xml_deserialize', 'output_sink'),
        ]

        # Data operations
        data_patterns = [
            # SQL
            (r'SqlCommand\s*\(', 'sql_command', 'data_operation'),
            (r'\.ExecuteNonQuery\s*\(', 'sql_execute', 'data_operation'),
            (r'\.ExecuteReader\s*\(', 'sql_reader', 'data_operation'),
            (r'\.ExecuteScalar\s*\(', 'sql_scalar', 'data_operation'),
            (r'FromSqlRaw\s*\(', 'sql_raw', 'data_operation'),
            (r'FromSqlInterpolated\s*\(', 'sql_interpolated', 'data_operation'),
            # Entity Framework
            (r'\.Where\s*\(', 'ef_where', 'data_operation'),
            (r'\.FirstOrDefault\s*\(', 'ef_query', 'data_operation'),
            (r'\.SaveChanges', 'ef_save', 'data_operation'),
            # File operations
            (r'File\.(Read|Write|Open|Create|Delete)', 'file_operation', 'data_operation'),
            (r'StreamReader\s*\(', 'stream_reader', 'data_operation'),
            (r'StreamWriter\s*\(', 'stream_writer', 'data_operation'),
        ]

        # Security controls
        security_patterns = [
            (r'HtmlEncoder\.Encode\s*\(', 'html_encode', 'security_control'),
            (r'WebUtility\.HtmlEncode\s*\(', 'html_encode', 'security_control'),
            (r'UrlEncoder\.Encode\s*\(', 'url_encode', 'security_control'),
            (r'AntiXssEncoder', 'antixss', 'security_control'),
            (r'\[ValidateAntiForgeryToken\]', 'csrf', 'security_control'),
            (r'\[Authorize\]', 'authorize', 'security_control'),
            (r'\[AllowAnonymous\]', 'allow_anonymous', 'security_control'),
            (r'PasswordHasher', 'password_hash', 'security_control'),
            (r'DataProtection', 'data_protection', 'security_control'),
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
