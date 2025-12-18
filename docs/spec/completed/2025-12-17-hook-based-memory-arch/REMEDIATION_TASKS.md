# Remediation Tasks

Generated from code review on 2025-12-17.

---

## Critical (Do Immediately)

- [ ] **ARCH-001** `learnings/deduplicator.py:183-202` - Add threading.Lock to global singleton initialization
- [ ] **ARCH-002** `memory/capture.py:119-154` - Move `_sync_configured` from class-level to instance-level
- [ ] **PERF-001** `memory/embedding.py:52-103` - Pre-warm embedding model during SessionStart hook

---

## High Priority (This Sprint)

### Security
- [ ] **SEC-001** `hooks/command_detector.py:112-124` - Add path validation to `save_session_state()`
- [ ] **SEC-001** `hooks/post_command.py:80-112` - Add path validation to `load_session_state()` and `cleanup_session_state()`
- [ ] **SEC-002** `hooks/lib/fallback.py:28-32` - Add MAX_INPUT_SIZE limit (1MB)
- [ ] **SEC-003** `filters/pipeline.py:170-171` - Restrict regex quantifiers to prevent ReDoS
- [ ] **SEC-004** `hooks/command_detector.py:121` - Use `os.open()` with `0o600` permissions

### Performance
- [ ] **PERF-002** `memory/git_ops.py:84-135` - Batch git operations where possible

### Architecture
- [ ] **ARCH-003** `hooks/lib/memory_injector.py:54-64` - Define Protocol interfaces for services
- [ ] **ARCH-004** `hooks/session_start.py:80-89` - Consolidate duplicate I/O functions to fallback.py
- [ ] **ARCH-004** `hooks/command_detector.py:155-197` - Remove duplicate I/O, use shared module
- [ ] **ARCH-004** `hooks/post_command.py:143-186` - Remove duplicate I/O, use shared module
- [ ] **ARCH-005** Multiple files - Standardize sys.path manipulation into single module

### Test Coverage
- [ ] **TEST-001** Create `tests/test_learnings_models.py` - ToolLearning validation tests
- [ ] **TEST-001** Create `tests/test_learnings_detector.py` - Pattern detection tests
- [ ] **TEST-001** Create `tests/test_learnings_extractor.py` - Sanitization/truncation tests
- [ ] **TEST-001** Create `tests/test_learnings_deduplicator.py` - LRU cache behavior tests
- [ ] **TEST-002** Expand `hooks/post_tool_capture.py` tests - env var handling, edge cases

### Documentation
- [ ] **DOC-001** Create `learnings/DEVELOPER_GUIDE.md` - Pattern addition, deduplication, memory integration

---

## Medium Priority (Next 2-3 Sprints)

### Security
- [ ] **SEC-005** Multiple hooks - Sanitize error messages before logging to stderr
- [ ] **SEC-007** `memory/capture.py` - Consider rate limiting for capture operations

### Performance
- [ ] **PERF-003** `memory/index.py:38-75` - Add `__enter__`/`__exit__` context manager
- [ ] **PERF-004** `filters/log_writer.py:266-269` - Consider async writes or removing fsync
- [ ] **PERF-005** `hooks/lib/memory_injector.py:89-135` - Combine semantic + recent queries

### Architecture
- [ ] **ARCH-006** `memory/capture.py:1-740` - Extract capture strategies into separate classes
- [ ] **ARCH-007** Multiple modules - Add Protocol definitions for CaptureService, RecallService, etc.
- [ ] **ARCH-008** Multiple modules - Standardize error handling pattern (exceptions vs results)
- [ ] **ARCH-009** `config.py`, `config_loader.py` - Consolidate configuration to single source

### Code Quality
- [ ] **QUALITY-001** `memory/lifecycle.py:86-109` - Reuse `utils.calculate_temporal_decay()`
- [ ] **QUALITY-002** `hooks/post_tool_capture.py:116-147` - Import `detect_active_spec` from spec_detector
- [ ] **QUALITY-003** `hooks/lib/memory_injector.py:192-203` - Extract namespace icons to shared constant
- [ ] **QUALITY-004** `hooks/command_detector.py:170-229` - Extract I/O selection into separate function
- [ ] **QUALITY-005** `memory/capture.py:160-273` - Extract embedding/indexing into helper method
- [ ] **QUALITY-006** `memory/capture.py:264-266` - Log exception type and consider traceback
- [ ] **QUALITY-007** Multiple hooks - Standardize log prefix format to `cs-<module>`

### Test Coverage
- [ ] **TEST-003** Add ToolLearning `__post_init__` validation tests
- [ ] **TEST-004** Add signal pattern matching tests
- [ ] **TEST-005** Add path sanitization tests
- [ ] **TEST-006** Add LRU eviction boundary tests

### Documentation
- [ ] **DOC-002** `hooks/post_tool_capture.py` - Add docstrings to `get_session_queue()`, `queue_learning()`
- [ ] **DOC-003** `analyzers/__init__.py` - Add module docstring and __all__ exports
- [ ] **DOC-004** `memory/index.py` - Add IndexService class docstring
- [ ] **DOC-005** `memory/capture.py` - Document AUTO_CAPTURE_NAMESPACES
- [ ] **DOC-006** `memory/USER_GUIDE.md` - Add troubleshooting section
- [ ] **DOC-007** `hooks/lib/trigger_detector.py` - Add usage examples to docstrings

---

## Low Priority (Backlog)

### Code Quality
- [ ] `steps/context_loader.py:54` - Remove unused `warnings` list
- [ ] `learnings/models.py:11-13` - Remove unused TYPE_CHECKING block
- [ ] `memory/patterns.py:143` - Remove unused `context` parameter or implement
- [ ] `memory/index.py` - Align model field name (`content` vs database `full_content`)
- [ ] `hooks/command_detector.py:221` - Extract magic number `500` to constant
- [ ] `hooks/trigger_memory.py:191` - Extract magic number `0.2` to constant
- [ ] `hooks/prompt_capture.py:47-48` - Move limits to shared config
- [ ] Multiple files - Add type hints to untyped functions
- [ ] Multiple files - Add threading.Lock to all global singletons

### Documentation
- [ ] `utils/context_utils.py` - Document `_log_error()` writes to stderr
- [ ] `hooks/lib/memory_injector.py` - Add example output to `format_for_context()`
- [ ] `README.md` - Verify command examples match implementation
- [ ] `memory/sync.py` - Document auto-sync triggers and conflict resolution
- [ ] `learnings/extractor.py` - Add module-level usage examples

---

## Verification Checklist

After completing remediation:

- [ ] All tests pass: `make test`
- [ ] Lint clean: `make lint`
- [ ] Type check passes: `make typecheck`
- [ ] Security scan passes: `make security`
- [ ] No new warnings in CI

---

## Notes

- Security findings (SEC-001 through SEC-004) should be addressed before any production deployment
- Test coverage findings (TEST-001 through TEST-006) prevent regression detection in new code
- Architecture findings require careful refactoring to avoid breaking changes
