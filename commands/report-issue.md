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
# Parse flags
ISSUE_TYPE=""
TARGET_REPO=""

for arg in $ARGUMENTS; do
  case "$arg" in
    --type)
      shift
      ISSUE_TYPE="$1"
      ;;
    bug|feat|docs|chore|perf)
      if [ -z "$ISSUE_TYPE" ]; then
        ISSUE_TYPE="$arg"
      fi
      ;;
    --repo)
      shift
      TARGET_REPO="$1"
      ;;
    */*)
      if [ -z "$TARGET_REPO" ]; then
        TARGET_REPO="$arg"
      fi
      ;;
  esac
done

echo "ISSUE_TYPE=${ISSUE_TYPE}"
echo "TARGET_REPO=${TARGET_REPO}"
```
</argument_parsing>

<execution_protocol>

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
```

Store the selected type as `ISSUE_TYPE`.

### Step 1.2: Issue Title

```
Use AskUserQuestion with:
  header: "Title"
  question: "What's a concise title for this issue? (use 'Other' to type)"
  multiSelect: false
  options:
    - label: "[Will type custom title]"
      description: "Select 'Other' to enter a custom title"
```

User will select "Other" and provide a custom title. Store as `ISSUE_TITLE`.

### Step 1.3: Issue Description

```
Use AskUserQuestion with:
  header: "Details"
  question: "Describe the issue in detail (use 'Other' to type)"
  multiSelect: false
  options:
    - label: "[Will type description]"
      description: "Select 'Other' to enter details"
```

User will select "Other" and provide description. Store as `ISSUE_DESCRIPTION`.

### Step 1.4: Type-Specific Follow-ups

**For `bug` type:**
```
Use AskUserQuestion with:
  header: "Expected"
  question: "What did you expect to happen?"
  options:
    - label: "[Will describe expected behavior]"
      description: "Select 'Other' to type"

Use AskUserQuestion with:
  header: "Actual"
  question: "What actually happened?"
  options:
    - label: "[Will describe actual behavior]"
      description: "Select 'Other' to type"
```

**For `feat` type:**
```
Use AskUserQuestion with:
  header: "Use Case"
  question: "What problem would this solve?"
  options:
    - label: "[Will describe use case]"
      description: "Select 'Other' to type"
```

**For `docs` type:**
```
Use AskUserQuestion with:
  header: "Location"
  question: "Which doc or section needs updating?"
  options:
    - label: "[Will specify location]"
      description: "Select 'Other' to type"
```

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
# Check if we can detect from context
# Priority: error traces > current project > ask

# Get current repo
CURRENT_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")

# Check if error traces point to a plugin
# (Parse paths like ~/.claude/plugins/cache/claude-code-plugins/claude-spec/)
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
