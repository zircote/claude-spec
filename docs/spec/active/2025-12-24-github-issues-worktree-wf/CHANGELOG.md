# Changelog

## [2.0.0] - 2025-12-24

### Added - Implementation
- **Phase 1: Foundation**
  - Extended Step 0 argument parsing with `no_args` detection
  - Prerequisites checker for `gh` CLI with detailed error messages
  - Filter Selection UI for labels and assignee filtering
  - Issue Fetcher with dynamic `gh issue list` command building

- **Phase 2: Core Workflow**
  - Issue Selection UI with JSON parsing and pagination (max 4 per question)
  - Label-to-prefix mapper following conventional commits (bug > docs > chore > feat)
  - Branch name generator: `{prefix}/{issue-number}-{slugified-title}`
  - Worktree creation with `.issue-context.json` for agent context
  - Parallel agent launch with issue-aware prompts

- **Phase 3: Completeness & Comments**
  - AI-based completeness evaluation with 5-criteria weighted assessment
  - Three verdict levels: COMPLETE, NEEDS_CLARIFICATION, MINIMAL
  - Comment draft generator with professional tone
  - Comment posting workflow with confirmation UI
  - "Add details inline" option for user-provided context

### Changed
- Extended `commands/plan.md` with new `<github_issues_workflow>` section (~670 lines)
- Added 4th argument type (`no_args`) to Step 0 classification

## [1.0.0] - 2025-12-24

### Added
- Complete requirements specification (REQUIREMENTS.md)
  - 11 P0 requirements, 5 P1 requirements, 4 P2 requirements
  - User stories covering issue selection, worktree creation, and clarification workflow
  - Success metrics with measurable targets
- Technical architecture design (ARCHITECTURE.md)
  - 10 component designs with code snippets
  - Data models for issue context and registry extension
  - Security considerations and integration points
- Implementation plan (IMPLEMENTATION_PLAN.md)
  - 4 phases with 20 total tasks
  - Dependency graph showing task relationships
  - Testing checklist and launch criteria
- Architecture Decision Records (DECISIONS.md)
  - 8 ADRs documenting key design choices
  - Alternatives considered for each decision

### Research Conducted
- Analyzed existing plan.md argument parsing (3-tier classification system)
- Documented worktree management infrastructure (7 scripts, global registry)
- Researched gh CLI integration patterns (issue list, view, comment)
- Identified no existing gh CLI usage in codebase

## [0.1.0] - 2025-12-24

### Added
- Initial project creation
- Requirements elicitation begun
