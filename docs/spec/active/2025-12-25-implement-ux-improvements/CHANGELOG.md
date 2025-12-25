# Changelog

All notable changes to this specification will be documented in this file.

## [Unreleased]

## [1.0.1] - 2025-12-25

### Approved
- Spec approved by Robert Allen <zircote@gmail.com>
- Ready for implementation via /claude-spec:implement
- Status changed: in-review → approved

## [1.0.0] - 2025-12-25

### Added
- Initial project creation
- REQUIREMENTS.md with 6 P0, 4 P1, 3 P2 requirements
- ARCHITECTURE.md with checkbox sync engine and argument schema system designs
- IMPLEMENTATION_PLAN.md with 5 phases, 18 tasks
- DECISIONS.md with 6 ADRs

### Research Conducted
- Analyzed all 12 command files for argument-hint patterns
- Reviewed Issue #25 requirements for checkbox sync
- Explored existing Phase 5 documentation gaps in implement.md
- Cataloged validation and help generation patterns

## [1.0.0] - 2025-12-25

### Added
- Combined spec for Issue #25 (checkbox sync) and argument hinting improvements
- Requirements cover checkbox sync, argument schema, help generation, validation
- Architecture defines Checkbox Sync Engine with Task Finder, Checkbox Locator, Atomic Writer
- Architecture defines Argument Schema System with validation and help generation
- Implementation plan spans 5 phases with dependency graph

### Decisions
- ADR-001: Immediate sync chosen over batched
- ADR-002: Extended YAML object for argument hints
- ADR-003: Error + suggestion pattern for validation
- ADR-004: PROGRESS.md as source of truth
- ADR-005: Atomic file writes with backup
- ADR-006: Backward compatibility for simple hints
