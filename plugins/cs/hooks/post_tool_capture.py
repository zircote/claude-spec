#!/usr/bin/env python3
"""
PostToolUse Hook for Learning Capture

This hook fires after tool execution (Bash, Read, Write, Edit, WebFetch)
to detect and queue learnable moments for later capture.

Usage:
    Registered as a PostToolUse hook via hooks.json with matcher:
    {"toolName": "^(Bash|Read|Write|Edit|WebFetch)$"}

Input format:
    {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "..."},
        "tool_response": {"stdout": "...", "stderr": "...", "exit_code": 0},
        "session_id": "string",
        "cwd": "string"
    }

Output:
    - Always exits 0 (never blocks tool execution)
    - Queues learnings via CaptureAccumulator for later flush
    - Logs to stderr for debugging

Performance target:
    - Total execution < 100ms
    - Never block user interaction
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Add hooks directory to path for lib imports
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent

if str(SCRIPT_DIR / "lib") not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR / "lib"))
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

# Import components with graceful fallback
try:
    from learnings import LearningDetector, extract_learning

    LEARNINGS_AVAILABLE = True
except ImportError as e:
    LEARNINGS_AVAILABLE = False
    sys.stderr.write(f"post_tool_capture: Learnings import error: {e}\n")

try:
    from memory.capture import is_auto_capture_enabled

    MEMORY_AVAILABLE = True
except ImportError as e:
    MEMORY_AVAILABLE = False
    sys.stderr.write(f"post_tool_capture: Memory import error: {e}\n")

# Import file-based queue
try:
    from file_queue import enqueue_learning

    FILE_QUEUE_AVAILABLE = True
except ImportError as e:
    FILE_QUEUE_AVAILABLE = False
    sys.stderr.write(f"post_tool_capture: File queue import error: {e}\n")

# Environment variable to disable tool capture
TOOL_CAPTURE_ENV = "CS_TOOL_CAPTURE_ENABLED"
CAPTURE_THRESHOLD_ENV = "CS_CAPTURE_THRESHOLD"

# Default capture threshold (0.0-1.0)
DEFAULT_THRESHOLD = 0.6

LOG_PREFIX = "post_tool_capture"


def is_tool_capture_enabled() -> bool:
    """Check if tool capture is enabled via environment variable.

    Also checks if auto-capture is enabled (CS_AUTO_CAPTURE_ENABLED).
    Both must be true (or not set) for capture to proceed.
    """
    # Check tool-specific override first
    tool_env = os.environ.get(TOOL_CAPTURE_ENV, "").lower()
    if tool_env in ("false", "0", "no", "off"):
        return False

    # Check general auto-capture setting
    if MEMORY_AVAILABLE and not is_auto_capture_enabled():
        return False

    return True


def get_capture_threshold() -> float:
    """Get capture threshold from environment or default."""
    try:
        return float(os.environ.get(CAPTURE_THRESHOLD_ENV, DEFAULT_THRESHOLD))
    except ValueError:
        return DEFAULT_THRESHOLD


def read_input() -> dict[str, Any] | None:
    """Read and parse JSON input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"{LOG_PREFIX}: JSON decode error: {e}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"{LOG_PREFIX}: Error reading input: {e}\n")
        return None


def detect_active_spec(cwd: str) -> str | None:
    """Detect the active specification from project structure.

    Looks in docs/spec/active/ for a single active project.
    Returns the slug if found, None otherwise.
    """
    cwd_path = Path(cwd)
    spec_dir = cwd_path / "docs" / "spec" / "active"

    if not spec_dir.is_dir():
        return None

    # Look for subdirectories with README.md
    active_specs = []
    try:
        for entry in spec_dir.iterdir():
            if entry.is_dir() and (entry / "README.md").is_file():
                active_specs.append(entry.name)
    except (PermissionError, OSError) as e:
        sys.stderr.write(f"{LOG_PREFIX}: Error scanning spec dir: {e}\n")
        return None

    # Only return if exactly one active spec
    if len(active_specs) == 1:
        # Extract slug from dirname (format: YYYY-MM-DD-slug)
        dirname = active_specs[0]
        parts = dirname.split("-", 3)
        if len(parts) >= 4:
            return parts[3]  # The slug part
        return dirname

    return None


