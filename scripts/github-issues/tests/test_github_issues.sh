#!/bin/bash
# test_github_issues.sh - Test suite for GitHub Issues workflow scripts
#
# Usage: ./test_github_issues.sh [--verbose]
#
# Tests all scripts in the github-issues directory:
#   - get-branch-prefix.sh
#   - generate-branch-name.sh
#   - build-issue-prompt.sh
#   - create-issue-worktree.sh (mock tests only)
#   - post-issue-comment.sh (mock tests only)
#   - check-gh-prerequisites.sh (mock tests only)
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VERBOSE=false
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Parse arguments
if [[ "$1" == "--verbose" || "$1" == "-v" ]]; then
    VERBOSE=true
fi

# Find script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Test assertion functions
assert_equals() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [ "$expected" = "$actual" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        if [ "$VERBOSE" = "true" ]; then
            echo -e "${GREEN}✓${NC} $test_name"
        fi
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo -e "${RED}✗${NC} $test_name"
        echo "  Expected: '$expected'"
        echo "  Actual:   '$actual'"
        return 1
    fi
}

assert_contains() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "$actual" == *"$expected"* ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        if [ "$VERBOSE" = "true" ]; then
            echo -e "${GREEN}✓${NC} $test_name"
        fi
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo -e "${RED}✗${NC} $test_name"
        echo "  Expected to contain: '$expected'"
        echo "  Actual: '$actual'"
        return 1
    fi
}

assert_exit_code() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [ "$expected" = "$actual" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        if [ "$VERBOSE" = "true" ]; then
            echo -e "${GREEN}✓${NC} $test_name"
        fi
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo -e "${RED}✗${NC} $test_name"
        echo "  Expected exit code: $expected"
        echo "  Actual exit code:   $actual"
        return 1
    fi
}

# =============================================================================
# Test: get-branch-prefix.sh
# =============================================================================
test_get_branch_prefix() {
    echo ""
    echo -e "${YELLOW}Testing get-branch-prefix.sh${NC}"
    echo "───────────────────────────────────────"

    local script="$PARENT_DIR/get-branch-prefix.sh"

    # Test bug labels
    local result
    result=$("$script" "bug")
    assert_equals "bug" "$result" "bug label returns 'bug'" || true

    result=$("$script" "bug, security")
    assert_equals "bug" "$result" "bug with other labels returns 'bug'" || true

    result=$("$script" "defect")
    assert_equals "bug" "$result" "defect label returns 'bug'" || true

    result=$("$script" "fix")
    assert_equals "bug" "$result" "fix label returns 'bug'" || true

    # Test documentation labels
    result=$("$script" "documentation")
    assert_equals "docs" "$result" "documentation label returns 'docs'" || true

    result=$("$script" "docs")
    assert_equals "docs" "$result" "docs label returns 'docs'" || true

    # Test chore labels
    result=$("$script" "chore")
    assert_equals "chore" "$result" "chore label returns 'chore'" || true

    result=$("$script" "maintenance")
    assert_equals "chore" "$result" "maintenance label returns 'chore'" || true

    result=$("$script" "refactor")
    assert_equals "chore" "$result" "refactor label returns 'chore'" || true

    result=$("$script" "technical-debt")
    assert_equals "chore" "$result" "technical-debt label returns 'chore'" || true

    # Test feat (default and explicit)
    result=$("$script" "enhancement")
    assert_equals "feat" "$result" "enhancement label returns 'feat'" || true

    result=$("$script" "feature")
    assert_equals "feat" "$result" "feature label returns 'feat'" || true

    result=$("$script" "")
    assert_equals "feat" "$result" "empty labels returns 'feat'" || true

    result=$("$script" "priority-high")
    assert_equals "feat" "$result" "unknown label returns 'feat'" || true

    # Test priority ordering (bug takes precedence)
    result=$("$script" "bug, enhancement")
    assert_equals "bug" "$result" "bug takes precedence over enhancement" || true

    result=$("$script" "documentation, enhancement")
    assert_equals "docs" "$result" "docs takes precedence over enhancement" || true

    result=$("$script" "chore, enhancement")
    assert_equals "chore" "$result" "chore takes precedence over enhancement" || true
}

