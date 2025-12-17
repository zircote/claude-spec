"""
Memory Queue Flusher Step

Post-step that flushes queued learnings from PostToolUse captures to git notes.
Runs as part of the Stop hook lifecycle to persist in-memory queue before session end.

This step:
1. Reads the in-memory queue from the PostToolUse hook
2. Calls CaptureService.capture_learning() for each queued item
3. Generates a summary of what was flushed
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
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from steps.base import BaseStep, StepResult

# Import queue accessor with graceful fallback
try:
    from hooks.post_tool_capture import get_session_queue

    QUEUE_AVAILABLE = True
except ImportError:
    QUEUE_AVAILABLE = False

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
            sys.stderr.write(f"{LOG_PREFIX}: Queue module not available\n")
            return False

        if not CAPTURE_AVAILABLE:
            sys.stderr.write(f"{LOG_PREFIX}: Capture service not available\n")
            return False

        return True

    def execute(self) -> StepResult:
        """Flush queued learnings to git notes."""
        queue = get_session_queue()

        if queue is None or queue.count == 0:
            return StepResult.ok(
                "No queued learnings to flush",
                flushed=0,
                skipped=0,
            )

        capture_service = CaptureService()

        flushed = 0
        skipped = 0
        errors = []
        warnings_list = []

        for capture_result in queue.captures:
            if capture_result.memory is None:
                skipped += 1
                continue

            # Skip already-processed items (in case of retry)
            if not capture_result.memory.id.startswith("pending:"):
                skipped += 1
                continue

            try:
                # Extract learning data from the pending memory
                memory = capture_result.memory

                # Call capture service to persist
                result = capture_service.capture_learning(
                    spec=memory.spec,
                    summary=memory.summary,
                    insight=memory.content,
                    applicability=None,  # Already in content
                    tags=list(memory.tags),
                )

                if result.success:
                    flushed += 1
                    sys.stderr.write(
                        f"{LOG_PREFIX}: Flushed learning: {memory.summary[:50]}\n"
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
            by_namespace=queue.by_namespace,
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
