"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

JavaScript/TypeScript language parser using regex.
"""

import re
from pathlib import Path
from typing import List

from ..database import ComponentData
from .base import BaseParser, ParseResult


class JavaScriptTypeScriptParser(BaseParser):
    """Parser for JavaScript/TypeScript/JSX/TSX using regex."""

    # HTTP methods for route detection
    HTTP_METHODS = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'all']

    def __init__(self, is_typescript: bool = False, is_react: bool = False):
        self.is_typescript = is_typescript
        self.is_react = is_react

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse JavaScript/TypeScript file."""
        result = ParseResult()
        lines = content.split('\n')

        # Extract imports
        self._extract_imports(content, file_path, result)

        # Extract components
        self._extract_classes(content, lines, file_path, result)
        self._extract_functions(content, lines, file_path, result)

        # Extract framework-specific patterns
        self._extract_route_handlers(content, lines, file_path, result)
        self._extract_middleware(content, lines, file_path, result)
        self._extract_object_methods(content, lines, file_path, result)

        # Extract test blocks
        self._extract_test_blocks(content, lines, file_path, result)

        if self.is_typescript:
            self._extract_interfaces(content, lines, file_path, result)
            self._extract_types(content, lines, file_path, result)
            self._extract_enums(content, lines, file_path, result)
            self._extract_abstract_classes(content, lines, file_path, result)

        if self.is_react:
            self._extract_react_components(content, lines, file_path, result)

        return result

    def _extract_imports(self, content: str, file_path: str, result: ParseResult):
        """Extract import statements."""
        patterns = [
            r'import\s+(?:\{[^}]+\}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s*\([\'"]([^\'"]+)[\'"]\)',
            r'require\s*\([\'"]([^\'"]+)[\'"]\)',
        ]

        file_stem = Path(file_path).stem

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                result.add_relationship(
                    from_name=file_stem,
                    to_name=match.group(1),
                    rel_type='imports',
                    line=content[:match.start()].count('\n') + 1
                )

    def _extract_classes(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract class definitions."""
        pattern = r'(?:export\s+)?(?:default\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'

        for i, line in enumerate(lines, 1):
            if match := re.search(pattern, line):
                is_exported = 'export' in line

                component = ComponentData(
                    name=match.group(1),
                    type='class',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported=is_exported
                )
                result.add_component(component)

                # Add extends relationship
                if match.group(2):
                    result.add_relationship(
                        from_name=match.group(1),
                        to_name=match.group(2),
                        rel_type='extends',
                        line=i
                    )

    def _extract_functions(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract function definitions."""
        # Regular functions (including generators)
        func_pattern = r'(?:export\s+)?(?:async\s+)?function\s*(\*)?\s*(\w+)\s*\('

        # Arrow functions
        arrow_pattern = r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[\w<>\[\]|&\s]+)?\s*=>'

        # Getter/setter pattern
        accessor_pattern = r'^\s*(?:export\s+)?(?:static\s+)?(get|set)\s+(\w+)\s*\('

        for i, line in enumerate(lines, 1):
            # Getter/Setter
            if match := re.search(accessor_pattern, line):
                accessor_type = match.group(1)
                name = f"{accessor_type}_{match.group(2)}"
                is_exported = 'export' in line

                component = ComponentData(
                    name=name,
                    type='accessor',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported=is_exported,
                    metadata={'accessor_type': accessor_type}
                )
                result.add_component(component)

            # Regular function (including generators)
            elif match := re.search(func_pattern, line):
                is_generator = match.group(1) == '*'
                is_async = 'async' in line
                is_exported = 'export' in line
                func_name = match.group(2)

                modifiers = []
                if is_generator:
                    modifiers.append('generator')
                if is_async:
                    modifiers.append('async')

                component = ComponentData(
                    name=func_name,
                    type='function',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=self._extract_signature(lines, i - 1),
                    exported=is_exported,
                    is_async=is_async,
                    modifiers=modifiers,
                    metadata={'generator': is_generator} if is_generator else {}
                )
                result.add_component(component)

            # Arrow function
            elif match := re.search(arrow_pattern, line):
                is_async = 'async' in line
                is_exported = 'export' in line

                component = ComponentData(
                    name=match.group(1),
                    type='function',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip(),
                    exported=is_exported,
                    is_async=is_async
                )
                result.add_component(component)

    def _extract_route_handlers(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract route handlers from Express, Hono, Fastify, Koa patterns."""
        route_pattern = (
            r'(\w+)\.(get|post|put|patch|delete|head|options|all)\s*\(\s*'
            r'[\'"`]([^\'"`,]+)[\'"`]'
        )

        for i, line in enumerate(lines, 1):
            if match := re.search(route_pattern, line, re.IGNORECASE):
                router_name = match.group(1)
                http_method = match.group(2).upper()
                route_path = match.group(3)

                if router_name.lower() in ('console', 'math', 'json', 'object', 'array', 'string'):
                    continue

                is_async = 'async' in line
                route_name = self._route_to_name(http_method, route_path)
                signature = f"{router_name}.{http_method.lower()}('{route_path}')"

                component = ComponentData(
                    name=route_name,
                    type='route',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=signature,
                    is_async=is_async,
                    exported=False,
                    metadata={
                        'http_method': http_method,
                        'path': route_path,
                        'router': router_name
                    }
                )
                result.add_component(component)

    def _route_to_name(self, method: str, path: str) -> str:
        """Convert route path to a meaningful component name."""
        clean_path = path.strip('/')
        if not clean_path:
            clean_path = 'root'

        clean_path = re.sub(r':(\w+)', r'\1', clean_path)
        clean_path = re.sub(r'\*', 'wildcard', clean_path)
        clean_path = re.sub(r'[^a-zA-Z0-9_]', '_', clean_path)
        clean_path = re.sub(r'_+', '_', clean_path)
        clean_path = clean_path.strip('_')

        return f"{method}_{clean_path}"

    def _extract_middleware(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract middleware registrations."""
        middleware_pattern = r'(\w+)\.use\s*\('

        for i, line in enumerate(lines, 1):
            if match := re.search(middleware_pattern, line):
                router_name = match.group(1)

                if router_name.lower() in ('console', 'promise', 'set', 'map'):
                    continue

                path_match = re.search(r"\.use\s*\(\s*['\"`]([^'\"`]+)['\"`]", line)
                mw_match = re.search(r"\.use\s*\(\s*(\w+)", line)

                if path_match:
                    path = path_match.group(1)
                    name = f"middleware_{path.strip('/').replace('/', '_') or 'root'}"
                elif mw_match and mw_match.group(1) not in ("'", '"', '`'):
                    name = f"use_{mw_match.group(1)}"
                else:
                    name = f"middleware_line_{i}"

                component = ComponentData(
                    name=name,
                    type='middleware',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=line.strip(),
                    exported=False
                )
                result.add_component(component)

    def _extract_object_methods(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract method definitions inside objects."""
        brace_depth = 0
        method_shorthand = r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{'
        method_property = r'^\s*(\w+)\s*:\s*(?:async\s+)?(?:function\s*)?\([^)]*\)\s*(?:=>)?\s*\{'

        for i, line in enumerate(lines, 1):
            brace_depth += line.count('{') - line.count('}')

            if brace_depth > 0:
                if match := re.match(method_shorthand, line):
                    method_name = match.group(1)
                    if method_name in ('if', 'for', 'while', 'switch', 'try', 'catch', 'finally', 'with'):
                        continue
                    if re.search(r'(?:export\s+)?(?:async\s+)?function\s+' + method_name, line):
                        continue

                    is_async = 'async' in line.split(method_name)[0]

                    component = ComponentData(
                        name=method_name,
                        type='method',
                        file_path=file_path,
                        line_start=i,
                        line_end=self._find_block_end(lines, i - 1),
                        signature=line.strip().rstrip('{').strip(),
                        is_async=is_async,
                        exported=False
                    )
                    result.add_component(component)

                elif match := re.match(method_property, line):
                    method_name = match.group(1)
                    is_async = 'async' in line

                    component = ComponentData(
                        name=method_name,
                        type='method',
                        file_path=file_path,
                        line_start=i,
                        line_end=self._find_block_end(lines, i - 1),
                        signature=line.strip().rstrip('{').strip(),
                        is_async=is_async,
                        exported=False
                    )
                    result.add_component(component)

    def _extract_test_blocks(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract test blocks from Jest, Mocha, Vitest, etc."""
        test_patterns = [
            (r"describe\s*\(\s*['\"`]([^'\"`]+)['\"`]", 'test_suite'),
            (r"it\s*\(\s*['\"`]([^'\"`]+)['\"`]", 'test_case'),
            (r"test\s*\(\s*['\"`]([^'\"`]+)['\"`]", 'test_case'),
            (r"beforeEach\s*\(", 'test_hook'),
            (r"afterEach\s*\(", 'test_hook'),
            (r"beforeAll\s*\(", 'test_hook'),
            (r"afterAll\s*\(", 'test_hook'),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, test_type in test_patterns:
                if match := re.search(pattern, line):
                    if match.lastindex and match.lastindex >= 1:
                        name = match.group(1)
                        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)[:50]
                    else:
                        name = test_type

                    component = ComponentData(
                        name=name,
                        type=test_type,
                        file_path=file_path,
                        line_start=i,
                        line_end=self._find_block_end(lines, i - 1),
                        signature=line.strip()[:100],
                        is_test=True,
                        exported=False
                    )
                    result.add_component(component)
                    break

    def _extract_enums(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract TypeScript enums."""
        pattern = r'(?:export\s+)?(?:const\s+)?enum\s+(\w+)'

        for i, line in enumerate(lines, 1):
            if match := re.search(pattern, line):
                is_exported = 'export' in line
                is_const = 'const' in line.split('enum')[0]

                component = ComponentData(
                    name=match.group(1),
                    type='enum',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported=is_exported,
                    metadata={'const': is_const}
                )
                result.add_component(component)

    def _extract_abstract_classes(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract abstract class definitions."""
        pattern = r'(?:export\s+)?abstract\s+class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+(\w+))?'

        for i, line in enumerate(lines, 1):
            if match := re.search(pattern, line):
                is_exported = 'export' in line

                component = ComponentData(
                    name=match.group(1),
                    type='class',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported=is_exported,
                    modifiers=['abstract'],
                    metadata={'abstract': True}
                )
                result.add_component(component)

                if match.group(2):
                    result.add_relationship(
                        from_name=match.group(1),
                        to_name=match.group(2),
                        rel_type='extends',
                        line=i
                    )

    def _extract_interfaces(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract TypeScript interfaces."""
        pattern = r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+(\w+))?'

        for i, line in enumerate(lines, 1):
            if match := re.search(pattern, line):
                is_exported = 'export' in line

                component = ComponentData(
                    name=match.group(1),
                    type='interface',
                    file_path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i - 1),
                    signature=line.strip().rstrip('{').strip(),
                    exported=is_exported
                )
                result.add_component(component)

                if match.group(2):
                    result.add_relationship(
                        from_name=match.group(1),
                        to_name=match.group(2),
                        rel_type='extends',
                        line=i
                    )

    def _extract_types(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract TypeScript type aliases."""
        pattern = r'(?:export\s+)?type\s+(\w+)\s*='

        for i, line in enumerate(lines, 1):
            if match := re.search(pattern, line):
                is_exported = 'export' in line

                component = ComponentData(
                    name=match.group(1),
                    type='type',
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=line.strip().rstrip(';').strip(),
                    exported=is_exported
                )
                result.add_component(component)

    def _extract_react_components(self, content: str, lines: List[str], file_path: str, result: ParseResult):
        """Extract React functional components with hooks."""
        for component in result.components:
            if component.type == 'function':
                start = component.line_start - 1
                end = min(component.line_end, len(lines))
                func_content = '\n'.join(lines[start:end])

                if '<' in func_content and '/>' in func_content or '></' in func_content:
                    component.type = 'component'

                    hooks_used = list(set(re.findall(r'(use\w+)\s*\(', func_content)))
                    component.hooks = hooks_used

                    rendered = list(set(re.findall(r'<(\w+)[\s/>]', func_content)))
                    rendered = [r for r in rendered if r[0].isupper()]
                    component.renders_components = rendered

                    api_patterns = [
                        r'fetch\s*\([\'"]([^\'"]+)[\'"]',
                        r'axios\.\w+\s*\([\'"]([^\'"]+)[\'"]',
                        r'useQuery\s*\([\'"]([^\'"]+)[\'"]',
                    ]
                    api_calls = []
                    for pattern in api_patterns:
                        for match in re.finditer(pattern, func_content):
                            api_calls.append({'url': match.group(1)})
                    component.api_calls = api_calls

    def _extract_signature(self, lines: List[str], start_idx: int) -> str:
        """Extract full function signature."""
        sig_lines = []
        paren_depth = 0
        found_opening = False

        for i in range(start_idx, min(start_idx + 5, len(lines))):
            line = lines[i].strip()
            sig_lines.append(line)

            paren_depth += line.count('(') - line.count(')')
            if '(' in line:
                found_opening = True

            if found_opening and paren_depth == 0:
                break

        signature = ' '.join(sig_lines)
        signature = re.sub(r'\s+', ' ', signature)
        signature = signature.split('{')[0].strip()
        return signature
