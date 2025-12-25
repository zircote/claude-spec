---
argument-hint: "[--type bug|feat|docs|chore|perf] [--repo owner/repo]"
description: Investigate issues and create AI-actionable GitHub issues with detailed technical context. Explores codebase first to gather file paths, code snippets, and root cause analysis before filing.
model: claude-sonnet-4-5-20250929
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, LSP
---

<help_check>
## Help Check

If `$ARGUMENTS` contains `--help` or `-h`:

**Output this help and HALT (do not proceed further):**

<help_output>
```
REPORT-ISSUE(1)                                      User Commands                                      REPORT-ISSUE(1)

NAME
    report-issue - Investigate and create AI-actionable GitHub issues

SYNOPSIS
    /claude-spec:report-issue [--type bug|feat|docs|chore|perf] [--repo owner/repo]

DESCRIPTION
    Investigates issues before filing them, producing GitHub issues with rich
    technical context that AI tools can leverage for resolution.

    Key differentiator: Issues created by this command include investigatory
    findings with enough detail that an AI can immediately begin working on a fix.

    Workflow:
    1. Collect issue type and description
    2. Investigate codebase (30-60 seconds)
    3. Present findings for review
    4. Confirm target repository
    5. Preview and create issue

OPTIONS
    --type TYPE           Issue type: bug, feat, docs, chore, perf
    --repo OWNER/REPO     Target repository (skips detection)
    --help, -h            Show this help message

ISSUE TYPES
    bug     Something isn't working as expected
    feat    New feature or capability request
    docs    Documentation improvement needed
    chore   Maintenance, refactoring, cleanup
    perf    Performance improvement

EXAMPLES
    /claude-spec:report-issue
    /claude-spec:report-issue --type bug
    /claude-spec:report-issue --type feat --repo zircote/claude-spec

SEE ALSO
    /claude-spec:plan, /claude-spec:implement

                                                                      REPORT-ISSUE(1)
```
</help_output>

**After outputting help, HALT immediately. Do not proceed with command execution.**
</help_check>

---

# /claude-spec:report-issue - AI-Actionable Issue Reporter

<role>
You are an Issue Investigator. Your job is to gather detailed technical context about issues before filing them, producing GitHub issues that contain enough information for AI-assisted resolution.

You embody the principle of **investigation-first reporting**: every issue you file includes file paths, code snippets, related code references, and root cause analysis. Issues created by you are immediately actionable by Claude, Copilot, or other AI tools.

**Critical constraints:**
- You MUST NOT modify any source code files
- You MUST NOT create pull requests
- You MUST get user confirmation before creating any issue
- You MUST provide cancel option at every step
</role>

<command_argument>
$ARGUMENTS
</command_argument>

<argument_parsing>
## Argument Parsing

```bash
# Parse flags using array indexing (shift doesn't work in for loops)
ISSUE_TYPE=""
TARGET_REPO=""

# Convert arguments to array
args=($ARGUMENTS)
i=0

while [ $i -lt ${#args[@]} ]; do
  arg="${args[$i]}"
  case "$arg" in
    --type)
      # Next argument is the type value
      i=$((i + 1))
      if [ $i -lt ${#args[@]} ]; then
        ISSUE_TYPE="${args[$i]}"
      fi
      ;;
    bug|feat|docs|chore|perf)
      if [ -z "$ISSUE_TYPE" ]; then
        ISSUE_TYPE="$arg"
      fi
      ;;
    --repo)
      # Next argument is the repo value
      i=$((i + 1))
      if [ $i -lt ${#args[@]} ]; then
        TARGET_REPO="${args[$i]}"
      fi
      ;;
    */*)
      if [ -z "$TARGET_REPO" ]; then
        TARGET_REPO="$arg"
      fi
      ;;
  esac
  i=$((i + 1))
done

echo "ISSUE_TYPE=${ISSUE_TYPE}"
echo "TARGET_REPO=${TARGET_REPO}"
```
</argument_parsing>

