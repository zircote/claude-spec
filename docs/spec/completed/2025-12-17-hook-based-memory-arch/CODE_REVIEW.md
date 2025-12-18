# Code Review Report

## Metadata
- **Project**: cs (claude-spec plugin)
- **Review Date**: 2025-12-17
- **Reviewer**: Claude Code Review Agent (6 Parallel Specialists)
- **Scope**: Full plugin codebase (`plugins/cs/`)
- **Branch**: feat/hook-based-memory
- **Files Reviewed**: 126 files across 23 directories

---

## Executive Summary

### Overall Health Score: 7.5/10

| Dimension | Score | Critical | High | Medium | Low |
|-----------|-------|----------|------|--------|-----|
| Security | 7/10 | 0 | 4 | 6 | 3 |
| Performance | 8/10 | 1 | 2 | 3 | 0 |
| Architecture | 6/10 | 2 | 5 | 4 | 4 |
| Code Quality | 8/10 | 0 | 0 | 7 | 16 |
| Test Coverage | 6/10 | 0 | 5 | 5 | 0 |
| Documentation | 7/10 | 0 | 4 | 6 | 5 |

### Key Findings
1. **Global mutable state** in `learnings/deduplicator.py` and `memory/capture.py` creates race condition risks
2. **Path traversal vulnerability** in hooks that accept `cwd` from untrusted input
3. **Embedding model cold start** can cause 2-5 second latency on first search
4. **Test coverage gaps** in new `learnings/` module (no dedicated unit tests)
5. **DRY violations** with duplicated I/O functions across multiple hooks

### Recommended Action Plan
1. **Immediate** (before next deploy):
   - Fix path traversal in `command_detector.py`, `post_command.py`
   - Add input size limits to `fallback.py`

2. **This Sprint**:
   - Refactor global singletons to dependency injection
   - Pre-warm embedding model during SessionStart
   - Create unit tests for `learnings/` module

3. **Next Sprint**:
   - Consolidate duplicated I/O logic
   - Add Protocol interfaces for services
   - Create `learnings/DEVELOPER_GUIDE.md`

4. **Backlog**:
   - Standardize log prefix format
   - Extract magic numbers to constants
   - Add context manager to IndexService

---

## Critical Findings

### ARCH-001: Global Mutable State in Deduplicator
**Severity**: CRITICAL | **Category**: Architecture

**Location**: `learnings/deduplicator.py:183-202`

**Description**: Module-level global state (`_session_deduplicator`) with no thread safety or session isolation.

```python
# Current code
_session_deduplicator: SessionDeduplicator | None = None

def get_session_deduplicator() -> SessionDeduplicator:
    global _session_deduplicator
    if _session_deduplicator is None:
        _session_deduplicator = SessionDeduplicator()
    return _session_deduplicator
```

**Impact**:
- Race conditions in concurrent hook executions
- State leakage between sessions if process is reused
- Difficult to test in isolation

**Remediation**:
```python
# Use dependency injection or context-scoped instances
class SessionContext:
    def __init__(self):
        self.deduplicator = SessionDeduplicator()

# Or use threading.Lock for initialization
_lock = threading.Lock()
_session_deduplicator = None

def get_session_deduplicator():
    global _session_deduplicator
    if _session_deduplicator is None:
        with _lock:
            if _session_deduplicator is None:
                _session_deduplicator = SessionDeduplicator()
    return _session_deduplicator
```

---

### ARCH-002: Global Mutable State in CaptureService
**Severity**: CRITICAL | **Category**: Architecture

**Location**: `memory/capture.py:119-154`

**Description**: Class-level mutable state for sync configuration tracking.

```python
class CaptureService:
    _sync_configured: bool = False  # Shared across all instances
```

**Impact**:
- All instances share configuration state
- Test isolation problems
- Process reuse could skip necessary reconfiguration

**Remediation**: Move to instance-level state or use a proper configuration service.

---

### PERF-001: Embedding Model Cold Start Latency
**Severity**: CRITICAL | **Category**: Performance

**Location**: `memory/embedding.py:52-103`

**Description**: The `EmbeddingService` lazily loads the sentence-transformers model on first use, causing 2-5 second delay.

**Impact**: If model loading occurs during a UserPromptSubmit or PostToolUse hook (which have <50ms and <100ms targets), it causes significant latency violation.

**Remediation**: Pre-warm the embedding model during SessionStart hook (which has 500ms budget) or cache at module level with explicit initialization.

```python
_embedding_service: EmbeddingService | None = None

def get_embedding_service(preload: bool = False) -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        if preload:
            _ = _embedding_service.model  # Force load
    return _embedding_service
```

---

## High Priority Findings

### SEC-001: Path Traversal in Session State Files
**Severity**: HIGH | **Category**: Security

**Location**:
- `hooks/command_detector.py:112-124`
- `hooks/post_command.py:80-112`

**Description**: The `save_session_state()` and `load_session_state()` functions trust the `cwd` value from JSON input without validation.

```python
# Current code - vulnerable
def save_session_state(cwd: str, state: dict[str, Any]) -> None:
    state_file = Path(cwd) / SESSION_STATE_FILE  # No validation!
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
```

