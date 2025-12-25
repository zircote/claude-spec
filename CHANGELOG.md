# Changelog

All notable changes to the claude-spec plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.0] - 2025-12-25

### Added
- **report-issue**: New `/claude-spec:report-issue` command for AI-actionable GitHub issues
  - Investigates codebase before filing (30-60 seconds exploration)
  - Gathers file paths, code snippets, error traces, related code
  - Produces issues with enough detail for AI-assisted resolution
  - Supports issue types: bug, feat, docs, chore, perf
  - Repository detection from error traces, plugin paths, or current project
  - Cancel option at every step for safe exit
- **plan.md**: Error recovery integration with `/report-issue`
  - Captures error context (traceback, files, recent actions)
  - Offers to launch issue reporter with pre-filled context
  - Session and permanent suppression options for error prompts
- **implement.md**: Error recovery integration with `/report-issue`
  - Same error context capture and reporting flow
  - Checkpoints progress before launching issue reporter
- **report-issue**: Phase 0 error context detection
  - Auto-detects when invoked from `/plan` or `/implement` after error
  - Pre-fills issue type, description, and investigation findings
  - Displays pre-filled context for user review

### Fixed
- **report-issue**: Argument parsing logic (array indexing instead of shift in for loop)
- **report-issue**: Added cancel option to all Phase 1 AskUserQuestion prompts
- **report-issue**: Improved Step 1.2/1.3 title and description UX
- **report-issue**: Added chore and perf type-specific follow-up prompts
- **report-issue**: Implemented full repository detection logic in Step 4.1
- **plan.md/implement.md**: Added initialization guidance for suppression flags

## [0.10.0] - 2025-12-25

### Added
- **approve**: New `/claude-spec:approve` command for explicit plan acceptance
  - Review and approve/reject specs before implementation
  - Records approver identity and timestamp in README.md frontmatter
  - Request Changes workflow keeps spec in review status
  - Rejection workflow moves spec to `docs/spec/rejected/`
- **deep-clean**: Added `--focus=MAX` mode for maximum coverage (12+ specialist agents)
  - Deploys all 6 base agents with all focus enhancements combined
  - Adds 6 additional specialists: Database Expert, Penetration Tester, Compliance Auditor, Chaos Engineer, Accessibility Tester, Prompt Engineer
  - Prompt Engineer uses `claude-code-guide` for Anthropic best practices and Claude patterns
  - Full verification with pr-review-toolkit agents
- **deep-clean**: Added `--focus=MAXALL` convenience wrapper
  - Equivalent to `--focus=MAX --all`
  - Maximum agents + auto-remediate all findings + no user prompts
  - One command for fully autonomous comprehensive review and fix
- **plan.md**: Approval workflow integration with draft status
- **implement.md**: Warning banner when spec not approved
- **ci**: Add changelog automation to release workflow

### Changed
- **Renamed**: `/claude-spec:code-cleanup` to `/claude-spec:deep-clean`
- **README.md**: Reorganized features with Deep Analysis Commands at top
- **Config File Rename**: `worktree-manager.config.json` to `claude-spec.config.json`
  - User config now at `~/.claude/claude-spec.config.json`
  - Default config moved from `skills/worktree-manager/config.template.json` to plugin root `./claude-spec.config.json`
  - Auto-migration: old config path is automatically renamed to new path on first load
  - Command keys updated: `cs:*` to `claude-spec:*` (e.g., `cs:c` to `claude-spec:complete`)
- **Simplified Architecture**: Plugin now focuses on Commands, Filters, and Worktree Manager only

### Fixed
- **plan.md**: Normalize relative file paths to absolute before worktree context switch
- **plan.md**: Update PROJECT_ID regex to match full format `SPEC-YYYY-MM-DD-SEQ`
- **plan.md**: Clarify worktree creation is conditional on user selecting "Start fresh"
- **plan.md**: Replace invalid placeholder `[derive-from-plan-title]` with bash function call
- **plan.md**: Add sequence number increment logic for same-date project creation

### Removed
- **Memory System**: Removed entire `memory/` module (Git-native memory with semantic search)
  - Removed commands: `/remember`, `/recall`, `/context`, `/memory`
  - Removed dependencies: `sentence-transformers`, `sqlite-vec`
  - Memory functionality being replaced by external system
- **Hook System**: Removed all lifecycle hooks
  - Removed `hooks/` directory (session_start.py, command_detector.py, post_command.py, prompt_capture.py)
  - Removed `hooks.json` registration
  - Hooks being replaced by external system
- **Prompt Capture**: Removed `/log` command and prompt capture functionality
  - Removed `.prompt-log-enabled` marker file handling from plan.md, complete.md
  - Removed `.prompt-log.json` and `.prompt-log-enabled` from marker_cleaner.py cleanup list
- **Code Review Commands**: Removed `/code-review` and `/code-fix` commands
- **Memory Spec Projects**: Removed related completed spec documentation

## [0.9.0] - 2025-12-25

### Removed
- Remove `.prompt-log-enabled` dead code references

## [0.8.x] - 2025-12-24

