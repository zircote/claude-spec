#!/bin/bash
# create-issue-worktree.sh - Create a git worktree for a GitHub issue
#
# Usage: ./create-issue-worktree.sh <issue-json> [worktree-base] [repo-name]
#
# Creates a git worktree with:
#   - Branch named according to conventional commits (bug/, feat/, docs/, chore/)
#   - .issue-context.json file with issue details for agent consumption
#
# Arguments:
#   $1 - Issue JSON (from gh issue list --json ...)
#   $2 - Worktree base directory (default: $HOME/Projects/worktrees)
#   $3 - Repository name (default: auto-detected from git)
#
# Issue JSON Required Fields:
#   - number: Issue number
#   - title: Issue title
#   - labels: Array of label objects with "name" field
#   - body: Issue description (can be null)
#   - url: Issue URL
#
# Output:
#   WORKTREE_PATH=<path>
#   BRANCH=<branch-name>
#   ISSUE_NUMBER=<number>
#
# Examples:
#   ./create-issue-worktree.sh '{"number":42,"title":"Fix bug","labels":[{"name":"bug"}],"body":"desc","url":"..."}'
#   ./create-issue-worktree.sh "$ISSUE_JSON" ~/Projects/worktrees my-repo

set -e

# Find script directory for sourcing dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the generate-branch-name function (which also sources get-branch-prefix)
source "$SCRIPT_DIR/generate-branch-name.sh"

create_issue_worktree() {
    local issue_json="$1"
    local worktree_base="${2:-$HOME/Projects/worktrees}"
    local repo_name="$3"

    # Validate input
    if [ -z "$issue_json" ]; then
        echo "Error: issue_json is required" >&2
        return 1
    fi

    # SEC-001: Validate JSON structure before parsing
    # This prevents command injection via malformed JSON
    if ! echo "$issue_json" | jq -e 'has("number") and has("title") and (.number | type == "number")' >/dev/null 2>&1; then
        echo "Error: Invalid issue JSON structure - must have 'number' (numeric) and 'title' fields" >&2
        return 1
    fi

    # Auto-detect repo name if not provided
    if [ -z "$repo_name" ]; then
        repo_name=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
        if [ -z "$repo_name" ]; then
            echo "Error: Could not detect repository name and none provided" >&2
            return 1
        fi
    fi

    # Parse issue data from JSON
    # SEC-001: Use jq's -r flag safely - values are validated after extraction
    local number title labels body url

    number=$(echo "$issue_json" | jq -r '.number')
    title=$(echo "$issue_json" | jq -r '.title // ""')
    labels=$(echo "$issue_json" | jq -r '[.labels[].name] | join(", ")' 2>/dev/null || echo "")
    body=$(echo "$issue_json" | jq -r '.body // ""')
    url=$(echo "$issue_json" | jq -r '.url // ""')

    # Validate parsed data
    if [ -z "$number" ] || [ "$number" = "null" ]; then
        echo "Error: Could not parse issue number from JSON" >&2
        return 1
    fi

    if [ -z "$title" ] || [ "$title" = "null" ]; then
        echo "Error: Could not parse issue title from JSON" >&2
        return 1
    fi

    # Generate branch name using our function
    local branch
    branch=$(generate_branch_name "$number" "$title" "$labels")

    # Convert branch to worktree slug (replace / with -)
    local worktree_slug
    worktree_slug=$(echo "$branch" | tr '/' '-')

    local worktree_path="${worktree_base}/${repo_name}/${worktree_slug}"

    # Create worktree directory structure
    mkdir -p "${worktree_base}/${repo_name}"

    # RES-MED-001: Check if branch/worktree already exists (idempotent operation)
    # If both branch and worktree exist together, return existing worktree info
    local branch_exists=false
    local worktree_exists=false

    if git show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null; then
        branch_exists=true
    fi

    if [ -d "$worktree_path" ]; then
        worktree_exists=true
    fi

    # If worktree exists with matching branch, return existing (idempotent)
    if [ "$worktree_exists" = true ]; then
        # Verify it's actually a git worktree for this branch
        local existing_branch
        existing_branch=$(git -C "$worktree_path" branch --show-current 2>/dev/null || echo "")
        if [ "$existing_branch" = "$branch" ]; then
            echo "INFO: Worktree already exists, returning existing path" >&2
            echo "WORKTREE_PATH=$worktree_path"
            echo "BRANCH=$branch"
            echo "ISSUE_NUMBER=$number"
            echo "EXISTING=true"
            return 0
        else
            echo "Error: Worktree path exists but with different branch: $worktree_path" >&2
            return 1
        fi
    fi

    # If only branch exists without worktree, that's an error
    if [ "$branch_exists" = true ]; then
        echo "Error: Branch '$branch' already exists but no worktree found" >&2
        echo "Hint: Use 'git worktree add $worktree_path $branch' to attach worktree" >&2
        return 1
    fi

    # SEC-003: Validate branch name format before git commands
    # Branch names must match: prefix/number-slug pattern
    if ! [[ "$branch" =~ ^[a-z]+/[0-9]+-[a-z0-9-]+$ ]]; then
        echo "Error: Invalid branch name format: $branch" >&2
        return 1
    fi

    # SEC-005: Validate worktree path is within expected base directory
    local canonical_base canonical_path
    canonical_base=$(cd "$worktree_base" 2>/dev/null && pwd -P)
    # Use mkdir -p to ensure parent exists, then get canonical path
    mkdir -p "$(dirname "$worktree_path")"
    canonical_path=$(cd "$(dirname "$worktree_path")" && pwd -P)/$(basename "$worktree_path")
    if [[ "$canonical_path" != "$canonical_base"/* ]]; then
        echo "Error: Worktree path escapes base directory" >&2
        return 1
    fi

    # Create git worktree
    git worktree add -b "$branch" "$worktree_path" HEAD

    # Convert labels string to JSON array for .issue-context.json
    local labels_json
    if [ -n "$labels" ] && [ "$labels" != "null" ]; then
        # Split by ", " and create JSON array
        labels_json=$(echo "$labels" | jq -R 'split(", ")')
    else
        labels_json="[]"
    fi

    # SEC-HIGH-002: Save issue context using jq for safe JSON construction
    # This prevents JSON injection via malicious issue data
    local context_file="${worktree_path}/.issue-context.json"
    jq -n \
        --argjson number "$number" \
        --arg title "$title" \
        --arg url "$url" \
        --arg body "$body" \
        --argjson labels "$labels_json" \
        --arg fetched_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{
            number: $number,
            title: $title,
            url: $url,
            body: $body,
            labels: $labels,
            fetched_at: $fetched_at
        }' > "$context_file"

    # COMP-MED-006: Set restrictive permissions (owner read/write only)
    # Prevents world-readable access to issue context which may contain sensitive data
    chmod 600 "$context_file"

    # Output results
    echo "WORKTREE_PATH=$worktree_path"
    echo "BRANCH=$branch"
    echo "ISSUE_NUMBER=$number"
}

# Main execution (when run directly, not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        head -36 "$0" | tail -34
        exit 0
    fi

    if [ $# -lt 1 ]; then
        echo "Usage: $0 <issue-json> [worktree-base] [repo-name]" >&2
        exit 1
    fi

    create_issue_worktree "$1" "${2:-}" "${3:-}"
fi
