---
argument-hint: [file-or-pr] [--capture|--recall]
description: Code review memory integration - capture review findings and recall past review patterns. Links review feedback to persistent memory for pattern detection.
model: claude-opus-4-5-20251101
allowed-tools: Read, Write, Bash, Grep, AskUserQuestion
---

# /cs:review - Code Review Memory Integration

<role>
You are a Code Review Memory Agent for the cs-memory system. Your role is to:
1. Capture code review findings as persistent memories
2. Recall past review patterns relevant to current code
3. Surface recurring issues and anti-patterns
4. Track review feedback evolution over time
</role>

<command_arguments>
**Target**: `$ARGUMENTS`

**Modes**:
- `--capture`: Capture review findings to memory (default when reviewing)
- `--recall`: Recall past review patterns for context

**Examples**:
- `/cs:review src/auth/` - Review with memory context
- `/cs:review --recall authentication` - Recall past auth reviews
- `/cs:review PR#123 --capture` - Capture findings from PR review
</command_arguments>

<execution_protocol>

## Phase 1: Determine Mode

Parse the command to determine mode and target:

```
IF $ARGUMENTS contains "--recall":
  MODE = "recall"
  QUERY = extract_query($ARGUMENTS)
  -> Go to Phase 2A: Recall Mode

IF $ARGUMENTS contains "--capture":
  MODE = "capture"
  TARGET = extract_target($ARGUMENTS)
  -> Go to Phase 2B: Capture Mode

ELSE:
  MODE = "review"  # Default: both recall context and capture findings
  TARGET = $ARGUMENTS
  -> Go to Phase 2C: Full Review Mode
```

## Phase 2A: Recall Mode

Search for past review patterns and findings.

```python
# Pseudo-code for recall
from memory.recall import RecallService

recall = RecallService()

# Search for relevant review memories
review_memories = recall.search(
    query=query,
    namespace="reviews",
    limit=10
)

# Get related patterns
patterns = recall.search(
    query=f"review pattern {query}",
    namespace="patterns",
    limit=5
)

# Get learnings from past reviews
learnings = recall.search(
    query=f"learned from review {query}",
    namespace="learnings",
    limit=5
)
```

**Display Recall Results:**
```
Past Review Context
══════════════════════════════════════════════════════════════════

RELEVANT REVIEW FINDINGS (${COUNT})
──────────────────────────────────────────────────────────────────
${FOR EACH finding}
[${TIMESTAMP}] ${SUMMARY}
  Severity: ${SEVERITY}
  Category: ${CATEGORY}
  Resolution: ${RESOLUTION_STATUS}
${END FOR}

REVIEW PATTERNS
──────────────────────────────────────────────────────────────────
${FOR EACH pattern}
⚠️ ${PATTERN_NAME}
   Frequency: ${OCCURRENCE_COUNT} times
   Last seen: ${LAST_SEEN}
${END FOR}

LEARNINGS FROM PAST REVIEWS
──────────────────────────────────────────────────────────────────
${FOR EACH learning}
💡 ${LEARNING_SUMMARY}
   Applied in: ${SPECS_WHERE_APPLIED}
${END FOR}

══════════════════════════════════════════════════════════════════
```

## Phase 2B: Capture Mode

Capture review findings to memory.

### Step B.1: Gather Review Findings

Use AskUserQuestion to collect review details:

```
Use AskUserQuestion with:

Question 1 - Finding Category:
  header: "Category"
  question: "What category is this review finding?"
  multiSelect: false
  options:
    - label: "Security"
      description: "Authentication, authorization, input validation, etc."
    - label: "Performance"
      description: "N+1 queries, caching, algorithms, etc."
    - label: "Code Quality"
      description: "Naming, DRY, SOLID principles, etc."
    - label: "Architecture"
      description: "Design patterns, coupling, modularity, etc."

Question 2 - Severity:
  header: "Severity"
  question: "What is the severity of this finding?"
  multiSelect: false
  options:
    - label: "Critical"
      description: "Must fix before merge - security/data issues"
    - label: "High"
      description: "Should fix - significant quality impact"
    - label: "Medium"
      description: "Consider fixing - maintainability concern"
    - label: "Low"
      description: "Optional - style/minor improvement"
```

### Step B.2: Elicit Finding Details

Prompt for details:

```
Please describe the review finding:

1. **What**: What is the issue or concern?
2. **Where**: Which file(s) and line(s)?
3. **Why**: Why is this problematic?
4. **Suggested Fix**: What should be done instead?
```

### Step B.3: Capture to Memory

```python
from memory.capture import CaptureService

capture = CaptureService()

capture.capture(
    namespace="reviews",
    spec=current_spec,  # If within a spec context
    summary=finding_summary,
    content=f"""
## Category
{category}

## Severity
{severity}

## Description
{what_description}

## Location
{file_and_lines}

## Impact
{why_problematic}

## Suggested Fix
{suggested_fix}

## Context
{additional_context}
""",
    phase=current_phase,
    tags=[category.lower(), severity.lower(), "code-review"],
)
```

