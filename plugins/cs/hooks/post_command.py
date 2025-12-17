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

Security Features:
    - Path traversal prevention via validate_cwd()
    - Input size limits via hook_io module
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
    sys.stderr.write(f"cs-post_command: Config import error: {e}\n")

# Import shared I/O and step runner
try:
    from hook_io import read_input, stop_response, write_output
    from step_runner import run_step

    IO_AVAILABLE = True
except ImportError as e:
    IO_AVAILABLE = False
    sys.stderr.write(f"cs-post_command: Lib import error: {e}\n")

# Import fallback functions (ARCH-004)
try:
    from fallback import (
        fallback_read_input,
        fallback_stop_response,
        fallback_write_output,
    )

    FALLBACK_AVAILABLE = True
except ImportError:
    FALLBACK_AVAILABLE = False

LOG_PREFIX = "post_command"

# Session state file created by command_detector
SESSION_STATE_FILE = ".cs-session-state.json"


def validate_cwd(cwd: str) -> Path | None:
    """Validate and resolve the working directory path.

    Security: Prevents path traversal attacks by ensuring the resolved
    path is a valid directory without symlink-based escapes.

    Args:
        cwd: The working directory path to validate

    Returns:
        Resolved Path object if valid, None otherwise
    """
    if not cwd or not cwd.strip():
        return None

    try:
        # Resolve to absolute path, following symlinks
        resolved = Path(cwd).resolve(strict=True)

        # Verify it's a directory
        if not resolved.is_dir():
            sys.stderr.write(f"cs-{LOG_PREFIX}: cwd is not a directory: {cwd}\n")
            return None

        # Security: Reject paths containing null bytes
        if "\x00" in str(resolved):
            sys.stderr.write(f"cs-{LOG_PREFIX}: Invalid null byte in path\n")
            return None

        return resolved

    except (OSError, ValueError) as e:
        sys.stderr.write(f"cs-{LOG_PREFIX}: Invalid cwd path: {e}\n")
        return None


def load_session_state(cwd: str) -> dict[str, Any] | None:
    """Load session state from command_detector.

    Security: Validates cwd to prevent path traversal attacks.

    Args:
        cwd: Current working directory

    Returns:
        State dictionary if found, None otherwise
    """
    # SEC-001: Validate cwd to prevent path traversal
    validated_cwd = validate_cwd(cwd)
    if validated_cwd is None:
        return None

    state_file = validated_cwd / SESSION_STATE_FILE

    # SEC-001: Verify the state file path is still within validated_cwd
    try:
        resolved_state_file = state_file.resolve()
        # Ensure the resolved path is under the validated cwd
        resolved_state_file.relative_to(validated_cwd)
    except (ValueError, OSError) as e:
        sys.stderr.write(f"cs-{LOG_PREFIX}: Path traversal detected: {e}\n")
        return None

    if not resolved_state_file.is_file():
        return None

    try:
        with open(resolved_state_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        sys.stderr.write(f"cs-{LOG_PREFIX}: Error loading state: {e}\n")
        return None


def cleanup_session_state(cwd: str) -> None:
    """Remove session state file.

    Security: Validates cwd to prevent path traversal attacks.

    Args:
        cwd: Current working directory
    """
    # SEC-001: Validate cwd to prevent path traversal
    validated_cwd = validate_cwd(cwd)
    if validated_cwd is None:
        return

    state_file = validated_cwd / SESSION_STATE_FILE

    # SEC-001: Verify the state file path is still within validated_cwd
    try:
        resolved_state_file = state_file.resolve()
        # Ensure the resolved path is under the validated cwd
        resolved_state_file.relative_to(validated_cwd)
    except (ValueError, OSError) as e:
        sys.stderr.write(f"cs-{LOG_PREFIX}: Path traversal detected: {e}\n")
        return

    try:
        if resolved_state_file.is_file():
            resolved_state_file.unlink()
    except Exception as e:
        sys.stderr.write(f"cs-{LOG_PREFIX}: Error cleaning state: {e}\n")


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
                run_step(cwd, step_name, step_config, log_prefix="cs-post-step")
            else:
                # Fallback: skip step execution if libs not available
                sys.stderr.write(
                    f"cs-post-step {step_name}: skipped (libs not available)\n"
                )
        except Exception as e:
            # Fail-open: log error but continue
            sys.stderr.write(f"cs-post-step {step_name} error: {e}\n")


# I/O wrapper functions to avoid lambda expressions (E731)
def _io_read_input() -> dict[str, Any] | None:
    """Read input using hook_io module."""
    return read_input(LOG_PREFIX)


def _fallback_io_read_input() -> dict[str, Any] | None:
    """Read input using fallback module."""
    return fallback_read_input(LOG_PREFIX)


def _fallback_io_write_output(response: dict[str, Any]) -> None:
    """Write output using fallback module."""
    fallback_write_output(response, LOG_PREFIX, '{"continue": false}')


def main() -> None:
    """Main entry point for the post-command hook."""
    # Select I/O functions - prefer shared module, fall back to fallback module
    if IO_AVAILABLE:
        _read_input = _io_read_input
        _write_output = write_output
        _stop_response = stop_response
    elif FALLBACK_AVAILABLE:
        _read_input = _fallback_io_read_input
        _write_output = _fallback_io_write_output
        _stop_response = fallback_stop_response
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
                print('{"continue": false}', file=sys.stdout)

        def _stop_response() -> dict[str, Any]:
            return {"continue": False}

    input_data = _read_input()

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
