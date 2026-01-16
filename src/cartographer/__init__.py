"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Package initialization and exports.
"""

__version__ = "3.0.0"
__author__ = "Mike Piekarski"
__email__ = "mp@breachcraft.io"
__copyright__ = "Copyright (c) 2025 Breach Craft"
__license__ = "MIT"

from .database import TokenOptimizedDatabase, ComponentData
from .mapper import CodebaseMapper
from .integration import ClaudeCodeIntegration
from .watcher import CodebaseWatcher
from .benchmark import TokenOptimizationBenchmark
from .claude_integration import ClaudeIntegrationInstaller
from .session_tracker import SessionTracker, SessionStats, QueryRecord

__all__ = [
    'TokenOptimizedDatabase',
    'ComponentData',
    'CodebaseMapper',
    'ClaudeCodeIntegration',
    'CodebaseWatcher',
    'TokenOptimizationBenchmark',
    'ClaudeIntegrationInstaller',
    'SessionTracker',
    'SessionStats',
    'QueryRecord',
    '__version__',
    '__author__',
    '__email__',
]
