# Code Review Summary: cs-memory Module

**Review Date**: 2025-12-14
**Scope**: `plugins/cs/memory/` (14 Python files, 12 test files)
**Commit**: 2ea817e

---

## Overall Health: 7.5/10

| Dimension | Score | Key Issue |
|-----------|-------|-----------|
| Security | 8/10 | Command injection risk in git refs |
| Performance | 6/10 | N+1 queries in RecallService |
| Architecture | 7/10 | Private method access across services |
| Code Quality | 7/10 | DRY violations, shadowed built-in |
| Test Coverage | 8/10 | Missing edge case tests |
| Documentation | 7/10 | Guide/API mismatches |

---

## Critical Issues (2)

1. **PERF-001**: `RecallService.search()` triggers N+1 database queries - each search result causes a separate `get()` call
2. **PERF-002**: `RecallService.context()` generates the same embedding 10 times (once per namespace)

**Impact**: With 50 results across namespaces, this could trigger 500+ queries and 10 embedding generations.

---

## Top Recommendations

### Before Deploy
- [ ] Add `get_batch()` method to IndexService
- [ ] Refactor `context()` to use single spec-filtered query

### This Sprint
- [ ] Rename `IndexError` to `MemoryIndexError` (shadows Python built-in)
- [ ] Add public `list_recent()` and `get_by_commit()` to IndexService (stop accessing `_get_connection()`)
- [ ] Add git ref validation (`^[a-zA-Z0-9_./-]+$`, no dash prefix)

### Next Sprint
- [ ] Split god modules (lifecycle.py: 531 lines, patterns.py: 650 lines)
- [ ] Extract shared `calculate_temporal_decay()` utility
- [ ] Use OrderedDict for O(1) cache eviction

---

## Findings Summary

| Severity | Count | Categories |
|----------|-------|------------|
| Critical | 2 | Performance |
| High | 9 | Architecture (3), Quality (4), Test (5) |
| Medium | 12 | Security (2), Architecture (4), Performance (4), Quality (2) |
| Low | 22 | Security (4), Performance (4), Quality (8), Documentation (6) |

---

## Test Coverage Gaps

Missing tests for:
- `__init__.py` factory functions (`get_capture_service()`, etc.)
- Configuration constants validation
- Exception hierarchy
- Lock timeout / concurrent capture scenarios
- Date filters / file hydration failures

---

## Next Steps

1. Run `/cr-fx --severity=critical` to fix N+1 query issues
2. Run `/cr-fx --category=architecture` to add proper public methods
3. Review REMEDIATION_TASKS.md for full checklist

See [CODE_REVIEW.md](./CODE_REVIEW.md) for detailed findings and remediation code.
