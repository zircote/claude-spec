# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**claude-spec** is a Claude Code plugin for project specification and implementation lifecycle management. It provides slash commands (`/cs:*`) for strategic planning, progress tracking, and project close-out with retrospectives.

## Build & Test Commands

All commands run from `plugins/cs/` directory:

```bash
cd plugins/cs

# Install dependencies
make install          # or: uv sync

# Run all CI checks (recommended before commits)
make ci               # format-check + lint + typecheck + security + shellcheck + test

# Individual checks
make format           # Format code with ruff
make format-check     # Check formatting (CI mode)
make lint             # Lint with ruff
make lint-fix         # Lint and auto-fix
make typecheck        # Type check with mypy
make security         # Security scan with bandit
make test             # Run tests with coverage
make shellcheck       # Lint shell scripts

# Run single test
uv run pytest tests/test_pipeline.py -v
uv run pytest tests/test_hook.py::test_main_with_logging_enabled -v

# Clean generated files
make clean
```

## Architecture

### Plugin Structure

```
plugins/cs/
├── commands/           # Slash command definitions (markdown)
│   ├── p.md           # /cs:p - Strategic project planning
│   ├── i.md           # /cs:i - Implementation progress tracking
│   ├── s.md           # /cs:s - Status monitoring
│   ├── c.md           # /cs:c - Project close-out
│   ├── log.md         # /cs:log - Prompt capture toggle
│   ├── remember.md    # /cs:remember - Memory capture
│   ├── recall.md      # /cs:recall - Memory search
│   ├── context.md     # /cs:context - Load spec memories
│   ├── memory.md      # /cs:memory - Memory admin
│   └── wt/            # Worktree commands
├── memory/            # cs-memory Git-native memory system
│   ├── models.py      # Data models (Memory, CaptureResult, etc.)
│   ├── config.py      # Configuration constants
│   ├── git_ops.py     # Git notes operations
│   ├── note_parser.py # YAML front matter parsing
│   ├── capture.py     # Memory capture service
│   ├── recall.py      # Search/recall service
│   ├── embedding.py   # sentence-transformers embeddings
│   ├── index.py       # SQLite + sqlite-vec index
│   ├── USER_GUIDE.md  # End-user documentation
│   └── DEVELOPER_GUIDE.md  # Developer integration guide
├── filters/           # Content filtering pipeline
│   ├── pipeline.py    # Secret detection + truncation
│   ├── log_entry.py   # Log entry schema (dataclass)
│   └── log_writer.py  # Atomic JSON file writer
├── hooks/
│   ├── hooks.json         # Hook registration for Claude Code
│   ├── session_start.py   # SessionStart hook - loads context + memory injection
│   ├── command_detector.py # UserPromptSubmit hook - detects /cs:* commands
│   ├── post_command.py    # Stop hook - runs post-steps
│   ├── prompt_capture.py  # UserPromptSubmit hook - logs prompts
│   ├── trigger_memory.py  # UserPromptSubmit hook - trigger-based memory injection
│   ├── post_tool_capture.py # PostToolUse hook - learning capture
│   └── lib/
│       ├── config_loader.py   # Lifecycle configuration loader
│       ├── memory_injector.py # Memory injection for SessionStart
│       ├── spec_detector.py   # Active spec detection
│       └── trigger_detector.py # Trigger phrase detection
├── learnings/             # PostToolUse learning capture system
│   ├── models.py          # ToolLearning, LearningCategory, LearningSeverity
│   ├── detector.py        # LearningDetector with signal patterns
│   ├── deduplicator.py    # SessionDeduplicator with LRU cache
│   └── extractor.py       # extract_learning() with secret filtering
├── steps/              # Pre/post step modules
│   ├── base.py         # StepResult, BaseStep classes
│   ├── context_loader.py    # Load CLAUDE.md, git state, structure
│   ├── security_reviewer.py # Run bandit security scan
│   ├── log_archiver.py      # Archive prompt logs to completed/
│   ├── marker_cleaner.py    # Clean up temp files
│   └── retrospective_gen.py # Generate RETROSPECTIVE.md
├── analyzers/
│   ├── log_analyzer.py    # Log file analysis
│   └── analyze_cli.py     # CLI for retrospective analysis
├── skills/worktree-manager/  # Worktree automation (config at ~/.claude/worktree-manager.config.json)
└── tests/             # Pytest test suite (1236 tests, 95% coverage enforced)
```

### cs-memory Module

The memory module (`plugins/cs/memory/`) provides Git-native persistent memory:

**Key Files:**
- `models.py` - Frozen dataclasses: `Memory`, `MemoryResult`, `CaptureResult`, `HydrationLevel`
- `capture.py` - `CaptureService` with auto-sync configuration
- `recall.py` - `RecallService` for semantic search
- `git_ops.py` - `GitOps` for Git notes operations
- `index.py` - `IndexService` using SQLite + sqlite-vec
- `note_parser.py` - YAML front matter parsing, memory ID generation

**Memory ID Format:** `<namespace>:<short_sha>:<timestamp_ms>`
- Example: `decisions:abc123d:1702560000000`
- Timestamp ensures uniqueness when multiple memories attach to the same commit

**Auto-Configuration:** On first capture, git is configured for notes sync:
- Push/fetch refspecs: `refs/notes/cs/*:refs/notes/cs/*`
- Rewrite ref: `refs/notes/cs/*` (preserves notes during rebase)
- Merge strategy: `cat_sort_uniq`

**Auto-Capture:** Memories are automatically captured during `/cs:*` commands:
- `/cs:p` - Inception, elicitation, research, decisions
- `/cs:i` - Progress, blockers, learnings, deviations
- `/cs:c` - Retrospective, learnings, patterns
- `/cs:review` - Review findings, recurring patterns

Specialized capture methods: `capture_review()`, `capture_retrospective()`, `capture_pattern()`

Control via environment variable:
```bash
export CS_AUTO_CAPTURE_ENABLED=false  # Disable auto-capture
```

### Data Flow