**Exploitation Scenario**: An attacker sends `{"cwd": "/etc/", ...}` as input, causing the hook to write to `/etc/.cs-session-state.json`.

**Remediation**:
```python
def save_session_state(cwd: str, state: dict[str, Any]) -> None:
    cwd_path = Path(cwd).resolve()
    if not cwd_path.is_dir():
        sys.stderr.write(f"cs-{LOG_PREFIX}: Invalid cwd: {cwd}\n")
        return

    state_file = cwd_path / SESSION_STATE_FILE
    try:
        state_file.resolve().relative_to(cwd_path)
    except ValueError:
        sys.stderr.write(f"cs-{LOG_PREFIX}: Path traversal detected\n")
        return

    # Use restrictive permissions (0o600)
    fd = os.open(str(state_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
```

---

### SEC-002: Unbounded Input Size in Fallback
**Severity**: HIGH | **Category**: Security

**Location**: `hooks/lib/fallback.py:28-32`

**Description**: `fallback_read_input()` uses `json.load(sys.stdin)` without size limits, unlike `hook_io.read_input()` which properly limits to 1MB.

**Exploitation Scenario**: Multi-gigabyte JSON payload causes memory exhaustion DoS.

**Remediation**:
```python
def fallback_read_input(log_prefix: str = "hook", max_size: int = 1024 * 1024):
    try:
        raw_input = sys.stdin.read(max_size + 1)
        if len(raw_input) > max_size:
            sys.stderr.write(f"cs-{log_prefix}: Input exceeds max size\n")
            raw_input = raw_input[:max_size]
        return json.loads(raw_input)
    except Exception as e:
        sys.stderr.write(f"cs-{log_prefix}: Error: {e}\n")
        return None
```

---

### SEC-003: Potential ReDoS in Secret Patterns
**Severity**: HIGH | **Category**: Security

**Location**: `filters/pipeline.py:170-171, 196`

**Description**: Some regex patterns use unbounded quantifiers that could cause catastrophic backtracking.

```python
# Potentially problematic patterns
"aws_secret_key": re.compile(r'(?i)aws.{0,20}secret.{0,20}[\'"][0-9a-zA-Z/+=]{40}[\'"]')
```

**Remediation**: Use more restrictive character classes:
```python
"aws_secret_key": re.compile(r'(?i)\baws[^\'"]{0,20}secret[^\'"]{0,20}[\'"][0-9a-zA-Z/+=]{40}[\'"]')
```

---

### SEC-004: Permissive File Permissions for Session State
**Severity**: HIGH | **Category**: Security

**Location**: `hooks/command_detector.py:121`

**Description**: Session state files created with default umask, potentially readable by other users.

**Remediation**: Use `os.open()` with `0o600` permissions (same pattern as `log_writer.py`).

---

### PERF-002: Subprocess Overhead in Git Operations
**Severity**: HIGH | **Category**: Performance

**Location**: `memory/git_ops.py:84-135`

**Description**: Each `_run_git()` call spawns a subprocess (50-200ms overhead). Multiple calls compound latency.

**Remediation**: Batch git operations where possible. Consider using git plumbing commands that return multiple pieces of information.

---

### ARCH-003: Dependency Inversion Violation
**Severity**: HIGH | **Category**: Architecture

**Location**: `hooks/lib/memory_injector.py:54-64`

**Description**: Hooks layer directly imports from memory module internals.

```python
from memory.recall import RecallService
from memory.models import MemoryResult
```

**Impact**: Tight coupling, changes ripple across modules.

**Remediation**: Define abstract interfaces/Protocols in a shared location.

---

### ARCH-004: Duplicated I/O Logic Across Hooks
**Severity**: HIGH | **Category**: Architecture

**Location**:
- `hooks/session_start.py:80-89`
- `hooks/command_detector.py:155-197`
- `hooks/post_command.py:143-186`
- `hooks/prompt_capture.py:198-214`

**Description**: Each hook has duplicate inline fallback I/O functions.

**Remediation**: Extract to a single utility or make `fallback.py` always importable.

---

### ARCH-005: sys.path Manipulation
**Severity**: HIGH | **Category**: Architecture

**Location**: Multiple hook files (session_start.py:36-39, command_detector.py:40-45, etc.)

**Description**: Pervasive `sys.path.insert()` calls to resolve imports.

**Impact**: Fragile import resolution, potential conflicts.

**Remediation**: Properly structure as Python package with relative imports.

---

### TEST-001: Missing Unit Tests for learnings/ Module
**Severity**: HIGH | **Category**: Test Coverage

**Files Missing Tests**:
- `learnings/models.py` - No unit tests for ToolLearning validation
- `learnings/detector.py` - No pattern detection unit tests
- `learnings/extractor.py` - No sanitization/truncation tests
- `learnings/deduplicator.py` - No LRU cache behavior tests

**Impact**: New module has no safety net for regressions.

**Remediation**: Create dedicated test files for each module.

---

### DOC-001: Missing learnings/ Developer Guide
**Severity**: HIGH | **Category**: Documentation

**Description**: The new `learnings/` module lacks developer documentation.

