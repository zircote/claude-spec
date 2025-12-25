#!/usr/bin/env bash
#
# check-approved-spec.sh - Prevention hook for claude-spec workflow
#
# This hook blocks Write/Edit operations to implementation files
# unless an approved spec exists in docs/spec/active/.
#
# Exit codes:
#   0 = Allow operation (approved spec exists OR file is exempt)
#   1 = Block operation (no approved spec for implementation files)
#
# Usage: Called by Claude Code PreToolUse hook
#   Input: JSON on stdin with tool_name, file_path
#   Output: JSON with decision (allow/block) and message

set -euo pipefail

# Parse input from stdin (expects JSON with tool_name and file_path)
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "unknown"')
FILE_PATH=$(echo "$INPUT" | jq -r '.file_path // ""')

# Only check Write and Edit tools
if [[ "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "Edit" ]]; then
    echo '{"decision": "allow", "message": "Not a file modification tool"}'
    exit 0
fi

# Exempt patterns - always allow these files/directories
EXEMPT_PATTERNS=(
    "docs/"
    "tests/"
    "test_"
    ".md$"
    ".json$"
    ".yaml$"
    ".yml$"
    ".toml$"
    ".gitignore"
    ".gitkeep"
    "CLAUDE.md"
    "README.md"
    "CHANGELOG.md"
    "LICENSE"
    "Makefile"
    ".claude/"
    "hooks/"
)

# Check if file matches any exempt pattern
for pattern in "${EXEMPT_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" =~ $pattern ]]; then
        echo '{"decision": "allow", "message": "File is exempt from spec requirement"}'
        exit 0
    fi
done

# Find project root (look for .git directory)
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# Check for approved specs in docs/spec/active/
SPEC_DIR="${PROJECT_ROOT}/docs/spec/active"

if [[ ! -d "$SPEC_DIR" ]]; then
    # No spec directory at all - block with guidance
    cat <<EOF
{
    "decision": "block",
    "message": "No spec directory found. Run /claude-spec:plan to create a specification before implementing."
}
EOF
    exit 1
fi

# Look for any approved spec (status: approved in README.md frontmatter)
APPROVED_SPEC=""
for readme in "$SPEC_DIR"/*/README.md; do
    if [[ -f "$readme" ]]; then
        if grep -q "^status: approved" "$readme" 2>/dev/null; then
            APPROVED_SPEC=$(dirname "$readme")
            break
        fi
    fi
done

if [[ -n "$APPROVED_SPEC" ]]; then
    SPEC_NAME=$(basename "$APPROVED_SPEC")
    cat <<EOF
{
    "decision": "allow",
    "message": "Approved spec found: ${SPEC_NAME}"
}
EOF
    exit 0
else
    cat <<EOF
{
    "decision": "block",
    "message": "No approved spec found.

To implement code changes, you must first:
1. Create a spec: /claude-spec:plan \"your feature idea\"
2. Approve the spec: /claude-spec:approve <slug>
3. Then implement: /claude-spec:implement <slug>

This ensures all implementation work is planned and reviewed.

If you need to skip the approval workflow, you can:
- Disable this hook in .claude/hooks.json
- Or approve an existing draft: /claude-spec:approve"
}
EOF
    exit 1
fi
