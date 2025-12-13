"""Tests for analyze_cli module."""

import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

# Add parent directory for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from analyzers.analyze_cli import format_json, format_metrics_table, main
from analyzers.log_analyzer import LogAnalysis


class TestFormatMetricsTable(unittest.TestCase):
    """Tests for format_metrics_table function."""

    def test_basic_metrics(self):
        """Test formatting basic metrics."""
        analysis = LogAnalysis(
            total_entries=10,
            user_inputs=8,
            expanded_prompts=2,
            response_summaries=0,
            session_count=2,
            avg_entries_per_session=5.0,
            total_questions=3,
            clarification_heavy_sessions=0,
            total_filtered_content=0,
            secrets_filtered=0,
            prompt_length_min=10,
            prompt_length_max=100,
            prompt_length_avg=50.0,
        )
        result = format_metrics_table(analysis)

        self.assertIn("Total Entries:", result)
        self.assertIn("10", result)
        self.assertIn("User Inputs:", result)
        self.assertIn("8", result)
        self.assertIn("Sessions:", result)
        self.assertIn("2", result)

    def test_with_duration(self):
        """Test formatting with duration."""
        analysis = LogAnalysis(
            total_entries=5,
            user_inputs=5,
            expanded_prompts=0,
            response_summaries=0,
            session_count=1,
            avg_entries_per_session=5.0,
            total_questions=1,
            clarification_heavy_sessions=0,
            total_filtered_content=0,
            secrets_filtered=0,
            prompt_length_min=10,
            prompt_length_max=100,
            prompt_length_avg=50.0,
            first_entry_time="2025-01-01T10:00:00+00:00",
            last_entry_time="2025-01-01T10:30:00+00:00",
        )
        result = format_metrics_table(analysis)
        self.assertIn("Duration:", result)
        self.assertIn("30", result)

    def test_with_filtered_content(self):
        """Test formatting with filtered content."""
        analysis = LogAnalysis(
            total_entries=5,
            user_inputs=5,
            expanded_prompts=0,
            response_summaries=0,
            session_count=1,
            avg_entries_per_session=5.0,
            total_questions=1,
            clarification_heavy_sessions=0,
            total_filtered_content=3,
            secrets_filtered=2,
            prompt_length_min=10,
            prompt_length_max=100,
            prompt_length_avg=50.0,
        )
        result = format_metrics_table(analysis)
        self.assertIn("Content Filtered:", result)
        self.assertIn("3", result)
        self.assertIn("Secrets:", result)

    def test_with_commands(self):
        """Test formatting with commands used."""
        analysis = LogAnalysis(
            total_entries=5,
            user_inputs=5,
            expanded_prompts=0,
            response_summaries=0,
            session_count=1,
            avg_entries_per_session=5.0,
            total_questions=1,
            clarification_heavy_sessions=0,
            total_filtered_content=0,
            secrets_filtered=0,
            prompt_length_min=10,
            prompt_length_max=100,
            prompt_length_avg=50.0,
            commands_used={"/cs:p": 3, "/cs:s": 1},
        )
        result = format_metrics_table(analysis)
        self.assertIn("Commands Used:", result)
        self.assertIn("/cs:p", result)


class TestFormatJson(unittest.TestCase):
    """Tests for format_json function."""

    def test_json_output(self):
        """Test JSON formatting."""
        analysis = LogAnalysis(
            total_entries=10,
            user_inputs=8,
            expanded_prompts=2,
            response_summaries=0,
            session_count=2,
            avg_entries_per_session=5.0,
            total_questions=3,
            clarification_heavy_sessions=1,
            total_filtered_content=2,
            secrets_filtered=1,
            prompt_length_min=5,
            prompt_length_max=200,
            prompt_length_avg=75.0,
            commands_used={"/cs:p": 2},
            first_entry_time="2025-01-01T10:00:00+00:00",
            last_entry_time="2025-01-01T10:30:00+00:00",
        )
        result = format_json(analysis)
        data = json.loads(result)

        self.assertEqual(data["total_entries"], 10)
        self.assertEqual(data["user_inputs"], 8)
        self.assertEqual(data["session_count"], 2)
        self.assertEqual(data["commands_used"], {"/cs:p": 2})
        self.assertIsNotNone(data["duration_minutes"])


