"""Performance benchmarks for hook-based memory system.

Tests verify that hooks meet their performance targets:
- PostToolUse: <50ms per tool execution
- SessionStart: <500ms total
- TriggerMemory: <200ms total

Run with: uv run pytest tests/test_performance_benchmarks.py -v
"""

import io
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks" / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Benchmark Fixtures
# =============================================================================


@pytest.fixture
def benchmark_iterations():
    """Number of iterations for benchmark tests."""
    return 100


@pytest.fixture
def mock_memory_results():
    """Create mock memory results for injection tests."""
    results = []
    for i in range(10):
        mock_memory = MagicMock()
        mock_memory.namespace = "decisions"
        mock_memory.summary = f"Test decision {i}"
        mock_memory.timestamp = datetime.now(UTC)
        mock_memory.content = f"Decision content for item {i}" * 10

        mock_result = MagicMock()
        mock_result.memory = mock_memory
        results.append(mock_result)
    return results


# =============================================================================
# PostToolUse Performance Benchmarks
# =============================================================================


class TestPostToolUsePerformance:
    """Performance benchmarks for PostToolUse hook components."""

    def test_learning_detector_speed(self, benchmark_iterations):
        """Benchmark learning detector - target <5ms per detection."""
        from learnings import LearningDetector

        detector = LearningDetector()

        # Sample responses of varying complexity
        responses = [
            {"exit_code": 0, "stdout": "Success", "stderr": ""},
            {"exit_code": 1, "stderr": "Error: command not found\n", "stdout": ""},
            {
                "exit_code": 1,
                "stderr": "Warning: deprecated\nError: failed\n",
                "stdout": "",
            },
            {"exit_code": 0, "stdout": "Line " * 100, "stderr": ""},
        ]

        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            for response in responses:
                detector.detect("Bash", response)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / (benchmark_iterations * len(responses))) * 1000
        print(f"\nLearningDetector avg: {avg_ms:.2f}ms per detection")

        assert avg_ms < 5, f"Detection took {avg_ms:.2f}ms, target <5ms"

    def test_deduplicator_speed(self, benchmark_iterations):
        """Benchmark deduplicator - target <1ms per check."""
        from learnings import SessionDeduplicator

        deduplicator = SessionDeduplicator(max_size=1000)

        start = time.perf_counter()
        for i in range(benchmark_iterations):
            # Mix of new and duplicate checks
            deduplicator.check_learning(
                tool_name="Bash",
                exit_code=1,
                output_excerpt=f"Error message variant {i % 10}",
            )
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / benchmark_iterations) * 1000
        print(f"\nSessionDeduplicator avg: {avg_ms:.3f}ms per check")

        assert avg_ms < 1, f"Dedup check took {avg_ms:.3f}ms, target <1ms"

    def test_extractor_speed(self, benchmark_iterations):
        """Benchmark full extraction pipeline - target <20ms."""
        from learnings import LearningDetector, SessionDeduplicator, extract_learning

        detector = LearningDetector(threshold=0.5)
        deduplicator = SessionDeduplicator(max_size=100)

        response = {
            "exit_code": 1,
            "stderr": "Error: something went wrong\nTraceback:\n  File line 1\n" * 5,
            "stdout": "",
        }

        start = time.perf_counter()
        for i in range(benchmark_iterations):
            # Reset deduplicator periodically to allow captures
            if i % 10 == 0:
                deduplicator = SessionDeduplicator(max_size=100)

            extract_learning(
                tool_name="Bash",
                response=response,
                detector=detector,
                deduplicator=deduplicator,
            )
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / benchmark_iterations) * 1000
        print(f"\nextract_learning avg: {avg_ms:.2f}ms per extraction")

        assert avg_ms < 20, f"Extraction took {avg_ms:.2f}ms, target <20ms"

    def test_post_tool_hook_speed(self, tmp_path, monkeypatch):
        """Benchmark full PostToolUse hook - target <50ms."""
        import post_tool_capture

        # Setup mock input
        input_data = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "npm test"},
            "tool_response": {
                "exit_code": 1,
                "stderr": "Error: test failed\n",
                "stdout": "Running tests...\n",
            },
            "cwd": str(tmp_path),
            "session_id": "bench-session",
        }

        times = []
        for _ in range(10):
            monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

            start = time.perf_counter()
            post_tool_capture.main()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        max_ms = max(times)
        print(f"\nPostToolUse hook avg: {avg_ms:.2f}ms, max: {max_ms:.2f}ms")

        assert avg_ms < 50, f"Hook avg {avg_ms:.2f}ms, target <50ms"


# =============================================================================
# SessionStart Performance Benchmarks
# =============================================================================


