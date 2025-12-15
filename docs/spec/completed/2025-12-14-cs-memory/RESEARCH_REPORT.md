# Research Report: cs-memory Specification Analysis

## Executive Summary

The cs-memory specification proposes a **Git-native memory system** for persisting AI-generated context across Claude Code sessions. The dual-layer architecture (Git notes for storage, sqlite-vec for indexing) is architecturally sound and addresses a real problem: context loss after compaction.

**Overall Assessment**: The specification is well-structured with clear requirements traceability. However, several architectural concerns require attention before implementation:

1. **High Risk**: Concurrent Git notes operations may cause data loss
2. **Medium Risk**: ADR counter synchronization in distributed environments
3. **Medium Risk**: Topic detection for proactive recall lacks specification
4. **Low Risk**: First-run experience not fully defined

**Recommendation**: Approve with conditions (address Critical findings before Phase 1 completion).

---

## Research Scope

- **Subject**: cs-memory specification (8 documents, ~4,500 lines)
- **Methodology**: Deep specification review, integration analysis, feasibility assessment
- **Sources**: PROJECT_BRIEF.md, REQUIREMENTS.md, ARCHITECTURE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md, RESEARCH_NOTES.md, existing claude-spec codebase
- **Limitations**: No prototype implementation to validate performance claims

---

## Key Findings

### Finding 1: Dual-Layer Architecture is Sound

**Evidence**: ADR-001, ADR-002, ADR-010, ARCHITECTURE.md Section 1

**Analysis**: The separation of concerns between Git notes (canonical, distributed) and sqlite-vec (derived, local) follows established patterns:
- Git notes as source of truth enables full recoverability
- Index-as-derived-data allows schema evolution without migration
- sqlite-vec's brute-force KNN is appropriate for <10k memories (per RESEARCH_NOTES.md benchmarks)

**Confidence**: HIGH

**Recommendation**: No changes needed.

---

### Finding 2: Commit Anchor Strategy Has Edge Cases

**Evidence**: ADR-007, IMPLEMENTATION_PLAN.md Milestone 2.5-2.7

**Analysis**: The "scaffold early, amend during phase" strategy is elegant but has gaps:

1. **What if user cancels mid-elicitation?** The scaffold commit exists, but elicitation memories may be incomplete.
2. **What if a commit is amended after notes are attached?** Notes reference the pre-amend SHA; post-amend SHA is different.
3. **What about squash/rebase workflows?** Notes attached to squashed commits become orphaned.

The specification does not address note migration during history rewriting operations.

**Confidence**: MEDIUM

**Recommendation**: Add ADR-015 addressing history rewriting scenarios. Consider:
- Detecting orphaned notes during `git notes list`
- Optional `cs:memory migrate` command after rebase
- Warning users about note loss when interactive rebase detected

---

### Finding 3: Concurrent Operations Risk Data Loss

**Evidence**: ARCHITECTURE.md CaptureService, ADR-008

**Analysis**: The capture flow is:
1. Format note → 2. `git notes add` → 3. Generate embedding → 4. Index in SQLite

**Problem**: Git notes doesn't support atomic append across processes. If two developers capture to the same commit simultaneously:
- Both run `git notes add`
- Second operation **overwrites** the first (not appends)
- First memory is lost

The specification mentions `cat_sort_uniq` merge strategy for sync, but this only helps during `git notes merge`, not concurrent local operations.

**Confidence**: HIGH

**Recommendation**:
1. Use file locking (like existing `log_writer.py`) for local note operations
2. Change from `git notes add` to `git notes append` by default
3. Add FR-022: Memory capture MUST be atomic within a single repository clone

---

### Finding 4: ADR Counter Has Distributed Sync Issue

**Evidence**: ADR-012, FR-003a

**Analysis**: The ADR counter is stored in the SQLite index:

```python
CREATE TABLE adr_counter (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_number INTEGER NOT NULL DEFAULT 0
);
```

**Problem**: If Developer A creates ADR-015 and Developer B creates ADR-015 before sync, both have duplicate numbers. The "take MAX during merge" strategy only works if:
- Index is rebuilt after `git fetch`
- Developers remember to pull notes before creating ADRs

**Current mitigation**: Rebuilding counter from existing ADR numbers during reindex.

