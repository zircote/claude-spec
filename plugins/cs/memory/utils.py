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