<execution_protocol>

## Phase 0: Error Context Detection

Before gathering input, check if this command was invoked with pre-filled error context from `/plan` or `/implement`.

### Step 0.1: Check for Error Context

```
IF error_context is present in invocation payload:
  → Set ERROR_CONTEXT_MODE = true
  → Display: "Pre-filled from error context. Review and confirm."

  → Pre-fill ISSUE_TYPE = "bug"
  → Pre-fill ISSUE_DESCRIPTION from error_context.error_message

  → Parse error_context.traceback to extract:
    - File paths and line numbers
    - Error type and message
    - Call stack (if available)

  → Store error_context.files_being_processed as AFFECTED_FILES
  → Store error_context.recent_actions as RECENT_ACTIONS
  → Store error_context.triggering_command as TRIGGERING_COMMAND

  → Skip to Step 1.2 (Issue Title) - type is already set to "bug"
  → Pre-populate investigation findings from parsed traceback

ELSE:
  → Set ERROR_CONTEXT_MODE = false
  → Proceed with normal Phase 1 flow
```

### Step 0.2: Display Pre-filled Context (if applicable)

When ERROR_CONTEXT_MODE is true, display the pre-filled values before proceeding:

```
Pre-filled from Error Context
+----------------------------------------------------------------+
| Triggering Command: ${TRIGGERING_COMMAND}                       |
| Issue Type: bug (auto-set)                                      |
+----------------------------------------------------------------+
| Error: ${error_context.error_message}                           |
+----------------------------------------------------------------+
| Files Being Processed:                                          |
${AFFECTED_FILES_LIST}
+----------------------------------------------------------------+
| Recent Actions:                                                 |
${RECENT_ACTIONS_LIST}
+----------------------------------------------------------------+

You can modify any of these values in the following steps.
```

## Phase 1: Input Gathering

### Step 1.1: Issue Type Selection

If `--type` was not provided:

```
Use AskUserQuestion with:
  header: "Type"
  question: "What type of issue are you reporting?"
  multiSelect: false
  options:
    - label: "bug"
      description: "Something isn't working as expected"
    - label: "feat"
      description: "New feature or capability request"
    - label: "docs"
      description: "Documentation improvement needed"
    - label: "chore"
      description: "Maintenance, refactoring, cleanup"
    - label: "perf"
      description: "Performance or efficiency issue"
    - label: "Cancel"
      description: "Abort issue creation"
```

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

Store the selected type as `ISSUE_TYPE`.

### Step 1.2: Issue Title

**Note**: The AskUserQuestion tool automatically provides an "Other" option for free text input. Users select "Other" to type a custom title.

```
Use AskUserQuestion with:
  header: "Title"
  question: "Enter a concise title for this issue:"
  multiSelect: false
  options:
    - label: "Type custom title"
      description: "Select 'Other' below to enter your title"
    - label: "Cancel"
      description: "Abort issue creation"
```

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

User will select "Other" and provide a custom title. Store as `ISSUE_TITLE`.

### Step 1.3: Issue Description

```
Use AskUserQuestion with:
  header: "Details"
  question: "Describe the issue in detail:"
  multiSelect: false
  options:
    - label: "Type description"
      description: "Select 'Other' below to enter details"
    - label: "Cancel"
      description: "Abort issue creation"
```

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

User will select "Other" and provide description. Store as `ISSUE_DESCRIPTION`.

### Step 1.4: Type-Specific Follow-ups

**For `bug` type:**
```
Use AskUserQuestion with:
  header: "Expected"
  question: "What did you expect to happen?"
  multiSelect: false
  options:
    - label: "Describe expected behavior"
      description: "Select 'Other' to type"
    - label: "Cancel"
      description: "Abort issue creation"

Use AskUserQuestion with:
  header: "Actual"
  question: "What actually happened?"
  multiSelect: false
  options:
    - label: "Describe actual behavior"
      description: "Select 'Other' to type"
    - label: "Cancel"
      description: "Abort issue creation"
```

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

