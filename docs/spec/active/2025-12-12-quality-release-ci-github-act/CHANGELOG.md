# Changelog

All notable changes to this project plan will be documented in this file.

## [1.0.1] - 2025-12-12

### Added
- Makefile for local CI (FR-012) - `make ci` mirrors GitHub Actions workflow
- Task 1.2 in implementation plan for Makefile creation

### Changed
- Phase 1 now has 5 tasks (was 4)
- Total tasks now 17 (was 16)

## [1.0.0] - 2025-12-12

### Added
- Complete requirements specification (REQUIREMENTS.md)
  - 12 P0 (must have) requirements
  - 4 P1 (should have) requirements
  - 3 P2 (nice to have) requirements
- Technical architecture document (ARCHITECTURE.md)
  - CI workflow design with quality and test jobs
  - Release workflow design with changelog extraction
  - Security considerations and permissions model
- Implementation plan with 16 tasks across 4 phases (IMPLEMENTATION_PLAN.md)
  - Phase 1: Foundation (pyproject.toml, tooling)
  - Phase 2: CI Workflow (quality, tests, shellcheck)
  - Phase 3: Release Workflow (tags, changelog, archives)
  - Phase 4: Ecosystem (templates, dependabot)
- 10 Architecture Decision Records (DECISIONS.md)
  - ADR-001: Use uv for Python package management
  - ADR-002: Use ruff for linting and formatting
  - ADR-003: Use stable action versions (v4)
  - ADR-004: Matrix testing with fail-fast: false
  - ADR-005: Separate quality and test jobs
  - ADR-006: Use softprops/action-gh-release
  - ADR-007: Extract changelog vs generate
  - ADR-008: Minimal workflow permissions
  - ADR-009: Python 3.11+ minimum version
  - ADR-010: shellcheck for shell validation
- Research notes documenting findings (RESEARCH_NOTES.md)
  - GitHub Actions version analysis
  - Python CI best practices with uv
  - Release automation patterns
  - Tool recommendations

### Research Conducted
- Parallel agent research on:
  - Current GitHub Actions versions (v4 stable, v6 requires newer runners)
  - Python CI best practices with uv and astral-sh/setup-uv
  - Release automation with softprops/action-gh-release
- github-ecosystem skill analysis for template patterns
- Existing codebase analysis (tests, shell scripts, changelog)

## [Unreleased]

### Added
- Initial project creation
- Requirements elicitation begun
- Created planning workspace at `docs/spec/active/2025-12-12-quality-release-ci-github-act/`
