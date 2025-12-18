"""
Context loader step - loads CLAUDE.md, git state, project structure.

This step is primarily used by the SessionStart hook to inject project
context into Claude's memory at session start.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Add plugin root to path for utils import
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent

if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from .base import BaseStep, StepResult

# Import shared context utilities
try:
    from utils.context_utils import (
        load_claude_md,
        load_git_state,
        load_project_structure,
    )

    CONTEXT_UTILS_AVAILABLE = True
except ImportError as e:
    CONTEXT_UTILS_AVAILABLE = False
    sys.stderr.write(f"context_loader: Context utils import error: {e}\n")

LOG_PREFIX = "context_loader"


class ContextLoaderStep(BaseStep):
    """Loads project context for SessionStart hook."""

    name = "context-loader"

    def execute(self) -> StepResult:
        """Execute the context loading step.

        Returns:
            StepResult with loaded context in data["context"]
        """
        if not CONTEXT_UTILS_AVAILABLE:
            return StepResult.fail("Context utilities not available")

        context_parts: list[str] = []
        warnings: list[str] = []

        # Load CLAUDE.md files
        claude_md = load_claude_md(
            self.cwd,
            log_prefix=LOG_PREFIX,
            truncate_indicator="\n...[truncated]...",
        )
        if claude_md:
            context_parts.append(claude_md)

        # Load git state
        git_state = load_git_state(self.cwd, log_prefix=LOG_PREFIX)
        if git_state:
            context_parts.append(git_state)

        # Load project structure
        structure = load_project_structure(self.cwd, log_prefix=LOG_PREFIX)
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
