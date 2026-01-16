"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Schema/database language parsers (SQL, GraphQL, Prisma).
"""

import re
from typing import List

from ..database import ComponentData
from .base import BaseParser, ParseResult


class SQLParser(BaseParser):
    """Parser for SQL files (tables, views, functions, procedures)."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse SQL file."""
        result = ParseResult()
        lines = content.split('\n')

        self._extract_tables(content, lines, file_path, result)
        self._extract_views(content, lines, file_path, result)
        self._extract_functions(content, lines, file_path, result)
        self._extract_indexes(content, lines, file_path, result)

        return result

    def _extract_tables(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract CREATE TABLE statements."""
        pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+)[`"\]]?'

        for i, line in enumerate(lines, 1):
            if match := re.search(pattern, line, re.IGNORECASE):
                name = match.group(1)
                end_line = self._find_statement_end(lines, i - 1)

                component = ComponentData(
                    name=name,
                    type='table',
                    file_path=file_path,
                    line_start=i,
                    line_end=end_line,
                    signature=f"CREATE TABLE {name}",
                    exported=True
                )
                result.add_component(component)

    def _extract_views(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract CREATE VIEW statements."""
        pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+[`"\[]?(\w+)[`"\]]?'

        for i, line in enumerate(lines, 1):
            if match := re.search(pattern, line, re.IGNORECASE):
                name = match.group(1)
                end_line = self._find_statement_end(lines, i - 1)

                component = ComponentData(
                    name=name,
                    type='view',
                    file_path=file_path,
                    line_start=i,
                    line_end=end_line,
                    signature=f"CREATE VIEW {name}",
                    exported=True
                )
                result.add_component(component)

    def _extract_functions(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract CREATE FUNCTION/PROCEDURE statements."""
        pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:FUNCTION|PROCEDURE)\s+[`"\[]?(\w+)[`"\]]?'

        for i, line in enumerate(lines, 1):
            if match := re.search(pattern, line, re.IGNORECASE):
                name = match.group(1)
                is_procedure = 'PROCEDURE' in line.upper()

                component = ComponentData(
                    name=name,
                    type='procedure' if is_procedure else 'function',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_statement_end(lines, i - 1),
                    signature=line.strip()[:100],
                    exported=True
                )
                result.add_component(component)

    def _extract_indexes(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract CREATE INDEX statements."""
        pattern = r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+)[`"\]]?\s+ON\s+[`"\[]?(\w+)[`"\]]?'

        for i, line in enumerate(lines, 1):
            if match := re.search(pattern, line, re.IGNORECASE):
                index_name = match.group(1)
                table_name = match.group(2)

                component = ComponentData(
                    name=index_name,
                    type='index',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"INDEX {index_name} ON {table_name}",
                    metadata={'table': table_name},
                    exported=True
                )
                result.add_component(component)

    def _find_statement_end(self, lines: List[str], start_idx: int) -> int:
        """Find the end of a SQL statement (semicolon or next statement)."""
        paren_depth = 0
        for i in range(start_idx, len(lines)):
            line = lines[i]
            paren_depth += line.count('(') - line.count(')')
            if ';' in line and paren_depth <= 0:
                return i + 1
        return start_idx + 1


class GraphQLParser(BaseParser):
    """Parser for GraphQL schema files."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse GraphQL schema file."""
        result = ParseResult()
        lines = content.split('\n')

        self._extract_types(content, lines, file_path, result)
        self._extract_queries_mutations(content, lines, file_path, result)
        self._extract_enums(content, lines, file_path, result)
        self._extract_inputs(content, lines, file_path, result)
        self._extract_interfaces(content, lines, file_path, result)

        return result

    def _extract_types(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract type definitions."""
        pattern = r'^type\s+(\w+)(?:\s+implements\s+(\w+))?'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                implements = match.group(2)

                if name in ('Query', 'Mutation', 'Subscription'):
                    continue

                component = ComponentData(
                    name=name,
                    type='type',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported=True,
                    metadata={'implements': implements} if implements else {}
                )
                result.add_component(component)

                if implements:
                    result.add_relationship(
                        from_name=name,
                        to_name=implements,
                        rel_type='implements',
                        line=i
                    )

    def _extract_queries_mutations(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract Query and Mutation type fields as operations."""
        in_query = False
        in_mutation = False
        in_subscription = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if re.match(r'^type\s+Query\b', stripped):
                in_query = True
                continue
            elif re.match(r'^type\s+Mutation\b', stripped):
                in_mutation = True
                continue
            elif re.match(r'^type\s+Subscription\b', stripped):
                in_subscription = True
                continue
            elif stripped == '}':
                in_query = in_mutation = in_subscription = False
                continue

            if in_query or in_mutation or in_subscription:
                if match := re.match(r'(\w+)\s*(?:\([^)]*\))?\s*:', stripped):
                    field_name = match.group(1)
                    op_type = 'query' if in_query else ('mutation' if in_mutation else 'subscription')

                    component = ComponentData(
                        name=field_name,
                        type=op_type,
                        file_path=file_path,
                        line_start=i,
                        line_end=i,
                        signature=stripped,
                        exported=True
                    )
                    result.add_component(component)

    def _extract_enums(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract enum definitions."""
        pattern = r'^enum\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)

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

    def _extract_inputs(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract input type definitions."""
        pattern = r'^input\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)

                component = ComponentData(
                    name=name,
                    type='input',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=f"input {name}",
                    exported=True
                )
                result.add_component(component)

    def _extract_interfaces(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract interface definitions."""
        pattern = r'^interface\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)

                component = ComponentData(
                    name=name,
                    type='interface',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=f"interface {name}",
                    exported=True
                )
                result.add_component(component)


class PrismaParser(BaseParser):
    """Parser for Prisma schema files."""

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse Prisma schema file."""
        result = ParseResult()
        lines = content.split('\n')

        self._extract_models(content, lines, file_path, result)
        self._extract_enums(content, lines, file_path, result)
        self._extract_datasource(content, lines, file_path, result)
        self._extract_generators(content, lines, file_path, result)

        return result

    def _extract_models(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract model definitions."""
        pattern = r'^model\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)
                end_line = self._find_block_end(lines, i - 1)

                fields = []
                relations = []
                for j in range(i, end_line):
                    field_line = lines[j - 1].strip()
                    if field_match := re.match(r'(\w+)\s+(\w+)(\[\])?\s*(@relation)?', field_line):
                        field_name = field_match.group(1)
                        field_type = field_match.group(2)
                        is_relation = field_match.group(4) is not None or field_type[0].isupper()

                        fields.append(field_name)
                        if is_relation and field_type not in ('String', 'Int', 'Float', 'Boolean', 'DateTime', 'Json', 'Bytes', 'BigInt', 'Decimal'):
                            relations.append(field_type)

                component = ComponentData(
                    name=name,
                    type='model',
                    file_path=file_path,
                    line_start=i,
                    line_end=end_line,
                    signature=f"model {name}",
                    exported=True,
                    metadata={'fields': fields[:10], 'relations': relations}
                )
                result.add_component(component)

                for rel in relations:
                    result.add_relationship(
                        from_name=name,
                        to_name=rel,
                        rel_type='relates_to',
                        line=i
                    )

    def _extract_enums(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract enum definitions."""
        pattern = r'^enum\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)

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

    def _extract_datasource(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract datasource configuration."""
        pattern = r'^datasource\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)

                component = ComponentData(
                    name=name,
                    type='datasource',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=f"datasource {name}",
                    exported=True
                )
                result.add_component(component)

    def _extract_generators(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract generator configurations."""
        pattern = r'^generator\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.match(pattern, line.strip()):
                name = match.group(1)

                component = ComponentData(
                    name=name,
                    type='generator',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=f"generator {name}",
                    exported=True
                )
                result.add_component(component)
