"""
Fallback I/O functions for claude-spec hooks (ARCH-004).

This module provides fallback implementations of I/O functions used when
the shared hook_io module is not available. All hooks should import these
fallbacks to avoid code duplication.

These functions mirror the interface of hook_io.py but with simpler
implementations that don't require any external dependencies.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def fallback_read_input(log_prefix: str = "hook") -> dict[str, Any] | None:
    """Fallback read_input if hook_io not available.

    Args:
        log_prefix: Prefix for error log messages.

    Returns:
        Parsed JSON dictionary, or None on error.
    """
    try:
        return json.load(sys.stdin)
    except Exception as e:
        sys.stderr.write(f"cs-{log_prefix}: Error reading input: {e}\n")
        return None


def fallback_write_output(
    response: dict[str, Any],
    log_prefix: str = "hook",
    fallback_response: str = '{"decision": "approve"}',
) -> None:
    """Fallback write_output if hook_io not available.

    Args:
        response: Dictionary to serialize as JSON.
        log_prefix: Prefix for error log messages.
        fallback_response: Response string to use if serialization fails.
    """
    try:
        print(json.dumps(response), file=sys.stdout)
    except Exception as e:
        sys.stderr.write(f"cs-{log_prefix}: Error writing output: {e}\n")
        print(fallback_response, file=sys.stdout)


def fallback_pass_through() -> dict[str, Any]:
    """Fallback pass_through if hook_io not available.

    Returns:
        Dictionary with decision: approve.
    """
    return {"decision": "approve"}


def fallback_stop_response() -> dict[str, Any]:
    """Fallback stop_response if hook_io not available.

    Returns:
        Dictionary with continue: False.
    """
    return {"continue": False}
