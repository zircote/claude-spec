"""
Memory Queue Flusher Step

Post-step that flushes queued learnings from PostToolUse captures to git notes.
Runs as part of the Stop hook lifecycle to persist file-based queue before session end.

This step:
1. Reads the file-based queue (.cs-learning-queue.json) from the project directory
2. Calls CaptureService.capture_learning() for each queued item
3. Clears the queue file after successful flush
4. Reports statistics for logging/display

Configuration (in ~/.claude/worktree-manager.config.json):
    {
        "lifecycle": {
            "commands": {
                "*": {
                    "postSteps": [
                        {"name": "flush-memory-queue", "enabled": true}
                    ]
                }
            }
        }
    }
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Add path for imports
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent
HOOKS_LIB = PLUGIN_ROOT / "hooks" / "lib"

if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
if str(HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(HOOKS_LIB))

from steps.base import BaseStep, StepResult

# Import file-based queue with graceful fallback
try:
    from file_queue import dequeue_all, get_queue_size

    QUEUE_AVAILABLE = True
except ImportError as e:
    QUEUE_AVAILABLE = False
    sys.stderr.write(f"memory_queue_flusher: File queue import error: {e}\n")

# Import capture service with graceful fallback
try:
    from memory.capture import CaptureService

    CAPTURE_AVAILABLE = True
except ImportError:
    CAPTURE_AVAILABLE = False

LOG_PREFIX = "memory_queue_flusher"


class MemoryQueueFlusherStep(BaseStep):
    """Post-step to flush the memory queue to git notes."""

    name = "flush-memory-queue"

    def validate(self) -> bool:
        """Check if queue and capture service are available."""
        if not QUEUE_AVAILABLE:
            sys.stderr.write(f"{LOG_PREFIX}: File queue module not available\n")
            return False

        if not CAPTURE_AVAILABLE:
            sys.stderr.write(f"{LOG_PREFIX}: Capture service not available\n")
            return False

        return True

    def execute(self) -> StepResult:
        """Flush queued learnings to git notes."""
        # Check queue size first
        queue_size = get_queue_size(self.cwd)

        if queue_size == 0:
            return StepResult.ok(
                "No queued learnings to flush",
                flushed=0,
                skipped=0,
            )

        # Dequeue all items (atomically clears the queue)
        items = dequeue_all(self.cwd)

        if not items:
            return StepResult.ok(
                "Queue empty after dequeue",
                flushed=0,
                skipped=0,
            )

        capture_service = CaptureService()

        flushed = 0
        skipped = 0
        errors = []
        warnings_list = []
        by_namespace: dict[str, int] = {}

        for item in items:
            try:
                summary = item.get("summary", "")
                content = item.get("content", "")
                spec = item.get("spec")
                tags = item.get("tags", [])

                if not summary:
                    skipped += 1
                    continue

                # Call capture service to persist
                result = capture_service.capture_learning(
                    spec=spec,
                    summary=summary,
                    insight=content,
                    applicability=None,  # Already in content
                    tags=tags,
                )

                if result.success:
                    flushed += 1
                    by_namespace["learnings"] = by_namespace.get("learnings", 0) + 1
                    sys.stderr.write(
                        f"{LOG_PREFIX}: Flushed learning: {summary[:50]}\n"
                    )
                else:
                    skipped += 1
                    if result.warning:
                        warnings_list.append(result.warning)

            except Exception as e:
                errors.append(str(e))
                sys.stderr.write(f"{LOG_PREFIX}: Error flushing: {e}\n")

        # Build result
        result = StepResult.ok(
            f"Flushed {flushed} learnings ({skipped} skipped, {len(errors)} errors)",
            flushed=flushed,
            skipped=skipped,
            error_count=len(errors),
            by_namespace=by_namespace,
        )

        # Add warnings
        for warning in warnings_list:
            result.add_warning(warning)
        for error in errors[:3]:  # Limit error warnings
            result.add_warning(f"Flush error: {error}")

        return result


def run(cwd: str, config: dict[str, Any] | None = None) -> StepResult:
    """Hook integration entry point.

    Args:
        cwd: Current working directory
        config: Step configuration

    Returns:
        StepResult from flush operation
    """
    step = MemoryQueueFlusherStep(cwd, config)
    return step.run()
