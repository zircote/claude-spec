# Changelog

All notable changes to this specification will be documented in this file.

## [COMPLETED] - 2025-12-15

### Project Closed
- Final status: success
- Actual effort: 12 hours (vs 40-80 hours planned, -70% variance)
- Final quality score: 9.0/10 (post code review remediation)
- Moved to: docs/spec/completed/2025-12-14-cs-memory/

### Implementation Completed
- All 77 planned tasks completed (6 deferred: integration tests, benchmarks, telemetry)
- 600 tests passing (84 new memory tests + 516 existing plugin tests)
- Comprehensive code review: 45 findings remediated (1 Critical, 3 High, 12 Medium, 29 Low)
- Full documentation: USER_GUIDE.md, DEVELOPER_GUIDE.md, RETROSPECTIVE.md

### Retrospective Summary
- **What went well**: Specification quality, modular architecture, code review process, technical achievements
- **What to improve**: Integration test coverage, performance benchmarks, documentation validation
- **Key learning**: 20-30% upfront planning investment compresses implementation time significantly

## [1.0.0] - 2025-12-14

### Added
- Initial project creation
- Adopted and revised specification package from `product-brief/`
- **US-015**: Session Start Awareness - minimal notification that memories exist
- **US-016**: Proactive Topic Search - automatic relevant memory suggestions
- **FR-003a**: Monotonic ADR numbering requirement
- **ADR-011**: Proactive Memory Recall Strategy
- **ADR-012**: Monotonic ADR Numbering

### Changed
- **PROJECT_BRIEF.md**: Reframed problem statement to focus on "Claude's context loss after compaction" as primary use case
- **REQUIREMENTS.md**: Added Section 1.5 "Proactive Memory Awareness" with 2 new user stories
- **ARCHITECTURE.md**: Added Section 5.0 "SessionStart Hook - Memory Awareness"
- **DECISIONS.md**: Added ADR-011 and ADR-012

### Clarified
- Primary problem: Claude straying from guidance after 2+ compactions
- Team scale: ~6 concurrent developers per project (not 300 simultaneously)
- Scope: Single-repo only, no cross-repo aggregation needed
- Memory role: Supplements CLAUDE.md with indexed, progressively-revealed detail

### Research Conducted
- Validated existing spec against actual pain points
- Confirmed commit-coupling principle is appropriate
- Identified proactive recall as key differentiator from "bloated unindexed .md files"

## [1.2.0] - 2025-12-14

### Added
- **ADR-015**: History Rewriting and Note Orphaning - documents behavior when rebase/squash orphans notes
- **FR-022**: Concurrency safety with file locking for memory capture operations
- **FR-023**: Use `git notes append` instead of `add` to prevent data loss
- **NFR-013**: Proactive search must surface ≤3 suggestions per topic (noise cap)
- **Section 7**: Error Handling in ARCHITECTURE.md with error taxonomy and graceful degradation
- **T1.4.5**: Performance baseline task added to implementation plan

### Changed
- **ADR-012**: Revised from "Monotonic ADR Numbering" to "SHA-Based Decision Identification"
  - Eliminated distributed synchronization problem
  - Use commit SHA + timestamp for ordering instead of counter
  - Display-only indices computed from timestamp ordering
- **FR-018**: Clarified review note storage as single JSON note per commit (Git notes constraint)
- **US-016**: Added implementation note deferring topic detection algorithm to Phase 3
- **CaptureService**: Added file locking pattern using `fcntl.flock`
- **Git Operations**: Changed from `add` to `append` for safe concurrent writes

### Removed
- **FR-003a**: ADR numbering requirement (replaced by SHA-based identification)
- `adr_counter` table concept from index schema

### Research Conducted
- Deep specification analysis with 10 findings (RESEARCH_REPORT.md)
- Architect review: 7.5/10, approved with conditions
- Counter-argument analysis for all recommendations

---

## [1.1.0] - 2025-12-14

### Added
- **US-017**: Code Review Memory Capture - automatic capture of review findings to cs/reviews namespace
- **US-018**: Code Review Remediation Tracking - resolution tracking with status updates
- **US-019**: Review Pattern Detection - identify recurring issues across reviews
- **FR-017 to FR-021**: Functional requirements for /cs:review and /cs:fix commands
- **ADR-013**: cs-memory Supplements (Not Replaces) Prompt Capture
- **ADR-014**: Code Review Findings as Commit-Anchored Notes
- **ReviewService**: New service in ARCHITECTURE.md for code review operations
- Data flow diagrams for Code Review Flow (Section 3.4) and Remediation Flow (Section 3.5)

### Changed
- **ARCHITECTURE.md**: Added /cs:review and /cs:fix command specifications
- **ARCHITECTURE.md**: Added ReviewService with specialist agent routing
- **ARCHITECTURE.md**: Updated file structure to include review.py and fix.md

### Analysis Conducted
- Compared cs-memory structured capture vs prompt capture raw logging
- Determined cs-memory captures "signal" (decisions, learnings) while prompt capture captures "noise + signal"
- Concluded: cs-memory supplements (not replaces) prompt capture, with prompt capture becoming optional debug mode
- Mapped existing /cr and /cr-fx commands to cs-memory-integrated /cs:review and /cs:fix
