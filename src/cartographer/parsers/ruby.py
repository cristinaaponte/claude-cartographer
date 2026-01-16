"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Ruby language parser.
"""

import re
from pathlib import Path
from typing import List

from ..database import ComponentData
from .base import BaseParser, ParseResult


class RubyParser(BaseParser):
    """Parser for Ruby language."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse Ruby file."""
        result = ParseResult()
        lines = content.split('\n')

        # Extract requires
        self._extract_requires(content, file_path, result)

        # Extract components
        self._extract_components(lines, file_path, result)

        # Extract security patterns
        self._extract_security_patterns(lines, file_path, result)

        return result

    def _extract_requires(self, content: str, file_path: str, result: ParseResult):
        """Extract require statements."""
        pattern = r"require(?:_relative)?\s+['\"]([^'\"]+)['\"]"
        file_stem = Path(file_path).stem

        for match in re.finditer(pattern, content):
            result.add_relationship(
                from_name=file_stem,
                to_name=match.group(1),
                rel_type='imports',
                line=content[:match.start()].count('\n') + 1
            )

    def _extract_components(self, lines: List[str], file_path: str, result: ParseResult):
        """Extract Ruby classes, modules, and methods."""
        current_class = None
        current_module = None
        indent_stack = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())

            # Track indent for end matching
            while indent_stack and indent_stack[-1][0] >= indent and stripped == 'end':
                popped = indent_stack.pop()
                if popped[1] == 'class':
                    current_class = None
                elif popped[1] == 'module':
                    current_module = None

            # Class definition
            if match := re.match(r'class\s+(\w+)(?:\s*<\s*(\w+))?', stripped):
                class_name = match.group(1)
                parent_class = match.group(2)

                component = ComponentData(
                    name=class_name,
                    type='class',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=stripped,
                    parent=parent_class,
                    exported=True
                )
                result.add_component(component)

                if parent_class:
                    result.add_relationship(
                        from_name=class_name,
                        to_name=parent_class,
                        rel_type='extends',
                        line=i
                    )

                current_class = class_name
                indent_stack.append((indent, 'class'))

            # Module definition
            elif match := re.match(r'module\s+(\w+)', stripped):
                module_name = match.group(1)

                component = ComponentData(
                    name=module_name,
                    type='module',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=stripped,
                    exported=True
                )
                result.add_component(component)

                current_module = module_name
                indent_stack.append((indent, 'module'))

            # Method definition
            elif match := re.match(r'def\s+(?:self\.)?(\w+[?!=]?)', stripped):
                method_name = match.group(1)
                is_class_method = 'self.' in stripped

                modifiers = ['class_method'] if is_class_method else []

                component = ComponentData(
                    name=method_name,
                    type='method',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=stripped,
                    parent=current_class or current_module,
                    modifiers=modifiers,
                    exported=not method_name.startswith('_')
                )
                result.add_component(component)

            # attr_accessor, attr_reader, attr_writer
            elif match := re.match(r'attr_(accessor|reader|writer)\s+(.+)', stripped):
                attr_type = match.group(1)
                attrs_str = match.group(2)
                attrs = re.findall(r':(\w+)', attrs_str)

                for attr in attrs:
                    component = ComponentData(
                        name=attr,
                        type='attribute',
                        file_path=file_path,
                        line_start=i,
                        line_end=i,
                        signature=f"attr_{attr_type} :{attr}",
                        parent=current_class or current_module,
                        metadata={'attr_type': attr_type},
                        exported=True
                    )
                    result.add_component(component)

            # RSpec describe blocks
            elif match := re.match(r"describe\s+['\"]?([^'\"]+)['\"]?\s+do", stripped):
                name = match.group(1).strip()
                name = re.sub(r'[^a-zA-Z0-9_]', '_', name)[:50]

                component = ComponentData(
                    name=name,
                    type='test_suite',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=stripped,
                    is_test=True,
                    exported=False
                )
                result.add_component(component)

            # RSpec it/context blocks
            elif match := re.match(r"(it|context|specify)\s+['\"]([^'\"]+)['\"]", stripped):
                block_type = match.group(1)
                name = match.group(2)
                name = re.sub(r'[^a-zA-Z0-9_]', '_', name)[:50]

                component = ComponentData(
                    name=name,
                    type='test_case' if block_type == 'it' else 'test_context',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=stripped,
                    is_test=True,
                    exported=False
                )
                result.add_component(component)

            # Rails scope/has_many/belongs_to
            elif match := re.match(r'(scope|has_many|has_one|belongs_to|has_and_belongs_to_many)\s+:(\w+)', stripped):
                assoc_type = match.group(1)
                assoc_name = match.group(2)

                component = ComponentData(
                    name=assoc_name,
                    type='association' if assoc_type != 'scope' else 'scope',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=stripped,
                    parent=current_class,
                    metadata={'association_type': assoc_type},
                    exported=True
                )
                result.add_component(component)

    def _extract_security_patterns(self, lines: List[str], file_path: str, result: ParseResult):
        """
        Extract security-relevant patterns for security auditing.
        Categories: input_source, output_sink, data_operation, security_control
        """
        # Input sources
        input_patterns = [
            # Rails request access
            (r'params\[', 'params', 'input_source'),
            (r'params\.permit\s*\(', 'params_permit', 'input_source'),
            (r'params\.require\s*\(', 'params_require', 'input_source'),
            (r'request\.headers\[', 'http_header', 'input_source'),
            (r'request\.env\[', 'request_env', 'input_source'),
            (r'cookies\[', 'cookie', 'input_source'),
            (r'session\[', 'session', 'input_source'),
            # Environment
            (r'ENV\[', 'env_var', 'input_source'),
            (r'ENV\.fetch\s*\(', 'env_var', 'input_source'),
            # User input
            (r'gets\b', 'stdin', 'input_source'),
            (r'ARGV\[', 'cli_arg', 'input_source'),
        ]

        # Output sinks
        output_patterns = [
            # Template rendering
            (r'\.html_safe\b', 'html_safe', 'output_sink'),
            (r'raw\s*\(', 'raw', 'output_sink'),
            (r'render\s+inline:', 'render_inline', 'output_sink'),
            # Code execution
            (r'eval\s*\(', 'eval', 'output_sink'),
            (r'instance_eval\s*\(', 'instance_eval', 'output_sink'),
            (r'class_eval\s*\(', 'class_eval', 'output_sink'),
            (r'send\s*\(', 'send', 'output_sink'),
            (r'public_send\s*\(', 'public_send', 'output_sink'),
            (r'system\s*\(', 'system', 'output_sink'),
            (r'exec\s*\(', 'exec', 'output_sink'),
            (r'`[^`]+`', 'backtick', 'output_sink'),
            (r'%x\{', 'backtick', 'output_sink'),
            # Deserialization
            (r'Marshal\.load\s*\(', 'marshal_load', 'output_sink'),
            (r'YAML\.load\s*\(', 'yaml_load', 'output_sink'),
        ]

        # Data operations
        data_patterns = [
            # ActiveRecord SQL
            (r'\.where\s*\(', 'where', 'data_operation'),
            (r'\.find_by_sql\s*\(', 'find_by_sql', 'data_operation'),
            (r'\.execute\s*\(', 'sql_execute', 'data_operation'),
            (r'\.select\s*\(', 'select', 'data_operation'),
            (r'\.joins\s*\(', 'joins', 'data_operation'),
            (r'\.order\s*\(', 'order', 'data_operation'),
            # File operations
            (r'File\.(open|read|write|delete)\s*\(', 'file_operation', 'data_operation'),
            (r'IO\.(read|write)\s*\(', 'io_operation', 'data_operation'),
        ]

        # Security controls
        security_patterns = [
            (r'ERB::Util\.html_escape\s*\(', 'html_escape', 'security_control'),
            (r'h\s*\(', 'html_escape', 'security_control'),
            (r'sanitize\s*\(', 'sanitize', 'security_control'),
            (r'strip_tags\s*\(', 'strip_tags', 'security_control'),
            (r'protect_from_forgery', 'csrf', 'security_control'),
            (r'authenticate_user!', 'auth', 'security_control'),
            (r'authorize!', 'authorize', 'security_control'),
            (r'BCrypt::', 'bcrypt', 'security_control'),
            (r'has_secure_password', 'secure_password', 'security_control'),
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
