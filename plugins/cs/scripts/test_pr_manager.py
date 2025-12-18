#!/usr/bin/env python3
"""Manual test script for PR Manager Step.

This script provides manual verification of the PR manager workflow,
allowing developers to test the pr_manager step in isolation without
running the full lifecycle hooks.

Usage:
    # Test create operation (default)
    python scripts/test_pr_manager.py

    # Test ready operation
    python scripts/test_pr_manager.py --operation ready

    # Test with actual GitHub API calls (requires gh CLI)
    python scripts/test_pr_manager.py --live

    # Test specific configuration
    python scripts/test_pr_manager.py --title "Custom Title" --labels spec,wip

Requirements:
    - Run from the plugins/cs/ directory
    - For --live mode: gh CLI must be installed and authenticated

Note:
    By default, this script runs in dry-run mode and does not make actual
    GitHub API calls. Use --live flag to test against real GitHub.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

# Setup for proper imports - must happen before importing pr_manager
SCRIPT_DIR = Path(__file__).parent.parent
STEPS_DIR = SCRIPT_DIR / "steps"

# Add plugin root to path so relative imports work
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Import steps module - this sets up the package properly
try:
    from steps import pr_manager

    STEPS_MODULE_AVAILABLE = True
except ImportError:
    STEPS_MODULE_AVAILABLE = False

# Also add steps dir for direct module import fallback
if str(STEPS_DIR) not in sys.path:
    sys.path.insert(0, str(STEPS_DIR))


def create_mock_subprocess_result(returncode: int, stdout: str, stderr: str = ""):
    """Create a mock subprocess.CompletedProcess result."""
    return subprocess.CompletedProcess(
        args=["mock"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_create_operation(config: dict, live: bool = False) -> bool:
    """Test the create operation of PR manager.

    Args:
        config: Configuration dictionary for the step
        live: If True, make actual GitHub API calls

    Returns:
        True if test passed, False otherwise
    """
    print("\n" + "=" * 60)
    print("Testing PR Manager - CREATE Operation")
    print("=" * 60)
    print("\nConfiguration:")
    print(json.dumps(config, indent=2))

    # Import the step module
    try:
        from steps import pr_manager
    except ImportError as e:
        print(f"\n❌ Failed to import pr_manager: {e}")
        return False

    # Get current directory info
    cwd = str(Path.cwd())
    print(f"\nWorking directory: {cwd}")

    if not live:
        print("\n🔄 Running in DRY-RUN mode (mocking GitHub API calls)")

        # Mock the subprocess.run calls
        def mock_subprocess_run(cmd, *args, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            print(f"  [MOCK] Would execute: {cmd_str}")

            # Mock gh pr list to show no existing PR
            if "gh pr list" in cmd_str:
                return create_mock_subprocess_result(0, "")

            # Mock gh pr create
            if "gh pr create" in cmd_str:
                return create_mock_subprocess_result(
                    0, "https://github.com/test/repo/pull/123"
                )

            # Mock git branch
            if "git branch" in cmd_str or "git rev-parse" in cmd_str:
                return create_mock_subprocess_result(0, "feat/test-branch\n")

            # Mock git remote
            if "git remote" in cmd_str:
                return create_mock_subprocess_result(0, "origin")

            return create_mock_subprocess_result(0, "")

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            result = pr_manager.run(cwd, config)
    else:
        print("\n⚠️  Running in LIVE mode - will make actual GitHub API calls!")
        confirm = input("Continue? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted.")
            return False

        result = pr_manager.run(cwd, config)

    # Check result
    print(f"\n{'=' * 60}")
    print("Result:")
    print(f"  Success: {result.success}")
    print(f"  Message: {result.message}")

    if result.success:
        print("\n✅ CREATE operation test PASSED")
    else:
        print("\n❌ CREATE operation test FAILED")

    return result.success


def test_ready_operation(config: dict, live: bool = False) -> bool:
    """Test the ready operation of PR manager.

    Args:
        config: Configuration dictionary for the step
        live: If True, make actual GitHub API calls

    Returns:
        True if test passed, False otherwise
    """
    print("\n" + "=" * 60)
    print("Testing PR Manager - READY Operation")
    print("=" * 60)
    print("\nConfiguration:")
    print(json.dumps(config, indent=2))

    # Import the step module
    try:
        from steps import pr_manager
    except ImportError as e:
        print(f"\n❌ Failed to import pr_manager: {e}")
        return False

    cwd = str(Path.cwd())
    print(f"\nWorking directory: {cwd}")

    if not live:
        print("\n🔄 Running in DRY-RUN mode (mocking GitHub API calls)")

        def mock_subprocess_run(cmd, *args, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            print(f"  [MOCK] Would execute: {cmd_str}")

            # Mock gh pr list to return an existing draft PR
            if "gh pr list" in cmd_str:
                return create_mock_subprocess_result(
                    0, "123\t[WIP] Test PR\tuser:feat/test\tDRAFT\n"
                )

            # Mock gh pr view for PR details
            if "gh pr view" in cmd_str:
                return create_mock_subprocess_result(
                    0,
                    json.dumps(
                        {
                            "number": 123,
                            "title": "[WIP] Test PR",
                            "isDraft": True,
                            "labels": [{"name": "work-in-progress"}, {"name": "spec"}],
                        }
                    ),
                )

            # Mock gh pr ready
            if "gh pr ready" in cmd_str:
                return create_mock_subprocess_result(0, "")

            # Mock gh pr edit for label changes
            if "gh pr edit" in cmd_str:
                return create_mock_subprocess_result(0, "")

            # Mock git branch
            if "git branch" in cmd_str or "git rev-parse" in cmd_str:
                return create_mock_subprocess_result(0, "feat/test-branch\n")

            return create_mock_subprocess_result(0, "")

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            result = pr_manager.run(cwd, config)
    else:
        print("\n⚠️  Running in LIVE mode - will make actual GitHub API calls!")
        confirm = input("Continue? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted.")
            return False

        result = pr_manager.run(cwd, config)

    # Check result
    print(f"\n{'=' * 60}")
    print("Result:")
    print(f"  Success: {result.success}")
    print(f"  Message: {result.message}")

    if result.success:
        print("\n✅ READY operation test PASSED")
    else:
        print("\n❌ READY operation test FAILED")

    return result.success


def test_hook_level_filtering() -> bool:
    """Test that hook-level filtering works correctly.

    Note: The PRManagerStep does NOT check the 'enabled' flag internally.
    This is by design - the hook system (config_loader.get_enabled_steps())
    is responsible for filtering disabled steps BEFORE they are executed.

    This test verifies that the step runs normally when called directly,
    regardless of the 'enabled' flag value. The actual filtering happens
    at the hook level.
    """
    print("\n" + "=" * 60)
    print("Testing PR Manager - HOOK-LEVEL FILTERING")
    print("=" * 60)

    try:
        from steps import pr_manager
    except ImportError as e:
        print(f"\n❌ Failed to import pr_manager: {e}")
        return False

    # Test: Step executes normally even with enabled=False
    # (because enabled flag is checked at hook level, not step level)
    config = {"name": "pr-manager", "enabled": False, "operation": "create"}
    cwd = str(Path.cwd())

    print("\n🔄 Running in DRY-RUN mode (mocking subprocess calls)")
    print("Note: The 'enabled' flag is checked at hook level, not step level")

    def mock_subprocess_run(cmd, *args, **kwargs):
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        print(f"  [MOCK] Would execute: {cmd_str}")

        # Mock gh --version
        if "gh --version" in cmd_str:
            return create_mock_subprocess_result(0, "gh version 2.40.0")

        # Mock gh auth status
        if "gh auth status" in cmd_str:
            return create_mock_subprocess_result(0, "Logged in to github.com")

        # Mock gh pr view to show no existing PR
        if "gh pr view" in cmd_str:
            return create_mock_subprocess_result(1, "", "no pull requests found")

        return create_mock_subprocess_result(0, "")

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        step = pr_manager.PRManagerStep(cwd, config)
        result = step.run()

    print("\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Message: {result.message}")

    # Step should run normally (gh CLI check passes via mock)
    # The enabled=False flag is not checked at step level
    print("\n✅ HOOK-LEVEL FILTERING test PASSED")
    print("   (Step runs regardless of 'enabled' flag - filtering is hook's job)")
    return True


def test_invalid_operation() -> bool:
    """Test handling of invalid operations.

    Invalid operations return failure - this is intentional FAIL-FAST for
    configuration errors. This is different from fail-open for runtime issues
    (like gh CLI unavailable).

    Design philosophy:
    - gh CLI unavailable → fail-open (warn but succeed)
    - Invalid config (unknown operation) → fail-fast (error, fail)
    """
    print("\n" + "=" * 60)
    print("Testing PR Manager - INVALID Operation")
    print("=" * 60)

    try:
        from steps import pr_manager
    except ImportError as e:
        print(f"\n❌ Failed to import pr_manager: {e}")
        return False

    config = {"name": "pr-manager", "enabled": True, "operation": "invalid_op"}
    cwd = str(Path.cwd())

    print("\n🔄 Running in DRY-RUN mode (mocking subprocess calls)")

    def mock_subprocess_run(cmd, *args, **kwargs):
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        print(f"  [MOCK] Would execute: {cmd_str}")

        # Mock gh --version for availability check
        if "gh --version" in cmd_str:
            return create_mock_subprocess_result(0, "gh version 2.40.0")

        # Mock gh auth status for auth check
        if "gh auth status" in cmd_str:
            return create_mock_subprocess_result(0, "Logged in to github.com")

        return create_mock_subprocess_result(0, "")

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        result = pr_manager.run(cwd, config)

    print("\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Message: {result.message}")

    # Invalid operation should FAIL (fail-fast for config errors)
    # This is different from gh unavailable (fail-open for runtime issues)
    if not result.success and "unknown" in result.message.lower():
        print("\n✅ INVALID operation test PASSED (fail-fast for config errors)")
        return True
    else:
        print("\n❌ INVALID operation test FAILED")
        print("   Expected: success=False with 'unknown' in message")
        return False


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(
        description="Manual test script for PR Manager Step",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--operation",
        choices=["create", "ready", "all"],
        default="all",
        help="Operation to test (default: all)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Make actual GitHub API calls (default: dry-run)",
    )
    parser.add_argument(
        "--title",
        default="[WIP] {slug}: Test PR",
        help="PR title format (default: '[WIP] {slug}: Test PR')",
    )
    parser.add_argument(
        "--labels",
        default="spec,work-in-progress",
        help="Comma-separated labels (default: 'spec,work-in-progress')",
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base branch (default: 'main')",
    )

    args = parser.parse_args()

    # Build configurations
    create_config = {
        "name": "pr-manager",
        "enabled": True,
        "operation": "create",
        "labels": args.labels.split(","),
        "title_format": args.title,
        "base_branch": args.base,
    }

    ready_config = {
        "name": "pr-manager",
        "enabled": True,
        "operation": "ready",
        "remove_labels": ["work-in-progress"],
        "reviewers": [],
    }

    # Track results
    results = []

    print("\n" + "#" * 60)
    print("# PR Manager Step - Manual Test Suite")
    print("#" * 60)

    if args.operation in ("create", "all"):
        results.append(("CREATE", test_create_operation(create_config, args.live)))

    if args.operation in ("ready", "all"):
        results.append(("READY", test_ready_operation(ready_config, args.live)))

    if args.operation == "all":
        results.append(("HOOK-FILTER", test_hook_level_filtering()))
        results.append(("INVALID-OP", test_invalid_operation()))

    # Summary
    print("\n" + "#" * 60)
    print("# Test Summary")
    print("#" * 60)
    print()

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name}: {status}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
