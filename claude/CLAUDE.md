# Codebase Cartographer Integration

This project uses **Codebase Cartographer** for token-efficient code exploration.

## Quick Reference

```bash
# Find components (fastest - use this first!)
.claude-map/bin/claude-map find <name>

# Natural language queries
.claude-map/bin/claude-map query "<question>"

# Show file contents
.claude-map/bin/claude-map show <file>

# List public API
.claude-map/bin/claude-map exports

# Update map after changes
.claude-map/bin/claude-map update
```

## Best Practice: Search Before Read

**Before using the Read tool**, use the cartographer to find what you need:

```bash
# Find a component
.claude-map/bin/claude-map find UserProfile
# Output: class UserProfile(p:3, m:5) - src/models/user.py:42

# Then read only the specific lines
Read src/models/user.py lines 42-80
```

This saves **95%+ tokens** compared to reading entire files.

## Automatic Updates

The map is automatically updated when you modify files via hooks.
Use `/map update` for manual updates after git operations.

## Token Savings

| Query Type | Without Map | With Map | Savings |
|------------|-------------|----------|---------|
| Find component | 15,000 | 200 | 98.7% |
| Dependencies | 25,000 | 500 | 98.0% |
| List exports | 30,000 | 1,000 | 96.7% |

---
*Codebase Cartographer - Copyright (c) 2025 Breach Craft - Mike Piekarski*