class TestSessionStartPerformance:
    """Performance benchmarks for SessionStart hook."""

    def test_spec_detector_speed(self, tmp_path, benchmark_iterations):
        """Benchmark spec detection - target <10ms."""
        from spec_detector import detect_active_spec

        # Create spec structure
        spec_dir = tmp_path / "docs" / "spec" / "active" / "2025-12-17-test-feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "README.md").write_text("# Test Feature\n")
        (spec_dir / "REQUIREMENTS.md").write_text("# Requirements\n")
        (spec_dir / "ARCHITECTURE.md").write_text("# Architecture\n")

        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            detect_active_spec(tmp_path)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / benchmark_iterations) * 1000
        print(f"\nSpec detector avg: {avg_ms:.2f}ms per detection")

        assert avg_ms < 10, f"Spec detection took {avg_ms:.2f}ms, target <10ms"

    def test_memory_injector_format_speed(
        self, mock_memory_results, benchmark_iterations
    ):
        """Benchmark memory formatting - target <10ms for 10 memories."""
        from memory_injector import MemoryInjector

        injector = MemoryInjector()

        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            injector.format_for_context(mock_memory_results)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / benchmark_iterations) * 1000
        print(f"\nMemory formatting avg: {avg_ms:.2f}ms for 10 memories")

        assert avg_ms < 10, f"Formatting took {avg_ms:.2f}ms, target <10ms"

    def test_session_start_hook_speed(self, tmp_path, monkeypatch, capsys):
        """Benchmark full SessionStart hook - target <500ms."""
        import session_start

        # Setup CS project
        (tmp_path / "docs" / "spec").mkdir(parents=True)
        (tmp_path / "CLAUDE.md").write_text("# Test Project\n")

        input_data = {
            "hook_event_name": "SessionStart",
            "cwd": str(tmp_path),
            "session_id": "bench-session",
        }

        # Mock memory injection to avoid external dependencies
        with patch.object(session_start, "MEMORY_INJECTION_AVAILABLE", False):
            times = []
            for _ in range(10):
                monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))
                capsys.readouterr()  # Clear previous output

                start = time.perf_counter()
                session_start.main()
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

        avg_ms = sum(times) / len(times)
        max_ms = max(times)
        print(f"\nSessionStart hook avg: {avg_ms:.2f}ms, max: {max_ms:.2f}ms")

        assert avg_ms < 500, f"Hook avg {avg_ms:.2f}ms, target <500ms"


# =============================================================================
# TriggerMemory Performance Benchmarks
# =============================================================================


