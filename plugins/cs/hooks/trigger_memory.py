#!/usr/bin/env python3
"""
UserPromptSubmit Hook for Trigger-Based Memory Injection

This hook fires on user prompt submission and detects trigger phrases
that indicate the user wants to recall previous context or decisions.
When triggered, it injects relevant memories as additionalContext.

Usage:
    Registered as a UserPromptSubmit hook via hooks.json with matcher:
    {"prompt": "."} (matches all prompts)

Input format:
    {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "string",
        "session_id": "string",
        "cwd": "string"
    }

Output format:
    {
        "decision": "approve",
        "additionalContext": "## Relevant Memories\\n..."
    }

Performance target:
    - Total execution < 200ms
    - Never blocks user interaction
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
    from trigger_detector import TriggerMemoryInjector, get_trigger_detector

    TRIGGER_AVAILABLE = True
except ImportError as e:
    TRIGGER_AVAILABLE = False
    sys.stderr.write(f"trigger_memory: Trigger detector import error: {e}\n")

try:
    from spec_detector import detect_active_spec

    SPEC_DETECTOR_AVAILABLE = True
except ImportError as e:
    SPEC_DETECTOR_AVAILABLE = False
    sys.stderr.write(f"trigger_memory: Spec detector import error: {e}\n")

# Environment variable to disable trigger memory injection
TRIGGER_MEMORY_ENV = "CS_TRIGGER_MEMORY_ENABLED"

LOG_PREFIX = "trigger_memory"


def is_trigger_memory_enabled() -> bool:
    """Check if trigger memory injection is enabled."""
    env = os.environ.get(TRIGGER_MEMORY_ENV, "").lower()
    if env in ("false", "0", "no", "off"):
        return False
    return True


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


def write_output(output: dict[str, Any]) -> None:
    """Write JSON output to stdout."""
    print(json.dumps(output))


def process_prompt(prompt: str, cwd: str) -> str | None:
    """
    Process a prompt and return additional context if triggered.

    Args:
        prompt: User's input prompt
        cwd: Current working directory

    Returns:
        Additional context string if triggered, None otherwise
    """
    if not TRIGGER_AVAILABLE:
        return None

    # Check for trigger phrase first (fast path)
    detector = get_trigger_detector()
    if not detector.should_inject(prompt):
        return None

    # Detect active spec
    spec_slug = None
    if SPEC_DETECTOR_AVAILABLE:
        try:
            active_spec = detect_active_spec(cwd)
            if active_spec:
                spec_slug = active_spec.slug
        except Exception as e:
            sys.stderr.write(f"{LOG_PREFIX}: Error detecting spec: {e}\n")

    # Create injector and process
    try:
        injector = TriggerMemoryInjector()
        memories = injector.process_prompt(prompt, spec=spec_slug)

        if memories:
            return injector.format_for_additional_context(memories)

    except Exception as e:
        sys.stderr.write(f"{LOG_PREFIX}: Error processing trigger: {e}\n")

    return None


def main() -> None:
    """Main entry point for the trigger memory hook."""
    start_time = time.time()

    # Default output - always approve
    output: dict[str, Any] = {"decision": "approve"}

    try:
        # Check if trigger memory is enabled
        if not is_trigger_memory_enabled():
            write_output(output)
            return

        # Check if required modules are available
        if not TRIGGER_AVAILABLE:
            sys.stderr.write(f"{LOG_PREFIX}: Trigger module not available\n")
            write_output(output)
            return

        # Read input
        input_data = read_input()

        if input_data is None:
            write_output(output)
            return

        # Validate input
        prompt = input_data.get("prompt", "")
        cwd = input_data.get("cwd", "")

        if not prompt or not cwd:
            write_output(output)
            return

        # Process the prompt
        additional_context = process_prompt(prompt, cwd)

        if additional_context:
            output["additionalContext"] = additional_context
            sys.stderr.write(
                f"{LOG_PREFIX}: Injected memory context "
                f"({len(additional_context)} chars)\n"
            )

    except Exception as e:
        # Log error but never fail
        sys.stderr.write(f"{LOG_PREFIX}: Unexpected error: {e}\n")

    finally:
        elapsed = time.time() - start_time
        if elapsed > 0.2:  # Warn if total time exceeds 200ms
            sys.stderr.write(
                f"{LOG_PREFIX}: WARN: Hook took {elapsed * 1000:.1f}ms (target <200ms)\n"
            )

        write_output(output)


if __name__ == "__main__":
    main()
