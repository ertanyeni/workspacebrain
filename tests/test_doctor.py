"""Tests for the brain doctor module."""

import os
from pathlib import Path

import pytest

from workspacebrain.core.doctor import BrainDoctor, CheckStatus
from workspacebrain.core.installer import BrainInstaller
from workspacebrain.core.linker import AI_RULE_FILES, BrainLinker
from workspacebrain.core.scanner import WorkspaceScanner
from workspacebrain.models import BrainConfig


class TestBrainDoctor:
    """Tests for BrainDoctor class."""

    def test_diagnose_missing_brain(self, temp_workspace: Path) -> None:
        """Test diagnosis when brain directory doesn't exist."""
        config = BrainConfig(workspace_path=temp_workspace)
        doctor = BrainDoctor(config)

        report = doctor.diagnose()

        assert not report.is_healthy
        assert report.total_errors == 1

        # Should have error about missing brain
        brain_check = report.brain_checks[0]
        assert brain_check.status == CheckStatus.ERROR
        assert "not found" in brain_check.message.lower()

    def test_diagnose_healthy_brain(self, temp_workspace: Path) -> None:
        """Test diagnosis of a healthy brain."""
        config = BrainConfig(workspace_path=temp_workspace)

        # Initialize brain
        installer = BrainInstaller(config)
        installer.install()

        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        # Should be healthy (no projects = no project checks)
        assert report.total_errors == 0
        assert all(c.status == CheckStatus.OK for c in report.brain_checks)

    def test_diagnose_manifest_valid(self, temp_workspace: Path) -> None:
        """Test that valid MANIFEST.yaml is detected."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)
        installer.install()

        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        manifest_check = next(
            c for c in report.brain_checks if c.name == "MANIFEST.yaml"
        )
        assert manifest_check.status == CheckStatus.OK
        assert "Valid" in manifest_check.message

    def test_diagnose_project_with_valid_symlink(
        self, temp_workspace: Path
    ) -> None:
        """Test diagnosis of project with valid .brain symlink."""
        # Setup workspace with project
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)
        installer.install()

        project = temp_workspace / "my-app"
        project.mkdir()
        (project / "pyproject.toml").write_text("[project]\n")

        scanner = WorkspaceScanner(config)
        scanner.scan()

        linker = BrainLinker(config)
        linker.link_all()

        # Run doctor
        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        assert len(report.project_health) == 1
        project_health = report.project_health[0]

        # Find symlink check
        symlink_check = next(
            c for c in project_health.checks if ".brain" in c.name
        )
        assert symlink_check.status == CheckStatus.OK
        # New format: "OK: symlink (../brain)" or "OK: pointer json"
        assert "OK:" in symlink_check.message

    def test_diagnose_project_missing_link(
        self, temp_workspace: Path
    ) -> None:
        """Test diagnosis of project without .brain link."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)
        installer.install()

        project = temp_workspace / "my-app"
        project.mkdir()
        (project / "pyproject.toml").write_text("[project]\n")

        scanner = WorkspaceScanner(config)
        scanner.scan()

        # Don't link - doctor should warn

        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        assert len(report.project_health) == 1
        project_health = report.project_health[0]

        # Should have warning about missing link
        link_check = next(
            c for c in project_health.checks if ".brain" in c.name
        )
        assert link_check.status == CheckStatus.WARNING
        assert "Not found" in link_check.message

    def test_diagnose_drift_detection(
        self, temp_workspace: Path
    ) -> None:
        """Test that drift in generated files is detected."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)
        installer.install()

        project = temp_workspace / "my-app"
        project.mkdir()
        (project / "pyproject.toml").write_text("[project]\n")

        scanner = WorkspaceScanner(config)
        scanner.scan()

        linker = BrainLinker(config)
        linker.link_all()

        # Modify a generated file to cause drift (in project root)
        claude_md = project / "CLAUDE.md"
        content = claude_md.read_text()
        claude_md.write_text(content + "\n# Modified by hand\n")

        # Run doctor
        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        project_health = report.project_health[0]

        # Find CLAUDE.md check (name includes directory prefix)
        claude_check = next(
            c for c in project_health.checks if "CLAUDE.md" in c.name
        )
        assert claude_check.status == CheckStatus.WARNING
        assert "Drift" in claude_check.message

    def test_diagnose_no_drift_when_in_sync(
        self, temp_workspace: Path
    ) -> None:
        """Test that no drift is reported when files are in sync."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)
        installer.install()

        project = temp_workspace / "my-app"
        project.mkdir()
        (project / "pyproject.toml").write_text("[project]\n")

        scanner = WorkspaceScanner(config)
        scanner.scan()

        linker = BrainLinker(config)
        linker.link_all()

        # Don't modify - should be in sync

        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        project_health = report.project_health[0]

        # All AI rule files should be in sync (names are file names in project root)
        for check in project_health.checks:
            if check.name in AI_RULE_FILES:
                assert check.status == CheckStatus.OK
                assert "In sync" in check.message

    def test_diagnose_broken_symlink(
        self, temp_workspace: Path
    ) -> None:
        """Test diagnosis of broken .brain symlink."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)
        installer.install()

        project = temp_workspace / "my-app"
        project.mkdir()
        (project / "pyproject.toml").write_text("[project]\n")

        scanner = WorkspaceScanner(config)
        scanner.scan()

        # Create symlink to non-existent path
        symlink = project / ".brain"
        symlink.symlink_to("../nonexistent")

        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        project_health = report.project_health[0]
        symlink_check = next(
            c for c in project_health.checks if ".brain" in c.name
        )

        assert symlink_check.status == CheckStatus.ERROR
        # New format: "ERROR: broken link"
        assert "broken" in symlink_check.message.lower()

    def test_diagnose_manual_file_not_flagged(
        self, temp_workspace: Path
    ) -> None:
        """Test that manually created files are not flagged for drift."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)
        installer.install()

        project = temp_workspace / "my-app"
        project.mkdir()
        (project / "pyproject.toml").write_text("[project]\n")

        scanner = WorkspaceScanner(config)
        scanner.scan()

        # Create manual CLAUDE.md without our banner (in project root)
        (project / "CLAUDE.md").write_text("# My custom instructions\n")

        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        project_health = report.project_health[0]
        claude_check = next(
            c for c in project_health.checks if "CLAUDE.md" in c.name
        )

        assert claude_check.status == CheckStatus.OK
        assert "Manual" in claude_check.message

    def test_report_total_counts(self, temp_workspace: Path) -> None:
        """Test that report correctly counts errors and warnings."""
        config = BrainConfig(workspace_path=temp_workspace)
        installer = BrainInstaller(config)
        installer.install()

        # Create projects - one linked, one not
        project1 = temp_workspace / "app1"
        project1.mkdir()
        (project1 / "pyproject.toml").write_text("[project]\n")

        project2 = temp_workspace / "app2"
        project2.mkdir()
        (project2 / "pyproject.toml").write_text("[project]\n")

        scanner = WorkspaceScanner(config)
        scanner.scan()

        # Only link first project
        linker = BrainLinker(config)
        linker.link_project(project1, "python-be")

        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        # app2 should have warnings for missing link and files
        assert report.total_warnings > 0
        assert not report.is_healthy