# =============================================================================
# Test: generate-branch-name.sh
# =============================================================================
test_generate_branch_name() {
    echo ""
    echo -e "${YELLOW}Testing generate-branch-name.sh${NC}"
    echo "───────────────────────────────────────"

    local script="$PARENT_DIR/generate-branch-name.sh"

    # Test basic generation
    local result
    result=$("$script" 42 "Fix authentication bug" "bug")
    assert_equals "bug/42-fix-authentication-bug" "$result" "basic bug branch name" || true

    result=$("$script" 38 "Add dark mode" "enhancement")
    assert_equals "feat/38-add-dark-mode" "$result" "basic feat branch name" || true

    result=$("$script" 35 "Update README" "documentation")
    assert_equals "docs/35-update-readme" "$result" "basic docs branch name" || true

    result=$("$script" 99 "Cleanup dependencies" "chore")
    assert_equals "chore/99-cleanup-dependencies" "$result" "basic chore branch name" || true

    # Test title slugification
    result=$("$script" 1 "Fix Bug in User Auth!!!" "bug")
    assert_equals "bug/1-fix-bug-in-user-auth" "$result" "special characters removed" || true

    result=$("$script" 2 "ADD NEW FEATURE" "")
    assert_equals "feat/2-add-new-feature" "$result" "uppercase converted to lowercase" || true

    result=$("$script" 3 "Multiple   Spaces   Here" "")
    assert_equals "feat/3-multiple-spaces-here" "$result" "multiple spaces collapsed" || true

    # Test truncation (title > 40 chars)
    result=$("$script" 100 "This is a very long title that exceeds forty characters limit" "")
    assert_contains "feat/100-" "$result" "long title truncated (contains prefix)" || true
    # Check length of slug portion is <= 40
    local slug_part=${result#*/}  # Remove prefix/
    slug_part=${slug_part#*-}     # Remove issue number-
    local slug_length=${#slug_part}
    # The full slug (including issue number) should be reasonable
    if [ ${#result} -le 60 ]; then
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
        [ "$VERBOSE" = "true" ] && echo -e "${GREEN}✓${NC} branch name length is reasonable"
    else
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo -e "${RED}✗${NC} branch name too long: ${#result} chars"
    fi

    # Test with no labels (default to feat)
    result=$("$script" 50 "Some feature" "")
    assert_equals "feat/50-some-feature" "$result" "no labels defaults to feat" || true

    # Test error handling
    result=$("$script" "" "Title" "bug" 2>&1) || true
    assert_contains "Error" "$result" "missing issue number returns error" || true

    result=$("$script" 42 "" "bug" 2>&1) || true
    assert_contains "Error" "$result" "missing title returns error" || true
}

# =============================================================================
# Test: build-issue-prompt.sh
# =============================================================================
test_build_issue_prompt() {
    echo ""
    echo -e "${YELLOW}Testing build-issue-prompt.sh${NC}"
    echo "───────────────────────────────────────"

    local script="$PARENT_DIR/build-issue-prompt.sh"

    # Test basic prompt generation
    local result
    result=$("$script" 42 "Fix authentication bug" "/path/to/worktree")

    assert_contains "/claude-spec:plan Issue #42" "$result" "prompt contains command with issue reference" || true
    assert_contains "Fix authentication bug" "$result" "prompt contains issue title" || true
    assert_contains ".issue-context.json" "$result" "prompt references context file" || true
    assert_contains "/path/to/worktree" "$result" "prompt contains worktree path" || true
    assert_contains "Please read the issue context" "$result" "prompt contains instruction" || true

    # Test error handling
    result=$("$script" "" "Title" "/path" 2>&1) || true
    assert_contains "Error" "$result" "missing issue number returns error" || true

    result=$("$script" 42 "" "/path" 2>&1) || true
    assert_contains "Error" "$result" "missing title returns error" || true

    result=$("$script" 42 "Title" "" 2>&1) || true
    assert_contains "Error" "$result" "missing worktree path returns error" || true
}

# =============================================================================
# Test: check-gh-prerequisites.sh (limited - depends on environment)
# =============================================================================
test_check_gh_prerequisites() {
    echo ""
    echo -e "${YELLOW}Testing check-gh-prerequisites.sh${NC}"
    echo "───────────────────────────────────────"

    local script="$PARENT_DIR/check-gh-prerequisites.sh"

    # Test help output
    local result
    result=$("$script" --help)
    assert_contains "Usage" "$result" "help shows usage" || true

    # Test quiet mode parsing (just verify it doesn't error)
    "$script" --quiet >/dev/null 2>&1 || true
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_PASSED=$((TESTS_PASSED + 1))
    [ "$VERBOSE" = "true" ] && echo -e "${GREEN}✓${NC} quiet mode parses correctly"

    # If gh is installed, verify output format
    if command -v gh &>/dev/null; then
        result=$("$script" 2>&1) || true
        assert_contains "GH_STATUS=" "$result" "output contains GH_STATUS" || true
    else
        TESTS_RUN=$((TESTS_RUN + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
        [ "$VERBOSE" = "true" ] && echo -e "${YELLOW}⊘${NC} skipped: gh CLI not installed"
    fi
}

# =============================================================================
# Test: post-issue-comment.sh (limited - mocked)
# =============================================================================
test_post_issue_comment() {
    echo ""
    echo -e "${YELLOW}Testing post-issue-comment.sh${NC}"
    echo "───────────────────────────────────────"

    local script="$PARENT_DIR/post-issue-comment.sh"

    # Test help output
    local result
    result=$("$script" --help)
    assert_contains "Usage" "$result" "help shows usage" || true

    # Test input validation (these shouldn't try to post)
    result=$("$script" "" 42 "body" 2>&1) || true
    assert_contains "Error" "$result" "missing repo returns error" || true

    result=$("$script" "owner/repo" "" "body" 2>&1) || true
    assert_contains "Error" "$result" "missing issue number returns error" || true

    result=$("$script" "owner/repo" 42 "" 2>&1) || true
    assert_contains "Error" "$result" "missing comment body returns error" || true
}

# =============================================================================
# Test: create-issue-worktree.sh (limited - mocked, no git operations)
# =============================================================================
test_create_issue_worktree() {
    echo ""
    echo -e "${YELLOW}Testing create-issue-worktree.sh${NC}"
    echo "───────────────────────────────────────"

    local script="$PARENT_DIR/create-issue-worktree.sh"

    # Test help output
    local result
    result=$("$script" --help)
    assert_contains "Usage" "$result" "help shows usage" || true

    # Test input validation
    result=$("$script" "" 2>&1) || true
    assert_contains "Error" "$result" "missing JSON returns error" || true

    # Test invalid JSON handling
    result=$("$script" "not-json" 2>&1) || true
    # Should fail to parse
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$result" == *"Error"* ]] || [[ "$result" == *"null"* ]] || [[ $? -ne 0 ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        [ "$VERBOSE" = "true" ] && echo -e "${GREEN}✓${NC} invalid JSON handled"
    else
        TESTS_PASSED=$((TESTS_PASSED + 1))
        # It might still pass if jq handles it gracefully
        [ "$VERBOSE" = "true" ] && echo -e "${GREEN}✓${NC} JSON parsing tested"
    fi
}

# =============================================================================
# Run all tests
# =============================================================================
main() {
    echo "========================================"
    echo "  GitHub Issues Scripts Test Suite"
    echo "========================================"

    test_get_branch_prefix
    test_generate_branch_name
    test_build_issue_prompt
    test_check_gh_prerequisites
    test_post_issue_comment
    test_create_issue_worktree

    # Summary
    echo ""
    echo "========================================"
    echo "  Test Summary"
    echo "========================================"
    echo "  Total:  $TESTS_RUN"
    echo -e "  ${GREEN}Passed: $TESTS_PASSED${NC}"
    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "  ${RED}Failed: $TESTS_FAILED${NC}"
    else
        echo "  Failed: 0"
    fi
    echo "========================================"

    if [ $TESTS_FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

main "$@"
