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
    sys.stderr.write(f"claude-spec command_detector: Config import error: {e}\n")

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


def read_input() -> dict[str, Any] | None:
    """Read and parse JSON input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"claude-spec command_detector: JSON decode error: {e}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"claude-spec command_detector: Error reading input: {e}\n")
        return None


def write_output(response: dict[str, Any]) -> None:
    """Write JSON response to stdout."""
    try:
        print(json.dumps(response), file=sys.stdout)
    except Exception as e:
        sys.stderr.write(f"claude-spec command_detector: Error writing output: {e}\n")
        print('{"decision": "approve"}', file=sys.stdout)


def pass_through() -> dict[str, Any]:
    """Return a pass-through response that allows the prompt to proceed."""
    return {"decision": "approve"}


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
        sys.stderr.write(f"claude-spec command_detector: Error saving state: {e}\n")


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
            run_step(cwd, step_name, step_config)
        except Exception as e:
            # Fail-open: log error but don't block
            sys.stderr.write(f"claude-spec pre-step {step_name} error: {e}\n")


def run_step(cwd: str, step_name: str, config: dict[str, Any]) -> None:
    """Run a single step module.

    Args:
        cwd: Current working directory
        step_name: Name of the step to run
        config: Step configuration
    """
    # Import step module dynamically
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
                    f"claude-spec pre-step {step_name}: {result.message}\n"
                )
    except ImportError as e:
        sys.stderr.write(f"claude-spec: Could not import step {step_name}: {e}\n")
    except Exception as e:
        # Catch-all for step execution errors (fail-open)
        sys.stderr.write(f"claude-spec: Step {step_name} execution error: {e}\n")


def main() -> None:
    """Main entry point for the command detector hook."""
    # Read input
    input_data = read_input()

    if input_data is None:
        # Malformed input - fail open
        write_output(pass_through())
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
    write_output(pass_through())


if __name__ == "__main__":
    main()
