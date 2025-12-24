#!/bin/bash
# build-issue-prompt.sh - Build initial prompt for Claude agent with issue context
#
# Usage: ./build-issue-prompt.sh <issue-number> "<issue-title>" <worktree-path>
#
# Generates a prompt string that:
#   - Invokes /claude-spec:plan with the issue reference
#   - Points agent to the .issue-context.json file
#   - Provides clear instructions for starting planning
#
# Arguments:
#   $1 - Issue number
#   $2 - Issue title
#   $3 - Worktree path
#
# Output:
#   Multi-line prompt string suitable for --prompt argument
#
# Examples:
#   ./build-issue-prompt.sh 42 "Fix authentication bug" ~/Projects/worktrees/repo/bug-42-fix-auth
#   PROMPT=$(./build-issue-prompt.sh 42 "Fix auth" "$WORKTREE_PATH")
#   launch-agent.sh "$WORKTREE_PATH" "" --prompt "$PROMPT"

build_issue_prompt() {
    local issue_number="$1"
    local issue_title="$2"
    local worktree_path="$3"

    # Validate inputs
    if [ -z "$issue_number" ]; then
        echo "Error: issue_number is required" >&2
        return 1
    fi

    if [ -z "$issue_title" ]; then
        echo "Error: issue_title is required" >&2
        return 1
    fi

    if [ -z "$worktree_path" ]; then
        echo "Error: worktree_path is required" >&2
        return 1
    fi

    # Build the prompt
    # SEC-CRIT-001: Use quoted heredoc delimiter to prevent shell expansion
    # This prevents command injection via malicious issue titles containing $() or ``
    local template
    template=$(cat << 'EOF_TEMPLATE'
/claude-spec:plan Issue #ISSUE_NUM: ISSUE_TITLE

This worktree was created for GitHub Issue #ISSUE_NUM.
Issue context is available at: WORKTREE_PATH/.issue-context.json

Please read the issue context and begin planning.
EOF_TEMPLATE
)
    # Escape special characters in inputs for safe sed substitution
    # Using | as delimiter since paths may contain /
    # SFH-002: Include pipe character | in escape pattern since it's our sed delimiter
    local safe_title safe_path
    safe_title=$(printf '%s' "$issue_title" | sed 's/[&/\|]/\\&/g')
    safe_path=$(printf '%s' "$worktree_path" | sed 's/[&/\|]/\\&/g')

    printf '%s\n' "$template" | \
        sed "s|ISSUE_NUM|${issue_number}|g" | \
        sed "s|ISSUE_TITLE|${safe_title}|g" | \
        sed "s|WORKTREE_PATH|${safe_path}|g"
}

# Main execution (when run directly, not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        head -26 "$0" | tail -24
        exit 0
    fi

    if [ $# -lt 3 ]; then
        echo "Usage: $0 <issue-number> \"<issue-title>\" <worktree-path>" >&2
        exit 1
    fi

    build_issue_prompt "$1" "$2" "$3"
fi
