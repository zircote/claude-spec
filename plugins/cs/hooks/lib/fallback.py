"""
Fallback I/O functions for claude-spec hooks (ARCH-004).

This module provides fallback implementations of I/O functions used when
the shared hook_io module is not available. All hooks should import these
fallbacks to avoid code duplication.

These functions mirror the interface of hook_io.py but with simpler
implementations that don't require any external dependencies.

Security Features:
    - Input size limits to prevent memory exhaustion (SEC-002)
    - JSON parsing with size validation
"""

from __future__ import annotations

import json
import sys
from typing import Any

# SEC-002: Maximum input size limit to prevent memory exhaustion
# This matches the limit in hook_io.py for consistency
MAX_INPUT_SIZE = 1024 * 1024  # 1MB


def fallback_read_input(
    log_prefix: str = "hook",
    max_size: int = MAX_INPUT_SIZE,
) -> dict[str, Any] | None:
    """Fallback read_input if hook_io not available.

    Security: Enforces a maximum input size to prevent memory exhaustion
    attacks from oversized JSON payloads (SEC-002).

    Args:
        log_prefix: Prefix for error log messages.
        max_size: Maximum allowed input size in bytes (default 1MB).

    Returns:
        Parsed JSON dictionary, or None on error.
    """
    try:
        # SEC-002: Read with size limit to prevent memory exhaustion
        raw_input = sys.stdin.read(max_size + 1)

        # Check if input exceeded size limit
        if len(raw_input) > max_size:
            sys.stderr.write(
                f"cs-{log_prefix}: Input exceeds maximum size "
                f"({max_size} bytes), truncating\n"
            )
            raw_input = raw_input[:max_size]

        # Handle empty input
        if not raw_input or not raw_input.strip():
            sys.stderr.write(f"cs-{log_prefix}: Empty input received\n")
            return None

        return json.loads(raw_input)

    except json.JSONDecodeError as e:
        sys.stderr.write(f"cs-{log_prefix}: JSON decode error: {e}\n")
        return None
    except OSError as e:
        sys.stderr.write(f"cs-{log_prefix}: I/O error reading input: {e}\n")
        return None
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
