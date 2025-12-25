# Changelog

All notable changes to the claude-spec plugin will be documented in this file.

## [Unreleased]

### Added
- **deep-clean**: Added `--focus=MAX` mode for maximum coverage (12+ specialist agents)
  - Deploys all 6 base agents with all focus enhancements combined
  - Adds 6 additional specialists: Database Expert, Penetration Tester, Compliance Auditor, Chaos Engineer, Accessibility Tester, Prompt Engineer
  - Prompt Engineer uses `claude-code-guide` for Anthropic best practices and Claude patterns
  - Full verification with pr-review-toolkit agents
- **deep-clean**: Added `--focus=MAXALL` convenience wrapper
  - Equivalent to `--focus=MAX --all`
  - Maximum agents + auto-remediate all findings + no user prompts
  - One command for fully autonomous comprehensive review and fix

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

### Changed
- **Config File Rename**: `worktree-manager.config.json` → `claude-spec.config.json`
  - User config now at `~/.claude/claude-spec.config.json`
  - Default config moved from `skills/worktree-manager/config.template.json` to plugin root `./claude-spec.config.json`
  - Auto-migration: old config path is automatically renamed to new path on first load
  - Command keys updated: `cs:*` → `claude-spec:*` (e.g., `cs:c` → `claude-spec:complete`)
- **Simplified Architecture**: Plugin now focuses on Commands, Filters, and Worktree Manager only

## [1.1.0] - 2025-12-13

### Added
- **Lifecycle Hook System**: Pre/post step execution for `/*` commands
  - `hooks/session_start.py` - SessionStart hook that loads context (CLAUDE.md, git state, project structure)
  - `hooks/command_detector.py` - UserPromptSubmit hook that detects `/*` commands and triggers pre-steps
  - `hooks/post_command.py` - Stop hook that runs post-steps and cleans up session state
- **Step Modules**: Configurable step system with fail-open design
  - `steps/base.py` - BaseStep ABC with StepResult dataclass
  - `steps/context_loader.py` - Loads CLAUDE.md (global + local), git state, project structure
  - `steps/security_reviewer.py` - Bandit-based security scanning
  - `steps/log_archiver.py` - Archives .prompt-log.json to completed project directories
  - `steps/marker_cleaner.py` - Removes temp files (.cs-session-state.json)
  - `steps/retrospective_gen.py` - Generates RETROSPECTIVE.md from log analysis
- **Lifecycle Configuration**: Step configuration in `~/.claude/worktree-manager.config.json`
  - `lifecycle.pre_steps` - Steps to run before commands (context_loader by default)
  - `lifecycle.post_steps` - Steps to run after commands (log_archiver, marker_cleaner, retrospective_gen by default)
  - `lifecycle.<command>_pre_steps` - Command-specific pre-steps
  - `lifecycle.<command>_post_steps` - Command-specific post-steps
- **Expanded Test Suite**: 105 new tests (230 total, 96% coverage)
  - `tests/test_session_start.py` - 27 tests for session start hook
  - `tests/test_command_detector.py` - 27 tests for command detector hook
  - `tests/test_post_command.py` - 23 tests for post command hook
  - `tests/test_steps.py` - 28 tests for all step modules
  - `tests/test_hooks_lib.py` - Tests for hooks/lib module exports
- `analyzers/` directory with log analysis tools
  - `analyze_cli.py` - CLI for generating interaction analysis
  - `log_analyzer.py` - Core analysis logic for prompt logs

### Fixed
- **hooks.json**: Fixed malformed nested structure that prevented hook registration
- **c.md**: Fixed analyzer path from `~/.claude/hooks/analyzers/` to `${CLAUDE_PLUGIN_ROOT}/analyzers/`
- **c.md**: Fixed log filename reference from `PROMPT_LOG.json` to `.prompt-log.json`
- **log.md**: Fixed log filename references to use `.prompt-log.json` consistently
- **log_analyzer.py**: Removed `profanity_count` references (FilterInfo only has `secret_count`)
- **iTerm2-tab script**: Fixed window vs tab differentiation for proper tab creation

### Changed
- **hooks.json**: Now registers SessionStart, UserPromptSubmit (2 hooks), and Stop hooks
- **plugin.json**: Added `hooks` field pointing to `../hooks/hooks.json` for hook discovery
- **p.md**: Added `post_approval_halt` enforcement for strict phase separation
- **i.md**: Added `implementation_gate` for explicit `/i` requirement
- Interaction analysis now generated from plugin's own analyzer scripts
- All prompt log references standardized to `.prompt-log.json`

## [1.0.0] - 2025-12-12

### Added
- Initial release of claude-spec plugin
- `/p` - Project planning command with parallel agent orchestration
- `/i` - Implementation tracking with document synchronization
- `/s` - Status and portfolio monitoring
- `/c` - Project close-out and archival
- `/log` - Prompt capture toggle
- `/migrate` - Migration from legacy `/arch:*` commands
- `/wt:create` - Worktree creation with agent launching
- `/wt:status` - Worktree status display
- `/wt:cleanup` - Worktree cleanup
- Prompt capture hook with filtering pipeline
- Project artifact templates with Agent fields
- Worktree management scripts

### Attribution
- Worktree management based on original `worktree-manager` skill
