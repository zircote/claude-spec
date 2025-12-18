---
document_type: implementation_plan
project_id: SPEC-2025-12-17-001
version: 1.0.0
last_updated: 2025-12-17T14:00:00Z
status: draft
estimated_effort: 16-24 hours
---

# Hooks Based Git-Native Memory Architecture - Implementation Plan

## Overview

Implementation of 4 hook enhancements for bidirectional memory flow:
1. **PostToolUse hook** - Automatic learning capture
2. **SessionStart enhancement** - Memory injection
3. **Trigger phrase detection** - Context-aware recall
4. **Stop hook enhancement** - Memory queue flush

## Phase Summary

| Phase | Focus | Tasks | Estimated Effort |
|-------|-------|-------|------------------|
| Phase 1 | PostToolUse Infrastructure | 8 tasks | 6-8 hours |
| Phase 2 | SessionStart Memory Injection | 5 tasks | 3-4 hours |
| Phase 3 | Trigger Phrase Detection | 5 tasks | 3-4 hours |
| Phase 4 | Integration & Testing | 6 tasks | 4-8 hours |

---

## Phase 1: PostToolUse Infrastructure

**Goal**: Implement automatic learning capture from tool execution.

**Prerequisites**: cs-memory module operational (completed)

### Task 1.1: Create Learning Detector Module

- **Description**: Create `plugins/cs/learnings/detector.py` with signal detection and scoring
- **Files**: `plugins/cs/learnings/__init__.py`, `plugins/cs/learnings/detector.py`
- **Acceptance Criteria**:
  - [ ] LearningDetector class with calculate_score() method
  - [ ] Signal patterns for errors, workarounds, discoveries
  - [ ] Score calculation returns 0.0-1.0 float
  - [ ] Noise patterns for filtering routine output
- **Dependencies**: None

### Task 1.2: Create ToolLearning Model

- **Description**: Add ToolLearning dataclass to models
- **Files**: `plugins/cs/learnings/models.py`
- **Acceptance Criteria**:
  - [ ] Frozen dataclass with tool_name, category, severity, summary, etc.
  - [ ] Validation for category and severity values
  - [ ] to_memory() method for conversion to Memory type
- **Dependencies**: None

### Task 1.3: Implement Content Deduplication

- **Description**: Create deduplication module with content hashing
- **Files**: `plugins/cs/learnings/deduplicator.py`
- **Acceptance Criteria**:
  - [ ] get_content_hash() function (SHA256, first 16 chars)
  - [ ] SessionDeduplicator class with LRU cache
  - [ ] is_duplicate() method checking session cache
- **Dependencies**: None

### Task 1.4: Implement Learning Extractor

- **Description**: Extract structured learning from tool responses
- **Files**: `plugins/cs/learnings/extractor.py`
- **Acceptance Criteria**:
  - [ ] extract_learning() function returning ToolLearning | None
  - [ ] Auto-generate summary from error/output
  - [ ] Truncate output_excerpt to 1KB
  - [ ] Filter through filter_pipeline for secrets
- **Dependencies**: Task 1.1, Task 1.2

### Task 1.5: Create PostToolUse Hook

- **Description**: Main hook script for tool execution capture
- **Files**: `plugins/cs/hooks/post_tool_capture.py`
- **Acceptance Criteria**:
  - [ ] Reads PostToolUse JSON from stdin
  - [ ] Uses LearningDetector to calculate score
  - [ ] Checks deduplication before queuing
  - [ ] Queues via CaptureAccumulator (imports from memory.models)
  - [ ] Returns exit 0 within 100ms (never blocks)
- **Dependencies**: Task 1.1, Task 1.3, Task 1.4

### Task 1.6: Register PostToolUse in hooks.json

- **Description**: Add PostToolUse event registration
- **Files**: `plugins/cs/hooks/hooks.json`
- **Acceptance Criteria**:
  - [ ] PostToolUse entry with matcher for Bash|Read|Write|Edit|WebFetch
  - [ ] Timeout set to 5 seconds
  - [ ] Command path to post_tool_capture.py
- **Dependencies**: Task 1.5

### Task 1.7: Add Queue Flusher Step

- **Description**: Create post-step for memory queue flush
- **Files**: `plugins/cs/steps/memory_queue_flusher.py`
- **Acceptance Criteria**:
  - [ ] MemoryQueueFlusherStep class with run() method
  - [ ] Reads queue from session state or global accumulator
  - [ ] Calls CaptureService for each queued learning
  - [ ] Returns StepResult with count summary
