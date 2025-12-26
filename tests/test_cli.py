"""Tests for the CLI module."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from workspacebrain.cli import app

runner = CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self) -> None:
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "workspacebrain" in result.stdout

    def test_help(self) -> None:
        """Test --help flag."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.stdout
        assert "scan" in result.stdout
        assert "link" in result.stdout
        assert "doctor" in result.stdout

    def test_init_command(self, temp_workspace: Path) -> None:
        """Test init command creates brain directory."""
        result = runner.invoke(app, ["init", str(temp_workspace)])

        assert result.exit_code == 0
        assert "initialized" in result.stdout.lower() or "Brain" in result.stdout
        assert (temp_workspace / "brain").exists()

    def test_init_with_force(self, temp_workspace: Path) -> None:
        """Test init --force overwrites existing brain."""
        # First init
        runner.invoke(app, ["init", str(temp_workspace)])

        # Modify a file
        readme = temp_workspace / "brain" / "README.md"
        original = readme.read_text()
        readme.write_text("modified")

        # Init with force
        result = runner.invoke(app, ["init", "--force", str(temp_workspace)])

        assert result.exit_code == 0
        assert readme.read_text() != "modified"

    def test_scan_requires_brain(self, temp_workspace: Path) -> None:
        """Test scan fails without initialized brain."""
        result = runner.invoke(app, ["scan", str(temp_workspace)])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "failed" in result.stdout.lower()

    def test_scan_after_init(self, temp_workspace: Path) -> None:
        """Test scan works after init."""
        # Create a project (needs more than just package.json for node-fe)
        project = temp_workspace / "my-project"
        project.mkdir()
        (project / "package.json").write_text('{"name": "test"}')
        (project / "next.config.js").write_text("module.exports = {}")

        # Init then scan
        runner.invoke(app, ["init", str(temp_workspace)])
        result = runner.invoke(app, ["scan", str(temp_workspace)])

        assert result.exit_code == 0
        assert "my-project" in result.stdout

    def test_doctor_healthy_brain(self, temp_workspace: Path) -> None:
        """Test doctor reports healthy brain."""
        runner.invoke(app, ["init", str(temp_workspace)])
        result = runner.invoke(app, ["doctor", str(temp_workspace)])

        assert result.exit_code == 0
        assert "healthy" in result.stdout.lower()

    def test_doctor_missing_brain(self, temp_workspace: Path) -> None:
        """Test doctor reports missing brain."""
        result = runner.invoke(app, ["doctor", str(temp_workspace)])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_link_requires_brain(self, temp_workspace: Path) -> None:
        """Test link fails without brain."""
        result = runner.invoke(app, ["link", str(temp_workspace)])

        assert result.exit_code == 1
