"""Shared utility functions for cs-memory.

This module provides common calculations used across multiple modules,
following DRY principles (QUAL-002).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from .config import SECONDS_PER_DAY


def calculate_temporal_decay(
    timestamp: datetime | None,
    half_life_days: float = 30.0,
    min_decay: float | None = None,
) -> float:
    """Calculate temporal decay using exponential decay formula.

    Uses the formula: decay = 2^(-age_days / half_life_days)

    Args:
        timestamp: The timestamp to calculate decay from. If None, returns 0.5.
        half_life_days: Days until value halves. Default is 30 days.
        min_decay: Optional minimum decay value to clamp to.

    Returns:
        Decay factor between 0 and 1 (or min_decay and 1 if min_decay specified).
    """
    if timestamp is None:
        return 0.5

    now = datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    age = now - timestamp
    age_days = age.total_seconds() / SECONDS_PER_DAY

    # Exponential decay: score = 2^(-age/half_life)
    decay = math.pow(2, -age_days / half_life_days)

    if min_decay is not None:
        return max(min_decay, decay)
    return decay


def calculate_age_days(timestamp: datetime | None) -> float:
    """Calculate the age in days from a timestamp.

    Args:
        timestamp: The timestamp to calculate age from. If None, returns 0.0.

    Returns:
        Age in days as a float.
    """
    if timestamp is None:
        return 0.0

    now = datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    age = now - timestamp
    return age.total_seconds() / SECONDS_PER_DAY


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """Parse an ISO 8601 timestamp string to datetime (ARCH-008).

    Handles both 'Z' suffix (Zulu time) and explicit timezone offsets.
    This is the canonical implementation to avoid duplicate timestamp
    parsing logic across modules.

    Args:
        timestamp_str: ISO 8601 timestamp string (e.g., "2025-12-14T10:30:00Z"
                       or "2025-12-14T10:30:00+00:00")

    Returns:
        datetime object with timezone info.

    Raises:
        ValueError: If the timestamp string is not valid ISO 8601 format.

    Examples:
        >>> parse_iso_timestamp("2025-12-14T10:30:00Z")
        datetime.datetime(2025, 12, 14, 10, 30, tzinfo=datetime.timezone.utc)

        >>> parse_iso_timestamp("2025-12-14T10:30:00+00:00")
        datetime.datetime(2025, 12, 14, 10, 30, tzinfo=datetime.timezone.utc)
    """
    # Handle Z suffix (Zulu time / UTC)
    if timestamp_str.endswith("Z"):
        timestamp_str = timestamp_str[:-1] + "+00:00"

    return datetime.fromisoformat(timestamp_str)


def parse_iso_timestamp_safe(timestamp_str: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string safely, returning None on error.

    A safe wrapper around parse_iso_timestamp that catches exceptions
    and returns None instead of raising.

    Args:
        timestamp_str: ISO 8601 timestamp string, or None.

    Returns:
        datetime object with timezone info, or None if parsing fails.
    """
    if not timestamp_str:
        return None

    try:
        return parse_iso_timestamp(timestamp_str)
    except (ValueError, TypeError):
        return None
