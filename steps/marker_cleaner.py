"""
Marker cleaner step - removes temp files.

This step is a post-step for /c that cleans up temporary files
created during the spec lifecycle.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .base import BaseStep, StepResult


class MarkerCleanerStep(BaseStep):
    """Cleans up marker files as post-step for /c."""

    name = "cleanup-markers"

    # Files to clean up
    CLEANUP_FILES = [
        ".cs-session-state.json",  # Session state from command_detector
    ]

    def execute(self) -> StepResult:
        """Execute the marker cleanup step.

        Returns:
            StepResult with cleanup info in data
        """
        cwd_path = Path(self.cwd)
        cleaned = []
        failed = []

        for filename in self.CLEANUP_FILES:
            file_path = cwd_path / filename

            if file_path.is_file():
                try:
                    file_path.unlink()
                    cleaned.append(filename)
                except Exception as e:
                    sys.stderr.write(
                        f"marker_cleaner: Failed to remove {filename}: {e}\n",
                    )
                    failed.append(filename)

        if failed:
            result = StepResult.fail(
                f"Cleaned {len(cleaned)} files, {len(failed)} failed",
                cleaned=cleaned,
                failed=failed,
            )
        else:
            result = StepResult.ok(
                f"Cleaned {len(cleaned)} marker files",
                cleaned=cleaned,
            )

        # Log what was cleaned for visibility
        if cleaned:
            sys.stderr.write(f"marker_cleaner: Removed: {', '.join(cleaned)}\n")

        return result


def run(cwd: str, config: dict[str, Any] | None = None) -> StepResult:
    """Module-level run function for hook integration.

    Args:
        cwd: Current working directory
        config: Optional step configuration

    Returns:
        StepResult from step execution
    """
    step = MarkerCleanerStep(cwd, config)
    return step.run()
