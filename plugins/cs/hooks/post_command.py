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

# Session state file created by command_detector
SESSION_STATE_FILE = ".cs-session-state.json"


def read_input() -> dict[str, Any] | None:
    """Read and parse JSON input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"claude-spec post_command: JSON decode error: {e}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"claude-spec post_command: Error reading input: {e}\n")
        return None


def write_output(response: dict[str, Any]) -> None:
    """Write JSON response to stdout."""
    try:
        print(json.dumps(response), file=sys.stdout)
    except Exception as e:
        sys.stderr.write(f"claude-spec post_command: Error writing output: {e}\n")
        print('{"continue": false}', file=sys.stdout)


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
        sys.stderr.write(f"claude-spec post_command: Error loading state: {e}\n")
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
        sys.stderr.write(f"claude-spec post_command: Error cleaning state: {e}\n")


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
            run_step(cwd, step_name, step_config)
        except Exception as e:
            # Fail-open: log error but continue
            sys.stderr.write(f"claude-spec post-step {step_name} error: {e}\n")


def run_step(cwd: str, step_name: str, config: dict[str, Any]) -> None:
    """Run a single step module.

    Args:
        cwd: Current working directory
        step_name: Name of the step to run
        config: Step configuration
    """
    steps_dir = PLUGIN_ROOT / "steps"

    # Map step names to module names
    step_modules = {
        "security-review": "security_reviewer",
        "context-loader": "context_loader",
        "generate-retrospective": "retrospective_gen",
        "archive-logs": "log_archiver",
        "cleanup-markers": "marker_cleaner",
    }

    module_name = step_modules.get(step_name)
    if not module_name:
        sys.stderr.write(f"claude-spec: Unknown step: {step_name}\n")
        return

    if str(steps_dir) not in sys.path:
        sys.path.insert(0, str(steps_dir))

    try:
        module = __import__(module_name)
        if hasattr(module, "run"):
            result = module.run(cwd, config)
            if result and hasattr(result, "success") and not result.success:
                sys.stderr.write(
                    f"claude-spec post-step {step_name}: {result.message}\n"
                )
    except ImportError as e:
        sys.stderr.write(f"claude-spec: Could not import step {step_name}: {e}\n")


def main() -> None:
    """Main entry point for the post-command hook."""
    # Read input
    input_data = read_input()

    if input_data is None:
        # Malformed input - exit cleanly
        write_output({"continue": False})
        return

    cwd = input_data.get("cwd", "")

    if not cwd:
        write_output({"continue": False})
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
    write_output({"continue": False})


if __name__ == "__main__":
    main()
