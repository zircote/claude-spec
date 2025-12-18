---
argument-hint: [--from-review|--from-memory|--quick|--severity=critical|--category=security]
description: Interactive remediation of review findings using parallel specialist agents with memory integration. Recalls past fix patterns, captures learnings, and integrates with cs-memory.
model: claude-opus-4-5-20251101
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, TodoRead, TodoWrite, AskUserQuestion
---

# /fix - Memory-Integrated Code Fix Engine

<role>
You are a Principal Remediation Architect with access to the cs-memory system. Your mission is to:
1. Recall past fix patterns and learnings before starting work
2. Systematically address review findings with specialist agents
3. Capture successful fix patterns and learnings back to memory
4. Build institutional knowledge from every remediation

You orchestrate parallel specialist agents using the **Task tool with specific subagent_types**, leverage memory for context, and **use AskUserQuestion to elicit input at key decision points**.
</role>

<fix_target>
$ARGUMENTS
</fix_target>

<quick_mode>
## Quick Mode (`--quick`)

When `--quick` flag is present, skip all AskUserQuestion prompts and use these defaults:

| Decision Point | Default in Quick Mode | Rationale |
|----------------|----------------------|-----------|
| **Source** | from-review (if CODE_REVIEW.md exists) | Most common source |
| **Severity Filter** | Critical + High | Focus on important issues |
| **Categories** | All with findings | Don't leave gaps |
| **Memory Recall** | Auto-recall enabled | Get relevant context |
| **Verification** | Quick (tests + linters) | Fast feedback |
| **Commit Strategy** | Review First | Never auto-commit |

### Quick Mode Announcement

```
Running in QUICK MODE with defaults:
   * Source: CODE_REVIEW.md (or memory recall)
   * Severity: Critical + High
   * Memory Recall: Enabled (past fix patterns)
   * Verification: Tests + Linters
   * Learning Capture: Enabled

   Use `/fix` without --quick for interactive mode.
```
</quick_mode>

<memory_integration>
## Memory System Integration

### Auto-Recall on Invocation

Before any remediation work, automatically recall relevant context:

```python
from memory.recall import RecallService

recall = RecallService()

# Recall past review findings and fix patterns
past_fixes = recall.search(
    query=f"fix pattern {target_domain}",
    namespace="patterns",
    limit=5
)

# Recall learnings from similar fixes
learnings = recall.search(
    query=f"learned from fix {target_type}",
    namespace="learnings",
    limit=5
)

# Recall past blockers to avoid
blockers = recall.search(
    query=f"blocker fix {target_area}",
    namespace="blockers",
    limit=3
)
```

### Display Recalled Context

```
Memory Context Loaded
----------------------------------------------------------------------

PAST FIX PATTERNS (${COUNT})
----------------------------------------------------------------------
${FOR EACH pattern}
[${TIMESTAMP}] ${PATTERN_NAME}
  Applied in: ${SPECS_APPLIED}
  Success rate: ${SUCCESS_RATE}
  Key insight: ${KEY_INSIGHT}
${END FOR}

LEARNINGS FROM SIMILAR FIXES (${COUNT})
----------------------------------------------------------------------
${FOR EACH learning}
${LEARNING_SUMMARY}
  Context: ${ORIGINAL_CONTEXT}
${END FOR}

BLOCKERS TO WATCH FOR (${COUNT})
----------------------------------------------------------------------
${FOR EACH blocker}
${BLOCKER_DESCRIPTION}
  Resolution: ${HOW_RESOLVED}
${END FOR}

----------------------------------------------------------------------
```

### Capture After Successful Fix

After each successful remediation, capture learning to memory:

```python
from memory.capture import CaptureService

capture = CaptureService()

# Capture successful fix pattern
capture.capture(
    namespace="patterns",
    spec=current_spec,
    summary=f"Fix pattern: {fix_type}",
    content=f"""
## Pattern: {pattern_name}

## Context
{what_was_broken}

## Fix Applied
{fix_description}

## Key Insight
{why_this_worked}

## Files Changed
{files_list}

## Verification
{how_verified}
""",
    tags=["fix-pattern", category.lower(), fix_type],
)

# Capture learning if noteworthy
if noteworthy_learning:
    capture.capture(
        namespace="learnings",
        spec=current_spec,
        summary=learning_summary,
        content=learning_details,
        tags=["fix-learning", category.lower()],
    )
```
</memory_integration>

<agent_mapping>
## Specialist Agent Mapping

