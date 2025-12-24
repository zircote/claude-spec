#!/bin/bash
# generate-branch-name.sh - Generate conventional commit branch name from issue data
#
# Usage: ./generate-branch-name.sh <issue-number> "<title>" "<labels>"
#
# Branch Name Format: <prefix>/<issue-number>-<slug>
#   - prefix: derived from labels via get-branch-prefix.sh
#   - issue-number: GitHub issue number
#   - slug: lowercase, hyphenated, max 40 chars
#
# Arguments:
#   $1 - Issue number (e.g., 42)
#   $2 - Issue title (e.g., "Fix authentication bug on mobile")
#   $3 - Comma-separated labels (e.g., "bug, security")
#
# Output:
#   Branch name string (e.g., "bug/42-fix-authentication-bug-on-mobile")
#
# Examples:
#   ./generate-branch-name.sh 42 "Fix authentication bug" "bug"
#   # Output: bug/42-fix-authentication-bug
#
#   ./generate-branch-name.sh 38 "Add dark mode support for user interface" "enhancement"
#   # Output: feat/38-add-dark-mode-support-for-user-interface
#
#   ./generate-branch-name.sh 35 "Update API documentation for v2 endpoints" "documentation"
#   # Output: docs/35-update-api-documentation-for-v2-endpoin

set -e

# Find script directory for sourcing dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the get-branch-prefix function
source "$SCRIPT_DIR/get-branch-prefix.sh"

generate_branch_name() {
    local issue_number="$1"
    local title="$2"
    local labels="$3"

    # Validate inputs
    if [ -z "$issue_number" ]; then
        echo "Error: issue_number is required" >&2
        return 1
    fi

    if [ -z "$title" ]; then
        echo "Error: title is required" >&2
        return 1
    fi

    # Get prefix from labels
    local prefix
    prefix=$(get_branch_prefix "$labels")

    # SEC-002: Slugify title safely using printf for proper quoting
    # 1. Convert to lowercase
    # 2. Replace non-alphanumeric with hyphens
    # 3. Collapse multiple hyphens
    # 4. Remove leading/trailing hyphens
    local slug
    # Use printf to safely handle the title without shell expansion
    slug=$(printf '%s' "$title" | \
        tr '[:upper:]' '[:lower:]' | \
        tr -cs '[:alnum:]' '-' | \
        sed 's/--*/-/g' | \
        sed 's/^-//;s/-$//')

    # Truncate slug to max 40 chars
    slug="${slug:0:40}"

    # Remove trailing hyphen if truncation created one
    slug="${slug%-}"

    # Format: prefix/issue-number-slug
    echo "${prefix}/${issue_number}-${slug}"
}

# Main execution (when run directly, not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        head -32 "$0" | tail -30
        exit 0
    fi

    if [ $# -lt 2 ]; then
        echo "Usage: $0 <issue-number> \"<title>\" [\"<labels>\"]" >&2
        exit 1
    fi

    generate_branch_name "$1" "$2" "${3:-}"
fi
