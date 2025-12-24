#!/bin/bash
# post-issue-comment.sh - Post a comment to a GitHub issue
#
# Usage: ./post-issue-comment.sh <repo> <issue-number> "<comment-body>"
#
# Posts a comment to the specified GitHub issue using the gh CLI.
#
# Arguments:
#   $1 - Repository (e.g., "owner/repo")
#   $2 - Issue number
#   $3 - Comment body (Markdown supported)
#
# Output:
#   COMMENT_POSTED=true|false
#   COMMENT_URL=<url> (if successful)
#   ERROR=<message> (if failed)
#
# Exit codes:
#   0 - Comment posted successfully
#   1 - Missing arguments
#   2 - gh CLI not available
#   3 - Failed to post comment
#
# Examples:
#   ./post-issue-comment.sh "owner/repo" 42 "Thanks for the report!"
#   ./post-issue-comment.sh "my-org/my-repo" 15 "Could you provide more details?"

set -e

post_issue_comment() {
    local repo="$1"
    local issue_number="$2"
    local comment_body="$3"

    # Validate inputs
    if [ -z "$repo" ]; then
        echo "Error: repo is required" >&2
        echo "COMMENT_POSTED=false"
        echo "ERROR=repo is required"
        return 1
    fi

    if [ -z "$issue_number" ]; then
        echo "Error: issue_number is required" >&2
        echo "COMMENT_POSTED=false"
        echo "ERROR=issue_number is required"
        return 1
    fi

    if [ -z "$comment_body" ]; then
        echo "Error: comment_body is required" >&2
        echo "COMMENT_POSTED=false"
        echo "ERROR=comment_body is required"
        return 1
    fi

    # Check gh CLI is available
    if ! command -v gh &>/dev/null; then
        echo "Error: gh CLI not installed" >&2
        echo "COMMENT_POSTED=false"
        echo "ERROR=gh CLI not installed"
        return 2
    fi

    # Post the comment and capture output
    local output
    if output=$(gh issue comment "$issue_number" --repo "$repo" --body "$comment_body" 2>&1); then
        echo "COMMENT_POSTED=true"
        # Try to extract comment URL from output
        local comment_url
        comment_url=$(echo "$output" | grep -oE 'https://github.com/[^[:space:]]+' | head -1 || echo "")
        if [ -n "$comment_url" ]; then
            echo "COMMENT_URL=$comment_url"
        fi
        return 0
    else
        echo "COMMENT_POSTED=false"
        # SEC-MED-004: Sanitize error output to avoid exposing secrets
        # Truncate long error messages and remove potential secrets
        local sanitized_output
        sanitized_output=$(echo "$output" | head -c 200 | tr -d '\n' | sed 's/[A-Za-z0-9_-]\{40,\}/[REDACTED]/g')
        echo "ERROR=$sanitized_output"
        return 3
    fi
}

# Main execution (when run directly, not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        head -30 "$0" | tail -28
        exit 0
    fi

    if [ $# -lt 3 ]; then
        echo "Usage: $0 <repo> <issue-number> \"<comment-body>\"" >&2
        exit 1
    fi

    post_issue_comment "$1" "$2" "$3"
fi
