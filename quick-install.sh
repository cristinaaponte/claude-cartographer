#!/bin/bash
# Codebase Cartographer - Quick Installation
# Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
#
# Usage:
#   ./quick-install.sh                    # Install in current directory
#   ./quick-install.sh /path/to/project   # Install in specific directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-.}"

echo "Codebase Cartographer - Quick Install"
echo "Copyright (c) 2025 Breach Craft"
echo ""

# Find Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python not found. Please install Python 3.8+."
    exit 1
fi

echo "Using Python: $PYTHON"
echo "Project: $PROJECT_ROOT"
echo ""

# Run installer
exec "$PYTHON" "$SCRIPT_DIR/install.py" "$PROJECT_ROOT"