**Residual risk**: Stale local counter may assign duplicate numbers before next sync.

**Confidence**: MEDIUM

**Recommendation**:
1. Store counter in a Git note (`refs/notes/cs/meta`) not just SQLite
2. Before assigning number, query existing notes for current MAX
3. Accept possibility of gaps (ADR-015, ADR-017) over duplicates

---

### Finding 5: Topic Detection is Underspecified

**Evidence**: US-016, ADR-011

**Analysis**: The specification states:
> "Topic detection triggers background search" and "proactive search triggered by topic detection"

But provides no specification for:
- How topics are detected from Claude's current work
- What constitutes a "known namespace topic"
- Threshold for triggering proactive search
- How to avoid noise (too many suggestions)

This is a key differentiating feature but has no functional requirements or architecture.

**Confidence**: HIGH

**Recommendation**:
1. Add FR-023: Topic detection algorithm specification
2. Options: keyword extraction, embedding similarity to recent memories, explicit topic tags
3. Add NFR-013: Proactive search MUST surface ≤3 suggestions per topic
4. Consider deferring to Phase 3 (Intelligence) with explicit scope

---

### Finding 6: ReviewService Creates Many Notes Per Commit

**Evidence**: ADR-014, FR-018, ARCHITECTURE.md Section 3.4

**Analysis**: The code review flow captures each finding as a separate note attached to the reviewed commit. A typical review may have 10-30 findings.

**Problem**: Git notes allows only one note per object per namespace. To store multiple findings:
- Use JSON array in single note (loses individual embedding)
- Create separate commits for each finding (pollutes history)
- Use finding ID in note content, not namespace

The specification implies separate notes but doesn't address this constraint.

**Confidence**: HIGH

**Recommendation**:
1. Clarify: Review findings should be stored as a **single JSON note per commit** in `cs/reviews`
2. Index extracts individual findings from the JSON for embedding
3. Update FR-018 with explicit storage format
4. Alternative: One note per file-level finding (not line-level)

---

### Finding 7: SessionStart Hook Integration is Clear

**Evidence**: ARCHITECTURE.md Section 5.0, existing `hooks/session_start.py`

**Analysis**: The specification correctly extends the existing hook pattern:

```python
# Existing session_start.py has:
# - is_cs_project() check
# - Context loading with config flags
# - Output to stdout for Claude injection

# Proposed addition:
def get_memory_awareness() -> str | None
```

The integration point is clean and follows established patterns.

**Confidence**: HIGH

**Recommendation**: No changes needed. Good specification.

---

### Finding 8: Performance Requirements Need Baselines

**Evidence**: NFR-001, NFR-002, NFR-003, RESEARCH_NOTES.md Section 4

**Analysis**: Performance claims:
- Search <500ms for <10k memories
- Capture <2s including embedding
- Reindex <60s for <10k memories

RESEARCH_NOTES.md cites sqlite-vec benchmarks:
- 100k vectors, 384 dimensions: ~26ms query time (in-memory)
- Embedding generation: ~30-50ms per text

The claims appear achievable, but:
- No baseline measurements in current environment
- No specification of hardware assumptions
- Embedding model load time (first query) not accounted for

**Confidence**: MEDIUM

**Recommendation**:
1. Add baseline benchmarks during Phase 1 Milestone 1.4 (Embedding Service)
2. Document cold-start latency for first-query scenario
3. Accept NFRs are aspirational until validated

---

### Finding 9: Missing Error Handling Specification

**Evidence**: ARCHITECTURE.md, IMPLEMENTATION_PLAN.md

**Analysis**: The specification defines happy-path flows but lacks error handling:
- What if `git notes add` fails (no commits, permission denied)?
- What if embedding model fails to load (OOM, corrupted cache)?
- What if SQLite is locked by another process?
- What if YAML parsing fails on malformed note?

NFR-009 states "Error messages MUST suggest corrective actions" but no error taxonomy exists.

**Confidence**: MEDIUM

**Recommendation**:
1. Add Section 7 to ARCHITECTURE.md: Error Handling
2. Define error categories: StorageError, IndexError, EmbeddingError, ParseError
3. Each error type should have: detection, user message, recovery action

---

### Finding 10: Implementation Plan Dependencies Look Correct

