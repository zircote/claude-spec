#!/bin/bash
# check-gh-prerequisites.sh - Verify GitHub CLI prerequisites for issue workflow
#
# Usage: ./check-gh-prerequisites.sh [--quiet]
#
# Checks:
#   1. gh CLI is installed
#   2. gh CLI is authenticated
#   3. Current directory is a GitHub repository
#
# Output (default):
#   GH_STATUS=installed|not_installed
#   GH_AUTH=authenticated|not_authenticated
#   GH_REPO=<owner/repo>|not_found
#   PREREQ_OK=true|false
#
# Exit codes:
#   0 - All prerequisites met
#   1 - gh CLI not installed
#   2 - Not authenticated
#   3 - Not in a GitHub repository
#
# Examples:
#   ./check-gh-prerequisites.sh
#   if ./check-gh-prerequisites.sh --quiet; then echo "Ready"; fi
#   eval "$(./check-gh-prerequisites.sh)"
#   echo "Repository: $GH_REPO"

set -e

QUIET=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --quiet|-q)
            QUIET=true
            shift
            ;;
        --help|-h)
            head -30 "$0" | tail -28
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Check gh CLI installed
if ! command -v gh &>/dev/null; then
    [ "$QUIET" = "false" ] && echo "GH_STATUS=not_installed"
    [ "$QUIET" = "false" ] && echo "PREREQ_OK=false"
    exit 1
fi
[ "$QUIET" = "false" ] && echo "GH_STATUS=installed"

# Check authentication status
if ! gh auth status &>/dev/null 2>&1; then
    [ "$QUIET" = "false" ] && echo "GH_AUTH=not_authenticated"
    [ "$QUIET" = "false" ] && echo "PREREQ_OK=false"
    exit 2
fi
[ "$QUIET" = "false" ] && echo "GH_AUTH=authenticated"

# Get repository info
# SFH-001: Preserve stderr for debugging while allowing command to fail gracefully
REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>&1) || REPO=""
# Filter out error messages, keeping only valid repo format (owner/repo)
if [[ ! "$REPO" =~ ^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$ ]]; then
    REPO=""
fi
if [ -z "$REPO" ]; then
    [ "$QUIET" = "false" ] && echo "GH_REPO=not_found"
    [ "$QUIET" = "false" ] && echo "PREREQ_OK=false"
    exit 3
fi
[ "$QUIET" = "false" ] && echo "GH_REPO=$REPO"
[ "$QUIET" = "false" ] && echo "PREREQ_OK=true"

exit 0
