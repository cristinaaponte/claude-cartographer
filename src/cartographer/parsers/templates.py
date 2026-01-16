"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Template language parsers (Jinja2, EJS, Handlebars).
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..database import ComponentData
from .base import BaseParser, ParseResult


class Jinja2Parser(BaseParser):
    """Parser for Jinja2/Django templates."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse Jinja2 template."""
        result = ParseResult()

        # Extract template info
        extends = self._extract_extends(content)
        blocks = self._extract_blocks(content)
        includes = self._extract_includes(content)
        macros = self._extract_macros(content, file_path, result)
        variables = self._extract_variables(content)

        # Create main template component
        template_name = Path(file_path).name

        component = ComponentData(
            name=template_name,
            type='template',
            file_path=file_path,
            line_start=1,
            line_end=content.count('\n') + 1,
            extends=extends,
            blocks=blocks,
            includes=includes,
            variables=variables,
            exported=True
        )
        result.add_component(component)

        # Add relationships
        if extends:
            result.add_relationship(
                from_name=template_name,
                to_name=extends,
                rel_type='extends',
                line=1
            )

        for inc in includes:
            result.add_relationship(
                from_name=template_name,
                to_name=inc,
                rel_type='imports',
                line=1
            )

        return result

    def _extract_extends(self, content: str) -> Optional[str]:
        """Extract extends directive."""
        match = re.search(r'{%\s*extends\s+[\'"]([^\'"]+)[\'"]', content)
        return match.group(1) if match else None

    def _extract_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract block definitions."""
        blocks = []
        for match in re.finditer(r'{%\s*block\s+(\w+)', content):
            line = content[:match.start()].count('\n') + 1
            blocks.append({'name': match.group(1), 'line': line})
        return blocks

    def _extract_includes(self, content: str) -> List[str]:
        """Extract include directives."""
        includes = []
        for match in re.finditer(r'{%\s*include\s+[\'"]([^\'"]+)[\'"]', content):
            includes.append(match.group(1))
        return list(set(includes))

    def _extract_macros(self, content: str, file_path: str, result: ParseResult) -> List[str]:
        """Extract macro definitions."""
        macros = []
        for match in re.finditer(r'{%\s*macro\s+(\w+)\s*\(([^)]*)\)', content):
            macro_name = match.group(1)
            params_str = match.group(2)
            line = content[:match.start()].count('\n') + 1

            params = []
            if params_str.strip():
                for p in params_str.split(','):
                    p = p.strip()
                    if '=' in p:
                        p = p.split('=')[0].strip()
                    if p:
                        params.append({'name': p})

            component = ComponentData(
                name=macro_name,
                type='macro',
                file_path=file_path,
                line_start=line,
                line_end=line,
                signature=f"macro {macro_name}({params_str})",
                params=params,
                exported=True
            )
            result.add_component(component)
            macros.append(macro_name)

        return macros

    def _extract_variables(self, content: str) -> List[str]:
        """Extract template variables."""
        variables = set()
        for match in re.finditer(r'{{\s*(\w+)', content):
            var = match.group(1)
            if var not in ('if', 'for', 'else', 'endif', 'endfor', 'block', 'endblock'):
                variables.add(var)
        return list(variables)


class EJSParser(BaseParser):
    """Parser for EJS templates."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse EJS template."""
        result = ParseResult()

        includes = self._extract_includes(content)
        variables = self._extract_variables(content)

        template_name = Path(file_path).name

        component = ComponentData(
            name=template_name,
            type='template',
            file_path=file_path,
            line_start=1,
            line_end=content.count('\n') + 1,
            includes=includes,
            variables=variables,
            exported=True
        )
        result.add_component(component)

        for inc in includes:
            result.add_relationship(
                from_name=template_name,
                to_name=inc,
                rel_type='imports',
                line=1
            )

        return result

    def _extract_includes(self, content: str) -> List[str]:
        """Extract include directives."""
        includes = []
        for match in re.finditer(r'<%[-=]?\s*include\s*\([\'"]([^\'"]+)[\'"]', content):
            includes.append(match.group(1))
        return list(set(includes))

    def _extract_variables(self, content: str) -> List[str]:
        """Extract template variables."""
        variables = set()
        for match in re.finditer(r'<%[=\-]?\s*(\w+)', content):
            var = match.group(1)
            if var not in ('if', 'for', 'else', 'include', 'var', 'let', 'const'):
                variables.add(var)
        return list(variables)


class HandlebarsParser(BaseParser):
    """Parser for Handlebars templates."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse Handlebars template."""
        result = ParseResult()

        partials = self._extract_partials(content)
        helpers = self._extract_helpers(content)
        variables = self._extract_variables(content)

        template_name = Path(file_path).name

        component = ComponentData(
            name=template_name,
            type='template',
            file_path=file_path,
            line_start=1,
            line_end=content.count('\n') + 1,
            includes=partials,
            variables=variables,
            exported=True
        )
        result.add_component(component)

        for partial in partials:
            result.add_relationship(
                from_name=template_name,
                to_name=partial,
                rel_type='imports',
                line=1
            )

        return result

    def _extract_partials(self, content: str) -> List[str]:
        """Extract partial references."""
        partials = []
        for match in re.finditer(r'{{>\s*(\w+)', content):
            partials.append(match.group(1))
        return list(set(partials))

    def _extract_helpers(self, content: str) -> List[str]:
        """Extract helper calls."""
        helpers = set()
        for match in re.finditer(r'{{#(\w+)', content):
            helpers.add(match.group(1))
        return list(helpers)

    def _extract_variables(self, content: str) -> List[str]:
        """Extract template variables."""
        variables = set()
        for match in re.finditer(r'{{\s*(\w+)', content):
            var = match.group(1)
            if var not in ('if', 'each', 'unless', 'with', 'else'):
                variables.add(var)
        return list(variables)