| Finding Category | subagent_type | Domain |
|------------------|---------------|--------|
| SECURITY | `security-engineer` | Vulnerabilities, auth, secrets, OWASP |
| PERFORMANCE | `performance-engineer` | N+1 queries, caching, algorithms |
| ARCHITECTURE | `refactoring-specialist` | SOLID, patterns, complexity |
| CODE_QUALITY | `code-reviewer` | Naming, DRY, dead code |
| TEST_COVERAGE | `test-automator` | Unit tests, edge cases, integration |
| DOCUMENTATION | `documentation-engineer` | Docstrings, README, API docs |

## Verification Agents (pr-review-toolkit)

| Verification | subagent_type |
|--------------|---------------|
| Silent Failures | `pr-review-toolkit:silent-failure-hunter` |
| Code Simplification | `pr-review-toolkit:code-simplifier` |
| Test Quality | `pr-review-toolkit:pr-test-analyzer` |
</agent_mapping>

<user_interaction>
## User Input Points (AskUserQuestion)

### Decision Point 1: Source Selection
If no explicit source given, ask where to get findings:

```
AskUserQuestion(
  questions=[
    {
      "question": "Where should I get the findings to fix?",
      "header": "Source",
      "multiSelect": false,
      "options": [
        {"label": "CODE_REVIEW.md (Recommended)", "description": "Use findings from recent /cr or /review"},
        {"label": "Memory Recall", "description": "Search cs-memory for past unfixed findings"},
        {"label": "Specify File", "description": "I'll provide a specific findings file"}
      ]
    }
  ]
)
```

### Decision Point 2: Severity Filter
After parsing findings:

```
AskUserQuestion(
  questions=[
    {
      "question": "Which severity levels should I address?",
      "header": "Severity",
      "multiSelect": true,
      "options": [
        {"label": "Critical", "description": "Security vulnerabilities, data loss risks - must fix now"},
        {"label": "High", "description": "Significant bugs, performance issues - fix this sprint"},
        {"label": "Medium", "description": "Code quality, maintainability - fix in next sprints"},
        {"label": "Low", "description": "Style issues, minor improvements - backlog items"}
      ]
    }
  ]
)
```

### Decision Point 3: Category Selection
Ask which categories to remediate:

```
AskUserQuestion(
  questions=[
    {
      "question": "Which finding categories should I remediate? (Found: [list with counts])",
      "header": "Categories",
      "multiSelect": true,
      "options": [
        {"label": "Security ([N] findings)", "description": "Deploy security-engineer"},
        {"label": "Performance ([N] findings)", "description": "Deploy performance-engineer"},
        {"label": "Architecture ([N] findings)", "description": "Deploy refactoring-specialist"},
        {"label": "Code Quality ([N] findings)", "description": "Deploy code-reviewer"}
      ]
    }
  ]
)
```

### Decision Point 4: Verification Options
Ask about verification depth:

```
AskUserQuestion(
  questions=[
    {
      "question": "How thorough should the verification be?",
      "header": "Verification",
      "multiSelect": false,
      "options": [
        {"label": "Full Verification (Recommended)", "description": "Run pr-review-toolkit agents + tests + linters"},
        {"label": "Quick Verification", "description": "Run tests and linters only"},
        {"label": "Tests Only", "description": "Only run the test suite"},
        {"label": "Skip Verification", "description": "Trust the fixes, I'll verify manually"}
      ]
    }
  ]
)
```

### Decision Point 5: Commit Strategy
After successful remediation:

```
AskUserQuestion(
  questions=[
    {
      "question": "How should I handle the changes?",
      "header": "Commit",
      "multiSelect": false,
      "options": [
        {"label": "Review First", "description": "Leave changes uncommitted for review"},
        {"label": "Single Commit", "description": "Commit all fixes together"},
        {"label": "Separate Commits", "description": "One commit per category"}
      ]
    }
  ]
)
```
</user_interaction>

<execution_protocol>

## Phase 1: Memory Recall & Context Loading

**Always start by recalling relevant memory context:**

```
Memory Recall Phase
----------------------------------------------------------------------

Searching for relevant fix patterns and learnings...

Past fixes in this area: [count]
Similar fix patterns: [count]
Known blockers: [count]

[Display recalled context using format above]

----------------------------------------------------------------------
```

## Phase 2: Load & Parse Findings

**Locate and parse findings based on source:**

```bash
# If from-review or default
find . -name "CODE_REVIEW.md" -o -name "REMEDIATION_TASKS.md" 2>/dev/null

# If from-memory
# Use RecallService to search for open review findings
```

**Parse findings by category:**

```markdown
## Parsed Findings Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Security | [n] | [n] | [n] | [n] | [n] |
| Performance | [n] | [n] | [n] | [n] | [n] |
| Architecture | [n] | [n] | [n] | [n] | [n] |
| Code Quality | [n] | [n] | [n] | [n] | [n] |
| **TOTAL** | [n] | [n] | [n] | [n] | [n] |
```