class TestMain(unittest.TestCase):
    """Tests for main CLI function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_nonexistent_directory(self):
        """Test with nonexistent directory."""
        with patch("sys.argv", ["analyze_cli.py", "/nonexistent/path"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                result = main()
                self.assertEqual(result, 1)
                self.assertIn("not found", mock_stderr.getvalue())

    def test_analyzer_not_available(self):
        """Test when analyzer module is not available."""
        with patch("sys.argv", ["analyze_cli.py", self.temp_dir]):
            with patch("analyzers.analyze_cli.ANALYZER_AVAILABLE", False):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    result = main()
                    self.assertEqual(result, 1)
                    self.assertIn("not available", mock_stderr.getvalue())

    def test_empty_log(self):
        """Test with no log file."""
        with patch("sys.argv", ["analyze_cli.py", self.temp_dir]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                result = main()
                self.assertEqual(result, 0)
                self.assertIn("No prompt log", mock_stderr.getvalue())

    def test_json_format(self):
        """Test JSON output format."""
        # Create a log file
        log_path = os.path.join(self.temp_dir, ".prompt-log.json")
        entry = {
            "timestamp": "2025-01-01T10:00:00+00:00",
            "session_id": "test-123",
            "type": "user_input",
            "content": "test prompt",
            "command": None,
            "filter_applied": {
                "secret_count": 0,
                "secret_types": [],
                "was_truncated": False,
            },
            "metadata": {"content_length": 11},
        }
        with open(log_path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        with patch("sys.argv", ["analyze_cli.py", self.temp_dir, "--format", "json"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = main()
                self.assertEqual(result, 0)
                output = mock_stdout.getvalue()
                data = json.loads(output)
                self.assertEqual(data["total_entries"], 1)

    def test_text_format(self):
        """Test text output format."""
        log_path = os.path.join(self.temp_dir, ".prompt-log.json")
        entry = {
            "timestamp": "2025-01-01T10:00:00+00:00",
            "session_id": "test-123",
            "type": "user_input",
            "content": "test prompt",
            "command": None,
            "filter_applied": {
                "secret_count": 0,
                "secret_types": [],
                "was_truncated": False,
            },
            "metadata": {"content_length": 11},
        }
        with open(log_path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        with patch("sys.argv", ["analyze_cli.py", self.temp_dir, "--format", "text"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = main()
                self.assertEqual(result, 0)
                self.assertIn("Total Entries:", mock_stdout.getvalue())

    def test_metrics_only(self):
        """Test metrics-only flag."""
        log_path = os.path.join(self.temp_dir, ".prompt-log.json")
        entry = {
            "timestamp": "2025-01-01T10:00:00+00:00",
            "session_id": "test-123",
            "type": "user_input",
            "content": "test prompt",
            "command": None,
            "filter_applied": {
                "secret_count": 0,
                "secret_types": [],
                "was_truncated": False,
            },
            "metadata": {"content_length": 11},
        }
        with open(log_path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        with patch("sys.argv", ["analyze_cli.py", self.temp_dir, "--metrics-only"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = main()
                self.assertEqual(result, 0)
                self.assertIn("Total Entries:", mock_stdout.getvalue())

    def test_markdown_format(self):
        """Test markdown output format (default)."""
        log_path = os.path.join(self.temp_dir, ".prompt-log.json")
        entry = {
            "timestamp": "2025-01-01T10:00:00+00:00",
            "session_id": "test-123",
            "type": "user_input",
            "content": "test prompt?",
            "command": None,
            "filter_applied": {
                "secret_count": 0,
                "secret_types": [],
                "was_truncated": False,
            },
            "metadata": {"content_length": 12},
        }
        with open(log_path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        with patch("sys.argv", ["analyze_cli.py", self.temp_dir]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = main()
                self.assertEqual(result, 0)
                output = mock_stdout.getvalue()
                # Markdown format includes headers
                self.assertIn("#", output)


if __name__ == "__main__":
    unittest.main()
