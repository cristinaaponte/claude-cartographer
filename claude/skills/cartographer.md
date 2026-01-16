# Codebase Cartographer Skill

**Token-optimized codebase mapping for efficient code exploration**

Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>

---

## Overview

You have access to Codebase Cartographer, a tool that provides token-efficient codebase exploration. Instead of loading entire files (consuming 10,000-50,000+ tokens), you can query the codebase map which returns 200-2,000 tokens with the same information.

**Always prefer using the cartographer for codebase exploration before reading full files.**

## When to Use

Use the cartographer when you need to:
- Find components, classes, or functions by name
- Understand file dependencies and imports
- Get an overview of the codebase structure
- Find exported/public APIs
- Trace call chains between functions
- Search for code patterns

## Commands

The cartographer is available via the `.claude-map/bin/claude-map` CLI:

```bash
# Find components by name (fastest)
.claude-map/bin/claude-map find <name>

# Natural language query
.claude-map/bin/claude-map query "<question>"

# Show components in a file
.claude-map/bin/claude-map show <file_path>

# List exported/public components
.claude-map/bin/claude-map exports

# Get codebase statistics
.claude-map/bin/claude-map stats

# Update map after changes
.claude-map/bin/claude-map update
```

## Query Examples

```bash
# Find a specific component
.claude-map/bin/claude-map find UserProfile
.claude-map/bin/claude-map find authenticate

# Ask questions
.claude-map/bin/claude-map query "find authentication components"
.claude-map/bin/claude-map query "what does auth.py depend on"
.claude-map/bin/claude-map query "show me exported functions"
.claude-map/bin/claude-map query "call chain for process_request"

# File exploration
.claude-map/bin/claude-map show src/auth/user.py
.claude-map/bin/claude-map query "dependencies for database.py"
```

## Best Practices

### 1. Search Before Reading
Before using the Read tool on a file, use the cartographer to:
- Verify the file exists and contains what you need
- Find the specific line numbers of interest
- Understand the file's structure

```bash
# Instead of reading entire file:
.claude-map/bin/claude-map show src/large_file.py
# Then read only the specific lines you need
```

### 2. Find Components First
When looking for a class or function:
```bash
# Use find for quick lookup
.claude-map/bin/claude-map find ClassName
# Returns: class ClassName(p:3, m:5) - path/to/file.py:42
# Then read just that section
```

### 3. Understand Dependencies
Before modifying a file, check what depends on it:
```bash
.claude-map/bin/claude-map query "what calls function_name"
.claude-map/bin/claude-map query "dependencies for module.py"
```

### 4. Update After Changes
After making significant file changes, update the map:
```bash
.claude-map/bin/claude-map update
```

## Output Format

### Compact Format (~50 tokens per result)
```
class UserProfile(p:3, m:5) - auth/user.py:15
func authenticate(params:2, async, exp) - auth/login.py:42
template base.html(blocks:3, inc:2) - templates/base.html:1
```

### Summary Format (~200 tokens)
```
**UserProfile** (class) [exported]
Location: src/auth/user.py:15
Signature: `class UserProfile(BaseModel)`
Props: id: int, email: str, name: str
Methods: validate, to_dict, from_dict
Doc: User profile model with validation
```

## Token Savings

| Operation | Without Map | With Map | Savings |
|-----------|-------------|----------|---------|
| Find component | 15,000 | 200 | 98.7% |
| File dependencies | 25,000 | 500 | 98.0% |
| List exports | 30,000 | 1,000 | 96.7% |

## Initialization

If the map doesn't exist, initialize it first:
```bash
.claude-map/bin/claude-map init
```

## Integration Notes

- The map is stored in `.claude-map/codebase.db`
- Updates are incremental (only changed files)
- Hooks automatically update the map when you modify files
- Use `/map` command to manually trigger a full update