- **Dependencies**: Task 1.5

### Task 1.8: Register Queue Flusher in Step Runner

- **Description**: Add memory_queue_flusher to STEP_MODULES whitelist
- **Files**: `plugins/cs/hooks/lib/step_runner.py`
- **Acceptance Criteria**:
  - [ ] Add "flush-memory-queue": "memory_queue_flusher" to STEP_MODULES
  - [ ] Update default config to include flush-memory-queue in postSteps
- **Dependencies**: Task 1.7

### Phase 1 Deliverables

- [ ] `plugins/cs/learnings/` module with detector, models, deduplicator, extractor
- [ ] `plugins/cs/hooks/post_tool_capture.py` hook
- [ ] `plugins/cs/steps/memory_queue_flusher.py` step
- [ ] Updated hooks.json with PostToolUse registration

### Phase 1 Exit Criteria

- [ ] PostToolUse hook fires on Bash commands
- [ ] Errors captured with score >= 0.6
- [ ] Queue flushed on session Stop
- [ ] All unit tests passing

---

## Phase 2: SessionStart Memory Injection

**Goal**: Inject relevant memories at session start.

**Prerequisites**: Phase 1 complete (queue flusher working)

### Task 2.1: Create Memory Injector Module

- **Description**: Module to query and format memories for injection
- **Files**: `plugins/cs/hooks/lib/memory_injector.py`
- **Acceptance Criteria**:
  - [ ] MemoryInjector class with RecallService dependency
  - [ ] get_session_memories() method with spec and limit params
  - [ ] format_for_context() method returning markdown
  - [ ] apply_aging() method using MemoryAger
- **Dependencies**: None

### Task 2.2: Extend SessionStart Hook

- **Description**: Add memory injection to existing session_start.py
- **Files**: `plugins/cs/hooks/session_start.py`
- **Acceptance Criteria**:
  - [ ] Import MemoryInjector
  - [ ] Detect active spec from docs/spec/active/
  - [ ] Call injector.get_session_memories() (limit 10)
  - [ ] Append "## Session Memories" section to context_parts
  - [ ] Graceful fallback if RecallService unavailable
- **Dependencies**: Task 2.1

### Task 2.3: Add Memory Injection Config

- **Description**: Add configuration for memory injection behavior
- **Files**: `plugins/cs/hooks/lib/config_loader.py`
- **Acceptance Criteria**:
  - [ ] is_session_memory_enabled() function
  - [ ] get_session_memory_config() returning limit, hydrationLevel
  - [ ] Default: enabled=true, limit=10, hydrationLevel="SUMMARY"
- **Dependencies**: None

### Task 2.4: Implement Spec Detection

- **Description**: Detect active specification from project structure
- **Files**: `plugins/cs/hooks/lib/spec_detector.py`
- **Acceptance Criteria**:
  - [ ] detect_active_spec() function
  - [ ] Check docs/spec/active/ for single active project
  - [ ] Parse README.md frontmatter for slug
  - [ ] Return None if no active spec or multiple specs
- **Dependencies**: None

### Task 2.5: Write Memory Injection Tests

- **Description**: Unit and integration tests for memory injection
- **Files**: `tests/hooks/test_memory_injection.py`
- **Acceptance Criteria**:
  - [ ] Test MemoryInjector.get_session_memories()
  - [ ] Test format_for_context() output
  - [ ] Test session_start.py with mocked RecallService
  - [ ] Test graceful fallback on service unavailability
- **Dependencies**: Task 2.1, Task 2.2

### Phase 2 Deliverables

- [ ] `plugins/cs/hooks/lib/memory_injector.py`
- [ ] `plugins/cs/hooks/lib/spec_detector.py`
- [ ] Extended `session_start.py` with memory injection
- [ ] Tests in `tests/hooks/test_memory_injection.py`

### Phase 2 Exit Criteria

- [ ] Session start shows "## Session Memories" section
- [ ] 5-10 relevant memories injected
- [ ] Graceful fallback when no memories exist
- [ ] Config options respected

---

## Phase 3: Trigger Phrase Detection

**Goal**: Detect memory-related phrases and inject context.

**Prerequisites**: Phase 2 complete (RecallService integration working)

### Task 3.1: Create Trigger Detector Module

