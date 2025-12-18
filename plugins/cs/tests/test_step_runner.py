"""Tests for step_runner module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add hooks/lib to path for imports
SCRIPT_DIR = Path(__file__).parent.parent / "hooks" / "lib"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from step_runner import (
    STEP_MODULES,
    get_available_steps,
    get_step_module_name,
    run_step,
)


class TestRunStep:
    """Tests for run_step function."""

    def test_unknown_step_returns_false(self, capsys):
        """Should return False for unknown step names."""
        result = run_step("/tmp", "nonexistent-step", {})

        assert result is False
        captured = capsys.readouterr()
        assert "Unknown step" in captured.err

    def test_missing_module_returns_false(self, capsys, monkeypatch):
        """Should return False when module import fails."""
        # Add a fake step to the whitelist for testing
        monkeypatch.setitem(STEP_MODULES, "test-step", "nonexistent_module")

        result = run_step("/tmp", "test-step", {})

        assert result is False
        captured = capsys.readouterr()
        assert "Could not import" in captured.err

    def test_module_without_run_returns_false(self, capsys, monkeypatch):
        """Should return False when module has no run function."""
        # Create a mock module without run
        mock_module = MagicMock(spec=[])
        del mock_module.run

        monkeypatch.setitem(STEP_MODULES, "test-step", "test_module")

        with patch.dict(sys.modules, {"test_module": mock_module}):
            with patch("builtins.__import__", return_value=mock_module):
                result = run_step("/tmp", "test-step", {})

        assert result is False
        captured = capsys.readouterr()
        assert "has no run function" in captured.err

    def test_successful_step_returns_true(self, monkeypatch):
        """Should return True when step runs successfully."""
        mock_module = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_module.run.return_value = mock_result

        monkeypatch.setitem(STEP_MODULES, "test-step", "test_module")

        with patch.dict(sys.modules, {"test_module": mock_module}):
            with patch("builtins.__import__", return_value=mock_module):
                result = run_step("/tmp", "test-step", {"config": "value"})

        assert result is True
        mock_module.run.assert_called_once()

    def test_failed_step_returns_false(self, capsys, monkeypatch):
        """Should return False when step result indicates failure."""
        mock_module = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "Step failed"
        mock_module.run.return_value = mock_result

        monkeypatch.setitem(STEP_MODULES, "test-step", "test_module")

        with patch.dict(sys.modules, {"test_module": mock_module}):
            with patch("builtins.__import__", return_value=mock_module):
                result = run_step("/tmp", "test-step", {})

        assert result is False
        captured = capsys.readouterr()
        assert "Step failed" in captured.err

    def test_step_exception_returns_false(self, capsys, monkeypatch):
        """Should return False when step raises exception."""
        mock_module = MagicMock()
        mock_module.run.side_effect = RuntimeError("Unexpected error")

        monkeypatch.setitem(STEP_MODULES, "test-step", "test_module")

        with patch.dict(sys.modules, {"test_module": mock_module}):
            with patch("builtins.__import__", return_value=mock_module):
                result = run_step("/tmp", "test-step", {})

        assert result is False
        captured = capsys.readouterr()
        assert "execution error" in captured.err

    def test_keyboard_interrupt_propagates(self, monkeypatch):
        """Should re-raise KeyboardInterrupt."""
        mock_module = MagicMock()
        mock_module.run.side_effect = KeyboardInterrupt()

        monkeypatch.setitem(STEP_MODULES, "test-step", "test_module")

        with patch.dict(sys.modules, {"test_module": mock_module}):
            with patch("builtins.__import__", return_value=mock_module):
                with pytest.raises(KeyboardInterrupt):
                    run_step("/tmp", "test-step", {})

    def test_system_exit_propagates(self, monkeypatch):
        """Should re-raise SystemExit."""
        mock_module = MagicMock()
        mock_module.run.side_effect = SystemExit(1)

        monkeypatch.setitem(STEP_MODULES, "test-step", "test_module")

        with patch.dict(sys.modules, {"test_module": mock_module}):
            with patch("builtins.__import__", return_value=mock_module):
                with pytest.raises(SystemExit):
                    run_step("/tmp", "test-step", {})

    def test_custom_log_prefix(self, capsys):
        """Should use custom log prefix."""
        result = run_step("/tmp", "unknown", {}, log_prefix="my-prefix")

        assert result is False
        captured = capsys.readouterr()
        assert "my-prefix" in captured.err


class TestGetStepModuleName:
    """Tests for get_step_module_name function."""

    def test_returns_module_name_for_known_step(self):
        """Should return module name for known step."""
        result = get_step_module_name("security-review")
        assert result == "security_reviewer"

    def test_returns_none_for_unknown_step(self):
        """Should return None for unknown step."""
        result = get_step_module_name("nonexistent")
        assert result is None

    def test_all_step_modules_have_mappings(self):
        """All steps in STEP_MODULES should have valid module names."""
        for step_name, module_name in STEP_MODULES.items():
            result = get_step_module_name(step_name)
            assert result == module_name
            assert isinstance(result, str)


class TestGetAvailableSteps:
    """Tests for get_available_steps function."""

    def test_returns_list_of_step_names(self):
        """Should return a list of step names."""
        result = get_available_steps()

        assert isinstance(result, list)
        assert len(result) > 0
        assert "security-review" in result
        assert "context-loader" in result

    def test_returns_all_known_steps(self):
        """Should return all steps from STEP_MODULES."""
        result = get_available_steps()
        assert set(result) == set(STEP_MODULES.keys())