def queue_learning(learning: Any, spec: str | None, cwd: str) -> bool:
    """Queue a learning for later flush using file-based queue.

    Args:
        learning: ToolLearning object to queue
        spec: Specification slug
        cwd: Working directory for queue file

    Returns:
        True if successfully queued
    """
    if not FILE_QUEUE_AVAILABLE:
        sys.stderr.write(f"{LOG_PREFIX}: File queue not available\n")
        return False

    try:
        # Convert learning to memory args for storage
        memory_args = learning.to_memory_args()

        # Enqueue using file-based queue
        return enqueue_learning(
            cwd=cwd,
            tool_name=learning.tool_name,
            summary=learning.summary,
            content=memory_args.get("insight", ""),
            category=learning.category,
            severity=learning.severity,
            spec=spec,
            tags=memory_args.get("tags", []),
        )

    except Exception as e:
        sys.stderr.write(f"{LOG_PREFIX}: Failed to queue: {e}\n")
        return False


def process_tool_response(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_response: dict[str, Any],
    cwd: str,
) -> None:
    """Process a tool response for potential learning capture.

    Args:
        tool_name: Name of the tool (Bash, Read, etc.)
        tool_input: Tool input parameters
        tool_response: Tool output
        cwd: Working directory
    """
    start_time = time.time()

    # Initialize detector with configured threshold
    threshold = get_capture_threshold()
    detector = LearningDetector(threshold=threshold)

    # Try to extract a learning
    spec = detect_active_spec(cwd)

    # Build context from tool input
    context = ""
    if tool_name == "Bash" and tool_input.get("command"):
        context = f"Running: {tool_input['command'][:200]}"
    elif tool_name == "Read" and tool_input.get("file_path"):
        context = f"Reading: {tool_input['file_path']}"
    elif tool_name == "Write" and tool_input.get("file_path"):
        context = f"Writing: {tool_input['file_path']}"
    elif tool_name == "Edit" and tool_input.get("file_path"):
        context = f"Editing: {tool_input['file_path']}"
    elif tool_name == "WebFetch" and tool_input.get("url"):
        context = f"Fetching: {tool_input['url'][:100]}"

    learning = extract_learning(
        tool_name=tool_name,
        response=tool_response,
        context=context,
        spec=spec,
        detector=detector,
    )

    elapsed = time.time() - start_time

    if learning is not None:
        queued = queue_learning(learning, spec, cwd)
        sys.stderr.write(
            f"{LOG_PREFIX}: Queued learning ({learning.category}, "
            f"score={detector.calculate_score(tool_name, tool_response):.2f}) "
            f"in {elapsed * 1000:.1f}ms [queued={queued}]\n"
        )
    elif elapsed > 0.05:  # Log if detection took >50ms
        sys.stderr.write(
            f"{LOG_PREFIX}: No learning detected in {elapsed * 1000:.1f}ms\n"
        )


def main() -> None:
    """Main entry point for the post tool capture hook."""
    start_time = time.time()

    # Always exit 0 - never block tool execution
    try:
        # Check if capture is enabled
        if not is_tool_capture_enabled():
            sys.stderr.write(f"{LOG_PREFIX}: Tool capture disabled\n")
            return

        # Check if required modules are available
        if not LEARNINGS_AVAILABLE:
            sys.stderr.write(f"{LOG_PREFIX}: Learnings module not available\n")
            return

        if not MEMORY_AVAILABLE:
            sys.stderr.write(f"{LOG_PREFIX}: Memory module not available\n")
            return

        if not FILE_QUEUE_AVAILABLE:
            sys.stderr.write(f"{LOG_PREFIX}: File queue not available\n")
            return

        # Read input
        input_data = read_input()

        if input_data is None:
            return

        # Validate input
        tool_name = input_data.get("tool_name", "")
        tool_response = input_data.get("tool_response", {})
        tool_input = input_data.get("tool_input", {})
        cwd = input_data.get("cwd", "")

        if not tool_name or not cwd:
            sys.stderr.write(f"{LOG_PREFIX}: Missing tool_name or cwd\n")
            return

        # Process the tool response
        process_tool_response(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_response=tool_response,
            cwd=cwd,
        )

    except Exception as e:
        # Log error but never fail
        sys.stderr.write(f"{LOG_PREFIX}: Unexpected error: {e}\n")

    finally:
        elapsed = time.time() - start_time
        if elapsed > 0.1:  # Warn if total time exceeds 100ms
            sys.stderr.write(
                f"{LOG_PREFIX}: WARN: Hook took {elapsed * 1000:.1f}ms (target <100ms)\n"
            )


if __name__ == "__main__":
    main()
