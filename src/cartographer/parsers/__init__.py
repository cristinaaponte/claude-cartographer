"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Language parsers for extracting code structure.
"""

from pathlib import Path
from typing import Dict, List, Optional

# Base classes
from .base import BaseParser, ParseResult, LanguageDetector

# Language-specific parsers
from .python import PythonParser
from .javascript import JavaScriptTypeScriptParser
from .go import GoParser
from .ruby import RubyParser
from .c import CParser
from .cpp import CppParser
from .csharp import CSharpParser

# Template parsers
from .templates import Jinja2Parser, EJSParser, HandlebarsParser

# Schema parsers
from .schema import SQLParser, GraphQLParser, PrismaParser


def get_parser_for_file(file_path: Path, language: str) -> Optional[BaseParser]:
    """Get appropriate parser for file."""

    parser_map: Dict[str, BaseParser] = {
        # Python
        'python': PythonParser(),

        # JavaScript/TypeScript
        'javascript': JavaScriptTypeScriptParser(is_typescript=False, is_react=False),
        'javascript-react': JavaScriptTypeScriptParser(is_typescript=False, is_react=True),
        'typescript': JavaScriptTypeScriptParser(is_typescript=True, is_react=False),
        'typescript-react': JavaScriptTypeScriptParser(is_typescript=True, is_react=True),

        # Other languages
        'go': GoParser(),
        'ruby': RubyParser(),

        # C/C++
        'c': CParser(),
        'c-header': CParser(),
        'cpp': CppParser(),
        'cpp-header': CppParser(),

        # C#
        'csharp': CSharpParser(),

        # Templates
        'jinja2': Jinja2Parser(),
        'ejs': EJSParser(),
        'handlebars': HandlebarsParser(),

        # Schema
        'sql': SQLParser(),
        'graphql': GraphQLParser(),
        'prisma': PrismaParser(),
    }

    return parser_map.get(language)


def get_supported_languages() -> List[str]:
    """Get list of supported languages."""
    return [
        'python',
        'javascript', 'javascript-react', 'typescript', 'typescript-react',
        'go', 'ruby',
        'c', 'c-header', 'cpp', 'cpp-header',
        'csharp',
        'jinja2', 'ejs', 'handlebars',
        'sql', 'graphql', 'prisma'
    ]


# Export all public symbols
__all__ = [
    # Base
    'BaseParser',
    'ParseResult',
    'LanguageDetector',

    # Parsers
    'PythonParser',
    'JavaScriptTypeScriptParser',
    'GoParser',
    'RubyParser',
    'CParser',
    'CppParser',
    'CSharpParser',
    'Jinja2Parser',
    'EJSParser',
    'HandlebarsParser',
    'SQLParser',
    'GraphQLParser',
    'PrismaParser',

    # Factory functions
    'get_parser_for_file',
    'get_supported_languages',
]
