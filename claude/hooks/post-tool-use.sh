#!/bin/bash
# Codebase Cartographer - Post Tool Use Hook
# Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
#
# This hook runs after Edit, Write, or NotebookEdit tools complete.
# It queues file updates to the codebase map.
#
# Hook receives JSON on stdin with tool information.

set -e

# Read hook input
INPUT=$(cat)

# Extract tool name
TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')

# Only process file modification tools
case "$TOOL_NAME" in
    Edit|Write|NotebookEdit)
        # Extract file path from tool input
        FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')

        if [ -n "$FILE_PATH" ]; then
            # Find project root (directory with .claude-map)
            CURRENT_DIR=$(dirname "$FILE_PATH")
            while [ "$CURRENT_DIR" != "/" ]; do
                if [ -d "$CURRENT_DIR/.claude-map" ]; then
                    PROJECT_ROOT="$CURRENT_DIR"
                    break
                fi
                CURRENT_DIR=$(dirname "$CURRENT_DIR")
            done

            # Queue update if map exists
            if [ -n "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/.claude-map/codebase.db" ]; then
                # Write to update queue (non-blocking)
                QUEUE_FILE="$PROJECT_ROOT/.claude-map/cache/update_queue.txt"
                echo "$FILE_PATH" >> "$QUEUE_FILE" 2>/dev/null || true

                # If queue has more than 10 files, trigger batch update
                if [ -f "$QUEUE_FILE" ]; then
                    QUEUE_SIZE=$(wc -l < "$QUEUE_FILE" 2>/dev/null || echo "0")
                    if [ "$QUEUE_SIZE" -gt 10 ]; then
                        # Run update in background
                        nohup "$PROJECT_ROOT/.claude-map/bin/claude-map" update > /dev/null 2>&1 &
                        rm -f "$QUEUE_FILE" 2>/dev/null || true
                    fi
                fi
            fi
        fi
        ;;
esac

# Always exit successfully (don't block Claude)
exit 0