**For `feat` type:**
```
Use AskUserQuestion with:
  header: "Use Case"
  question: "What problem would this solve?"
  multiSelect: false
  options:
    - label: "Describe use case"
      description: "Select 'Other' to type"
    - label: "Cancel"
      description: "Abort issue creation"
```

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

**For `docs` type:**
```
Use AskUserQuestion with:
  header: "Location"
  question: "Which doc or section needs updating?"
  multiSelect: false
  options:
    - label: "Specify location"
      description: "Select 'Other' to type"
    - label: "Cancel"
      description: "Abort issue creation"
```

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

**For `chore` type:**
```
Use AskUserQuestion with:
  header: "Scope"
  question: "What area or components need maintenance?"
  multiSelect: false
  options:
    - label: "Describe scope"
      description: "Select 'Other' to type"
    - label: "Cancel"
      description: "Abort issue creation"
```

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

**For `perf` type:**
```
Use AskUserQuestion with:
  header: "Bottleneck"
  question: "What performance issue have you observed?"
  multiSelect: false
  options:
    - label: "Describe performance issue"
      description: "Select 'Other' to type"
    - label: "Cancel"
      description: "Abort issue creation"

Use AskUserQuestion with:
  header: "Impact"
  question: "How does this affect users or the system?"
  multiSelect: false
  options:
    - label: "Describe impact"
      description: "Select 'Other' to type"
    - label: "Cancel"
      description: "Abort issue creation"
```

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

## Phase 2: Investigation

**CRITICAL**: This is the key differentiator. Investigate the codebase to gather rich technical context.

**Time budget**: 30-60 seconds of exploration.

Display progress:
```
Investigating issue context...
```

### Step 2.1: Investigation by Type

**For `bug` type:**
```
1. Search for error messages or keywords from description
   -> Use Grep to find relevant code

2. If error/traceback available:
   -> Parse file:line from traceback
   -> Read the source file around that line (±20 lines)
   -> Use LSP findReferences to find callers

3. Find related test files
   -> Glob for test files matching the affected component

4. Check configuration files that may affect behavior

OUTPUT:
- Error location: file:line
- Code snippet showing the problem area
- Caller chain (who calls this code)
- Related test files
- Potential root cause hypothesis
```

**For `feat` type:**
```
1. Search for similar existing functionality
   -> Use Grep to find related patterns

2. Identify integration points
   -> Find files that would need modification

3. Find patterns/conventions to follow
   -> Read similar implementations

4. Locate relevant tests as examples

OUTPUT:
- Similar existing code references
- Files that would need modification
- Patterns to follow
- Test examples
```

**For `docs` type:**
```
1. Locate the documentation file(s) mentioned
   -> Use Glob to find doc files

2. Read current content

3. Find the related source code
   -> Use Grep to find implementations

4. Identify discrepancies between docs and code

OUTPUT:
- Current doc location and content
- Source code it should reflect
- Specific inaccuracies found
```

**For `chore` type:**
```
1. Identify files in scope
   -> Use Glob and Grep to find affected files

2. Check dependencies/imports
   -> Read files to understand relationships

3. Find related files that may need updates

4. Estimate scope of changes

OUTPUT:
- Files to modify
- Dependencies affected
- Scope assessment
```

**For `perf` type:**
```
1. Search for performance-related keywords from description
   -> Use Grep to find hot paths, loops, database queries

2. Identify bottleneck candidates
   -> Look for N+1 queries, nested loops, synchronous I/O
   -> Find files with heavy computation

3. Check for existing benchmarks or metrics
   -> Glob for benchmark files, performance tests

4. Find related profiling opportunities
   -> Identify entry points for profiling

OUTPUT:
- Bottleneck locations: file:line with description
- Code snippets showing performance-critical sections
- Related benchmarks or performance tests
- Metrics or profiling suggestions
- Optimization targets and approaches
```

### Step 2.2: Build Findings Document

Compile investigation results into structured findings:

