"""
Shared context loading utilities for claude-spec hooks and steps.

This module provides functions to load:
- CLAUDE.md files (global and local)
- Git state information
- Project directory structure

These functions are used by both:
- hooks/session_start.py (SessionStart hook)
- steps/context_loader.py (ContextLoaderStep)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Default size limits (can be overridden by callers)
DEFAULT_GLOBAL_CLAUDE_MD_LIMIT = 5000
DEFAULT_LOCAL_CLAUDE_MD_LIMIT = 10000

# Key directories to check for project structure
KEY_DIRECTORIES = [
    "docs/spec/active",
    "docs/spec/completed",
    "plugins",
    "commands",
    "hooks",
    "steps",
    "src",
    "tests",
]


def _log_error(prefix: str, message: str) -> None:
    """Write error message to stderr.

    Args:
        prefix: The log prefix (e.g., "context_utils")
        message: The error message
    """
    sys.stderr.write(f"{prefix}: {message}\n")


def load_claude_md(
    cwd: str,
    log_prefix: str = "context_utils",
    global_limit: int = DEFAULT_GLOBAL_CLAUDE_MD_LIMIT,
    local_limit: int = DEFAULT_LOCAL_CLAUDE_MD_LIMIT,
    truncate_indicator: str = "",
) -> str:
    """Load CLAUDE.md content from global and local sources.

    Args:
        cwd: Current working directory
        log_prefix: Prefix for error log messages
        global_limit: Max characters for global CLAUDE.md (default 5000)
        local_limit: Max characters for local CLAUDE.md (default 10000)
        truncate_indicator: Text to append when truncating (e.g., "\\n...[truncated]...")

    Returns:
        Combined CLAUDE.md content, or empty string if none found
    """
    parts = []

    # Global CLAUDE.md (~/.claude/CLAUDE.md)
    global_claude = Path.home() / ".claude" / "CLAUDE.md"
    if global_claude.is_file():
        try:
            content = global_claude.read_text(encoding="utf-8")
            if len(content) > global_limit:
                content = content[:global_limit] + truncate_indicator
            parts.append(f"## Global CLAUDE.md\n\n{content}")
        except Exception as e:
            _log_error(log_prefix, f"Error reading global CLAUDE.md: {e}")

    # Local CLAUDE.md
    local_claude = Path(cwd) / "CLAUDE.md"
    if local_claude.is_file():
        try:
            content = local_claude.read_text(encoding="utf-8")
            if len(content) > local_limit:
                content = content[:local_limit] + truncate_indicator
            parts.append(f"## Project CLAUDE.md\n\n{content}")
        except Exception as e:
            _log_error(log_prefix, f"Error reading local CLAUDE.md: {e}")

    return "\n\n".join(parts) if parts else ""


def load_git_state(
    cwd: str,
    log_prefix: str = "context_utils",
    timeout: int = 5,
    include_changes_detail: bool = True,
    max_change_lines: int = 10,
) -> str:
    """Load current git state information.

    Args:
        cwd: Current working directory
        log_prefix: Prefix for error log messages
        timeout: Timeout for git commands in seconds
        include_changes_detail: Whether to include detailed change list
        max_change_lines: Max number of changed files to show in detail

    Returns:
        Git state markdown, or empty string on error
    """
    parts = ["## Git State\n"]

    try:
        # Current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # Handle return code manually
        )
        if result.returncode == 0:
            parts.append(f"**Branch**: {result.stdout.strip()}")

        # Recent commits (last 3)
        result = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # Handle return code manually
        )
        if result.returncode == 0 and result.stdout.strip():
            parts.append(f"\n**Recent commits**:\n```\n{result.stdout.strip()}\n```")

        # Uncommitted changes summary
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # Handle return code manually
        )
        if result.returncode == 0:
            changes = result.stdout.strip()
            if changes:
                lines = changes.split("\n")
                parts.append(f"\n**Uncommitted changes**: {len(lines)} files")

                if include_changes_detail:
                    if len(lines) <= max_change_lines:
                        parts.append(f"```\n{changes}\n```")
                    else:
                        parts.append(
                            f"```\n{chr(10).join(lines[:max_change_lines])}\n"
                            f"... and {len(lines) - max_change_lines} more\n```",
                        )
            else:
                parts.append("\n**Working tree**: clean")

    except subprocess.TimeoutExpired:
        _log_error(log_prefix, "Git command timed out")
        return ""  # Return empty on timeout
    except Exception as e:
        _log_error(log_prefix, f"Git error: {e}")
        return ""  # Return empty on error

    return "\n".join(parts) if len(parts) > 1 else ""


def load_project_structure(
    cwd: str,
    log_prefix: str = "context_utils",
    key_dirs: list[str] | None = None,
    max_active_projects: int = 5,
) -> str:
    """Load project directory structure summary.

    Args:
        cwd: Current working directory
        log_prefix: Prefix for error log messages
        key_dirs: List of directories to check (defaults to KEY_DIRECTORIES)
        max_active_projects: Max number of active spec projects to list

    Returns:
        Project structure markdown, or empty string if nothing found
    """
    parts = ["## Project Structure\n"]

    cwd_path = Path(cwd)

    # Use provided directories or defaults
    dirs_to_check = key_dirs if key_dirs is not None else KEY_DIRECTORIES

    found_dirs = []
    for dir_path in dirs_to_check:
        full_path = cwd_path / dir_path
        if full_path.is_dir():
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
                projects_display = ", ".join(projects[:max_active_projects])
                parts.append(f"\n**Active spec projects**: {projects_display}")
        except Exception as e:
            _log_error(log_prefix, f"Error listing active projects: {e}")

    return "\n".join(parts) if len(parts) > 1 else ""
