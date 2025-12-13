"""
Context loader step - loads CLAUDE.md, git state, project structure.

This step is primarily used by the SessionStart hook to inject project
context into Claude's memory at session start.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from .base import BaseStep, StepResult


class ContextLoaderStep(BaseStep):
    """Loads project context for SessionStart hook."""

    name = "context-loader"

    def execute(self) -> StepResult:
        """Execute the context loading step.

        Returns:
            StepResult with loaded context in data["context"]
        """
        context_parts = []
        warnings = []

        # Load CLAUDE.md files
        claude_md = self._load_claude_md()
        if claude_md:
            context_parts.append(claude_md)

        # Load git state
        git_state = self._load_git_state()
        if git_state:
            context_parts.append(git_state)

        # Load project structure
        structure = self._load_project_structure()
        if structure:
            context_parts.append(structure)

        if not context_parts:
            return StepResult.fail("No context loaded")

        result = StepResult.ok(
            f"Loaded {len(context_parts)} context sections",
            context="\n\n".join(context_parts),
        )

        for warning in warnings:
            result.add_warning(warning)

        return result

    def _load_claude_md(self) -> str:
        """Load CLAUDE.md content from global and local sources."""
        parts = []

        # Global CLAUDE.md (~/.claude/CLAUDE.md)
        global_claude = Path.home() / ".claude" / "CLAUDE.md"
        if global_claude.is_file():
            try:
                content = global_claude.read_text(encoding="utf-8")
                # Limit size to prevent context bloat
                if len(content) > 5000:
                    content = content[:5000] + "\n...[truncated]..."
                parts.append(f"## Global CLAUDE.md\n\n{content}")
            except Exception as e:
                sys.stderr.write(
                    f"context_loader: Error reading global CLAUDE.md: {e}\n"
                )

        # Local CLAUDE.md
        local_claude = Path(self.cwd) / "CLAUDE.md"
        if local_claude.is_file():
            try:
                content = local_claude.read_text(encoding="utf-8")
                if len(content) > 10000:
                    content = content[:10000] + "\n...[truncated]..."
                parts.append(f"## Project CLAUDE.md\n\n{content}")
            except Exception as e:
                sys.stderr.write(
                    f"context_loader: Error reading local CLAUDE.md: {e}\n"
                )

        return "\n\n".join(parts) if parts else ""

    def _load_git_state(self) -> str:
        """Load current git state information."""
        parts = ["## Git State\n"]

        try:
            # Current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                parts.append(f"**Branch**: {result.stdout.strip()}")

            # Recent commits (last 3)
            result = subprocess.run(
                ["git", "log", "--oneline", "-3"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts.append(
                    f"\n**Recent commits**:\n```\n{result.stdout.strip()}\n```"
                )

            # Uncommitted changes summary
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                changes = result.stdout.strip()
                if changes:
                    lines = changes.split("\n")
                    parts.append(f"\n**Uncommitted changes**: {len(lines)} files")
                else:
                    parts.append("\n**Working tree**: clean")

        except subprocess.TimeoutExpired:
            sys.stderr.write("context_loader: Git command timed out\n")
        except Exception as e:
            sys.stderr.write(f"context_loader: Git error: {e}\n")

        return "\n".join(parts) if len(parts) > 1 else ""

    def _load_project_structure(self) -> str:
        """Load project directory structure summary."""
        parts = ["## Project Structure\n"]

        cwd_path = Path(self.cwd)

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
                    parts.append(
                        f"\n**Active spec projects**: {', '.join(projects[:5])}"
                    )
            except Exception as e:
                sys.stderr.write(
                    f"context_loader: Error listing active projects: {e}\n"
                )

        return "\n".join(parts) if len(parts) > 1 else ""


def run(cwd: str, config: dict[str, Any] | None = None) -> StepResult:
    """Module-level run function for hook integration.

    Args:
        cwd: Current working directory
        config: Optional step configuration

    Returns:
        StepResult from step execution
    """
    step = ContextLoaderStep(cwd, config)
    return step.run()
