"""Tests for the brain installer module."""

from pathlib import Path

import pytest

from workspacebrain.core.installer import BrainInstaller
from workspacebrain.models import BrainConfig


class TestBrainInstaller:
    """Tests for BrainInstaller class."""

    def test_install_creates_brain_directory(self, temp_workspace: Path) -> None:
        """Test that install creates the brain directory structure."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)

        result = installer.install()

        assert result.success
        assert config.brain_path.exists()
        assert config.manifest_path.exists()
        assert config.readme_path.exists()
        assert config.decisions_path.exists()
        assert config.contracts_path.exists()
        assert config.handoffs_path.exists()
        assert config.rules_path.exists()

    def test_install_is_idempotent(self, temp_workspace: Path) -> None:
        """Test that running install twice doesn't overwrite existing files."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)

        # First install
        result1 = installer.install()
        assert result1.success

        # Modify README
        original_content = config.readme_path.read_text()
        config.readme_path.write_text("Modified content")

        # Second install (should skip existing)
        result2 = installer.install()
        assert result2.success
        assert "brain/README.md" in result2.skipped_paths

        # Content should be preserved
        assert config.readme_path.read_text() == "Modified content"

    def test_install_with_force_overwrites(self, temp_workspace: Path) -> None:
        """Test that --force flag overwrites existing files."""
        config = BrainConfig(workspace_path=temp_workspace, force=False)
        installer = BrainInstaller(config)

        # First install
        installer.install()

        # Modify README
        config.readme_path.write_text("Modified content")

        # Install with force
        config_force = BrainConfig(workspace_path=temp_workspace, force=True)
        installer_force = BrainInstaller(config_force)
        result = installer_force.install()

        assert result.success
        # Content should be overwritten
        assert config.readme_path.read_text() != "Modified content"

    def test_manifest_contains_workspace_path(self, temp_workspace: Path) -> None:
        """Test that MANIFEST.yaml contains the workspace path."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)

        installer.install()

        manifest_content = config.manifest_path.read_text()
        assert str(temp_workspace) in manifest_content

    def test_rules_index_created(self, temp_workspace: Path) -> None:
        """Test that RULES/INDEX.md is created."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)

        installer.install()

        index_path = config.rules_path / "INDEX.md"
        assert index_path.exists()
        assert "Workspace Rules" in index_path.read_text()
