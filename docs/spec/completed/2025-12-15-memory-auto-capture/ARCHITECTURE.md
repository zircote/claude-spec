---
document_type: architecture
project_id: SPEC-2025-12-15-001
version: 1.0.0
last_updated: 2025-12-15T20:00:00Z
status: draft
---

# Memory Auto-Capture Implementation - Technical Architecture

## System Overview

This architecture extends the existing cs-memory system to support automatic memory capture during command execution. It adds three missing capture methods, wires up unused configuration, and integrates capture triggers into command workflows.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Command Layer                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │  /cs:p   │  │  /cs:i   │  │  /cs:c   │  │/cs:review│                │
│  │ Planning │  │  Impl    │  │ Close-out│  │  Review  │                │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                │
│       │             │             │             │                       │
│       ▼             ▼             ▼             ▼                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Auto-Capture Triggers                         │   │
│  │  Phase transitions │ Task completions │ Findings │ Close-out    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Capture Service Layer                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     CaptureService (capture.py)                   │   │
│  │  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐   │   │
│  │  │ Existing Methods│  │  New Methods   │  │   Validation     │   │   │
│  │  │ - capture()     │  │ - capture_     │  │ - AUTO_CAPTURE_  │   │   │
│  │  │ - capture_      │  │   review()     │  │   NAMESPACES     │   │   │
│  │  │   decision()    │  │ - capture_     │  │ - validate_      │   │   │
│  │  │ - capture_      │  │   retrospective│  │   auto_capture() │   │   │
│  │  │   blocker()     │  │   ()           │  │                  │   │   │
│  │  │ - capture_      │  │ - capture_     │  │                  │   │   │
│  │  │   learning()    │  │   pattern()    │  │                  │   │   │
│  │  │ - capture_      │  │                │  │                  │   │   │
│  │  │   progress()    │  │                │  │                  │   │   │
│  │  └─────────────────┘  └────────────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Storage Layer (existing)                         │
│  ┌─────────────────────┐    ┌─────────────────────┐                     │
│  │   Git Notes         │    │   SQLite + vec      │                     │
│  │   refs/notes/cs/*   │    │   .cs-memory/       │                     │
│  └─────────────────────┘    └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Add methods to existing CaptureService | Maintain single responsibility, leverage existing infrastructure |
| Wire AUTO_CAPTURE_NAMESPACES for validation only | Keep capture flexible, validation catches typos |
| Command-integrated triggers (not hooks) | More reliable than hooks, explicit control |
| Silent capture with end-of-phase summary | Non-intrusive UX, batch visibility |
| Specialized methods per namespace | Type-safe, structured fields, better IDE support |

## Component Design

### Component 1: New Capture Methods

**Purpose**: Provide specialized capture methods for missing namespaces

**Location**: `memory/capture.py`

**New Methods**:

#### capture_review()

```python
def capture_review(
    self,
    spec: str | None,
    summary: str,
    category: str,           # security | performance | architecture | quality | tests | documentation
    severity: str,           # critical | high | medium | low
    file_path: str,
    line: int,
    description: str,
    suggested_fix: str | None = None,
    impact: str | None = None,
    commit: str = "HEAD",
    tags: list[str] | None = None,
) -> CaptureResult:
    """
    Capture a code review finding.

    Structured fields enable filtering and pattern detection across reviews.
    """
```

**Content Template**:
```markdown
## Category
{category}

## Severity
{severity}

## Location
{file_path}:{line}

## Description
{description}

## Impact
{impact}

## Suggested Fix
{suggested_fix}
```

#### capture_retrospective()

```python
def capture_retrospective(
    self,
    spec: str,
    summary: str,
    outcome: str,              # success | partial | failed | abandoned
    what_went_well: list[str],
    what_to_improve: list[str],
    key_learnings: list[str],
    recommendations: list[str] | None = None,
    metrics: dict[str, Any] | None = None,  # duration, effort, scope variance
    commit: str = "HEAD",
    tags: list[str] | None = None,
) -> CaptureResult:
    """
    Capture a project retrospective summary.

    Called during /cs:c close-out to preserve project learnings.
    """
```

**Content Template**:
```markdown
## Outcome
{outcome}

## What Went Well
{bullet_list(what_went_well)}

## What Could Be Improved
{bullet_list(what_to_improve)}

## Key Learnings
{bullet_list(key_learnings)}

## Recommendations
{bullet_list(recommendations)}

## Metrics
{metrics_table}
```

#### capture_pattern()

```python
def capture_pattern(
    self,
    spec: str | None,
    summary: str,
    pattern_type: str,        # success | anti-pattern | deviation
    description: str,
    context: str,
    applicability: str,       # When/where to apply
    evidence: str | None = None,
    commit: str = "HEAD",
    tags: list[str] | None = None,
) -> CaptureResult:
    """
    Capture a reusable pattern or anti-pattern.

    Patterns are cross-spec generalizations extracted from retrospectives
    and deviations encountered during implementation.
    """
```

**Content Template**:
```markdown
## Pattern Type
{pattern_type}

## Description
{description}

## Context
{context}

## Applicability
{applicability}

## Evidence
{evidence}
```

### Component 2: AUTO_CAPTURE_NAMESPACES Integration

**Purpose**: Validate namespace in auto-capture scenarios

**Location**: `memory/config.py` (existing) + `memory/capture.py`

**Changes**:

1. **Import AUTO_CAPTURE_NAMESPACES in capture.py**:
   ```python
   from .config import AUTO_CAPTURE_NAMESPACES, NAMESPACES, ...
   ```

2. **Add validation helper**:
   ```python
   def validate_auto_capture_namespace(namespace: str) -> bool:
       """
       Check if namespace is enabled for auto-capture.

       Returns True if namespace is in AUTO_CAPTURE_NAMESPACES.
       Raises CaptureError if namespace is invalid (not in NAMESPACES).
       """
       if namespace not in NAMESPACES:
           raise CaptureError(
               f"Invalid namespace: {namespace}",
               f"Use one of: {', '.join(sorted(NAMESPACES))}"
           )
       return namespace in AUTO_CAPTURE_NAMESPACES
   ```

3. **Use in capture methods**:
   ```python
   # In each specialized capture method
   if not validate_auto_capture_namespace("reviews"):
       return CaptureResult(success=False, warning="Auto-capture disabled for reviews")
   ```

### Component 3: Command Integration Points

**Purpose**: Define where auto-capture triggers in each command

**Trigger Design**: Each command has specific capture points at phase transitions or significant events.

#### /cs:p Integration Points

| Phase | Trigger | Namespace | Summary Template |
|-------|---------|-----------|------------------|
| Phase 0 | After scaffold commit | `inception` | "Initiated spec: {project_name}" |
| Phase 1 | After each elicitation round | `elicitation` | "Clarified: {topic}" |
| Phase 2 | After research completion | `research` | "Research: {topic}" |
| Phase 4 | After each ADR | `decisions` | ADR title |

**Implementation Approach**: Add capture calls to command execution flow via markdown instruction updates.

#### /cs:i Integration Points

| Event | Trigger | Namespace | Summary Template |
|-------|---------|-----------|------------------|
| Task done | After marking task complete | `progress` | "Completed: {task_description}" |
| Blocker hit | When user mentions "blocker" | `blockers` | Blocker title |
| Learning | When user mentions "learned/realized" | `learnings` | Learning summary |
| Deviation | When divergence logged | `patterns` | "Deviation: {type}" |

**Implementation Approach**: Add capture calls after state changes in command flow.

#### /cs:c Integration Points

| Phase | Trigger | Namespace | Summary Template |
|-------|---------|-----------|------------------|
| Step 4 | After RETROSPECTIVE.md generation | `retrospective` | "Retrospective: {project_name}" |
| Step 4.5 | For each key learning | `learnings` | Learning title |
| Step 4.5 | For each success pattern | `patterns` | "Pattern: {title}" |
| Step 4.5 | For each anti-pattern | `patterns` | "Anti-pattern: {title}" |

#### /cs:review Integration Points

| Event | Trigger | Namespace | Summary Template |
|-------|---------|-----------|------------------|
| Finding captured | After --capture mode | `reviews` | Finding summary |
| Pattern detected | When 2+ similar findings | `patterns` | "Review pattern: {title}" |

### Component 4: Capture Summary Display

**Purpose**: Show what was captured at end of phase/command

**Format**:
```
────────────────────────────────────────────────────────────────
Memory Capture Summary
────────────────────────────────────────────────────────────────
Captured: 3 memories
  ✓ inception:abc123d:1702560000000 - Initiated spec: user-auth
  ✓ elicitation:abc123e:1702560100000 - Clarified: auth method
  ✓ research:abc123f:1702560200000 - Research: OAuth providers
────────────────────────────────────────────────────────────────
```

**Implementation**: Accumulate captures during command execution, display summary at end.

## Data Design

### Capture Result Accumulator

New model for tracking captures during command execution:

```python
@dataclass
class CaptureAccumulator:
    """Tracks captures during a command execution for summary display."""
    captures: list[CaptureResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))

    def add(self, result: CaptureResult) -> None:
        """Add a capture result to the accumulator."""
        self.captures.append(result)

    def summary(self) -> str:
        """Generate summary string for display."""
        ...

    @property
    def count(self) -> int:
        return len(self.captures)

    @property
    def by_namespace(self) -> dict[str, int]:
        """Group counts by namespace."""
        ...
```

### ReviewFinding Integration

The existing `ReviewFinding` dataclass in `models.py` maps to `capture_review()`:

| ReviewFinding Field | capture_review Parameter |
|--------------------|--------------------------|
| severity | severity |
| category | category |
| file | file_path |
| line | line |
| summary | summary |
| details | description |
| resolution | (captured on update) |

## API Design

### CaptureService Extended API

```python
class CaptureService:
    # Existing methods
    def capture(...) -> CaptureResult: ...
    def capture_decision(...) -> CaptureResult: ...
    def capture_blocker(...) -> CaptureResult: ...
    def resolve_blocker(...) -> CaptureResult: ...
    def capture_learning(...) -> CaptureResult: ...
    def capture_progress(...) -> CaptureResult: ...

    # New methods (FR-001, FR-002, FR-003)
    def capture_review(
        self,
        spec: str | None,
        summary: str,
        category: str,
        severity: str,
        file_path: str,
        line: int,
        description: str,
        suggested_fix: str | None = None,
        impact: str | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
    ) -> CaptureResult: ...

    def capture_retrospective(
        self,
        spec: str,
        summary: str,
        outcome: str,
        what_went_well: list[str],
        what_to_improve: list[str],
        key_learnings: list[str],
        recommendations: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
    ) -> CaptureResult: ...

    def capture_pattern(
        self,
        spec: str | None,
        summary: str,
        pattern_type: str,
        description: str,
        context: str,
        applicability: str,
        evidence: str | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
    ) -> CaptureResult: ...
```

### Validation Function

```python
def validate_auto_capture_namespace(namespace: str) -> bool:
    """
    Check if namespace is valid and enabled for auto-capture.

    Args:
        namespace: The namespace to validate

    Returns:
        True if namespace is enabled for auto-capture

    Raises:
        CaptureError: If namespace is not a valid NAMESPACES value
    """
```

## Security Design

### Input Validation

All new methods validate:
1. **namespace**: Must be in NAMESPACES
2. **content length**: Must be < MAX_CONTENT_LENGTH
3. **summary length**: Must be < MAX_SUMMARY_LENGTH
4. **category/severity**: Must be in allowed values

### Allowed Values

```python
REVIEW_CATEGORIES = frozenset({
    "security", "performance", "architecture",
    "quality", "tests", "documentation"
})

REVIEW_SEVERITIES = frozenset({
    "critical", "high", "medium", "low"
})

RETROSPECTIVE_OUTCOMES = frozenset({
    "success", "partial", "failed", "abandoned"
})

PATTERN_TYPES = frozenset({
    "success", "anti-pattern", "deviation"
})
```

### Error Handling

All capture methods:
1. Never throw for content issues - return CaptureResult with warning
2. Do throw for invalid namespace (programming error)
3. Gracefully degrade if indexing fails (git note still saved)

## Performance Considerations

### Expected Load

- Typical command execution: 1-10 captures
- Close-out (/cs:c): Up to 20 captures (retrospective + extracted learnings)
- Review session: Up to 50 captures

### Performance Targets

| Operation | Target | Current (capture.py) |
|-----------|--------|---------------------|
| Single capture | < 500ms | ~300ms |
| Batch 10 captures | < 2s | N/A (sequential) |
| Summary generation | < 50ms | N/A (new) |

### Optimization Notes

- Captures are sequential (git notes append requires serialization)
- Embedding generation is the bottleneck (~200ms per capture)
- Consider batch embedding in future (P2 requirement)

## Testing Strategy

### Unit Testing

Each new method requires:
1. Happy path test with all parameters
2. Missing optional parameters test
3. Invalid category/severity/outcome test
4. Content length limit test
5. Integration with existing CaptureService

### Test Coverage Targets

| Component | Target |
|-----------|--------|
| capture_review() | 100% |
| capture_retrospective() | 100% |
| capture_pattern() | 100% |
| validate_auto_capture_namespace() | 100% |
| CaptureAccumulator | 100% |

### Integration Testing

1. Full /cs:p flow with auto-capture enabled
2. Full /cs:i flow with task completion capture
3. Full /cs:c flow with retrospective capture
4. Full /cs:review flow with finding capture

## Deployment Considerations

### Backward Compatibility

- All changes are additive to CaptureService
- Existing capture() and specialized methods unchanged
- Commands can use new methods without breaking existing workflows

### Migration

- No migration needed - new methods are opt-in
- Existing memories remain unchanged
- AUTO_CAPTURE_NAMESPACES wiring is validation-only

### Rollback Plan

- Remove new methods from capture.py
- Remove imports of AUTO_CAPTURE_NAMESPACES
- Commands gracefully degrade (pseudo-code remains non-functional)

## Future Considerations

### P2: Batch Capture Optimization

Current: Sequential captures with individual git notes append
Future: Batch multiple captures in single git operation

```python
def capture_batch(self, captures: list[CaptureRequest]) -> list[CaptureResult]:
    """
    Capture multiple memories in a single batch operation.

    Optimizes by:
    1. Acquiring lock once
    2. Appending all notes in sequence
    3. Batch embedding generation
    4. Batch index insertion
    """
```

### P2: Verbose Preview Mode

For debugging, add `--verbose` flag to show what will be captured:

```
[PREVIEW] Would capture:
  - inception: "Initiated spec: user-auth"
  - elicitation: "Clarified: auth method"

Proceed with capture? [Y/n]
```

### Future: Hook-Based Capture

Session-level hooks for automatic capture without command changes:
- SessionStart: Load context
- SessionEnd: Capture session summary
- UserPrompt: Pattern detection

This requires hook infrastructure changes beyond current scope.

## Appendix

### Namespace Coverage Matrix

| Namespace | Generic capture() | Specialized Method | Auto-Capture |
|-----------|------------------|-------------------|--------------|
| inception | ✓ | - | ✓ |
| elicitation | ✓ | - | ✓ |
| research | ✓ | - | ✓ |
| decisions | ✓ | capture_decision() | ✓ |
| progress | ✓ | capture_progress() | ✓ |
| blockers | ✓ | capture_blocker() | ✓ |
| reviews | ✓ | **capture_review()** (new) | ✓ |
| learnings | ✓ | capture_learning() | ✓ |
| retrospective | ✓ | **capture_retrospective()** (new) | ✓ |
| patterns | ✓ | **capture_pattern()** (new) | ✓ |

### References

- Existing capture.py implementation
- config.py namespace definitions
- models.py ReviewFinding dataclass
- Command files (p.md, i.md, c.md, review.md) memory integration sections
