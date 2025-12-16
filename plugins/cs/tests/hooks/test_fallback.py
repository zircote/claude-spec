"""Tests for hooks/lib/fallback.py fallback I/O functions."""

import io
import json
import os
import sys

# Add parent directories for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_DIR = os.path.dirname(SCRIPT_DIR)
PLUGIN_ROOT = os.path.dirname(TESTS_DIR)
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from hooks.lib.fallback import (
    fallback_pass_through,
    fallback_read_input,
    fallback_stop_response,
    fallback_write_output,
)


class TestFallbackReadInput:
    """Tests for fallback_read_input function."""

    def test_valid_json_input(self, monkeypatch):
        """Test reading valid JSON from stdin."""
        input_data = {"hook_event_name": "Test", "prompt": "hello"}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        result = fallback_read_input()
        assert result == input_data

    def test_invalid_json_returns_none(self, monkeypatch, capsys):
        """Test that invalid JSON returns None and logs error."""
        monkeypatch.setattr("sys.stdin", io.StringIO("not valid json"))

        result = fallback_read_input()
        assert result is None

        captured = capsys.readouterr()
        assert "Error reading input" in captured.err

    def test_empty_input_returns_none(self, monkeypatch, capsys):
        """Test that empty input returns None."""
        monkeypatch.setattr("sys.stdin", io.StringIO(""))

        result = fallback_read_input()
        assert result is None

    def test_custom_log_prefix(self, monkeypatch, capsys):
        """Test that custom log prefix is used in error messages."""
        monkeypatch.setattr("sys.stdin", io.StringIO("invalid"))

        result = fallback_read_input(log_prefix="custom-hook")
        assert result is None

        captured = capsys.readouterr()
        assert "cs-custom-hook:" in captured.err


class TestFallbackWriteOutput:
    """Tests for fallback_write_output function."""

    def test_valid_output(self, capsys):
        """Test writing valid JSON output."""
        response = {"decision": "approve", "data": "test"}
        fallback_write_output(response)

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output == response

    def test_non_serializable_uses_fallback(self, capsys):
        """Test that non-serializable data uses fallback response."""

        # Create an object that can't be JSON serialized
        class NonSerializable:
            pass

        response = {"data": NonSerializable()}
        fallback_write_output(response)

        captured = capsys.readouterr()
        # Should use the fallback response
        assert '"decision": "approve"' in captured.out

    def test_custom_fallback_response(self, capsys):
        """Test custom fallback response is used."""

        class NonSerializable:
            pass

        response = {"data": NonSerializable()}
        fallback_write_output(
            response, fallback_response='{"continue": false, "error": true}'
        )

        captured = capsys.readouterr()
        assert '"continue": false' in captured.out

    def test_custom_log_prefix_on_error(self, capsys):
        """Test custom log prefix in error messages."""

        class NonSerializable:
            pass

        response = {"data": NonSerializable()}
        fallback_write_output(response, log_prefix="my-hook")

        captured = capsys.readouterr()
        assert "cs-my-hook:" in captured.err


class TestFallbackPassThrough:
    """Tests for fallback_pass_through function."""

    def test_returns_approve_decision(self):
        """Test that pass_through returns approve decision."""
        result = fallback_pass_through()
        assert result == {"decision": "approve"}


class TestFallbackStopResponse:
    """Tests for fallback_stop_response function."""

    def test_returns_continue_false(self):
        """Test that stop_response returns continue: false."""
        result = fallback_stop_response()
        assert result == {"continue": False}
