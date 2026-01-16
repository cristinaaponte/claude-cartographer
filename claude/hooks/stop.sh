#!/bin/bash
# Codebase Cartographer - Stop Hook
# Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
#
# This hook runs when a Claude session ends.
# It processes any queued file updates to the codebase map.

set -e

# Find project root
find_project_root() {
    local dir="$PWD"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.claude-map" ]; then
            echo "$dir"
            return 0
        fi
        dir=$(dirname "$dir")
    done
    return 1
}

PROJECT_ROOT=$(find_project_root) || exit 0

# Check if map exists
if [ ! -f "$PROJECT_ROOT/.claude-map/codebase.db" ]; then
    exit 0
fi

# Process update queue if exists
QUEUE_FILE="$PROJECT_ROOT/.claude-map/cache/update_queue.txt"
if [ -f "$QUEUE_FILE" ] && [ -s "$QUEUE_FILE" ]; then
    echo "Updating codebase map..."
    "$PROJECT_ROOT/.claude-map/bin/claude-map" update 2>/dev/null || true
    rm -f "$QUEUE_FILE" 2>/dev/null || true
fi

exit 0