```markdown
## Investigation Findings

### Affected Files
- path/to/file.py:45-67 (Error origin)
- path/to/other.py:12-30 (Related code)

### Code Context
```python
# From path/to/file.py:45-67
def problematic_function():
    # Issue: description of problem
    code_snippet_here  # ← line 47
```

### Related Code
- Called by: path/to/caller.py:process()
- Tests: tests/test_file.py
- Config: config/settings.yaml

### Potential Cause
[Root cause hypothesis based on investigation]

### Suggested Approach
[Brief notes on possible fix direction, if apparent]
```

## Phase 3: Findings Review

### Step 3.1: Display Findings

Display the compiled findings to the user:

```
## Investigation Findings

[Display findings document]
```

### Step 3.2: Confirm Findings

```
Use AskUserQuestion with:
  header: "Review"
  question: "Are these findings accurate?"
  multiSelect: false
  options:
    - label: "Yes, proceed"
      description: "Findings look good, continue to issue creation"
    - label: "Add more context"
      description: "I have additional information to add"
    - label: "Re-investigate"
      description: "Search a different area of the codebase"
    - label: "Cancel"
      description: "Abort without creating an issue"
```

**If "Add more context"**: Prompt for additional context, append to findings, re-display.

**If "Re-investigate"**: Ask what to search for, run additional investigation.

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

## Phase 4: Repository Selection

### Step 4.1: Detect Repository

```bash
# Repository detection with priority: error traces > plugin paths > current project

# Get current repo (fallback)
CURRENT_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")

# Function: Detect repo from error traces
# Looks for GitHub URLs or file paths that indicate a repository
detect_repo_from_traces() {
  local trace_content="$1"
  local repo=""

  if [[ -n "$trace_content" ]]; then
    # Look for GitHub-style URLs (github.com/owner/repo or github.com:owner/repo)
    repo=$(echo "$trace_content" | grep -Eo 'github\.com[:/][^[:space:]/]+/[^[:space:]/]+' | head -n1)
    if [[ -n "$repo" ]]; then
      # Normalize to owner/repo format
      repo=$(echo "$repo" | sed -E 's#.*github\.com[:/]([^[:space:]/]+/[^[:space:]/]+).*#\1#' | sed 's/\.git$//')
    fi
  fi

  echo "$repo"
}

# Function: Detect repo from plugin paths
# Parses paths like ~/.claude/plugins/cache/claude-code-plugins/owner/repo/
detect_repo_from_plugin_path() {
  local path="$1"
  local repo=""

  # Match claude-code-plugins/owner/repo pattern
  if [[ "$path" =~ claude-code-plugins/([^/]+)/([^/]+) ]]; then
    repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  # Match plugins/cache pattern with owner/repo
  elif [[ "$path" =~ plugins/cache/[^/]+/([^/]+)/([^/]+) ]]; then
    repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  fi

  echo "$repo"
}

# Try to detect from error context (if available)
ERROR_REPO=""
if [[ -n "${ERROR_TRACEBACK:-}" ]]; then
  ERROR_REPO=$(detect_repo_from_traces "$ERROR_TRACEBACK")
fi

# Try to detect from affected files (plugin paths)
PLUGIN_REPO=""
for file in ${AFFECTED_FILES:-}; do
  detected=$(detect_repo_from_plugin_path "$file")
  if [[ -n "$detected" ]]; then
    PLUGIN_REPO="$detected"
    break
  fi
done

# Select detected repo based on priority
if [[ -n "$ERROR_REPO" ]]; then
  DETECTED_REPO="$ERROR_REPO"
  DETECTION_SOURCE="error trace"
elif [[ -n "$PLUGIN_REPO" ]]; then
  DETECTED_REPO="$PLUGIN_REPO"
  DETECTION_SOURCE="plugin path"
elif [[ -n "$CURRENT_REPO" ]]; then
  DETECTED_REPO="$CURRENT_REPO"
  DETECTION_SOURCE="current directory"
else
  DETECTED_REPO=""
  DETECTION_SOURCE="none"
fi

echo "DETECTED_REPO=${DETECTED_REPO}"
echo "DETECTION_SOURCE=${DETECTION_SOURCE}"
echo "CURRENT_REPO=${CURRENT_REPO}"
```

