"""
Log archiver step - archives .prompt-log.json to completed directory.

This step is a post-step for /c that moves the prompt log from the
project root to the completed spec project directory for archival.
"""

from __future__ import annotations

import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .base import LOG_FILE, BaseStep, StepResult, find_latest_completed_project


class LogArchiverStep(BaseStep):
    """Archives prompt logs as post-step for /c."""

    name = "archive-logs"

    def execute(self) -> StepResult:
        """Execute the log archival step.

        Returns:
            StepResult with archive info in data
        """
        cwd_path = Path(self.cwd)
        log_file = cwd_path / LOG_FILE

        # Check if log file exists
        if not log_file.is_file():
            return StepResult.ok("No prompt log to archive", archived=False)

        # Find the target directory - most recent completed project
        target_dir = find_latest_completed_project(cwd_path, "log_archiver")

        if target_dir is None:
            return StepResult.ok(
                "No completed project directories found",
                archived=False,
            ).add_warning("Log file remains at project root")

        # Generate unique archive filename with timestamp
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        archive_name = f"prompt-log-{timestamp}.json"
        target_path = target_dir / archive_name

        try:
            # Copy the log file (don't move yet - marker_cleaner handles deletion)
            shutil.copy2(log_file, target_path)

            return StepResult.ok(
                f"Archived prompt log to {target_dir.name}/",
                archived=True,
                source=str(log_file),
                destination=str(target_path),
            )

        except Exception as e:
            sys.stderr.write(f"log_archiver: Error archiving log: {e}\n")
            return StepResult.fail(f"Failed to archive log: {e}", archived=False)


def run(cwd: str, config: dict[str, Any] | None = None) -> StepResult:
    """Module-level run function for hook integration.

    Args:
        cwd: Current working directory
        config: Optional step configuration

    Returns:
        StepResult from step execution
    """
    step = LogArchiverStep(cwd, config)
    return step.run()