class TestTriggerMemoryPerformance:
    """Performance benchmarks for trigger-based memory injection."""

    def test_trigger_detector_speed(self, benchmark_iterations):
        """Benchmark trigger detection - target <1ms."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()

        prompts = [
            "Why did we choose this approach?",
            "Write a function to sort an array",
            "What was the decision about the API?",
            "Fix the bug in the login page",
            "Remind me what we discussed",
            "Create a new component",
        ]

        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            for prompt in prompts:
                detector.should_inject(prompt)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / (benchmark_iterations * len(prompts))) * 1000
        print(f"\nTriggerDetector avg: {avg_ms:.3f}ms per check")

        assert avg_ms < 1, f"Detection took {avg_ms:.3f}ms, target <1ms"

    def test_trigger_injector_format_speed(
        self, mock_memory_results, benchmark_iterations
    ):
        """Benchmark trigger formatting - target <10ms."""
        from trigger_detector import TriggerMemoryInjector

        injector = TriggerMemoryInjector()

        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            injector.format_for_additional_context(mock_memory_results)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / benchmark_iterations) * 1000
        print(f"\nTrigger formatting avg: {avg_ms:.2f}ms for 10 memories")

        assert avg_ms < 10, f"Formatting took {avg_ms:.2f}ms, target <10ms"

    def test_trigger_memory_hook_no_trigger(self, tmp_path, monkeypatch, capsys):
        """Benchmark trigger hook fast path (no trigger) - target <50ms."""
        import trigger_memory

        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Write a function to sort an array",
            "cwd": str(tmp_path),
            "session_id": "bench-session",
        }

        times = []
        for _ in range(10):
            monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))
            capsys.readouterr()

            start = time.perf_counter()
            trigger_memory.main()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        max_ms = max(times)
        print(f"\nTriggerMemory (no trigger) avg: {avg_ms:.2f}ms, max: {max_ms:.2f}ms")

        assert avg_ms < 50, f"Hook avg {avg_ms:.2f}ms, target <50ms"

    def test_trigger_memory_hook_with_trigger(self, tmp_path, monkeypatch, capsys):
        """Benchmark trigger hook with trigger phrase - target <200ms."""
        import trigger_memory

        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Why did we choose this approach?",
            "cwd": str(tmp_path),
            "session_id": "bench-session",
        }

        # Mock the injector to simulate memory retrieval
        mock_injector = MagicMock()
        mock_injector.process_prompt.return_value = []  # No memories
        mock_injector.format_for_additional_context.return_value = ""

        with patch("trigger_memory.TriggerMemoryInjector", return_value=mock_injector):
            times = []
            for _ in range(10):
                monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))
                capsys.readouterr()

                start = time.perf_counter()
                trigger_memory.main()
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

        avg_ms = sum(times) / len(times)
        max_ms = max(times)
        print(
            f"\nTriggerMemory (with trigger) avg: {avg_ms:.2f}ms, max: {max_ms:.2f}ms"
        )

        assert avg_ms < 200, f"Hook avg {avg_ms:.2f}ms, target <200ms"


# =============================================================================
# Memory Operations Performance
# =============================================================================


class TestMemoryOperationsPerformance:
    """Performance benchmarks for memory system operations."""

    def test_filter_pipeline_speed(self, benchmark_iterations):
        """Benchmark secret filter pipeline - target <5ms."""
        from filters.pipeline import filter_pipeline

        # Sample text with potential secrets
        text = """
        Running deployment...
        AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
        Secret key configured
        Connection to postgres://user:pass@localhost/db
        Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
        Deployment complete.
        """

        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            filter_pipeline(text)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / benchmark_iterations) * 1000
        print(f"\nFilter pipeline avg: {avg_ms:.2f}ms per filter")

        assert avg_ms < 5, f"Filtering took {avg_ms:.2f}ms, target <5ms"

    def test_config_loader_speed(self, benchmark_iterations, tmp_path, monkeypatch):
        """Benchmark config loading - target <10ms."""
        from config_loader import (
            get_memory_injection_config,
            is_memory_injection_enabled,
            reset_config_cache,
        )

        # Create config file
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "sessionStart": {
                            "memoryInjection": {
                                "enabled": True,
                                "limit": 10,
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config_file)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            reset_config_cache()  # Force fresh load
            is_memory_injection_enabled()
            get_memory_injection_config()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / benchmark_iterations) * 1000
        print(f"\nConfig loading avg: {avg_ms:.2f}ms per load")

        assert avg_ms < 10, f"Config load took {avg_ms:.2f}ms, target <10ms"


# =============================================================================
# Summary Report
# =============================================================================


class TestPerformanceSummary:
    """Generate performance summary report."""

    def test_generate_summary_report(
        self, benchmark_iterations, mock_memory_results, tmp_path, monkeypatch, capsys
    ):
        """Generate summary of all performance metrics."""
        results = {}

        # Learning Detector
        from learnings import LearningDetector

        detector = LearningDetector()
        response = {"exit_code": 1, "stderr": "Error\n", "stdout": ""}
        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            detector.detect("Bash", response)
        results["LearningDetector"] = (
            (time.perf_counter() - start) / benchmark_iterations
        ) * 1000

        # Trigger Detector
        from trigger_detector import TriggerDetector

        t_detector = TriggerDetector()
        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            t_detector.should_inject("Why did we choose this?")
        results["TriggerDetector"] = (
            (time.perf_counter() - start) / benchmark_iterations
        ) * 1000

        # Memory Injector Formatting
        from memory_injector import MemoryInjector

        injector = MemoryInjector()
        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            injector.format_for_context(mock_memory_results)
        results["MemoryInjector.format"] = (
            (time.perf_counter() - start) / benchmark_iterations
        ) * 1000

        # Filter Pipeline
        from filters.pipeline import filter_pipeline

        text = "Error: secret AKIAIOSFODNN7EXAMPLE found\n" * 10
        start = time.perf_counter()
        for _ in range(benchmark_iterations):
            filter_pipeline(text)
        results["FilterPipeline"] = (
            (time.perf_counter() - start) / benchmark_iterations
        ) * 1000

        # Print summary
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 60)
        print(f"{'Component':<30} {'Avg (ms)':<15} {'Target (ms)':<15}")
        print("-" * 60)

        targets = {
            "LearningDetector": 5.0,
            "TriggerDetector": 1.0,
            "MemoryInjector.format": 10.0,
            "FilterPipeline": 5.0,
        }

        all_passed = True
        for component, avg_ms in results.items():
            target = targets.get(component, 10.0)
            status = "✓" if avg_ms < target else "✗"
            print(f"{component:<30} {avg_ms:<15.3f} {target:<15.1f} {status}")
            if avg_ms >= target:
                all_passed = False

        print("=" * 60)
        print(f"Overall: {'PASS' if all_passed else 'FAIL'}")
        print("=" * 60)

        assert all_passed, "Some benchmarks exceeded targets"
