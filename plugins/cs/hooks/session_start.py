#!/usr/bin/env python3
"""
Session Start Hook for claude-spec Plugin

This hook fires on Claude Code session start and loads project context
into Claude's memory. Context includes CLAUDE.md files, git state,
and project structure.

Usage:
    Registered as a SessionStart hook via hooks.json.
    Receives JSON via stdin, outputs text context to stdout.

Input format:
    {
        "hook_event_name": "SessionStart",
        "session_id": "string",
        "cwd": "string"
    }

Output:
    Text content added to Claude's initial context (via stdout)
    Errors go to stderr (never block)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Add hooks directory to path for lib imports
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent

if str(SCRIPT_DIR / "lib") not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR / "lib"))
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

try:
    from config_loader import is_session_context_enabled, is_session_start_enabled

    CONFIG_AVAILABLE = True
except ImportError as e:
    CONFIG_AVAILABLE = False
    sys.stderr.write(f"claude-spec session_start: Config import error: {e}\n")


def read_input() -> dict[str, Any] | None:
    """Read and parse JSON input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"claude-spec session_start: JSON decode error: {e}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"claude-spec session_start: Error reading input: {e}\n")
        return None


def is_cs_project(cwd: str) -> bool:
    """Check if this appears to be a claude-spec managed project.

    A project is considered cs-managed if it has:
    - docs/spec/ directory, OR
    - .prompt-log-enabled marker, OR
    - CLAUDE.md with 'claude-spec' references
    """
    cwd_path = Path(cwd)

    # Check for docs/spec directory
    if (cwd_path / "docs" / "spec").is_dir():
        return True

    # Check for prompt log marker
    if (cwd_path / ".prompt-log-enabled").is_file():
        return True

    # Check CLAUDE.md for cs references
    claude_md = cwd_path / "CLAUDE.md"
    if claude_md.is_file():
        try:
            content = claude_md.read_text(encoding="utf-8")
            if "claude-spec" in content.lower() or "/cs:" in content:
                return True
        except Exception as e:
            sys.stderr.write(
                f"claude-spec session_start: Error reading {claude_md}: {e}\n"
            )

    return False


def load_claude_md(cwd: str) -> str:
    """Load CLAUDE.md content from global and local sources.

    Note: This function intentionally duplicates logic from steps/context_loader.py.
    The session_start hook runs at the very beginning of a Claude session, before
    any step modules are loaded. It needs to be self-contained and cannot import
    from the steps/ directory to avoid circular dependencies and ensure reliable
    execution as a standalone hook script.
    """
    parts = []

    # Global CLAUDE.md (~/.claude/CLAUDE.md)
    global_claude = Path.home() / ".claude" / "CLAUDE.md"
    if global_claude.is_file():
        try:
            content = global_claude.read_text(encoding="utf-8")
            parts.append(f"## Global CLAUDE.md\n\n{content[:5000]}")  # Limit size
        except Exception as e:
            sys.stderr.write(
                f"claude-spec session_start: Error reading global CLAUDE.md: {e}\n"
            )

    # Local CLAUDE.md
    local_claude = Path(cwd) / "CLAUDE.md"
    if local_claude.is_file():
        try:
            content = local_claude.read_text(encoding="utf-8")
            parts.append(f"## Project CLAUDE.md\n\n{content[:10000]}")  # Limit size
        except Exception as e:
            sys.stderr.write(
                f"claude-spec session_start: Error reading local CLAUDE.md: {e}\n"
            )

    return "\n\n".join(parts) if parts else ""


def load_git_state(cwd: str) -> str:
    """Load current git state information."""
    parts = ["## Git State\n"]

    try:
        # Current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            parts.append(f"**Branch**: {result.stdout.strip()}")

        # Recent commits (last 3)
        result = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts.append(f"\n**Recent commits**:\n```\n{result.stdout.strip()}\n```")

        # Uncommitted changes summary
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            changes = result.stdout.strip()
            if changes:
                lines = changes.split("\n")
                parts.append(f"\n**Uncommitted changes**: {len(lines)} files")
                # Show first few
                if len(lines) <= 10:
                    parts.append(f"```\n{changes}\n```")
                else:
                    parts.append(
                        f"```\n{chr(10).join(lines[:10])}\n... and {len(lines) - 10} more\n```"
                    )
            else:
                parts.append("\n**Working tree**: clean")

    except subprocess.TimeoutExpired:
        sys.stderr.write("claude-spec session_start: Git command timed out\n")
    except Exception as e:
        sys.stderr.write(f"claude-spec session_start: Git error: {e}\n")

    return "\n".join(parts)


def load_project_structure(cwd: str) -> str:
    """Load project directory structure summary."""
    parts = ["## Project Structure\n"]

    cwd_path = Path(cwd)

    # Key directories to look for
    key_dirs = [
        "docs/spec/active",
        "docs/spec/completed",
        "plugins",
        "commands",
        "hooks",
        "steps",
        "src",
        "tests",
    ]

    found_dirs = []
    for dir_path in key_dirs:
        full_path = cwd_path / dir_path
        if full_path.is_dir():
            # Count items
            try:
                items = list(full_path.iterdir())
                count = len(items)
                found_dirs.append(f"- `{dir_path}/` ({count} items)")
            except Exception:
                found_dirs.append(f"- `{dir_path}/`")

    if found_dirs:
        parts.append("\n".join(found_dirs))

    # Active spec projects
    active_specs = cwd_path / "docs" / "spec" / "active"
    if active_specs.is_dir():
        try:
            projects = [d.name for d in active_specs.iterdir() if d.is_dir()]
            if projects:
                parts.append(f"\n**Active spec projects**: {', '.join(projects[:5])}")
        except Exception as e:
            sys.stderr.write(
                f"claude-spec session_start: Error listing projects: {e}\n"
            )

    return "\n".join(parts)


def main() -> None:
    """Main entry point for the session start hook."""
    # Read input
    input_data = read_input()

    if input_data is None:
        # Malformed input - silent exit
        return

    cwd = input_data.get("cwd", "")

    if not cwd:
        return

    # Check if session start is enabled
    if CONFIG_AVAILABLE and not is_session_start_enabled():
        return

    # Check if this is a cs project
    if not is_cs_project(cwd):
        return

    # Build context parts based on config
    context_parts = []

    context_parts.append("# Claude Spec Session Context\n")
    context_parts.append("_Loaded by claude-spec plugin on session start_\n")

    # Load each context type if enabled
    if not CONFIG_AVAILABLE or is_session_context_enabled("claudeMd"):
        claude_md = load_claude_md(cwd)
        if claude_md:
            context_parts.append(claude_md)

    if not CONFIG_AVAILABLE or is_session_context_enabled("gitState"):
        git_state = load_git_state(cwd)
        if git_state:
            context_parts.append(git_state)

    if not CONFIG_AVAILABLE or is_session_context_enabled("projectStructure"):
        structure = load_project_structure(cwd)
        if structure:
            context_parts.append(structure)

    # Output context (stdout is added to Claude's initial context)
    if len(context_parts) > 2:  # More than just header
        print("\n\n".join(context_parts))


if __name__ == "__main__":
    main()
