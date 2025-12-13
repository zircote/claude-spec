# Changelog

## [Unreleased]

### Implementation Complete - 2025-12-13

**Phase 1: Config Foundation** (100%)
- Created `config.template.json` with sensible defaults (ghostty terminal)
- Created `lib/config.sh` with get_config() and get_config_nested() functions
- Removed old `config.json`

**Phase 2: Script Migration** (100%)
- Updated `launch-agent.sh` to use config loader
- Updated `allocate-ports.sh` to use config loader

**Phase 3: Interactive Setup** (100%)
- Added First-Time Setup section to SKILL.md with AskUserQuestion flow
- Created `/cs:wt:setup` command at `commands/wt/setup.md`

**Phase 4: Prompt Log Fix** (100%)
- Added Step 3b to p.md mandatory_first_actions
- Creates `.prompt-log-enabled` marker BEFORE launching agent

**Phase 5: Testing & Polish** (100%)
- Verified config loader fallback chain works
- Updated plugin README.md and SKILL.md documentation

---

## [COMPLETED] - 2025-12-13

### Project Closed
- Final status: success
- Moved to: docs/spec/completed/2025-12-13-worktree-config-install

### Retrospective Summary
- What went well: Clean config loader design, fallback chain, interactive setup UX
- What to improve: Consider execution flow tracing during planning for timing-sensitive features

### Post-Implementation Addition
- Prompt log marker moved to project root (not spec dir) to capture first prompt

---

## [1.0.0] - 2025-12-13

### Added
- Complete requirements specification (9 requirements)
- Technical architecture design with config loader library
- Implementation plan with 9 tasks across 5 phases
- Architecture Decision Records (5 ADRs)
- Research notes documenting codebase analysis

### Research Conducted
- Analyzed all 6 worktree-manager scripts for config usage
- Identified launch-agent.sh and allocate-ports.sh as config consumers
- Documented prompt log timing bug and fix location
- Mapped existing ~/.claude/ file structure

### Decisions Made
- User config at ~/.claude/worktree-manager.config.json (ADR-001)
- Fallback chain: user config → template → defaults (ADR-002)
- Interactive setup via AskUserQuestion tool (ADR-003)
- Rename config.json to config.template.json (ADR-004)
- Fix prompt log timing in p.md mandatory_first_actions (ADR-005)