- **Description**: Pattern matching for memory trigger phrases
- **Files**: `plugins/cs/hooks/lib/trigger_detector.py`
- **Acceptance Criteria**:
  - [ ] TRIGGER_PATTERNS list of compiled regexes
  - [ ] TriggerDetector class
  - [ ] should_inject() method returning bool
  - [ ] get_context_memories() using RecallService.search()
- **Dependencies**: None

### Task 3.2: Create Trigger Detector Hook

- **Description**: UserPromptSubmit hook for trigger detection
- **Files**: `plugins/cs/hooks/trigger_detector.py`
- **Acceptance Criteria**:
  - [ ] Read UserPromptSubmit JSON from stdin
  - [ ] Check TriggerDetector.should_inject()
  - [ ] Query memories if triggered
  - [ ] Return additionalContext with memories or empty
  - [ ] 5 second timeout
- **Dependencies**: Task 3.1

### Task 3.3: Register Trigger Detector in hooks.json

- **Description**: Add UserPromptSubmit hook registration
- **Files**: `plugins/cs/hooks/hooks.json`
- **Acceptance Criteria**:
  - [ ] Add trigger_detector.py to UserPromptSubmit hooks
  - [ ] Position after command_detector, before prompt_capture
  - [ ] Timeout set to 5 seconds
- **Dependencies**: Task 3.2

### Task 3.4: Implement Memory Context Formatter

- **Description**: Format retrieved memories for prompt context
- **Files**: `plugins/cs/hooks/lib/memory_formatter.py`
- **Acceptance Criteria**:
  - [ ] format_memory_context() function
  - [ ] Markdown output with memory type, summary, commit ref
  - [ ] Truncate to max_tokens parameter
  - [ ] Include "Use /cs:recall for more" hint
- **Dependencies**: None

### Task 3.5: Write Trigger Detection Tests

- **Description**: Tests for trigger phrase detection
- **Files**: `tests/hooks/test_trigger_detector.py`
- **Acceptance Criteria**:
  - [ ] Test pattern matching for all TRIGGER_PATTERNS
  - [ ] Test should_inject() edge cases
  - [ ] Test hook integration with mocked RecallService
  - [ ] Test formatting output
- **Dependencies**: Task 3.1, Task 3.2

### Phase 3 Deliverables

- [ ] `plugins/cs/hooks/lib/trigger_detector.py`
- [ ] `plugins/cs/hooks/trigger_detector.py` hook
- [ ] `plugins/cs/hooks/lib/memory_formatter.py`
- [ ] Updated hooks.json
- [ ] Tests in `tests/hooks/test_trigger_detector.py`

### Phase 3 Exit Criteria

- [ ] "why did we" triggers memory injection
- [ ] Relevant memories appear in additionalContext
- [ ] Non-trigger prompts pass through unchanged
- [ ] <50ms detection time

---

## Phase 4: Integration & Testing

**Goal**: End-to-end testing and documentation.

**Prerequisites**: Phases 1-3 complete

### Task 4.1: Write Integration Tests

- **Description**: End-to-end tests for full hook flow
- **Files**: `tests/hooks/test_hook_integration.py`
- **Acceptance Criteria**:
  - [ ] Test PostToolUse → Queue → Stop → Flush flow
  - [ ] Test SessionStart with populated memories
  - [ ] Test trigger detection with semantic search
  - [ ] Test multi-hook interaction (all 4 hooks in sequence)
- **Dependencies**: All previous phases

### Task 4.2: Performance Benchmarks

- **Description**: Benchmark hook execution times
- **Files**: `tests/benchmarks/test_hook_performance.py`
- **Acceptance Criteria**:
  - [ ] PostToolUse < 100ms (p99)
  - [ ] SessionStart < 500ms with memory query
  - [ ] Trigger detection < 50ms
  - [ ] Queue flush < 2s for 20 items
- **Dependencies**: All previous phases

### Task 4.3: Update Configuration Documentation

- **Description**: Document new configuration options
- **Files**: `plugins/cs/memory/USER_GUIDE.md`
- **Acceptance Criteria**:
  - [ ] Document postToolCapture config section
  - [ ] Document sessionMemory config section
  - [ ] Document CS_TOOL_CAPTURE_ENABLED env var
  - [ ] Add troubleshooting section
- **Dependencies**: All previous phases

### Task 4.4: Update CLAUDE.md

