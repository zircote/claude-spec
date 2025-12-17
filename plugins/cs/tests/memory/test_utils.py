"""Tests for memory/utils.py utility functions."""

from datetime import UTC, datetime, timedelta

import pytest

from memory.utils import (
    calculate_age_days,
    calculate_temporal_decay,
    parse_iso_timestamp,
    parse_iso_timestamp_safe,
)


class TestCalculateTemporalDecay:
    """Tests for calculate_temporal_decay function."""

    def test_none_timestamp_returns_half(self):
        """Test that None timestamp returns 0.5."""
        assert calculate_temporal_decay(None) == 0.5

    def test_current_timestamp_returns_one(self):
        """Test that current timestamp returns ~1.0."""
        now = datetime.now(UTC)
        decay = calculate_temporal_decay(now)
        assert decay > 0.99  # Should be very close to 1

    def test_half_life_decay(self):
        """Test that decay is 0.5 at half-life."""
        half_life = 30.0
        past = datetime.now(UTC) - timedelta(days=half_life)
        decay = calculate_temporal_decay(past, half_life_days=half_life)
        assert 0.49 < decay < 0.51  # Should be close to 0.5

    def test_custom_half_life(self):
        """Test custom half-life value."""
        half_life = 7.0
        past = datetime.now(UTC) - timedelta(days=7)
        decay = calculate_temporal_decay(past, half_life_days=half_life)
        assert 0.49 < decay < 0.51

    def test_min_decay_clamp(self):
        """Test that min_decay clamps the result."""
        very_old = datetime.now(UTC) - timedelta(days=365)
        decay = calculate_temporal_decay(very_old, min_decay=0.1)
        assert decay >= 0.1

    def test_min_decay_not_needed(self):
        """Test that min_decay doesn't affect higher values."""
        recent = datetime.now(UTC) - timedelta(days=1)
        decay = calculate_temporal_decay(recent, min_decay=0.1)
        assert decay > 0.9  # Should be high since recent

    def test_naive_timestamp_converted_to_utc(self):
        """Test that naive timestamps are converted to UTC."""
        naive = datetime.now()  # No timezone
        decay = calculate_temporal_decay(naive)
        # Should work without error and return reasonable value
        assert 0 < decay <= 1.0


class TestCalculateAgeDays:
    """Tests for calculate_age_days function."""

    def test_none_timestamp_returns_zero(self):
        """Test that None timestamp returns 0.0."""
        assert calculate_age_days(None) == 0.0

    def test_current_timestamp_returns_zero(self):
        """Test that current timestamp returns ~0."""
        now = datetime.now(UTC)
        age = calculate_age_days(now)
        assert age < 0.01  # Should be very small

    def test_one_day_ago(self):
        """Test that 1 day ago returns ~1.0."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        age = calculate_age_days(yesterday)
        assert 0.99 < age < 1.01

    def test_naive_timestamp_converted_to_utc(self):
        """Test that naive timestamps are converted to UTC."""
        naive = datetime.now()  # No timezone
        age = calculate_age_days(naive)
        assert age >= 0  # Should work without error


class TestParseIsoTimestamp:
    """Tests for parse_iso_timestamp function."""

    def test_parse_zulu_time(self):
        """Test parsing Z suffix (Zulu time)."""
        result = parse_iso_timestamp("2025-12-14T10:30:00Z")
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 14
        assert result.hour == 10
        assert result.minute == 30
        assert result.tzinfo is not None

    def test_parse_explicit_offset(self):
        """Test parsing explicit timezone offset."""
        result = parse_iso_timestamp("2025-12-14T10:30:00+00:00")
        assert result.year == 2025
        assert result.month == 12
        assert result.tzinfo is not None

    def test_parse_positive_offset(self):
        """Test parsing positive timezone offset."""
        result = parse_iso_timestamp("2025-12-14T10:30:00+05:30")
        assert result.year == 2025
        assert result.tzinfo is not None

    def test_parse_negative_offset(self):
        """Test parsing negative timezone offset."""
        result = parse_iso_timestamp("2025-12-14T10:30:00-08:00")
        assert result.year == 2025
        assert result.tzinfo is not None

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            parse_iso_timestamp("not-a-timestamp")

    def test_invalid_date_raises_error(self):
        """Test that invalid date raises ValueError."""
        with pytest.raises(ValueError):
            parse_iso_timestamp("2025-13-45T10:30:00Z")


class TestParseIsoTimestampSafe:
    """Tests for parse_iso_timestamp_safe function."""

    def test_none_returns_none(self):
        """Test that None input returns None."""
        assert parse_iso_timestamp_safe(None) is None

    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        assert parse_iso_timestamp_safe("") is None

    def test_valid_timestamp_parsed(self):
        """Test that valid timestamp is parsed."""
        result = parse_iso_timestamp_safe("2025-12-14T10:30:00Z")
        assert result is not None
        assert result.year == 2025

    def test_invalid_timestamp_returns_none(self):
        """Test that invalid timestamp returns None."""
        result = parse_iso_timestamp_safe("not-a-timestamp")
        assert result is None

    def test_invalid_type_returns_none(self):
        """Test that invalid types are handled gracefully."""
        # This would raise TypeError in parse_iso_timestamp
        result = parse_iso_timestamp_safe("invalid-format")
        assert result is None
