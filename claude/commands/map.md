# /map Command

Update or initialize the codebase map.

## Usage

```
/map [init|update|stats|find <name>]
```

## Actions

### Initialize (first time)
```
/map init
```
Creates the codebase map by scanning all source files.

### Update (incremental)
```
/map update
```
Updates only changed files since last scan.

### Statistics
```
/map stats
```
Shows mapping statistics and token savings.

### Quick Find
```
/map find <name>
```
Quick search for a component by name.

## Execution

When this command is invoked, run the appropriate claude-map CLI command:

```bash
# For /map init
.claude-map/bin/claude-map init

# For /map update (or just /map)
.claude-map/bin/claude-map update

# For /map stats
.claude-map/bin/claude-map stats

# For /map find <name>
.claude-map/bin/claude-map find <name>
```

## Notes

- If `.claude-map/` doesn't exist, suggest running `/map init` first
- The map is automatically updated by hooks when files change
- Use this command for manual full updates or after git operations