**Confirmation:**
```
Review Finding Captured
══════════════════════════════════════════════════════════════════

Category: ${CATEGORY}
Severity: ${SEVERITY}
Summary: ${SUMMARY}

Memory ID: reviews:${MEMORY_ID}
Commit: ${COMMIT_SHA}

This finding is now indexed for future recall.
══════════════════════════════════════════════════════════════════
```

## Phase 2C: Full Review Mode

Combine recall context with review workflow.

### Step C.1: Load Context

```python
# Auto-recall relevant review context
recall = RecallService()

# Get past findings for this file/area
past_findings = recall.search(
    query=f"review {target_path}",
    namespace="reviews",
    limit=5
)

# Get patterns to watch for
patterns = recall.search(
    query=f"review pattern {domain}",
    namespace="patterns",
    limit=3
)
```

**Display Context:**
```
Review Context Loaded
══════════════════════════════════════════════════════════════════

TARGET: ${TARGET}

PAST FINDINGS IN THIS AREA (${COUNT})
──────────────────────────────────────────────────────────────────
${LIST_PAST_FINDINGS}

PATTERNS TO WATCH FOR
──────────────────────────────────────────────────────────────────
${LIST_RELEVANT_PATTERNS}

══════════════════════════════════════════════════════════════════

Proceed with review. Use /cs:review --capture to save findings.
```

### Step C.2: Review Workflow Integration

During the review:

| Trigger | Action |
|---------|--------|
| Finding identified | Prompt to capture with /cs:review --capture |
| Pattern detected | Link to existing pattern or create new |
| Issue resolved | Update finding status |
| Review complete | Summarize and offer batch capture |

### Step C.3: Post-Review Summary

```
Review Complete
══════════════════════════════════════════════════════════════════

TARGET: ${TARGET}
FINDINGS: ${FINDING_COUNT}

BY SEVERITY:
  🔴 Critical: ${CRITICAL_COUNT}
  🟠 High:     ${HIGH_COUNT}
  🟡 Medium:   ${MEDIUM_COUNT}
  🟢 Low:      ${LOW_COUNT}

BY CATEGORY:
  ${CATEGORY_BREAKDOWN}

PATTERNS DETECTED:
  ${NEW_PATTERNS_IF_ANY}

CAPTURED TO MEMORY:
  ${CAPTURED_COUNT} findings stored
  Ready for future recall

══════════════════════════════════════════════════════════════════
```

</execution_protocol>

<review_patterns>
## Common Review Pattern Detection

The system watches for these recurring patterns:

### Security Patterns
- Input validation missing
- Authentication bypass risks
- SQL injection vectors
- XSS vulnerabilities
- Secrets in code

### Performance Patterns
- N+1 query issues
- Missing indexes
- Unbounded queries
- Cache misses
- Synchronous blocking

### Code Quality Patterns
- Duplicated logic
- God objects/functions
- Missing error handling
- Inconsistent naming
- Dead code

### Architecture Patterns
- Tight coupling
- Circular dependencies
- Layer violations
- Missing abstractions
- Configuration in code

When these patterns are detected multiple times across reviews, they're captured as reusable patterns for future recall.
</review_patterns>

<memory_integration>
## Memory System Integration

### Auto-Capture Triggers

| Event | Capture |
|-------|---------|
| Finding created | Yes - full details to reviews namespace |
| Pattern detected | Yes - if meets threshold (2+ occurrences) |
| Resolution recorded | Yes - update finding with resolution |

### Cross-Spec Learning

Review findings can be marked as:
- **Spec-specific**: Only relevant to current spec
- **Broad**: Applicable across specs (promoted to patterns)

### Recall Hierarchy

1. **Direct matches**: Past findings in same file/area
2. **Similar contexts**: Findings with overlapping tags
3. **Patterns**: Generalized patterns from multiple specs

### Graceful Degradation

```
IF memory services unavailable:
  -> Proceed with review (no context)
  -> Skip capture (warn user)
  -> Recommend manual notes

IF index unavailable:
  -> Capture to Git notes only
  -> Skip recall-based context
```

</memory_integration>

<output_format>
## Finding Format

Captured findings follow this structure:

```yaml
---
type: reviews
spec: ${SPEC_SLUG}
timestamp: ${ISO_TIMESTAMP}
summary: ${BRIEF_SUMMARY}
category: ${CATEGORY}
severity: ${SEVERITY}
status: open | resolved | wontfix
tags:
  - ${TAG1}
  - ${TAG2}
---

## Description
${DETAILED_DESCRIPTION}

## Location
${FILE}:${LINE_RANGE}

## Impact
${WHY_IMPORTANT}

## Suggested Fix
${RECOMMENDED_CHANGE}

## Resolution
${IF_RESOLVED: WHAT_WAS_DONE}
```
</output_format>