- **Description**: Add project to Active Spec Projects section
- **Files**: `CLAUDE.md`
- **Acceptance Criteria**:
  - [ ] Add entry under "Active Spec Projects"
  - [ ] Document new hook capabilities
  - [ ] Update Memory Commands section
- **Dependencies**: All previous phases

### Task 4.5: Create DECISIONS.md

- **Description**: Document architectural decisions made
- **Files**: `docs/spec/active/2025-12-17-hook-based-memory-arch/DECISIONS.md`
- **Acceptance Criteria**:
  - [ ] ADR-001: In-memory queue vs file-based
  - [ ] ADR-002: Capture threshold 0.6
  - [ ] ADR-003: Session memory limit 10
  - [ ] ADR-004: Tool matcher selection
- **Dependencies**: All previous phases

### Task 4.6: Final Testing and Validation

- **Description**: Run full test suite and validate requirements
- **Files**: N/A (validation only)
- **Acceptance Criteria**:
  - [ ] All tests passing (make ci)
  - [ ] Coverage > 80% for new code
  - [ ] All FR-* requirements verified
  - [ ] Performance targets met
- **Dependencies**: All previous tasks

### Phase 4 Deliverables

- [ ] Integration tests in `tests/hooks/test_hook_integration.py`
- [ ] Benchmarks in `tests/benchmarks/`
- [ ] Updated USER_GUIDE.md
- [ ] Updated CLAUDE.md
- [ ] DECISIONS.md with ADRs

### Phase 4 Exit Criteria

- [ ] All tests passing
- [ ] Documentation complete
- [ ] Performance targets met
- [ ] Ready for code review

---

## Dependency Graph

```
Phase 1: PostToolUse Infrastructure
├── Task 1.1 (Detector) ──────────────┬──────────────────────────────┐
├── Task 1.2 (Model) ─────────────────┤                              │
├── Task 1.3 (Deduplicator) ──────────┼── Task 1.4 (Extractor) ──────┼── Task 1.5 (Hook)
│                                     │                              │        │
│                                     │                              │        ▼
│                                     │                              │   Task 1.6 (hooks.json)
│                                     │                              │
│                                     └──────────────────────────────┴── Task 1.7 (Flusher)
│                                                                              │
└──────────────────────────────────────────────────────────────────── Task 1.8 (Step Runner)

Phase 2: SessionStart Memory
├── Task 2.1 (Injector) ────── Task 2.2 (Extend Hook) ────── Task 2.5 (Tests)
├── Task 2.3 (Config)
└── Task 2.4 (Spec Detector)

Phase 3: Trigger Detection
├── Task 3.1 (Detector Module) ────── Task 3.2 (Hook) ────── Task 3.3 (Register)
├── Task 3.4 (Formatter)
└── Task 3.5 (Tests)

Phase 4: Integration
├── Task 4.1 (Integration Tests)
├── Task 4.2 (Benchmarks)
├── Task 4.3 (User Docs)
├── Task 4.4 (CLAUDE.md)
├── Task 4.5 (DECISIONS.md)
└── Task 4.6 (Final Validation)
```

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| False positive captures | Tune threshold in Task 1.1 | 1 |
| Hook timeout blocking | Hard timeout in Task 1.5 | 1 |
| Queue loss on crash | File backup in Task 1.7 | 1 |
| Large context injection | Limit in Task 2.1 | 2 |

## Testing Checklist

- [ ] Unit tests for LearningDetector
- [ ] Unit tests for SessionDeduplicator
- [ ] Unit tests for MemoryInjector
- [ ] Unit tests for TriggerDetector
- [ ] Integration test: PostToolUse flow
- [ ] Integration test: SessionStart flow
- [ ] Integration test: Trigger detection flow
- [ ] Performance benchmark: all hooks
- [ ] E2E test: multi-hook sequence

## Documentation Tasks

- [ ] Update USER_GUIDE.md with new features
- [ ] Update DEVELOPER_GUIDE.md with hook extension points
- [ ] Create DECISIONS.md with ADRs
- [ ] Update CLAUDE.md project entry

## Launch Checklist

- [ ] All tests passing (`make ci`)
- [ ] Coverage > 80% for new code
- [ ] Documentation complete
- [ ] Performance benchmarks pass
- [ ] Code review complete
- [ ] No security vulnerabilities (bandit)

## Post-Launch

- [ ] Monitor stderr logs for hook errors
- [ ] Gather feedback on capture quality
- [ ] Tune threshold based on false positive rate
- [ ] Consider ML-based extraction for v2
