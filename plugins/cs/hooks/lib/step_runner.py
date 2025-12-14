"""
Shared step runner for claude-spec hooks.

This module provides the run_step() function used by both:
- hooks/command_detector.py (pre-steps)
- hooks/post_command.py (post-steps)

Security: Uses a whitelist to prevent arbitrary module loading.
Only modules in STEP_MODULES can be loaded.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Resolve plugin root relative to this file
# This file is at: hooks/lib/step_runner.py
# Plugin root is at: ../../ (two levels up)
PLUGIN_ROOT = Path(__file__).parent.parent.parent

# Map step names to module names (whitelist for security)
STEP_MODULES = {
    "security-review": "security_reviewer",
    "context-loader": "context_loader",
    "generate-retrospective": "retrospective_gen",
    "archive-logs": "log_archiver",
    "cleanup-markers": "marker_cleaner",
}


def run_step(
    cwd: str,
    step_name: str,
    config: dict[str, Any],
    log_prefix: str = "claude-spec",
) -> bool:
    """Run a single step module.

    Security: Only step names in STEP_MODULES whitelist can be loaded.
    This prevents arbitrary module loading attacks.

    Args:
        cwd: Current working directory
        step_name: Name of the step to run (e.g., "security-review")
        config: Step configuration dictionary
        log_prefix: Prefix for log messages

    Returns:
        True if step ran successfully, False otherwise
    """
    steps_dir = PLUGIN_ROOT / "steps"

    # Security: Validate step name is in whitelist
    module_name = STEP_MODULES.get(step_name)
    if not module_name:
        sys.stderr.write(f"{log_prefix}: Unknown step: {step_name}\n")
        return False

    if str(steps_dir) not in sys.path:
        sys.path.insert(0, str(steps_dir))

    try:
        # Import using whitelist-validated module name
        module = __import__(module_name)

        if hasattr(module, "run"):
            result = module.run(cwd, config)
            if result and hasattr(result, "success") and not result.success:
                sys.stderr.write(f"{log_prefix} step {step_name}: {result.message}\n")
                return False
            return True
        else:
            sys.stderr.write(
                f"{log_prefix}: Step module {module_name} has no run function\n"
            )
            return False
    except ImportError as e:
        sys.stderr.write(f"{log_prefix}: Could not import step {step_name}: {e}\n")
        return False
    except Exception as e:
        # Catch-all for step execution errors (fail-open)
        sys.stderr.write(f"{log_prefix}: Step {step_name} execution error: {e}\n")
        return False


def get_step_module_name(step_name: str) -> str | None:
    """Get the module name for a step.

    Args:
        step_name: Name of the step (e.g., "security-review")

    Returns:
        Module name (e.g., "security_reviewer") or None if unknown
    """
    return STEP_MODULES.get(step_name)


def get_available_steps() -> list[str]:
    """Get list of available step names.

    Returns:
        List of step names that can be run
    """
    return list(STEP_MODULES.keys())
