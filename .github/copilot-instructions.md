# GitHub Copilot Instructions

This file provides context for GitHub Copilot when working in this repository.

## Project Overview

**claude-spec** is a Claude Code plugin for project specification and implementation lifecycle management. It provides slash commands (`/cs:*`) for strategic planning, progress tracking, and project close-out with retrospectives.

## Technology Stack

- **Language**: Python 3.11+
- **Package Manager**: uv (not pip)
- **Testing**: pytest with coverage
- **Linting**: ruff (format + lint)
- **Type Checking**: mypy
- **Security**: bandit
- **Shell Scripts**: bash with shellcheck

## Project Structure

```
plugins/cs/
├── commands/           # Slash command definitions (markdown files)
├── memory/             # Git-native memory system (semantic search)
├── filters/            # Content filtering (secret detection, truncation)
├── hooks/              # Claude Code lifecycle hooks
├── steps/              # Pre/post step modules
├── analyzers/          # Log analysis tools
├── skills/             # Worktree automation
└── tests/              # Pytest test suite (600+ tests)
```

## Code Style Guidelines

### Python

- Use frozen dataclasses for immutable data models
- Use `from __future__ import annotations` for forward references
- Type hints required on all public functions
- Docstrings use Google style format
- Max line length: 100 characters
- Use `pathlib.Path` over `os.path`

### Imports

```python
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
```

### Data Models

```python
@dataclass(frozen=True, slots=True)
class Memory:
    """A captured memory with metadata."""

    id: str
    namespace: str
    content: str
    commit_sha: str
    timestamp: datetime
    tags: tuple[str, ...] = field(default_factory=tuple)
```

### Error Handling

- Hooks must NEVER crash - always return valid JSON
- Use specific exception types, not bare `except:`
- Log errors to stderr, return valid response to stdout

```python
def hook_main() -> None:
    try:
        result = process_hook()
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"decision": "approve"}))  # Never block
        print(f"Error: {e}", file=sys.stderr)
```

### Testing

- Use pytest fixtures extensively
- Mock external dependencies (git, filesystem)
- Test files mirror source structure: `hooks/foo.py` → `tests/test_foo.py`
- Use `monkeypatch` for stdin/stdout/env mocking

```python
@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create mock spec project structure."""
    project = tmp_path / "docs" / "spec" / "active" / "test-project"
    project.mkdir(parents=True)
    return project

def test_hook(temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))
    # ...
```

## Key Patterns

### Hook Input/Output Contract

All hooks receive JSON on stdin and must output JSON to stdout:

```python
# Input
{
    "hook_event_name": "UserPromptSubmit",
    "prompt": "string",
    "session_id": "string",
    "cwd": "string"
}

# Output (hooks never block)
{"decision": "approve"}
```

### Memory ID Format

`<namespace>:<short_sha>:<timestamp_ms>`

Example: `decisions:abc123d:1702560000000`

### Secret Detection

Add patterns to `filters/pipeline.py::SECRET_PATTERNS`:

```python
SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "github_pat"),
    # Add new patterns here
]
```

## Commands

### Build & Test

```bash
cd plugins/cs
make ci          # Full CI suite
make test        # Run tests
make lint        # Check linting
make format      # Auto-format
make typecheck   # Type check
```

### Single Test

```bash
uv run pytest tests/test_pipeline.py -v
uv run pytest tests/test_hook.py::test_specific -v
```

## Don't Do

- Don't use `pip install` - use `uv sync`
- Don't use bare `except:` - catch specific exceptions
- Don't print to stdout in hooks except for JSON response
- Don't modify files outside `plugins/cs/` for plugin code
- Don't skip type hints on public APIs
- Don't use mutable default arguments in dataclasses
