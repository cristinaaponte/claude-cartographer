"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Base parser classes and shared utilities.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from ..database import ComponentData


@dataclass
class ParseResult:
    """Result of parsing a file."""
    components: List[ComponentData] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)

    def add_component(self, component: ComponentData):
        """Add a component."""
        self.components.append(component)

    def add_relationship(
        self,
        from_name: str,
        to_name: str,
        rel_type: str,
        line: Optional[int] = None,
        confidence: float = 1.0
    ):
        """Add a relationship."""
        self.relationships.append({
            'from': from_name,
            'to': to_name,
            'type': rel_type,
            'line': line,
            'confidence': confidence,
        })


class LanguageDetector:
    """Detect programming language from file path."""

    EXTENSION_MAP = {
        # Python
        '.py': 'python',
        '.pyw': 'python',
        '.pyi': 'python',

        # JavaScript/TypeScript
        '.js': 'javascript',
        '.jsx': 'javascript-react',
        '.mjs': 'javascript',
        '.cjs': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript-react',

        # Go
        '.go': 'go',

        # Ruby
        '.rb': 'ruby',
        '.rake': 'ruby',
        '.gemspec': 'ruby',

        # Vue/Svelte
        '.vue': 'vue',
        '.svelte': 'svelte',

        # Templates
        '.html': 'html',
        '.jinja': 'jinja2',
        '.jinja2': 'jinja2',
        '.j2': 'jinja2',
        '.ejs': 'ejs',
        '.hbs': 'handlebars',
        '.handlebars': 'handlebars',
        '.liquid': 'liquid',
        '.pug': 'pug',
        '.jade': 'pug',
        '.erb': 'erb',

        # Database/Schema
        '.sql': 'sql',
        '.graphql': 'graphql',
        '.gql': 'graphql',
        '.prisma': 'prisma',

        # C/C++
        '.c': 'c',
        '.h': 'c-header',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.hpp': 'cpp-header',
        '.hxx': 'cpp-header',
        '.hh': 'cpp-header',

        # C#
        '.cs': 'csharp',
    }

    def detect(self, file_path: Path) -> str:
        """Detect language from file path."""
        ext = file_path.suffix.lower()

        # Special case for .html - check if it's a template
        if ext == '.html':
            return self._detect_html_type(file_path)

        return self.EXTENSION_MAP.get(ext, 'unknown')

    def _detect_html_type(self, file_path: Path) -> str:
        """Detect if .html is Jinja2, Django, EJS, or plain HTML."""
        path_str = str(file_path).lower()

        # Check path for template indicators
        if 'templates' in path_str or 'views' in path_str:
            try:
                content = file_path.read_text(encoding='utf-8')[:2000]

                if '{%' in content or '{{' in content:
                    return 'jinja2'
                elif '<%' in content:
                    return 'ejs'
                elif '{{#' in content or '{{>' in content:
                    return 'handlebars'
            except:
                pass

        return 'html'


class BaseParser(ABC):
    """Base parser class."""

    @abstractmethod
    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse file content and extract components."""
        pass

    def _estimate_complexity(self, loc: int, params: int, methods: int) -> int:
        """Estimate complexity score (0-100)."""
        score = 0
        score += min(loc // 10, 30)
        score += min(params * 5, 20)
        score += min(methods * 3, 25)
        return min(score, 100)

    def _find_block_end(self, lines: List[str], start_idx: int) -> int:
        """Find the end of a code block (brace-delimited)."""
        brace_depth = 0
        found_opening = False

        for i in range(start_idx, len(lines)):
            line = lines[i]
            brace_depth += line.count('{') - line.count('}')

            if '{' in line:
                found_opening = True

            if found_opening and brace_depth == 0:
                return i + 1

        return start_idx + 1
