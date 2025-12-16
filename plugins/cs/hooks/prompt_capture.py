#!/usr/bin/env python3
"""
Prompt Capture Hook for claude-spec Plugin

This hook intercepts UserPromptSubmit events when logging is enabled for a
claude-spec project, filters sensitive content, and logs prompts to
.prompt-log.json in the active project directory.

Logging is controlled by:
- Enable: Create .prompt-log-enabled marker file at project root
- Disable: Remove .prompt-log-enabled marker file

Marker and log file are at project root (not in docs/spec/active/) to ensure
the first prompt can be captured before spec directories are created.

When enabled, ALL user input is logged until disabled.

Usage:
    Registered as a UserPromptSubmit hook via hooks.json.
    Receives JSON via stdin, outputs JSON via stdout.

Input format:
    {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "string",
        "session_id": "string",
        "cwd": "string",
        "permission_mode": "string"
    }

Output format:
    {
        "decision": "approve"
    }

This hook NEVER blocks prompts - it always returns approve.
"""

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

# Edge case limits
MAX_PROMPT_LENGTH = 100000  # 100KB max per prompt to prevent memory issues
MAX_LOG_ENTRY_SIZE = 50000  # Truncate content if over 50KB

# Add hooks directory to path for sibling imports
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent

# Add filters directory to path
FILTERS_DIR = PLUGIN_ROOT / "filters"
if str(FILTERS_DIR) not in sys.path:
    sys.path.insert(0, str(FILTERS_DIR))
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
if str(SCRIPT_DIR / "lib") not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR / "lib"))

try:
    from filters.log_entry import LogEntry
    from filters.log_writer import append_to_log
    from filters.pipeline import filter_pipeline

    FILTERS_AVAILABLE = True
except ImportError as e:
    # Filters not available - will pass through without logging
    FILTERS_AVAILABLE = False
    sys.stderr.write(f"cs-prompt_capture: Filter import error: {e}\n")

# Import shared I/O
try:
    from hook_io import pass_through, read_input, write_output

    IO_AVAILABLE = True
except ImportError as e:
    IO_AVAILABLE = False
    sys.stderr.write(f"cs-prompt_capture: Lib import error: {e}\n")

# Import fallback functions (ARCH-004)
try:
    from fallback import (
        fallback_pass_through,
        fallback_read_input,
        fallback_write_output,
    )

    FALLBACK_AVAILABLE = True
except ImportError:
    FALLBACK_AVAILABLE = False

LOG_PREFIX = "prompt_capture"


def find_enabled_project_dir(cwd: str) -> str | None:
    """
    Find the project root if logging is enabled.

    Checks for .prompt-log-enabled marker at project root (cwd).
    The marker and log file are placed at project root to capture
    the first prompt before spec directories are created.

    Args:
        cwd: Current working directory (project root)

    Returns:
        Path to project root (cwd) if logging enabled, None otherwise
    """
    if not cwd:
        return None

    marker_path = os.path.join(cwd, ".prompt-log-enabled")

    if os.path.isfile(marker_path):
        return cwd

    return None


def is_logging_enabled(cwd: str) -> bool:
    """
    Check if prompt logging is enabled for the current project.

    Logging is enabled if a .prompt-log-enabled file exists at project root.

    Args:
        cwd: Current working directory (project root)

    Returns:
        True if logging is enabled, False otherwise
    """
    return find_enabled_project_dir(cwd) is not None


def truncate_content(content: str, max_length: int = MAX_LOG_ENTRY_SIZE) -> str:
    """Truncate content if too long, preserving information about truncation."""
    if len(content) <= max_length:
        return content
    truncate_notice = (
        f"\n...[TRUNCATED: {len(content) - max_length + 100} chars removed]..."
    )
    return content[: max_length - len(truncate_notice)] + truncate_notice


def generate_session_id() -> str:
    """Generate a unique session ID if none provided."""
    return f"hook-{uuid.uuid4().hex[:12]}"


def detect_command(prompt: str) -> str | None:
    """
    Detect /spec: command in the prompt.

    Args:
        prompt: The user prompt text

    Returns:
        The command string (e.g., "/spec:p") if found, None otherwise
    """
    prompt_stripped = prompt.strip()
    if prompt_stripped.startswith("/spec:"):
        parts = prompt_stripped.split(None, 1)
        if parts:
            return parts[0]
    return None


# I/O wrapper functions to avoid lambda expressions (E731)
def _io_read_input() -> dict[str, Any] | None:
    """Read input using hook_io module."""
    return read_input(LOG_PREFIX)


def _fallback_io_read_input() -> dict[str, Any] | None:
    """Read input using fallback module."""
    return fallback_read_input(LOG_PREFIX)


def _fallback_io_write_output(response: dict[str, Any]) -> None:
    """Write output using fallback module."""
    fallback_write_output(response, LOG_PREFIX)


def main() -> None:
    """Main entry point for the prompt capture hook."""
    # Select I/O functions - prefer shared module, fall back to fallback module
    if IO_AVAILABLE:
        _read_input = _io_read_input
        _write_output = write_output
        _pass_through = pass_through
    elif FALLBACK_AVAILABLE:
        _read_input = _fallback_io_read_input
        _write_output = _fallback_io_write_output
        _pass_through = fallback_pass_through
    else:
        # Last resort inline fallbacks
        def _read_input() -> dict[str, Any] | None:
            try:
                return json.load(sys.stdin)
            except Exception as e:
                sys.stderr.write(f"cs-{LOG_PREFIX}: Error reading input: {e}\n")
                return None

        def _write_output(response: dict[str, Any]) -> None:
            try:
                print(json.dumps(response), file=sys.stdout)
            except Exception:
                print('{"decision": "approve"}', file=sys.stdout)

        def _pass_through() -> dict[str, Any]:
            return {"decision": "approve"}

    input_data = _read_input()

    if input_data is None:
        # Malformed input - fail open
        _write_output(_pass_through())
        return

    # Extract fields with defaults
    # Note: Claude Code sends "prompt", not "user_prompt"
    cwd = input_data.get("cwd", "")
    user_prompt = input_data.get("prompt", "") or input_data.get("user_prompt", "")
    session_id = input_data.get("session_id", "") or generate_session_id()

    # Edge case: empty prompt
    if not user_prompt or not user_prompt.strip():
        _write_output(_pass_through())
        return

    # Edge case: extremely long prompt
    if len(user_prompt) > MAX_PROMPT_LENGTH:
        user_prompt = truncate_content(user_prompt, MAX_PROMPT_LENGTH)

    # Check if logging is enabled
    if not is_logging_enabled(cwd):
        _write_output(_pass_through())
        return

    # Get project directory for logging
    project_dir = find_enabled_project_dir(cwd)
    if not project_dir:
        _write_output(_pass_through())
        return

    # Check if filters are available
    if not FILTERS_AVAILABLE:
        _write_output(_pass_through())
        return

    # Detect /spec: command if present
    command = detect_command(user_prompt)

    # Filter the prompt content
    filter_result = filter_pipeline(user_prompt)

    # Truncate filtered content if still too long for log
    log_content = truncate_content(filter_result.filtered_text, MAX_LOG_ENTRY_SIZE)

    # Create and write log entry
    entry = LogEntry.create(
        session_id=session_id,
        entry_type="user_input",
        content=log_content,
        command=command,
        cwd=cwd,
        filter_info=filter_result.to_filter_info(),
    )

    # Attempt to write (failure doesn't block user)
    append_to_log(project_dir, entry)

    # Always approve
    _write_output(_pass_through())


if __name__ == "__main__":
    main()
