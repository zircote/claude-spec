"""
Spec detection for memory injection.

Detects the active specification from project structure to enable
context-aware memory queries.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple


class ActiveSpec(NamedTuple):
    """Information about an active specification project."""

    slug: str
    path: Path
    readme_path: Path


def detect_active_spec(cwd: str | Path) -> ActiveSpec | None:
    """
    Detect the active specification from project structure.

    Looks in docs/spec/active/ for a single active project.
    Returns spec info if found, None otherwise.

    Args:
        cwd: Project root directory

    Returns:
        ActiveSpec with slug and paths, or None if no active spec
    """
    cwd_path = Path(cwd)
    spec_dir = cwd_path / "docs" / "spec" / "active"

    if not spec_dir.is_dir():
        return None

    # Look for subdirectories with README.md
    active_specs: list[tuple[str, Path, Path]] = []
    try:
        for entry in spec_dir.iterdir():
            if entry.is_dir():
                readme = entry / "README.md"
                if readme.is_file():
                    slug = _extract_slug(entry.name)
                    active_specs.append((slug, entry, readme))
    except (PermissionError, OSError) as e:
        sys.stderr.write(f"spec_detector: Error scanning spec dir: {e}\n")
        return None

    # Only return if exactly one active spec
    if len(active_specs) == 1:
        slug, path, readme = active_specs[0]
        return ActiveSpec(slug=slug, path=path, readme_path=readme)

    return None


def _extract_slug(dirname: str) -> str:
    """
    Extract the slug from a spec directory name.

    Directory format: YYYY-MM-DD-slug-name
    Returns the slug-name part.

    Args:
        dirname: Directory name (e.g., "2025-12-17-my-feature")

    Returns:
        Slug portion (e.g., "my-feature")
    """
    # Match YYYY-MM-DD prefix
    match = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", dirname)
    if match:
        return match.group(1)
    return dirname


def get_spec_from_readme(readme_path: Path) -> str | None:
    """
    Extract spec slug from README.md frontmatter.

    Args:
        readme_path: Path to README.md file

    Returns:
        Slug from frontmatter, or None if not found
    """
    try:
        content = readme_path.read_text(encoding="utf-8")

        # Look for slug in YAML frontmatter
        if content.startswith("---"):
            # Find closing ---
            end_idx = content.find("---", 3)
            if end_idx > 0:
                frontmatter = content[3:end_idx]
                for line in frontmatter.split("\n"):
                    if line.strip().startswith("slug:"):
                        slug = line.split(":", 1)[1].strip()
                        # Remove quotes if present
                        return slug.strip("\"'")

    except (OSError, UnicodeDecodeError) as e:
        sys.stderr.write(f"spec_detector: Error reading {readme_path}: {e}\n")

    return None


def find_all_active_specs(cwd: str | Path) -> list[ActiveSpec]:
    """
    Find all active specifications (when multiple exist).

    Useful for disambiguation when more than one spec is active.

    Args:
        cwd: Project root directory

    Returns:
        List of ActiveSpec objects
    """
    cwd_path = Path(cwd)
    spec_dir = cwd_path / "docs" / "spec" / "active"

    if not spec_dir.is_dir():
        return []

    specs: list[ActiveSpec] = []
    try:
        for entry in spec_dir.iterdir():
            if entry.is_dir():
                readme = entry / "README.md"
                if readme.is_file():
                    # Try to get slug from README frontmatter first
                    slug = get_spec_from_readme(readme)
                    if not slug:
                        slug = _extract_slug(entry.name)
                    specs.append(ActiveSpec(slug=slug, path=entry, readme_path=readme))
    except (PermissionError, OSError):
        pass

    # Sort by modification time (most recent first)
    specs.sort(key=lambda s: s.readme_path.stat().st_mtime, reverse=True)

    return specs
