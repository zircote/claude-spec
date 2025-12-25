# Requirements: Issue Reporter Command

## Functional Requirements

### P0 - Must Have

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| F-01 | Command invocation | `/claude-spec:report-issue` command registered |
| F-02 | Issue type selection | Prompt for type: bug, feat, docs, chore, perf |
| F-03 | Initial description | Collect brief issue description from user |
| F-04 | **Investigation phase** | Explore codebase to gather technical context |
| F-05 | **File path collection** | Identify and list affected files with line numbers |
| F-06 | **Code snippet extraction** | Include relevant code snippets in findings |
| F-07 | **Error context capture** | Capture error traces, stack traces for bugs |
| F-08 | **Related code analysis** | Find related functions, classes, patterns |
| F-09 | Findings review | Present findings to user for confirmation |
| F-10 | Repository confirmation | Confirm target repository with user |
| F-11 | Issue creation | Create issue via `gh issue create` |
| F-12 | Issue URL reporting | Display created issue URL |

### P1 - Should Have

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| F-13 | Root cause hypothesis | Include potential cause analysis |
| F-14 | Suggested approach | Brief notes on possible fix direction |
| F-15 | Environment info | Include OS, versions, config context |
| F-16 | Label application | Apply appropriate labels |

### P2 - Nice to Have

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| F-17 | Duplicate detection | Search for similar existing issues |
| F-18 | Link to related issues | Reference existing related issues |

## Non-Functional Requirements

### Security

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| S-01 | No code modification | Command MUST NOT modify source files |
| S-02 | No PR creation | Command MUST NOT create PRs |
| S-03 | User confirmation | Issue creation requires explicit approval |
| S-04 | Sensitive data check | Warn if findings contain secrets/credentials |

### Usability

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| U-01 | Investigation visibility | Show progress during investigation |
| U-02 | Findings editable | User can modify findings before filing |
| U-03 | Abort option | User can cancel at any point |

## Command Specification

```
/claude-spec:report-issue [--type bug|feat|docs|chore|perf] [--repo owner/repo]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--type` | enum | No | Issue type (prompted if not provided) |
| `--repo` | string | No | Target repository (skips detection) |

## Investigation Phase

The **key differentiator** - before creating an issue, the command investigates:

### For `bug` Type
```
Investigation steps:
1. Parse error message/traceback if available
2. Locate error source file and line
3. Read surrounding code context (±20 lines)
4. Find callers of the failing function
5. Check for related test files
6. Identify configuration that may affect behavior

Output:
- Error location: file:line
- Code snippet showing the problem
- Call stack / caller chain
- Related test files
- Potential root cause hypothesis
```

### For `feat` Type
```
Investigation steps:
1. Search for similar existing functionality
2. Identify integration points
3. Find patterns/conventions to follow
4. Locate relevant config/schema files
5. Check for related tests to use as examples

Output:
- Similar existing code references
- Files that would need modification
- Patterns to follow
- Test examples
```

### For `docs` Type
```
Investigation steps:
1. Locate the documentation file(s)
2. Read current content
3. Find related source code
4. Check for discrepancies

Output:
- Current doc location and content
- Source code it should reflect
- Specific inaccuracies found
```

### For `chore` Type
```
Investigation steps:
1. Identify files in scope
2. Check dependencies/imports
3. Find related files that may need updates
4. Estimate scope of changes

Output:
- Files to modify
- Dependencies affected
- Scope assessment
```

## Interaction Flow

### Step 1: Type and Description
```
AskUserQuestion: "What type of issue?" → bug/feat/docs/chore

AskUserQuestion: "Briefly describe the issue" → [free text]
```

### Step 2: Investigation (Automatic)
```
Display: "Investigating..."
- Use Grep, Glob, Read tools to explore
- Gather file paths, code snippets, context
- Build findings document
```

### Step 3: Findings Review
```
Display findings:
┌─────────────────────────────────────────────────────────────┐
│ ## Investigation Findings                                   │
│                                                             │
│ ### Affected Files                                          │
│ - src/commands/implement.py:45-67                           │
│ - src/utils/parser.py:12-30                                 │
│                                                             │
│ ### Code Context                                            │
│ ```python                                                   │
│ def parse_args(self):                                       │
│     # Problem: doesn't handle empty input                   │
│     return self.args.split()  # ← line 47                   │
│ ```                                                         │
│                                                             │
│ ### Related Code                                            │
│ - Called by: src/main.py:process_command()                  │
│ - Tests: tests/test_parser.py                               │
│                                                             │
│ ### Potential Cause                                         │
│ Missing null check before split() operation                 │
└─────────────────────────────────────────────────────────────┘

AskUserQuestion: "Are these findings accurate?"
  ○ Yes, proceed to create issue
  ○ Add more context (let me explain more)
  ○ Re-investigate (search different area)
  ○ Cancel
```

### Step 4: Repository Selection
```
AskUserQuestion: "File in {detected_repo}?"
  ○ Yes (Recommended)
  ○ Different repository
```

### Step 5: Issue Preview and Confirmation
```
Display full issue preview with:
- Title (generated from type + description)
- Body with all findings
- Labels

AskUserQuestion: "Create this issue?"
  ○ Yes, create issue
  ○ Edit first
  ○ Cancel
```

## AI-Actionable Issue Template

```markdown
## Description
{user's description}

## Investigation Findings

### Affected Files
{list of file:line references}

### Code Context
```{language}
{relevant code snippets with annotations}
```

### Related Code
- {caller/callee relationships}
- {related tests}
- {configuration files}

### Analysis
{root cause hypothesis}
{suggested approach if applicable}

## Environment
- OS: {os}
- Claude Code: {version}
- Project: {project context}

## Reproduction
{steps if applicable}

---
*Investigated and reported via `/claude-spec:report-issue`*
*AI-actionable: This issue contains detailed context for automated resolution*
```

## Integration with Other Commands

### Proactive Bug Detection

The `/plan` and `/implement` commands should be updated to detect **any unexpected behavior** and offer users the opportunity to report them.

**Trigger conditions** (not just exceptions):
- Exceptions/tracebacks
- Command failures (non-zero exit, validation errors)
- Output that doesn't match expected patterns
- Unexpected empty results
- File operations that fail silently

```
When a command encounters unexpected behavior:

Display error information, then:

AskUserQuestion: "Would you like to report this issue?"
  ○ Yes, report it → Invoke /report-issue with error context pre-filled
  ○ No, continue → Continue without reporting
  ○ Don't ask again (this session) → Suppress prompts for rest of session
  ○ Never ask → Permanently disable (stored in settings)
```

**Low-friction design principles:**
- Single question, not a dialog
- "Don't ask again" respected immediately
- No additional confirmation if user declines
- Quick dismiss, no guilt-tripping

**Context to pass to /report-issue:**
- Error message and traceback
- Command that was running
- Files being processed
- Recent actions taken

**Implementation notes:**
- Add `<error_recovery>` section to plan.md and implement.md
- Pre-fill investigation context when invoked from another command
- Skip redundant questions if context already gathered

## Opt-Out Requirements

| Requirement | Implementation |
|-------------|----------------|
| Cancel at any step | Every AskUserQuestion includes cancel option |
| No forced filing | User must explicitly confirm issue creation |
| Exit gracefully | Cancellation returns to previous context cleanly |
| No data persistence | If cancelled, no issue data is stored |

## Out of Scope

- Implementing fixes
- Creating pull requests
- Modifying source code
- Auto-assignment
- Project board integration
