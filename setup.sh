#!/bin/bash
# Codebase Cartographer - Unified Setup
# Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
#
# One-command setup that installs everything:
# - Portable venv with dependencies
# - Codebase mapping tools
# - Claude Code integration (hooks, skills, commands)
# - Initial codebase map
#
# Usage:
#   ./setup.sh                    # Setup in current directory
#   ./setup.sh /path/to/project   # Setup in specific directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"

echo "======================================================================"
echo "Codebase Cartographer - Unified Setup"
echo "Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>"
echo "======================================================================"
echo ""
echo "Project: $PROJECT_ROOT"
echo ""

# Find Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python 3.8+ is required but not found."
    echo "Please install Python from https://python.org"
    exit 1
fi

# Check Python version
PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python: $PYTHON (version $PY_VERSION)"

# Step 1: Install Cartographer
echo ""
echo "Step 1: Installing Codebase Cartographer..."
echo "----------------------------------------------------------------------"
$PYTHON "$SCRIPT_DIR/install.py" "$PROJECT_ROOT"

# Step 2: Initialize the map
echo ""
echo "Step 2: Initializing codebase map..."
echo "----------------------------------------------------------------------"
cd "$PROJECT_ROOT"

if [ -f ".claude-map/bin/claude-map" ]; then
    .claude-map/bin/claude-map init
else
    echo "Error: Installation failed - claude-map not found"
    exit 1
fi

# Step 3: Run benchmark
echo ""
echo "Step 3: Running token optimization benchmark..."
echo "----------------------------------------------------------------------"
.claude-map/bin/claude-map benchmark

# Done
echo ""
echo "======================================================================"
echo "Setup Complete!"
echo "======================================================================"
echo ""
echo "Installation:"
echo "  Map database: $PROJECT_ROOT/.claude-map/codebase.db"
echo "  CLI tool:     $PROJECT_ROOT/.claude-map/bin/claude-map"
echo "  Claude hooks: $PROJECT_ROOT/.claude/hooks/"
echo ""
echo "Quick Start:"
echo "  .claude-map/bin/claude-map find <name>      # Find component"
echo "  .claude-map/bin/claude-map query '<text>'   # Natural language query"
echo "  .claude-map/bin/claude-map show <file>      # Show file components"
echo "  .claude-map/bin/claude-map stats            # Show statistics"
echo ""
echo "Claude Integration:"
echo "  - Hooks auto-update the map when files change"
echo "  - Use /map command for manual updates"
echo "  - Read .claude/skills/cartographer.md for usage tips"
echo ""
echo "Uninstall:"
echo "  rm -rf .claude-map .claude/hooks/cartographer-* .claude/skills/cartographer.md"
echo ""
