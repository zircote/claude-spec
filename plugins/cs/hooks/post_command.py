#!/usr/bin/env python3
"""
Post-Command Hook for claude-spec Plugin

This hook fires on Claude Code session Stop and executes post-steps
for any /cs:* command that was detected during the session.

Usage:
    Registered as a Stop hook via hooks.json.
    Receives JSON via stdin, outputs JSON via stdout.

Input format:
    {
        "hook_event_name": "Stop",
        "session_id": "string",
        "cwd": "string"
    }

Output format:
    {
        "continue": false
    }

Post-steps are executed based on the command stored in session state.
This hook never blocks - errors are logged to stderr.
"""

from __future__ import annotations

import json
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
    from config_loader import get_enabled_steps

    CONFIG_AVAILABLE = True
except ImportError as e:
    CONFIG_AVAILABLE = False
    sys.stderr.write(f"claude-spec post_command: Config import error: {e}\n")

# Import shared I/O and step runner
try:
    from hook_io import read_input, stop_response, write_output
    from step_runner import run_step

    IO_AVAILABLE = True
except ImportError as e:
    IO_AVAILABLE = False
    sys.stderr.write(f"claude-spec post_command: Lib import error: {e}\n")

LOG_PREFIX = "post_command"

# Session state file created by command_detector
SESSION_STATE_FILE = ".cs-session-state.json"


# Fallback I/O functions if shared module not available
def _fallback_read_input() -> dict[str, Any] | None:
    """Fallback read_input if hook_io not available."""
    try:
        return json.load(sys.stdin)
    except Exception as e:
        sys.stderr.write(f"claude-spec {LOG_PREFIX}: Error reading input: {e}\n")
        return None


def _fallback_write_output(response: dict[str, Any]) -> None:
    """Fallback write_output if hook_io not available."""
    try:
        print(json.dumps(response), file=sys.stdout)
    except Exception:
        print('{"continue": false}', file=sys.stdout)


def _fallback_stop_response() -> dict[str, Any]:
    """Fallback stop_response if hook_io not available."""
    return {"continue": False}


def load_session_state(cwd: str) -> dict[str, Any] | None:
    """Load session state from command_detector.

    Args:
        cwd: Current working directory

    Returns:
        State dictionary if found, None otherwise
    """
    state_file = Path(cwd) / SESSION_STATE_FILE
    if not state_file.is_file():
        return None

    try:
        with open(state_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        sys.stderr.write(f"claude-spec {LOG_PREFIX}: Error loading state: {e}\n")
        return None


def cleanup_session_state(cwd: str) -> None:
    """Remove session state file.

    Args:
        cwd: Current working directory
    """
    state_file = Path(cwd) / SESSION_STATE_FILE
    try:
        if state_file.is_file():
            state_file.unlink()
    except Exception as e:
        sys.stderr.write(f"claude-spec {LOG_PREFIX}: Error cleaning state: {e}\n")


def run_post_steps(cwd: str, command: str) -> None:
    """Run post-steps for a command.

    Args:
        cwd: Current working directory
        command: The detected command
    """
    if not CONFIG_AVAILABLE:
        return

    steps = get_enabled_steps(command, "postSteps")

    for step_config in steps:
        step_name = step_config.get("name", "unknown")
        try:
            if IO_AVAILABLE:
                run_step(
                    cwd, step_name, step_config, log_prefix="claude-spec post-step"
                )
            else:
                # Fallback: skip step execution if libs not available
                sys.stderr.write(
                    f"claude-spec post-step {step_name}: skipped (libs not available)\n"
                )
        except Exception as e:
            # Fail-open: log error but continue
            sys.stderr.write(f"claude-spec post-step {step_name} error: {e}\n")


def main() -> None:
    """Main entry point for the post-command hook."""
    # Read input using shared I/O or fallback
    if IO_AVAILABLE:
        input_data = read_input(LOG_PREFIX)
        _write_output = write_output
        _stop_response = stop_response
    else:
        input_data = _fallback_read_input()
        _write_output = _fallback_write_output
        _stop_response = _fallback_stop_response

    if input_data is None:
        # Malformed input - exit cleanly
        _write_output(_stop_response())
        return

    cwd = input_data.get("cwd", "")

    if not cwd:
        _write_output(_stop_response())
        return

    # Load session state
    state = load_session_state(cwd)

    if state:
        command = state.get("command")

        if command:
            # Run post-steps for the command
            run_post_steps(cwd, command)

        # Clean up state file
        cleanup_session_state(cwd)

    # Signal completion
    _write_output(_stop_response())


if __name__ == "__main__":
    main()