1. **SessionStart Hook** (`hooks/session_start.py`):
   - Fires when Claude Code session starts
   - Checks if project is claude-spec managed (has docs/spec/ or .prompt-log-enabled)
   - Loads context: CLAUDE.md files, git state, project structure
   - **Memory Injection**: Queries RecallService for relevant memories (5-10 items)
   - Outputs context to stdout (added to Claude's initial memory)
   - Respects lifecycle config for which context types to load

2. **UserPromptSubmit Hooks** (in order):
   - `hooks/command_detector.py` (runs first):
     - Detects /cs:* commands in user prompts
     - Saves command state to `.cs-session-state.json`
     - Triggers pre-steps (e.g., security review for /cs:c)
     - Always returns `{"decision": "approve"}`
   - `hooks/prompt_capture.py` (runs second):
     - Checks for `.prompt-log-enabled` marker at project root
     - Filters secrets via `filters/pipeline.py`
     - Appends to `.prompt-log.json` at project root
     - Always returns `{"decision": "approve"}` (never blocks)
   - `hooks/trigger_memory.py` (runs third):
     - **Trigger Detection**: Detects memory-related phrases (why did we, remind me, etc.)
     - Queries RecallService with prompt as semantic query
     - Returns `additionalContext` with matching memories
     - Always returns `{"decision": "approve"}`

3. **PostToolUse Hook** (`hooks/post_tool_capture.py`):
   - Fires after tool execution (Bash, Read, Write, Edit, WebFetch)
   - **Learning Detection**: Detects learnable signals (errors, warnings, workarounds)
   - Calculates capture score using heuristics (threshold ≥0.6)
   - Deduplicates against session captures
   - Filters secrets from output
   - Queues learnings for batch commit on session Stop
   - Returns immediately (never blocks, <50ms target)

4. **Stop Hook** (`hooks/post_command.py`):
   - Fires when Claude Code session ends
   - Reads command state from `.cs-session-state.json`
   - Triggers post-steps (e.g., log archival, retrospective gen for /cs:c)
   - Cleans up session state file
   - Returns `{"continue": false}`

5. **Filter Pipeline** (`filters/pipeline.py`):
   - Pre-compiled regex patterns for 15+ secret types (AWS, GitHub, API keys, etc.)
   - Order: secrets -> truncation
   - Returns `FilterResult` with statistics

### Lifecycle Configuration

Pre/post steps are configured via `~/.claude/worktree-manager.config.json`:

```json
{
  "lifecycle": {
    "sessionStart": {
      "enabled": true,
      "loadContext": {
        "claudeMd": true,
        "gitState": true,
        "projectStructure": true
      },
      "memoryInjection": {
        "enabled": true,
        "limit": 10,
        "includeContent": false
      }
    },
    "commands": {
      "cs:c": {
        "preSteps": [
          { "name": "security-review", "enabled": true, "timeout": 120 }
        ],
        "postSteps": [
          { "name": "generate-retrospective", "enabled": true },
          { "name": "archive-logs", "enabled": true },
          { "name": "cleanup-markers", "enabled": true }
        ]
      }
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CS_AUTO_CAPTURE_ENABLED` | `true` | Enable/disable auto-capture during /cs:* commands |
| `CS_TOOL_CAPTURE_ENABLED` | `true` | Enable/disable PostToolUse learning capture |
| `CS_TRIGGER_MEMORY_ENABLED` | `true` | Enable/disable trigger phrase memory injection |

```bash
# Disable all hook-based memory features
export CS_TOOL_CAPTURE_ENABLED=false
export CS_TRIGGER_MEMORY_ENABLED=false

# Disable only auto-capture (keeps hook-based capture)
export CS_AUTO_CAPTURE_ENABLED=false
```

6. **Log Writer** (`filters/log_writer.py`):
   - Atomic writes with file locking (`fcntl.flock`)
   - Creates backup before modifications
   - JSON array format with `LogEntry` schema

### Project Artifact Structure

```
project-root/
├── .prompt-log-enabled   # Marker at root to capture first prompt
├── .prompt-log.json      # Log file at root (archived to completed/)
├── .cs-memory/           # Memory index (gitignored)
│   ├── index.db          # SQLite + sqlite-vec index
│   └── models/           # Cached embedding model
└── docs/spec/
    ├── active/           # In-progress projects
    │   └── YYYY-MM-DD-slug/
    │       ├── README.md, REQUIREMENTS.md, ARCHITECTURE.md
    │       └── IMPLEMENTATION_PLAN.md, PROGRESS.md
    └── completed/        # Archived with RETROSPECTIVE.md + .prompt-log.json
```

## Key Patterns

### Hook Input/Output Contract

```python
# Input (stdin JSON)
{
    "hook_event_name": "UserPromptSubmit",
    "prompt": "string",       # NOTE: "prompt", not "user_prompt"
    "session_id": "string",
    "cwd": "string"
}

# Output (stdout JSON)
{"decision": "approve"}  # Hook never blocks
```

### Secret Detection

Patterns in `filters/pipeline.py::SECRET_PATTERNS` - add new patterns there for additional secret types. Secrets are replaced with `[SECRET:type]` placeholders.

### Test Patterns

Tests use fixtures and mocking extensively:

```python
@pytest.fixture
def temp_project_dir(tmp_path):
    """Create mock spec project structure."""
    project = tmp_path / "docs" / "spec" / "active" / "test-project"
    project.mkdir(parents=True)
    return project

def test_something(temp_project_dir, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))
    # ...
```

## CI/CD

- **GitHub Actions** in `.github/workflows/ci.yml`
- Tests run on Python 3.11, 3.12, 3.13
- Code coverage uploaded to Codecov
- Release workflow in `.github/workflows/release.yml`

## Plugin Command Workflow

```
/cs:p "idea"  ->  Plan with Socratic elicitation
       |
/cs:i slug    ->  Track implementation (PROGRESS.md)
       |
/cs:s         ->  Monitor status
       |
/cs:c slug    ->  Close out with retrospective
```

Enable logging with `/cs:log on` before `/cs:p` for prompt capture during planning.

### Memory Commands

| Command | Description |
|---------|-------------|
| `/cs:remember <type> <summary>` | Capture a memory (decision, learning, blocker, progress, pattern) |
| `/cs:recall <query>` | Semantic search across memories |
| `/cs:context [spec]` | Load all memories for a spec |
| `/cs:memory status` | View memory statistics and index health |
| `/cs:memory reindex` | Rebuild index from Git notes |
| `/cs:memory verify` | Check index consistency |
| `/cs:memory gc` | Remove orphaned entries |
| `/cs:memory export` | Export memories to JSON |

### Worktree Commands

| Command | Description |
|---------|-------------|
| `/cs:wt:setup` | Interactive configuration wizard (creates ~/.claude/worktree-manager.config.json) |
| `/cs:wt:create` | Create git worktree with Claude agent |
| `/cs:wt:status` | Show worktree status |
| `/cs:wt:cleanup` | Clean up stale worktrees |

## Active Spec Projects

(None - all projects completed)

## Completed Spec Projects

- `docs/spec/completed/2025-12-17-hook-based-memory-arch/` - Hooks Based Git-Native Memory Architecture
  - Completed: 2025-12-17
  - Outcome: success
  - Effort: 18 hours (24 tasks across 4 phases, within 16-24 hour estimate)
  - Quality: 1108 tests passing (+218 beyond target), code review 7.5/10
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, IMPLEMENTATION_PLAN.md, RETROSPECTIVE.md, DECISIONS.md
  - Key features:
    - PostToolUse hook for automatic learning capture (errors, workarounds, discoveries)
    - SessionStart memory injection (5-10 relevant memories per session)
    - Trigger phrase detection (16 patterns: "why did we", "remind me", etc.)
    - Memory queue flush on Stop hook
    - LearningDetector with threshold ≥0.6 for signal quality
    - SessionDeduplicator with LRU cache
    - Performance: All components 5-1000× faster than targets
    - Security: Secret filtering via filter_pipeline
    - Environment variables: CS_TOOL_CAPTURE_ENABLED, CS_TRIGGER_MEMORY_ENABLED
  - New components:
    - `learnings/` package: detector, models, deduplicator, extractor
    - `hooks/post_tool_capture.py`: PostToolUse learning capture
    - `hooks/trigger_memory.py`: UserPromptSubmit trigger detection
    - `hooks/lib/memory_injector.py`: Session memory injection
    - `hooks/lib/trigger_detector.py`: Pattern matching for memory recall
    - `hooks/lib/spec_detector.py`: Active spec detection
    - Stop hook flushes pending memory queue on session end

- `docs/spec/completed/2025-12-15-memory-auto-capture/` - Memory Auto-Capture Implementation
  - Completed: 2025-12-15
  - Outcome: success
  - Effort: 2.5 hours (17 tasks across 4 phases)
  - Quality: 634 tests passing, 87% coverage maintained
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, IMPLEMENTATION_PLAN.md, RETROSPECTIVE.md
  - Key changes:
    - 3 new capture methods: `capture_review()`, `capture_retrospective()`, `capture_pattern()`
    - Auto-capture integration in `/cs:p`, `/cs:i`, `/cs:c`, `/cs:review` commands
    - CaptureAccumulator model for tracking captures during command execution
    - CS_AUTO_CAPTURE_ENABLED environment variable for user control
    - Command file cleanup: 400+ lines of pseudo-code replaced with executable integration
    - validate_auto_capture_namespace() wiring AUTO_CAPTURE_NAMESPACES config

- `docs/spec/completed/2025-12-14-cs-memory/` - Git-Native Memory System for claude-spec
  - Completed: 2025-12-15
  - Outcome: success
  - Effort: 12 hours (vs 40-80 planned, -70% variance)
  - Quality: 9.0/10 (post code review remediation)
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, IMPLEMENTATION_PLAN.md, DECISIONS.md
  - Key changes:
    - Git notes storage + SQLite/sqlite-vec semantic search
    - 4 new commands: /cs:remember, /cs:recall, /cs:context, /cs:memory
    - Memory ID format: `namespace:sha:timestamp_ms` (supports multiple per commit)
    - Auto-configuration of git notes sync on first capture
    - 600 tests passing (84 new memory tests)
    - Comprehensive code review: 45 findings remediated

- `docs/spec/completed/2025-12-13-pre-post-steps-commands/` - Pre and Post Steps for cs:* Commands
  - Completed: 2025-12-13
  - Outcome: success
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, RETROSPECTIVE.md
  - Key changes: Lifecycle hook system (SessionStart, UserPromptSubmit, Stop), 230 tests, 96% coverage

- `docs/spec/completed/2025-12-13-worktree-config-install/` - Worktree Manager Configuration Installation
  - Completed: 2025-12-13
  - Outcome: success
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, RETROSPECTIVE.md
  - Key changes: User config at ~/.claude/worktree-manager.config.json, prompt log at project root

- `docs/spec/completed/2025-12-12-quality-release-ci-github-act/` - Quality Release CI/CD with GitHub Actions
  - Completed: 2025-12-13
  - Outcome: success
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, RETROSPECTIVE.md

- `docs/spec/completed/2025-12-12-test-and-validate-command-au/` - Test and Validate Command
  - Completed: 2025-12-13
  - Outcome: success
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, RETROSPECTIVE.md

- `docs/spec/completed/2025-12-12-prompt-capture-log/` - Prompt Capture Logging
  - Completed: 2025-12-12
  - Outcome: partial (hooks integration needs validation)
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, RETROSPECTIVE.md

- `docs/spec/completed/2025-12-12-arch-lifecycle-automation/` - Architecture Lifecycle Automation
  - Completed: 2025-12-12
  - Outcome: success
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, RETROSPECTIVE.md

- `docs/spec/completed/2025-12-12-claude-spec-plugin/` - Claude Spec Plugin (initial)
  - Completed: 2025-12-12
  - Outcome: success
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, RETROSPECTIVE.md