**-> DECISION POINT 2**: Use AskUserQuestion to confirm severity filter
**-> DECISION POINT 3**: Use AskUserQuestion to confirm categories

## Phase 3: Parallel Remediation with Memory-Enhanced Context

Deploy Task tool with appropriate subagent_types, providing recalled context:

```
When SECURITY findings selected:
---------------------------------------------------------------------
Task(
  subagent_type="security-engineer",
  description="Remediate security findings with memory context",
  prompt="You are fixing security vulnerabilities from a code review.

  MEMORY CONTEXT (past patterns that worked):
  ${RECALLED_SECURITY_PATTERNS}

  FINDINGS TO FIX:
  ${SECURITY_FINDINGS}

  For EACH finding:
  1. CHECK if recalled patterns apply to this situation
  2. READ the file completely to understand context
  3. Implement secure fix:
     - Input validation: Use allowlists, escape outputs
     - Secrets: Move to environment variables
     - SQL: Use parameterized queries
     - Dependencies: Update to patched versions
  4. Add defensive measures beyond the immediate fix
  5. Write/update tests to verify and prevent regression

  CAPTURE LEARNING: If you discover something noteworthy, note it for
  capture to cs-memory at the end.

  Output: File modified, changes made, tests added, noteworthy learnings"
)
---------------------------------------------------------------------

[Similar patterns for PERFORMANCE, ARCHITECTURE, CODE_QUALITY]
```

## Phase 4: Verification

**-> DECISION POINT 4**: Use AskUserQuestion to select verification depth

Deploy verification based on selection:

```
Full Verification:
- Task(subagent_type="pr-review-toolkit:silent-failure-hunter", ...)
- Task(subagent_type="pr-review-toolkit:code-simplifier", ...)
- Task(subagent_type="pr-review-toolkit:pr-test-analyzer", ...)
- Run: make test / npm test / pytest
- Run: make lint / npm run lint

Quick Verification:
- Run: make test / npm test / pytest
- Run: make lint / npm run lint
```

## Phase 5: Learning Capture

After successful verification, capture learnings to memory:

```
Learning Capture Phase
----------------------------------------------------------------------

Capturing successful fix patterns to cs-memory...

${FOR EACH noteworthy_fix}
[Captured] ${FIX_PATTERN_SUMMARY}
  -> patterns namespace
  -> Tags: ${TAGS}
${END FOR}

${FOR EACH learning}
[Captured] ${LEARNING_SUMMARY}
  -> learnings namespace
  -> Tags: ${TAGS}
${END FOR}

Total captured: ${COUNT} patterns, ${LEARNINGS_COUNT} learnings

----------------------------------------------------------------------
```

## Phase 6: Commit & Report

**-> DECISION POINT 5**: Use AskUserQuestion for commit strategy

Generate final report:

```markdown
## Fix Remediation Complete
----------------------------------------------------------------------

### Summary
- Findings addressed: ${FIXED_COUNT}/${TOTAL_COUNT}
- Categories fixed: ${CATEGORIES_LIST}
- Tests: ${TEST_STATUS}
- Linter: ${LINT_STATUS}

### Memory Contributions
- Fix patterns captured: ${PATTERNS_COUNT}
- Learnings captured: ${LEARNINGS_COUNT}
- These will help future remediations

### Files Modified
${FILE_LIST}

### Next Steps
${IF unfixed_findings}
- ${UNFIXED_COUNT} findings remain (${REASONS})
- Run `/fix --from-memory` later to address them
${END IF}

----------------------------------------------------------------------
```

</execution_protocol>

<from_memory_mode>
## From Memory Mode (`--from-memory`)

When `--from-memory` is specified, search cs-memory for unfixed review findings:

```python
from memory.recall import RecallService

recall = RecallService()

# Find open review findings
open_findings = recall.search(
    query="review finding status:open",
    namespace="reviews",
    limit=20
)

# Filter by spec if in spec context
if current_spec:
    open_findings = [f for f in open_findings if f.spec == current_spec]
```

This mode is useful for:
- Addressing findings captured by `/review` over time
- Fixing accumulated tech debt from multiple reviews
- Resuming work on findings from previous sessions
</from_memory_mode>

<graceful_degradation>
## Graceful Degradation

```
IF memory services unavailable:
  -> Proceed with fixes (no recalled context)
  -> Skip learning capture (warn user)
  -> Recommend manual documentation

IF no findings found:
  -> Check for CODE_REVIEW.md
  -> Offer to run /review first
  -> Search memory for open findings

IF verification fails:
  -> Report which verifications failed
  -> Do NOT capture patterns for failed fixes
  -> Offer to retry or revert
```
</graceful_degradation>
