# Changelog

All notable changes to the claude-spec plugin will be documented in this file.

## [Unreleased]

## [1.1.0] - 2025-12-13

### Added
- **Lifecycle Hook System**: Pre/post step execution for `/cs:*` commands
  - `hooks/session_start.py` - SessionStart hook that loads context (CLAUDE.md, git state, project structure)
  - `hooks/command_detector.py` - UserPromptSubmit hook that detects `/cs:*` commands and triggers pre-steps
  - `hooks/post_command.py` - Stop hook that runs post-steps and cleans up session state
- **Step Modules**: Configurable step system with fail-open design
  - `steps/base.py` - BaseStep ABC with StepResult dataclass
  - `steps/context_loader.py` - Loads CLAUDE.md (global + local), git state, project structure
  - `steps/security_reviewer.py` - Bandit-based security scanning
  - `steps/log_archiver.py` - Archives .prompt-log.json to completed project directories
  - `steps/marker_cleaner.py` - Removes temp files (.prompt-log-enabled, .cs-session-state.json)
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
- **i.md**: Added `implementation_gate` for explicit `/cs:i` requirement
- Interaction analysis now generated from plugin's own analyzer scripts
- All prompt log references standardized to `.prompt-log.json`

## [1.0.0] - 2025-12-12

### Added
- Initial release of claude-spec plugin
- `/cs:p` - Project planning command with parallel agent orchestration
- `/cs:i` - Implementation tracking with document synchronization
- `/cs:s` - Status and portfolio monitoring
- `/cs:c` - Project close-out and archival
- `/cs:log` - Prompt capture toggle
- `/cs:migrate` - Migration from legacy `/arch:*` commands
- `/cs:wt:create` - Worktree creation with agent launching
- `/cs:wt:status` - Worktree status display
- `/cs:wt:cleanup` - Worktree cleanup
- Prompt capture hook with filtering pipeline
- Project artifact templates with Agent fields
- Worktree management scripts

### Attribution
- Worktree management based on original `worktree-manager` skill
