"""
Shared I/O utilities for claude-spec hooks.

This module provides common input/output functions used by all hooks:
- read_input(): Read JSON from stdin with size limits
- write_output(): Write JSON to stdout
- pass_through(): Return approval response

All hooks use these for consistent error handling and response formatting.

Security features:
- Input size limits to prevent memory exhaustion
- JSON parsing with size validation
"""

from __future__ import annotations

import json
import sys
from typing import Any

# Maximum input size: 1MB
# This prevents memory exhaustion attacks via oversized JSON payloads
MAX_INPUT_SIZE = 1024 * 1024  # 1MB


def read_input(
    log_prefix: str = "hook",
    max_size: int = MAX_INPUT_SIZE,
) -> dict[str, Any] | None:
    """Read and parse JSON input from stdin with size limits.

    Security: Enforces a maximum input size to prevent memory exhaustion
    attacks from oversized JSON payloads.

    Args:
        log_prefix: Prefix for error log messages (e.g., "prompt_capture")
        max_size: Maximum allowed input size in bytes (default 1MB)

    Returns:
        Parsed JSON dictionary, or None on error
    """
    try:
        # Read with size limit to prevent memory exhaustion
        raw_input = sys.stdin.read(max_size + 1)

        # Check if input exceeded size limit
        if len(raw_input) > max_size:
            sys.stderr.write(
                f"claude-spec {log_prefix}: Input exceeds maximum size "
                f"({max_size} bytes), truncating\n"
            )
            raw_input = raw_input[:max_size]

        # Handle empty input
        if not raw_input or not raw_input.strip():
            sys.stderr.write(f"claude-spec {log_prefix}: Empty input received\n")
            return None

        return json.loads(raw_input)

    except json.JSONDecodeError as e:
        sys.stderr.write(f"claude-spec {log_prefix}: JSON decode error: {e}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"claude-spec {log_prefix}: Error reading input: {e}\n")
        return None


def write_output(
    response: dict[str, Any],
    log_prefix: str = "hook",
    fallback_response: str = '{"decision": "approve"}',
) -> None:
    """Write JSON response to stdout.

    Args:
        response: Dictionary to serialize as JSON
        log_prefix: Prefix for error log messages
        fallback_response: Response string to use if serialization fails
    """
    try:
        print(json.dumps(response), file=sys.stdout)
    except Exception as e:
        sys.stderr.write(f"claude-spec {log_prefix}: Error writing output: {e}\n")
        print(fallback_response, file=sys.stdout)


def pass_through() -> dict[str, Any]:
    """Return a pass-through response that allows the prompt to proceed.

    Returns:
        Dictionary with decision: approve
    """
    return {"decision": "approve"}


def stop_response() -> dict[str, Any]:
    """Return a stop response for Stop hooks.

    Returns:
        Dictionary with continue: False
    """
    return {"continue": False}
