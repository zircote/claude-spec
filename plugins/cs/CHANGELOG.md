# Changelog

All notable changes to the claude-spec plugin will be documented in this file.

## [Unreleased]

### Added
- `analyzers/` directory with log analysis tools
  - `analyze_cli.py` - CLI for generating interaction analysis
  - `log_analyzer.py` - Core analysis logic for prompt logs
- `tests/` directory with 62 unit tests
  - `test_log_entry.py` - LogEntry/FilterInfo serialization tests
  - `test_pipeline.py` - Secret detection and truncation tests
  - `test_analyzer.py` - Log analysis tests
  - `test_hook.py` - Prompt capture hook tests

### Fixed
- **hooks.json**: Fixed malformed nested structure that prevented hook registration
- **c.md**: Fixed analyzer path from `~/.claude/hooks/analyzers/` to `${CLAUDE_PLUGIN_ROOT}/analyzers/`
- **c.md**: Fixed log filename reference from `PROMPT_LOG.json` to `.prompt-log.json`
- **log.md**: Fixed log filename references to use `.prompt-log.json` consistently
- **log_analyzer.py**: Removed `profanity_count` references (FilterInfo only has `secret_count`)

### Changed
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
