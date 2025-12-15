#!/usr/bin/env python3
"""
Command Detector Hook for claude-spec Plugin

This hook intercepts UserPromptSubmit events, detects /cs:* commands,
triggers pre-steps for commands that need them, and stores command
state for post-command processing.

Usage:
    Registered as a UserPromptSubmit hook via hooks.json.
    Receives JSON via stdin, outputs JSON via stdout.

Input format:
    {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "string",
        "session_id": "string",
        "cwd": "string"
    }

Output format:
    {
        "decision": "approve"
    }

This hook NEVER blocks prompts - it always returns approve.
Pre-step output goes to stderr or is stored for post-processing.
"""

from __future__ import annotations

import json
import re
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
    sys.stderr.write(f"cs-command_detector: Config import error: {e}\n")

# Import shared I/O and step runner
try:
    from hook_io import pass_through, read_input, write_output
    from step_runner import run_step

    IO_AVAILABLE = True
except ImportError as e:
    IO_AVAILABLE = False
    sys.stderr.write(f"cs-command_detector: Lib import error: {e}\n")

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

LOG_PREFIX = "command_detector"

# Session state file for passing command info to post-command hook
SESSION_STATE_FILE = ".cs-session-state.json"

# Command patterns to detect
COMMAND_PATTERNS = {
    r"^/cs:p\b": "cs:p",
    r"^/cs:c\b": "cs:c",
    r"^/cs:i\b": "cs:i",
    r"^/cs:s\b": "cs:s",
    r"^/cs:log\b": "cs:log",
    r"^/cs:migrate\b": "cs:migrate",
    r"^/cs:wt:": "cs:wt",
}


def detect_command(prompt: str) -> str | None:
    """Detect /cs:* command in the prompt.

    Args:
        prompt: The user prompt text

    Returns:
        The command name (e.g., "cs:c") if found, None otherwise
    """
    prompt_stripped = prompt.strip()

    for pattern, command in COMMAND_PATTERNS.items():
        if re.match(pattern, prompt_stripped):
            return command

    return None


def save_session_state(cwd: str, state: dict[str, Any]) -> None:
    """Save session state for post-command hook.

    Args:
        cwd: Current working directory
        state: State dictionary to save
    """
    state_file = Path(cwd) / SESSION_STATE_FILE
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"cs-{LOG_PREFIX}: Error saving state: {e}\n")


def run_pre_steps(cwd: str, command: str) -> None:
    """Run pre-steps for a command.

    Args:
        cwd: Current working directory
        command: The detected command
    """
    if not CONFIG_AVAILABLE:
        return

    steps = get_enabled_steps(command, "preSteps")

    for step_config in steps:
        step_name = step_config.get("name", "unknown")
        try:
            if IO_AVAILABLE:
                run_step(cwd, step_name, step_config, log_prefix="cs-pre-step")
            else:
                # Fallback: skip step execution if libs not available
                sys.stderr.write(
                    f"cs-pre-step {step_name}: skipped (libs not available)\n"
                )
        except Exception as e:
            # Fail-open: log error but don't block
            sys.stderr.write(f"cs-pre-step {step_name} error: {e}\n")


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
    """Main entry point for the command detector hook."""
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

    # Extract fields
    prompt = input_data.get("prompt", "")
    cwd = input_data.get("cwd", "")
    session_id = input_data.get("session_id", "")

    # Detect command
    command = detect_command(prompt)

    if command and cwd:
        # Save state for post-command hook
        save_session_state(
            cwd,
            {
                "command": command,
                "session_id": session_id,
                "prompt": prompt[:500],  # Truncate for state file
            },
        )

        # Run pre-steps
        run_pre_steps(cwd, command)

    # Always approve
    _write_output(_pass_through())


if __name__ == "__main__":
    main()
