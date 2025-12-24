#!/bin/bash
# get-branch-prefix.sh - Map issue labels to conventional commit branch prefixes
#
# Usage: ./get-branch-prefix.sh "<comma-separated-labels>"
#
# Label-to-Prefix Mapping (priority order):
#   bug, defect, fix              → bug
#   documentation, docs           → docs
#   chore, maintenance, refactor, technical-debt → chore
#   enhancement, feature, (default) → feat
#
# Arguments:
#   $1 - Comma-separated labels (e.g., "bug, security, priority-high")
#
# Output:
#   Single prefix string: bug, docs, chore, or feat
#
# Examples:
#   ./get-branch-prefix.sh "bug, security"           # Output: bug
#   ./get-branch-prefix.sh "enhancement"             # Output: feat
#   ./get-branch-prefix.sh "documentation"           # Output: docs
#   ./get-branch-prefix.sh "chore, refactor"         # Output: chore
#   ./get-branch-prefix.sh ""                        # Output: feat
#   ./get-branch-prefix.sh "priority-high"           # Output: feat (default)

get_branch_prefix() {
    local labels="$1"

    # Priority order: bug > docs > chore > feat (default)

    # Check for bug-related labels (case-insensitive, word boundary)
    if echo "$labels" | grep -qiE '\bbug\b|\bdefect\b|\bfix\b'; then
        echo "bug"
        return 0
    fi

    # Check for documentation labels
    if echo "$labels" | grep -qiE '\bdocumentation\b|\bdocs\b'; then
        echo "docs"
        return 0
    fi

    # Check for chore/maintenance labels
    if echo "$labels" | grep -qiE '\bchore\b|\bmaintenance\b|\brefactor\b|\btechnical-debt\b'; then
        echo "chore"
        return 0
    fi

    # Default to feat for enhancement/feature or unknown
    echo "feat"
    return 0
}

# Main execution (when run directly, not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        head -26 "$0" | tail -24
        exit 0
    fi

    get_branch_prefix "$1"
fi