**Remediation**: Create `learnings/DEVELOPER_GUIDE.md` explaining:
- How to add new signal patterns
- How deduplication works
- Integration with memory system

---

## Medium Priority Findings

### Security (6)
| ID | Finding | Location |
|----|---------|----------|
| SEC-005 | Sensitive data in stderr logging | Multiple hooks |
| SEC-006 | YAML parsing (uses safe_load - acceptable) | note_parser.py |
| SEC-007 | No rate limiting on captures | memory/capture.py |
| SEC-008 | SQL IN clause string formatting (safe but fragile) | memory/index.py:232-236 |
| SEC-009 | Model download supply chain risk | memory/embedding.py |
| SEC-010 | Timing side channel in secret detection | filters/pipeline.py |

### Performance (3)
| ID | Finding | Location |
|----|---------|----------|
| PERF-003 | SQLite connection no context manager | memory/index.py:38-75 |
| PERF-004 | fsync in log writer (5-50ms) | filters/log_writer.py:266-269 |
| PERF-005 | Multiple queries in memory injector | hooks/lib/memory_injector.py:89-135 |

### Architecture (4)
| ID | Finding | Location |
|----|---------|----------|
| ARCH-006 | Large CaptureService (740 lines) | memory/capture.py |
| ARCH-007 | Missing Protocol definitions | Multiple modules |
| ARCH-008 | Inconsistent error handling | Multiple modules |
| ARCH-009 | Configuration scattered | config.py, config_loader.py |

### Code Quality (7)
| ID | Finding | Location |
|----|---------|----------|
| QUALITY-001 | Duplicated temporal decay calc | lifecycle.py, utils.py |
| QUALITY-002 | Duplicated detect_active_spec() | spec_detector.py, post_tool_capture.py |
| QUALITY-003 | Duplicated namespace icons | memory_injector.py, trigger_detector.py |
| QUALITY-004 | High complexity in main() | command_detector.py:170-229 |
| QUALITY-005 | Deep nesting (5 levels) | memory/capture.py:160-273 |
| QUALITY-006 | Broad exception catch | memory/capture.py:264-266 |
| QUALITY-007 | Inconsistent log prefix format | Multiple hooks |

### Test Coverage (5)
| ID | Finding | Priority |
|----|---------|----------|
| TEST-002 | hooks/post_tool_capture.py minimal tests | HIGH |
| TEST-003 | learnings/models.py no validation tests | HIGH |
| TEST-004 | learnings/detector.py no pattern tests | HIGH |
| TEST-005 | learnings/extractor.py no sanitization tests | HIGH |
| TEST-006 | learnings/deduplicator.py no LRU tests | HIGH |

### Documentation (6)
| ID | Finding | Location |
|----|---------|----------|
| DOC-002 | post_tool_capture.py missing docstrings | hooks/post_tool_capture.py |
| DOC-003 | analyzers/__init__.py incomplete | analyzers/__init__.py |
| DOC-004 | IndexService missing class docstring | memory/index.py |
| DOC-005 | Auto-capture namespaces undocumented | memory/capture.py |
| DOC-006 | USER_GUIDE.md missing troubleshooting | memory/USER_GUIDE.md |
| DOC-007 | TriggerDetector missing examples | hooks/lib/trigger_detector.py |

---

## Low Priority Findings

### Code Quality (16)
- Unused warnings list in context_loader.py
- Unused TYPE_CHECKING block in models.py
- Unused context parameter in patterns.py
- Mixed content/full_content field names
- Magic numbers (prompt[:500], 0.2 threshold)
- Hardcoded limits without constants
- Missing type hints in various functions
- Global singletons without thread safety
- Minor documentation gaps

### Documentation (5)
- Various minor docstring enhancements
- Example output formats missing
- README command verification needed

---

## Positive Findings (Strengths)

### Security
- Path traversal protection in `log_writer.py`
- Symlink attack prevention with `O_NOFOLLOW`
- Restrictive file permissions (`0o600`) for logs
- Input size limits in `hook_io.py` (1MB max)
- Git ref validation preventing command injection
- Step module whitelist
- YAML safe_load throughout

### Performance
- Pre-compiled regex patterns at module level
- LRU caching with proper bounds
- N+1 query prevention with batch retrieval
- Performance monitoring with timing warnings
- Content length limits preventing memory exhaustion

### Architecture
- Good module separation in memory/
- Well-structured step system with BaseStep ABC
- Graceful degradation philosophy in hooks
- Immutable data models with frozen dataclasses
- Comprehensive docstrings in most files

---

## Appendix

### Files Reviewed
```
analyzers/          - 3 files
commands/           - 13 markdown files
filters/            - 4 files
hooks/              - 7 files
hooks/lib/          - 8 files
learnings/          - 5 files
memory/             - 17 files
steps/              - 8 files
templates/          - 9 files
tests/              - 24 files
utils/              - 2 files
```

### Review Methodology
- 6 parallel specialist agents (Security, Performance, Architecture, Code Quality, Test Coverage, Documentation)
- "Very thorough" exploration level
- All source files READ before findings documented
- Cross-referenced findings across specialists
