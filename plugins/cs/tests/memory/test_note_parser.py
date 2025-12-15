"""Tests for the note parser module."""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Add memory module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memory.exceptions import ParseError
from memory.note_parser import (
    extract_memory_id,
    format_note,
    parse_memory_id,
    parse_note,
    validate_note,
)


class TestParseNote:
    """Tests for parse_note function."""

    def test_valid_note_parsing(self):
        """Test parsing a valid note with all required fields."""
        content = """---
type: decision
spec: user-auth
timestamp: 2025-12-14T10:30:00Z
summary: Chose RS256 for JWT signing
---

## Context
Need key rotation support.

## Decision
Use asymmetric signing.
"""
        metadata, body = parse_note(content)

        assert metadata["type"] == "decision"
        assert metadata["spec"] == "user-auth"
        assert metadata["summary"] == "Chose RS256 for JWT signing"
        assert isinstance(metadata["timestamp"], datetime)
        assert "## Context" in body
        assert "## Decision" in body

    def test_note_with_tags_as_list(self):
        """Test parsing note with tags as YAML list."""
        content = """---
type: learning
spec: api-design
timestamp: 2025-12-14T10:30:00Z
summary: REST vs GraphQL tradeoffs
tags:
  - api
  - graphql
  - rest
---

Body content.
"""
        metadata, _ = parse_note(content)
        assert metadata["tags"] == ["api", "graphql", "rest"]

    def test_note_with_tags_as_string(self):
        """Test parsing note with tags as comma-separated string."""
        content = """---
type: learning
spec: api-design
timestamp: 2025-12-14T10:30:00Z
summary: REST vs GraphQL tradeoffs
tags: api, graphql, rest
---

Body content.
"""
        metadata, _ = parse_note(content)
        assert metadata["tags"] == ["api", "graphql", "rest"]

    def test_empty_content_raises_error(self):
        """Test that empty content raises ParseError."""
        with pytest.raises(ParseError) as exc_info:
            parse_note("")
        assert "empty" in str(exc_info.value).lower()

    def test_missing_front_matter_raises_error(self):
        """Test that missing front matter raises ParseError."""
        content = "Just some content without front matter."
        with pytest.raises(ParseError) as exc_info:
            parse_note(content)
        assert "front matter" in str(exc_info.value).lower()

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ParseError."""
        content = """---
type: decision
spec: user-auth
---

Missing timestamp and summary.
"""
        with pytest.raises(ParseError) as exc_info:
            parse_note(content)
        assert "missing required" in str(exc_info.value).lower()

    def test_invalid_yaml_raises_error(self):
        """Test that invalid YAML raises ParseError."""
        content = """---
type: decision
spec: [user-auth  # unclosed bracket
---

Body.
"""
        with pytest.raises(ParseError) as exc_info:
            parse_note(content)
        assert "invalid yaml" in str(exc_info.value).lower()

    def test_invalid_timestamp_raises_error(self):
        """Test that invalid timestamp format raises ParseError."""
        content = """---
type: decision
spec: user-auth
timestamp: not-a-date
summary: Test
---

Body.
"""
        with pytest.raises(ParseError) as exc_info:
            parse_note(content)
        assert "timestamp" in str(exc_info.value).lower()


class TestFormatNote:
    """Tests for format_note function."""

    def test_basic_formatting(self):
        """Test basic note formatting."""
        metadata = {
            "type": "decision",
            "spec": "user-auth",
            "timestamp": datetime(2025, 12, 14, 10, 30, 0, tzinfo=UTC),
            "summary": "Test decision",
        }
        body = "## Context\nSome context."

        result = format_note(metadata, body)

        assert result.startswith("---\n")
        assert "type: decision" in result
        assert "spec: user-auth" in result
        assert "summary: Test decision" in result
        assert "## Context" in result

    def test_round_trip(self):
        """Test that format -> parse -> format preserves data."""
        original_metadata = {
            "type": "learning",
            "spec": "api-design",
            "timestamp": datetime(2025, 12, 14, 10, 30, 0, tzinfo=UTC),
            "summary": "API versioning patterns",
            "tags": ["api", "versioning"],
        }
        original_body = "## Insight\nUse URL-based versioning."

        formatted = format_note(original_metadata, original_body)
        parsed_metadata, parsed_body = parse_note(formatted)

        assert parsed_metadata["type"] == original_metadata["type"]
        assert parsed_metadata["spec"] == original_metadata["spec"]
        assert parsed_metadata["summary"] == original_metadata["summary"]
        assert parsed_body.strip() == original_body.strip()

    def test_missing_required_field_raises_error(self):
        """Test that formatting without required fields raises error."""
        metadata = {"type": "decision"}  # Missing spec, timestamp, summary
        with pytest.raises(ParseError):
            format_note(metadata, "Body")

    def test_summary_length_validation(self):
        """Test that long summaries raise error."""
        metadata = {
            "type": "decision",
            "spec": "test",
            "timestamp": datetime.now(UTC),
            "summary": "x" * 150,  # Exceeds 100 char limit
        }
        with pytest.raises(ParseError) as exc_info:
            format_note(metadata, "Body")
        assert "length" in str(exc_info.value).lower()


class TestValidateNote:
    """Tests for validate_note function."""

    def test_valid_note_returns_empty_warnings(self):
        """Test that a fully valid note returns no warnings."""
        content = """---
type: decision
spec: user-auth
timestamp: 2025-12-14T10:30:00Z
summary: A descriptive summary about this decision
tags: [jwt, security]
---

## Context
Full context here.
"""
        warnings = validate_note(content)
        # May have some style warnings but should parse
        assert all("missing" not in w.lower() for w in warnings)

    def test_invalid_note_returns_error_as_warning(self):
        """Test that invalid notes return error as warning."""
        content = "No front matter here."
        warnings = validate_note(content)
        assert len(warnings) > 0
        assert any("front matter" in w.lower() for w in warnings)


class TestMemoryIdFunctions:
    """Tests for memory ID functions."""

    def test_extract_memory_id(self):
        """Test memory ID generation."""
        memory_id = extract_memory_id("decisions", "abc123def")
        assert memory_id == "decisions:abc123def"

    def test_parse_memory_id(self):
        """Test memory ID parsing."""
        namespace, commit_sha = parse_memory_id("decisions:abc123def")
        assert namespace == "decisions"
        assert commit_sha == "abc123def"

    def test_parse_invalid_memory_id_raises_error(self):
        """Test that invalid memory ID raises error."""
        with pytest.raises(ParseError):
            parse_memory_id("invalid-no-colon")

    def test_memory_id_round_trip(self):
        """Test extract -> parse round trip."""
        original_ns = "learnings"
        original_sha = "deadbeef1234"

        memory_id = extract_memory_id(original_ns, original_sha)
        parsed_ns, parsed_sha = parse_memory_id(memory_id)

        assert parsed_ns == original_ns
        assert parsed_sha == original_sha