**Evidence**: IMPLEMENTATION_PLAN.md Dependencies section

**Analysis**: The dependency graph is:
```
M1.1 → M1.2, M1.3, M1.4, M1.5
M1.2 + M1.3 → M1.6
M1.4 + M1.5 → M1.6
```

This correctly captures that CaptureService (M1.6) requires both:
- Note parser + Git operations (storage side)
- Embedding + Index (retrieval side)

The critical path is: M1.1 → M1.4 → M1.6 → M1.7 → M1.8 → Phase 2

**Confidence**: HIGH

**Recommendation**: No changes needed.

---

## Gap Analysis

### Requirements vs. Architecture Coverage

| Requirement | Architecture Support | Gap |
|-------------|---------------------|-----|
| US-001 through US-014 | ✅ Fully specified | None |
| US-015 (Session Awareness) | ✅ Section 5.0 | None |
| US-016 (Proactive Topic Search) | ⚠️ ADR-011 only | No algorithm spec |
| US-017 through US-019 | ✅ ReviewService | JSON vs. separate notes unclear |
| FR-001 through FR-016 | ✅ Fully specified | None |
| FR-017 through FR-021 | ✅ Added in v1.1.0 | None |
| NFR-001 through NFR-012 | ⚠️ Aspirational | No baseline validation |

### Missing Specifications

1. **Topic detection algorithm** (US-016)
2. **Error handling taxonomy** (NFR-009)
3. **History rewriting scenarios** (ADR-007 gap)
4. **Concurrent operation safety** (FR-006, FR-007)
5. **Review note storage format** (FR-018 clarification)

---

## Risk Assessment

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| Concurrent note writes cause data loss | Medium | High | **CRITICAL** | Add file locking, use append |
| ADR number duplicates in team | Medium | Medium | HIGH | Store counter in notes, query MAX |
| Topic detection causes noise | High | Low | MEDIUM | Cap suggestions, defer to Phase 3 |
| Performance doesn't meet NFRs | Low | Medium | MEDIUM | Baseline early, adjust targets |
| Notes lost during rebase | Medium | Medium | MEDIUM | Add migration command |
| Embedding model OOM on first load | Low | High | MEDIUM | Add graceful degradation |

---

## Recommendations

### Critical (Block Phase 1 completion)

1. **Add concurrency safety to CaptureService**
   - File locking for note operations
   - Change `add` to `append` for safe concurrent writes

2. **Clarify review note storage format**
   - Single JSON note per commit, or
   - One note per file (not per line finding)

### High Priority (Address before Phase 2)

3. **Add ADR counter to Git notes**
   - Store in `refs/notes/cs/meta`
   - Query existing notes for MAX before assigning

4. **Specify topic detection algorithm**
   - Minimum viable: keyword extraction + recent spec matching
   - Add FR-023 and NFR-013

### Medium Priority (Address before Phase 3)

5. **Add error handling section to ARCHITECTURE.md**
   - Error categories and recovery actions

6. **Add ADR-015 for history rewriting**
   - Document note migration during rebase/squash

7. **Establish performance baselines**
   - Cold-start embedding load time
   - Query latency at 1k, 5k, 10k memories

---

## Open Questions

1. Should topic detection use Claude's embedding of current prompt, or explicit keyword extraction?
2. What is acceptable latency for proactive search (background, but how background)?
3. Should review findings support amendment (updating severity after fix)?
4. What privacy controls are needed for sensitive memories (e.g., security findings)?

---

## Appendix: Document Summary

| Document | Lines | Purpose |
|----------|-------|---------|
| PROJECT_BRIEF.md | 100 | Problem statement, scope, success criteria |
| REQUIREMENTS.md | 378 | 19 user stories, 21 FRs, 12 NFRs, 5 constraints |
| ARCHITECTURE.md | 933 | System design, service layer, data flows |
| DECISIONS.md | 581 | 14 Architecture Decision Records |
| IMPLEMENTATION_PLAN.md | 635 | 3 phases, 35 milestones, 90+ tasks |
| RESEARCH_NOTES.md | 339 | Prior art, technical references, benchmarks |
| CHANGELOG.md | 55 | Version history (v1.0.0, v1.1.0) |
| README.md | 65 | Quick links, status, metrics |

**Total**: ~3,086 lines of specification
