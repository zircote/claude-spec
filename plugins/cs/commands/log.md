---
argument-hint: "on|off|status|show"
description: "Toggle prompt logging for spec work"
---

# /cs:log - Prompt Logging Control

<role>
You manage prompt logging for spec projects. You can enable/disable logging and display log status/contents.
</role>

<command_argument>
$ARGUMENTS
</command_argument>

<execution>
## Parse Command

Marker and log files are at **project root** (not in docs/spec/active/) to ensure
the first prompt can be captured before spec directories are created.

Based on the argument provided:

### `on` - Enable logging
1. Create `.prompt-log-enabled` marker file at project root
2. Confirm logging is enabled

### `off` - Disable logging
1. Remove `.prompt-log-enabled` marker file from project root
2. Confirm logging is disabled

### `status` - Show current status
1. Check if `.prompt-log-enabled` exists at project root
2. Report logging status
3. Show log file size if exists

### `show` - Display recent log entries
1. Find `.prompt-log.json` at project root
2. Display last 10 entries in readable format
3. Show summary statistics

## Implementation

Execute the appropriate action based on the argument:

```bash
# Marker and log are at project root
MARKER_FILE=".prompt-log-enabled"
LOG_FILE=".prompt-log.json"
PROJECT_NAME=$(basename "$(pwd)")
```

For `on`:
```bash
touch "$MARKER_FILE"
echo "[OK] Prompt logging enabled for: $PROJECT_NAME"
echo "     Marker: $MARKER_FILE"
echo "     Log will be written to: $LOG_FILE"
```

For `off`:
```bash
rm -f "$MARKER_FILE"
echo "[OK] Prompt logging disabled for: $PROJECT_NAME"
```

For `status`:
```bash
if [ -f "$MARKER_FILE" ]; then
    echo "Logging: ENABLED"
else
    echo "Logging: DISABLED"
fi
echo "Project: $PROJECT_NAME"
if [ -f "$LOG_FILE" ]; then
    ENTRIES=$(wc -l < "$LOG_FILE")
    SIZE=$(du -h "$LOG_FILE" | cut -f1)
    echo "Log entries: $ENTRIES ($SIZE)"
fi
```

For `show`:
- Read `.prompt-log.json` from project root
- Parse NDJSON entries
- Display last 10 entries formatted nicely

## Response Format

After executing the command, provide a clear confirmation message.
</execution>
