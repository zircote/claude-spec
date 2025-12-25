# Architecture: Issue Reporter Command

## Overview

The `/report-issue` command investigates issues before filing them, producing AI-actionable GitHub issues with rich technical context. It can be invoked directly or triggered by other commands when they detect errors.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  /claude-spec:report-issue                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
│  │    Input     │   │ Investigator │   │   Findings   │         │
│  │   Gatherer   │──▶│    Engine    │──▶│   Reviewer   │         │
│  └──────────────┘   └──────────────┘   └──────────────┘         │
│         │                                      │                │
│         │ (pre-filled                          │                │
│         │  from error)                         ▼                │
│         │                            ┌──────────────┐           │
│  ┌──────────────┐                    │    Issue     │           │
│  │   /plan or   │───context─────────▶│   Creator    │           │
│  │  /implement  │                    └──────────────┘           │
│  └──────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Input Gatherer

**Purpose**: Collect initial issue information from user

**Modes**:
- **Direct invocation**: Full prompting for type, description
- **Error-triggered**: Pre-filled with error context from calling command

**Outputs**:
```yaml
input:
  type: bug | feat | docs | chore | perf
  description: "User's description"
  error_context:          # If triggered by error
    traceback: "..."
    command: "/plan"
    files_involved: [...]
  source: direct | error_triggered
```

### 2. Investigator Engine

**Purpose**: Explore codebase to gather technical context

**Investigation depth**: Moderate (30-60 seconds)
- Find error source and immediate context
- Identify callers and related code
- Locate relevant tests
- Brief root cause analysis

**Tools Used**:
- `Grep` - Search for patterns, error messages
- `Glob` - Find related files
- `Read` - Extract code snippets
- `LSP` - Find references, definitions (if available)

**Investigation by Type**:

| Type | Investigation Focus |
|------|---------------------|
| bug | Error trace → source file → callers → tests |
| feat | Similar code → patterns → integration points |
| docs | Doc files → source code → discrepancies |
| chore | Affected files → dependencies → scope |

**Outputs**:
```yaml
findings:
  affected_files:
    - path: "src/commands/plan.py"
      lines: "45-67"
      relevance: "Error origin"
  code_snippets:
    - file: "src/commands/plan.py"
      lines: "45-67"
      content: "..."
      annotation: "Missing null check"
  related_code:
    - type: "caller"
      location: "src/main.py:process()"
    - type: "test"
      location: "tests/test_plan.py"
  analysis:
    potential_cause: "..."
    suggested_approach: "..."
```

### 3. Findings Reviewer

**Purpose**: Present findings for user validation

**Interaction**:
```
AskUserQuestion: "Are these findings accurate?"
  ○ Yes, proceed
  ○ Add more context
  ○ Re-investigate different area
  ○ Cancel
```

**Allows**:
- User to add missing context
- Request deeper investigation
- Abort without filing

### 4. Issue Creator

**Purpose**: Format and submit the issue

**Steps**:
1. Detect/confirm target repository
2. Generate title from type + description
3. Format body with findings template
4. Show preview for confirmation
5. Create via `gh issue create`
6. Report URL

## Integration with Other Commands

### Error Recovery Flow

When `/plan` or `/implement` encounters an error:

```
┌─────────────┐     error      ┌─────────────┐
│   /plan     │───────────────▶│   Display   │
│ /implement  │                │    Error    │
└─────────────┘                └──────┬──────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │ AskUser:    │
                               │ Report it?  │
                               └──────┬──────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │ Yes             │ No              │
                    ▼                 ▼                 │
             ┌─────────────┐   ┌─────────────┐         │
             │ /report-    │   │  Continue   │         │
             │   issue     │   │  normally   │         │
             │ (pre-filled)│   └─────────────┘         │
             └─────────────┘                           │
```

### Context Handoff

When triggered from another command, `/report-issue` receives:

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

This context:
- Pre-fills the description
- Seeds the investigation
- Reduces redundant questions

## Data Flow

```
User invokes /report-issue (or error triggers it)
        │
        ▼
┌───────────────────┐
│ Gather input      │ ─── Type, description (or pre-filled from error)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Investigate       │ ─── Grep, Glob, Read to find context
│ (type-specific)   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Review findings   │ ─── User confirms or requests more
└─────────┬─────────┘
          │
          ▼ (user confirms)
┌───────────────────┐
│ Select repository │ ─── Auto-detect + confirm
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Preview issue     │ ─── Show formatted issue
└─────────┬─────────┘
          │
          ▼ (user confirms)
┌───────────────────┐
│ Create issue      │ ─── gh issue create
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Report URL        │ ─── Display issue link
└───────────────────┘
```

## File Structure

```
commands/
├── report-issue.md     # New command
├── plan.md             # Add <error_recovery> section
└── implement.md        # Add <error_recovery> section
```

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Secrets in code snippets | Scan findings for patterns, warn user |
| Sensitive file paths | Allow user to redact before filing |
| No code modification | Command only reads, never writes |
| User confirmation | Every action requires explicit approval |