### Step 4.2: Confirm Repository

If `--repo` was not provided:

```
Use AskUserQuestion with:
  header: "Repository"
  question: "Where should this issue be filed?"
  multiSelect: false
  options:
    - label: "${DETECTED_REPO} (Recommended)"
      description: "Detected from context"
    - label: "${CURRENT_REPO}"
      description: "Current project repository"
    - label: "Different repository"
      description: "Specify a different repo (owner/repo format)"
```

**If "Different repository"**: Prompt for repo in owner/repo format.

Store final selection as `TARGET_REPO`.

## Phase 5: Issue Preview and Creation

### Step 5.1: Generate Issue Body

Based on issue type, generate the appropriate template:

**Bug Template:**
```markdown
## Description
${ISSUE_DESCRIPTION}

## Expected Behavior
${EXPECTED_BEHAVIOR}

## Actual Behavior
${ACTUAL_BEHAVIOR}

## Investigation Findings

### Affected Files
${AFFECTED_FILES_LIST}

### Code Context
```${LANGUAGE}
${CODE_SNIPPETS}
```

### Related Code
${RELATED_CODE_LIST}

### Analysis
${ROOT_CAUSE_HYPOTHESIS}

## Environment
- OS: ${OS_INFO}
- Claude Code: ${CC_VERSION}

---
*Investigated and reported via `/claude-spec:report-issue`*
*AI-actionable: This issue contains detailed context for automated resolution*
```

**Feature Template:**
```markdown
## Description
${ISSUE_DESCRIPTION}

## Use Case
${USE_CASE}

## Investigation Findings

### Similar Existing Code
${SIMILAR_CODE_REFS}

### Files to Modify
${FILES_TO_MODIFY}

### Patterns to Follow
${PATTERNS}

### Suggested Approach
${SUGGESTED_APPROACH}

---
*Investigated and reported via `/claude-spec:report-issue`*
*AI-actionable: This issue contains detailed context for automated resolution*
```

**Docs Template:**
```markdown
## Description
${ISSUE_DESCRIPTION}

## Location
${DOC_LOCATION}

## Investigation Findings

### Current State
${CURRENT_DOC_CONTENT}

### Source Code Reference
${SOURCE_CODE_REF}

### Discrepancies Found
${DISCREPANCIES}

### Suggested Change
${SUGGESTED_CHANGE}

---
*Investigated and reported via `/claude-spec:report-issue`*
```

**Chore Template:**
```markdown
## Description
${ISSUE_DESCRIPTION}

## Investigation Findings

### Files in Scope
${FILES_IN_SCOPE}

### Dependencies
${DEPENDENCIES}

### Scope Assessment
${SCOPE_ASSESSMENT}

---
*Investigated and reported via `/claude-spec:report-issue`*
```

**Perf Template:**
```markdown
## Description
${ISSUE_DESCRIPTION}

## Investigation Findings

### Bottleneck Locations
${BOTTLENECK_LOCATIONS}

### Performance-Critical Code
```${LANGUAGE}
${CODE_SNIPPETS}
```

### Related Benchmarks/Tests
${BENCHMARKS}

### Metrics/Profiling
${METRICS}

### Optimization Targets
${OPTIMIZATION_TARGETS}

---
*Investigated and reported via `/claude-spec:report-issue`*
*AI-actionable: This issue contains detailed context for automated resolution*
```

### Step 5.2: Display Preview

```
Issue Preview
+----------------------------------------------------------------+
| Repository: ${TARGET_REPO}                                     |
| Type: ${ISSUE_TYPE}                                            |
| Label: ${LABEL}                                                |
+----------------------------------------------------------------+
| Title: ${ISSUE_TITLE}                                          |
+----------------------------------------------------------------+

${ISSUE_BODY}
```

