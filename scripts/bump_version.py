#!/usr/bin/env python3
"""Bump version number in pyproject.toml and __init__.py"""

import re
from pathlib import Path

# Get project root
project_root = Path(__file__).parent.parent

# Files to update
pyproject_toml = project_root / "pyproject.toml"
init_py = project_root / "src" / "workspacebrain" / "__init__.py"


def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    content = pyproject_toml.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in pyproject.toml")


def bump_version(version: str) -> str:
    """Bump patch version: 0.1.0 -> 0.1.1"""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    
    major, minor, patch = parts
    new_patch = int(patch) + 1
    return f"{major}.{minor}.{new_patch}"


def update_pyproject_toml(old_version: str, new_version: str) -> None:
    """Update version in pyproject.toml."""
    content = pyproject_toml.read_text()
    content = content.replace(f'version = "{old_version}"', f'version = "{new_version}"')
    pyproject_toml.write_text(content)
    print(f"✓ Updated pyproject.toml: {old_version} -> {new_version}")


def update_init_py(old_version: str, new_version: str) -> None:
    """Update version in __init__.py."""
    content = init_py.read_text()
    content = content.replace(f'__version__ = "{old_version}"', f'__version__ = "{new_version}"')
    init_py.write_text(content)
    print(f"✓ Updated __init__.py: {old_version} -> {new_version}")


def main():
    """Main function."""
    try:
        current_version = get_current_version()
        new_version = bump_version(current_version)
        
        update_pyproject_toml(current_version, new_version)
        update_init_py(current_version, new_version)
        
        print(f"\n✅ Version bumped: {current_version} -> {new_version}")
        return new_version
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
