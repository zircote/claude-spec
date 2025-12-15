# Remediation Tasks: cs-memory Module

Generated from code review on 2025-12-14. Run `/cr-fx` to auto-remediate.

---

## Critical (Fix Before Deploy)

- [ ] **PERF-001**: Add batch get to IndexService
  - File: `plugins/cs/memory/index.py`
  - Action: Add `get_batch(memory_ids: list[str]) -> dict[str, Memory]` method
  - Impact: Fixes N+1 queries in search()

- [ ] **PERF-002**: Optimize RecallService.context()
  - File: `plugins/cs/memory/recall.py:163-206`
  - Action: Replace per-namespace search loop with single spec-filtered query
  - Impact: Reduces 10 embedding generations to 0, eliminates N+1

---

## High Priority (This Sprint)

### Architecture

- [ ] **ARCH-001**: Add public methods to IndexService for RecallService
  - File: `plugins/cs/memory/index.py`
  - Action: Add `list_recent(spec, namespace, limit)` and `get_by_commit(sha)` public methods
  - Removes: Direct `_get_connection()` access in `recall.py:237,253,287`

- [ ] **ARCH-002**: Add public method to IndexService for SyncService
  - File: `plugins/cs/memory/index.py`
  - Action: Add `get_all_ids() -> set[str]` method
  - Removes: Direct `_get_connection()` access in `sync.py:174-176`

- [ ] **ARCH-003**: Batch lookup in RecallService.search()
  - File: `plugins/cs/memory/recall.py:91-101`
  - Action: Use new `get_batch()` instead of per-result `get()`

### Code Quality

- [ ] **QUAL-001**: Rename IndexError exception
  - File: `plugins/cs/memory/exceptions.py:53`
  - Action: Rename `class IndexError` to `class MemoryIndexError`
  - Update: All imports/usages across codebase

- [ ] **QUAL-002**: Extract temporal decay calculation
  - Files: `lifecycle.py:86-165`, `search.py:326-353`
  - Action: Create `utils.py` with `calculate_temporal_decay(timestamp, half_life_days)`

- [ ] **QUAL-003**: Extract namespace validation
  - Files: `git_ops.py:112-209`, `capture.py:115-119`
  - Action: Create `validators.py` with `validate_namespace(namespace)`

- [ ] **QUAL-004**: Extract base service class
  - Files: `capture.py:66-82`, `recall.py:26-42`, `sync.py:31-47`
  - Action: Create `BaseMemoryService` with common constructor pattern

### Tests

- [ ] **TEST-001**: Add tests for `__init__.py` factory functions
  - File: `tests/memory/test_init.py` (new)
  - Cover: `get_capture_service()`, `get_recall_service()`, etc.

- [ ] **TEST-002**: Add tests for config.py
  - File: `tests/memory/test_config.py` (new)
  - Cover: NAMESPACES, EMBEDDING_DIMENSIONS, MAX_RECALL_LIMIT validation

- [ ] **TEST-003**: Add tests for exceptions.py
  - File: `tests/memory/test_exceptions.py` (new)
  - Cover: Exception hierarchy, pre-defined error constants

- [ ] **TEST-004**: Add capture error path tests
  - File: `tests/memory/test_capture.py`
  - Add: Lock timeout, cleanup on exceptions, concurrent capture tests

- [ ] **TEST-005**: Add recall edge case tests
  - File: `tests/memory/test_recall.py`
  - Add: Date filters, file hydration failures, multiple memories per commit

---

## Medium Priority (Next Sprint)

### Security

- [ ] **SEC-001**: Add git ref validation
  - File: `plugins/cs/memory/git_ops.py`
  - Action: Add `validate_git_ref(ref)` with regex `^[a-zA-Z0-9_./-]+$` and dash prefix check

- [ ] **SEC-002**: Add model integrity verification
  - File: `plugins/cs/memory/embedding.py:74-82`
  - Action: Consider SHA256 verification for known-good model versions

### Architecture

- [ ] **ARCH-003**: Split lifecycle.py (531 lines)
  - Current: `lifecycle.py`
  - Split into: `lifecycle/aging.py`, `lifecycle/summarization.py`, `lifecycle/archival.py`

- [ ] **ARCH-004**: Split patterns.py (650 lines)
  - Current: `patterns.py`
  - Split into: `patterns/models.py`, `patterns/detection.py`, `patterns/suggestion.py`

- [ ] **ARCH-005**: Fix module-level singleton anti-pattern
  - Files: `lifecycle.py:521-530`, `patterns.py:640-649`, `search.py:406-415`
  - Action: Use proper DI or registry pattern

- [ ] **ARCH-006**: Add Protocol interfaces
  - Action: Create `protocols.py` with `GitOpsProtocol`, `EmbeddingServiceProtocol`, `IndexServiceProtocol`

### Performance

- [ ] **PERF-003**: Add file hydration limits
  - File: `plugins/cs/memory/recall.py:140-158`
  - Action: Add `MAX_FILES_PER_HYDRATION = 20`, `MAX_FILE_SIZE_BYTES = 100_000`

- [ ] **PERF-004**: Stream full_reindex
  - File: `plugins/cs/memory/sync.py:106-151`
  - Action: Process notes in streaming fashion with batched embeddings

- [ ] **PERF-005**: Add embedding cache
  - File: `plugins/cs/memory/capture.py:169-171`
  - Action: Add LRU cache for recently embedded text

- [ ] **PERF-006**: Use OrderedDict for cache
  - File: `plugins/cs/memory/search.py:119-121`
  - Action: Replace dict with `collections.OrderedDict` for O(1) eviction

### Code Quality

- [ ] **QUAL-005**: Use CaptureRequest dataclass
  - File: `plugins/cs/memory/capture.py:84-94`
  - Action: Replace 8 parameters with `CaptureRequest` dataclass

- [ ] **QUAL-006**: Add TypedDict for get_sync_status
  - File: `plugins/cs/memory/sync.py:228`
  - Action: Create `SyncStatus` TypedDict

### Documentation

- [ ] **DOC-001**: Add prerequisites to USER_GUIDE.md
  - Add: `pip install sentence-transformers sqlite-vec`

- [ ] **DOC-002**: Fix DEVELOPER_GUIDE.md API references
  - Remove: References to non-existent `RecallError`, `SyncError`, `VALID_NAMESPACES`

---

## Low Priority (Backlog)

### Security
- [ ] **SEC-003**: Add namespace validation to `remove_note`
- [ ] **SEC-004**: Fix file locking resource leak pattern
- [ ] **SEC-005**: Add content length limits
- [ ] **SEC-006**: Make singleton initialization thread-safe

### Performance
- [ ] **PERF-007**: Consider lazy/deferred model loading
- [ ] **PERF-008**: Add SQLite connection lifecycle management

### Code Quality
- [ ] **QUAL-007**: Extract `SECONDS_PER_DAY = 86400` constant
- [ ] **QUAL-008**: Remove unused `context` parameter from `detect_patterns()`

---

## Quick Commands

```bash
# Fix critical issues
/cr-fx --severity=critical

# Fix all high priority
/cr-fx --severity=high

# Fix only architecture issues
/cr-fx --category=architecture

# Fix only test gaps
/cr-fx --category=tests

# Interactive mode (prompts at each decision)
/cr-fx

# Non-interactive with sensible defaults
/cr-fx --quick
```