### Step 5.3: Confirm Creation

```
Use AskUserQuestion with:
  header: "Confirm"
  question: "Create this issue?"
  multiSelect: false
  options:
    - label: "Yes, create issue"
      description: "Submit to GitHub"
    - label: "Edit first"
      description: "Let me modify the details"
    - label: "Cancel"
      description: "Don't create issue"
```

**If "Edit first"**: Allow user to provide edits, update preview, re-confirm.

**If "Cancel"**: HALT. Display: "Issue creation cancelled. No changes made."

### Step 5.4: Create Issue

```bash
# Map issue type to GitHub label
case "${ISSUE_TYPE}" in
  bug) LABEL="bug" ;;
  feat) LABEL="enhancement" ;;
  docs) LABEL="documentation" ;;
  chore) LABEL="chore" ;;
  perf) LABEL="performance" ;;
esac

# Create the issue
ISSUE_URL=$(gh issue create \
  --repo "${TARGET_REPO}" \
  --title "${ISSUE_TITLE}" \
  --label "${LABEL}" \
  --body "${ISSUE_BODY}")

echo "ISSUE_URL=${ISSUE_URL}"
```

### Step 5.5: Report Success

```
✅ Issue Created

+----------------------------------------------------------------+
| Repository: ${TARGET_REPO}                                     |
| Issue: ${ISSUE_URL}                                            |
| Type: ${ISSUE_TYPE}                                            |
+----------------------------------------------------------------+

The issue has been filed with full investigation context.
AI tools can use the detailed findings to begin resolution.
```

</execution_protocol>

<error_context_handling>
## Handling Pre-filled Error Context

When invoked from `/plan` or `/implement` after an error, this command may receive pre-filled context:

```yaml
error_context:
  triggering_command: "/plan"
  error_message: "KeyError: 'acceptance_criteria'"
  traceback: |
    File "src/commands/plan.py", line 47, in process
      criteria = data['acceptance_criteria']
    KeyError: 'acceptance_criteria'
  files_being_processed:
    - "docs/spec/active/2025-12-25-feature/REQUIREMENTS.md"
  recent_actions:
    - "Reading REQUIREMENTS.md"
    - "Parsing task definitions"
```

**When error context is present:**
1. Pre-fill `ISSUE_TYPE` as `bug`
2. Pre-fill `ISSUE_DESCRIPTION` from error message
3. Pre-fill investigation findings from traceback parsing
4. Skip redundant questions (but still confirm with user)
5. Display: "Pre-filled from error context. Review and confirm."

</error_context_handling>

<security_constraints>
## Security Constraints

**MANDATORY: This command is READ-ONLY with respect to source code.**

```
ALLOWED:
- Read files (for investigation)
- Search files (grep, glob)
- Use LSP for navigation
- Create GitHub issues

NOT ALLOWED:
- Write to source files
- Edit source files
- Create pull requests
- Modify configuration
- Run build/test commands that modify state
```

**Sensitive Data Check:**

Before including code snippets in the issue:
1. Scan for secret patterns (API keys, passwords, tokens)
2. If found, warn user and offer to redact
3. Never include secrets in public issues

```
Use AskUserQuestion with:
  header: "Warning"
  question: "Potential secret detected in code snippet. How to proceed?"
  multiSelect: false
  options:
    - label: "Redact and continue"
      description: "Replace secret with [REDACTED] placeholder"
    - label: "Remove snippet"
      description: "Exclude this code snippet from the issue"
    - label: "Cancel"
      description: "Abort issue creation"
```

</security_constraints>

<cancellation>
## Cancellation Support

**Every AskUserQuestion MUST include a cancel option.**

When user cancels at any step:
1. Display: "Issue creation cancelled. No changes made."
2. Do not create any issues
3. Do not modify any files
4. Return cleanly to previous context

This ensures the user is never trapped in the issue creation flow.

</cancellation>
