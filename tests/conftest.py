"""Pytest fixtures for WorkspaceBrain tests."""

from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary workspace directory for testing."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    yield workspace


@pytest.fixture
def temp_workspace_with_projects(temp_workspace: Path) -> Path:
    """Create a temporary workspace with mock projects."""
    # Python project
    python_project = temp_workspace / "python-app"
    python_project.mkdir()
    (python_project / "pyproject.toml").write_text("[project]\nname = 'python-app'\n")

    # Node project
    node_project = temp_workspace / "node-app"
    node_project.mkdir()
    (node_project / "package.json").write_text('{"name": "node-app"}')

    # Rust project
    rust_project = temp_workspace / "rust-app"
    rust_project.mkdir()
    (rust_project / "Cargo.toml").write_text('[package]\nname = "rust-app"\n')

    return temp_workspace


@pytest.fixture
def temp_workspace_with_brain(temp_workspace: Path) -> Path:
    """Create a temporary workspace with an initialized brain."""
    brain_dir = temp_workspace / "brain"
    brain_dir.mkdir()

    # Create required structure
    (brain_dir / "README.md").write_text("# Test Brain\n")
    (brain_dir / "MANIFEST.yaml").write_text(
        f"workspace_path: {temp_workspace}\nbrain_version: '1.0'\n"
        "created_at: '2024-01-01T00:00:00'\nupdated_at: '2024-01-01T00:00:00'\n"
        "detected_projects: []\n"
    )
    (brain_dir / "DECISIONS.md").write_text("# Decisions\n")

    (brain_dir / "CONTRACTS").mkdir()
    (brain_dir / "HANDOFFS").mkdir()
    (brain_dir / "RULES").mkdir()
    (brain_dir / "LOGS").mkdir()
    (brain_dir / "CONTEXT").mkdir()

    return temp_workspace
