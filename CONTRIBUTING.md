# Contributing to claude-spec

Thank you for your interest in contributing to claude-spec! This document provides guidelines and workflows for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Contribution Workflow](#contribution-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming environment for all contributors

## Getting Started

### Prerequisites

- **Claude Code CLI** — Install from [claude.ai/code](https://claude.ai/code)
- **Git** — Version 2.20+
- **Python 3.8+** — For hooks and filters
- **jq** — For shell script JSON processing (`brew install jq`)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/claude-spec.git
   cd claude-spec
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/zircote/claude-spec.git
   ```

## Development Setup

### Install the Plugin Locally

```bash
# Install directly from your local clone
claude plugins install --marketplace ./.claude-plugin/marketplace.json cs
```

### Test Your Changes

After making changes, reinstall to test:

```bash
claude plugins uninstall cs
claude plugins install --marketplace ./.claude-plugin/marketplace.json cs
```

## Project Structure

```
claude-spec/
├── .claude-plugin/               # Root marketplace configuration
│   └── marketplace.json
│
├── plugins/cs/                   # Main plugin directory
│   ├── .claude-plugin/
│   │   └── plugin.json           # Plugin metadata
│   │
│   ├── hooks/                    # Event handlers
│   │   ├── hooks.json            # Hook registration
│   │   └── prompt_capture.py     # Main hook implementation
│   │
│   ├── filters/                  # Content processing
│   │   ├── __init__.py
│   │   ├── pipeline.py           # Secret detection & filtering
│   │   ├── log_entry.py          # Log entry schema
│   │   └── log_writer.py         # Atomic file operations
│   │
│   ├── commands/                 # Slash commands
│   │   ├── p.md                  # /p - Planning
│   │   ├── i.md                  # /i - Implementation
│   │   ├── s.md                  # /s - Status
│   │   ├── c.md                  # /c - Close-out
│   │   ├── log.md                # /log - Logging control
│   │   ├── migrate.md            # /migrate - Migration
│   │   └── wt/                   # Worktree subcommands
│   │       ├── create.md
│   │       ├── status.md
│   │       └── cleanup.md
│   │
│   ├── skills/                   # Skills (invokable behaviors)
│   │   └── worktree-manager/
│   │       ├── SKILL.md
│   │       ├── config.json
│   │       └── scripts/
│   │
│   └── templates/                # Project artifact templates
│
└── docs/                         # Documentation
    └── ARCHITECTURE.md           # Technical architecture
```

## Contribution Workflow

### 1. Create a Feature Branch

```bash
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation only
- `refactor/` — Code refactoring
- `chore/` — Maintenance tasks

### 2. Make Your Changes

Follow the [Coding Standards](#coding-standards) below.

### 3. Commit Your Changes

Use conventional commits:

```bash
git commit -m "feat(commands): add timeout option to /p"
git commit -m "fix(filters): handle unicode in secret detection"
git commit -m "docs(readme): clarify worktree setup instructions"
```

Prefixes:
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation
- `refactor` — Code restructuring
- `test` — Tests
- `chore` — Maintenance

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Coding Standards

### Python (hooks, filters)

```python
# Use type hints
def process_prompt(prompt: str, max_length: int = 50000) -> dict:
    """
    Process and filter a user prompt.

    Args:
        prompt: The raw user prompt
        max_length: Maximum allowed length

    Returns:
        Filtered prompt data with metadata
    """
    ...

# Use dataclasses for structured data
@dataclass
class LogEntry:
    timestamp: str
    session_id: str
    prompt: str

# Constants at module level
MAX_PROMPT_LENGTH = 50000
SECRET_PATTERNS = [...]
```

**Style:**
- Follow PEP 8
- Use type hints throughout
- Document functions with docstrings
- Handle errors explicitly, don't fail silently in hooks

### Markdown Commands

Commands are markdown files with YAML frontmatter:

```yaml
---
argument-hint: <required-arg> [optional-arg]
description: Brief description shown in help
model: claude-opus-4-5-20251101  # Optional model override
allowed-tools: Read, Write, Bash, Glob, Grep  # Restrict available tools
---

# /command-name - Full Name

<role>
Clear role definition for the AI.
</role>

<command_argument>
$ARGUMENTS
</command_argument>

<protocol>
## Step 1: First Step

Clear instructions...

## Step 2: Second Step

More instructions...
</protocol>

<edge_cases>
### Case 1
How to handle...
</edge_cases>
```

**Guidelines:**
- Use XML-style tags for major sections
- Include edge case handling
- Provide example outputs
- Reference other commands when relevant

### Shell Scripts

```bash
#!/bin/bash
# script-name.sh - Brief description
#
# Usage: ./script-name.sh <arg1> [arg2]
#
# Arguments:
#   arg1  - Description of arg1
#   arg2  - Optional description
#
# Examples:
#   ./script-name.sh foo
#   ./script-name.sh foo bar

set -e  # Exit on error

# Validate input
if [ -z "$1" ]; then
    echo "Error: arg1 required" >&2
    echo "Usage: $0 <arg1> [arg2]" >&2
    exit 1
fi

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required" >&2
    exit 1
fi

# Main logic
...
```

**Guidelines:**
- Include usage header
- Use `set -e` for error handling
- Validate inputs
- Check dependencies
- Quote variables properly

### Templates

Templates use variable placeholders:

```markdown
---
document_type: template_type
project_id: ${PROJECT_ID}
---

# ${PROJECT_NAME}

## Section

[Placeholder text for user to fill]
```

Variables:
- `${PROJECT_ID}` — SPEC-YYYY-MM-DD-NNN
- `${PROJECT_NAME}` — Human readable name
- `${DATE}` — ISO date
- `${TIMESTAMP}` — ISO timestamp
- `${SLUG}` — URL-safe identifier

## Testing

### Manual Testing

1. Install your development version
2. Create a test project:
   ```
   /p test feature for manual testing
   ```
3. Walk through the full workflow:
   - Planning → Implementation → Status → Close-out
4. Verify document generation and sync

### Hook Testing

Test the prompt capture hook:

```bash
# Simulate hook input
echo '{"type":"UserPromptSubmit","prompt":"test prompt"}' | \
  python3 plugins/cs/hooks/prompt_capture.py
```

Expected output:
```json
{"decision": "approve"}
```

### Filter Testing

```python
# Test secret detection
from filters.pipeline import FilterPipeline

pipeline = FilterPipeline()
result = pipeline.process("my secret key is AKIAIOSFODNN7EXAMPLE")
assert "[SECRET:aws_access_key]" in result["filtered_prompt"]
```

## Documentation

### When to Update Docs

- **New command** — Update README.md command table
- **Changed behavior** — Update relevant command's .md file
- **New template field** — Update template and README
- **Configuration change** — Update config.json and SKILL.md

### Documentation Locations

| Type | Location |
|------|----------|
| User-facing | `README.md` |
| Command usage | `commands/*.md` (in frontmatter) |
| Skill usage | `skills/*/SKILL.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Contributing | `CONTRIBUTING.md` |

## Pull Request Process

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated if needed
- [ ] Tested manually end-to-end
- [ ] Commit messages follow conventional format
- [ ] Branch is up to date with main

### PR Template

```markdown
## Summary

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring

## Testing Done

Describe how you tested the changes.

## Checklist

- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No secrets or sensitive data included
```

### Review Process

1. Automated checks run (if configured)
2. Maintainer review
3. Address feedback
4. Squash and merge

## Questions?

Open an issue with the `question` label or start a discussion in GitHub Discussions.

---

Thank you for contributing to claude-spec!