### Fixed
- **v0.8.3**: Prevent context exhaustion cascading failure in implement command (#33)
- **v0.8.1**: Prevent conversation state corruption in implement and plan commands

## [0.7.0] - 2025-12-24

### Added
- **plan**: Implement GitHub Issues worktree workflow
  - Issue-to-worktree automation
  - `/claude-spec:plan` without arguments now shows issue selection

### Fixed
- Address code review feedback
- Complete MAXALL code cleanup remediation (101 findings)

## [0.6.x] - 2025-12-24

### Added
- **v0.6.4**: Real-time progress tracking for remediation in code-cleanup command
- **v0.6.2**: `--focus=MAX` and `--focus=MAXALL` modes for code-cleanup
- **v0.6.1**: `make release-{patch,minor,major}` combined targets
- **v0.6.0**: Help sections and date-based report paths for commands
- **CLAUDE.md**: LSP code intelligence guidelines
- LSP hooks for Python development (format-on-edit, lint-check, typecheck)

### Fixed
- **v0.6.0**: Address 5 code review findings from PR#24
- **v0.6.0**: Add argument type detection and migration protocol to plan command
- Expand truncated help text in command DESCRIPTION sections

## [0.5.0] - 2025-12-21

### Added
- **commands**: Add deep-explore and deep-research Opus 4.5 commands
- **plugin**: Add missing commands and sync version

### Fixed
- **make**: Require CI checks to pass before release
- **make**: Simplify release target to avoid Python 3.13 compatibility issues

### Changed
- **ci**: Bump actions/github-script from 7 to 8
- **ci**: Bump actions/setup-python from 5 to 6
- **ci**: Bump actions/checkout from 4 to 6

## [0.4.x] - 2025-12-19

### Added
- **v0.4.4**: `/code-cleanup` slash command for code quality analysis
- **v0.4.4**: `make version` and `make release` targets
- **v0.4.1**: bump-my-version for semantic versioning
- **v0.4.0**: Git-native memory system removed in later version

### Changed
- **v0.4.4**: Complete prompt engineering refactoring for implement command
- **v0.4.4**: Add execution_mode and shared_configuration to implement
- **v0.4.0**: Move plugin structure from `plugins/cs/` to repository root
- **v0.4.0**: Update config paths and documentation

### Fixed
- **v0.4.0**: Update workflows for memory/hooks removal
- **v0.4.0**: Remove Memory and Hook systems from claude-spec plugin
- **v0.4.0**: CI workflow fixes for root-level plugin structure

## [0.3.0] - 2025-12-17

### Added
- **commands**: Add artifact verification gate to `/cs:i`
- **commands**: Add documentation gate to `/cs:i`
- **commands**: Integrate `/cs:review` and `/cs:fix` into `/cs:i`
- **cs**: Report placement directive to review/fix commands
- **cs**: Hook-based memory architecture (removed in v0.4.0)
- **memory**: Auto-capture for cs:* commands (removed in v0.4.0)
- **memory**: Git notes auto-sync configuration (removed in v0.4.0)
- **recall**: API reference with common pitfalls
- **worktree**: iTerm2 tab mode for agent launching
- **worktree**: User config persistence and prompt log timing fix
- **cs**: Pre and post steps for /cs:* commands
- GitHub Actions CI/CD and improved test coverage
- Expanded test suite (230 tests, 96% coverage)

### Changed
- Convert marketplace to plugin with nested path references
- Update plugin installation for public GitHub repo
- Rename ARTIFACT_CLEANUP_RETROSPECTIVE to RETROSPECTIVE

### Fixed
- Address Copilot code review findings
- Correct hook paths for nested plugin structure
- Enforce AskUserQuestion and add quality gate
- Add TodoWrite to multi-step commands
- Add AskUserQuestion to allowed-tools
- Update hooks.json to match Claude Code plugin schema
- Unique IDs for multiple memories per commit
- Address PR review comments and critical findings
- Address code review findings with shared modules and enhanced tests
- Fix wt:setup bash reliability and eliminate mapping errors
- Use jq for proper JSON escaping in setup.md
- Repair shellcheck and test failures

## [0.1.x] - 2025-12-12

### Added
- Initial release of claude-spec plugin
- `/p` - Project planning command with parallel agent orchestration
- `/i` - Implementation tracking with document synchronization
- `/s` - Status and portfolio monitoring
- `/c` - Project close-out and archival
- `/log` - Prompt capture toggle (removed in v0.10.0)
- `/migrate` - Migration from legacy `/arch:*` commands
- `/wt:create` - Worktree creation with agent launching
- `/wt:status` - Worktree status display
- `/wt:cleanup` - Worktree cleanup
- Prompt capture hook with filtering pipeline
- Project artifact templates with Agent fields
- Worktree management scripts

### Fixed
- **v0.1.3**: Correct hooks path in plugin.json to relative location
- **v0.1.2**: Pre and post steps lifecycle feature with 95% coverage
- **v0.1.2**: Address PR review findings for error handling and silent failures

### Attribution
- Worktree management based on original `worktree-manager` skill
