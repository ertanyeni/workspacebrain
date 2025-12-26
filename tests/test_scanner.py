"""Tests for the workspace scanner module."""

from pathlib import Path

import pytest

from workspacebrain.core.scanner import ProjectDetector, WorkspaceScanner
from workspacebrain.models import BrainConfig


class TestProjectDetector:
    """Tests for ProjectDetector class."""

    def test_detect_python_backend_pyproject(self, tmp_path: Path) -> None:
        """Test detection of Python backend with pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "python-be"
        assert "pyproject.toml" in result.signals
        assert result.confidence >= 0.5

    def test_detect_python_backend_django(self, tmp_path: Path) -> None:
        """Test detection of Django project with higher confidence."""
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        (tmp_path / "manage.py").write_text("#!/usr/bin/env python\n")

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "python-be"
        assert "pyproject.toml" in result.signals
        assert "manage.py (Django)" in result.signals
        assert result.confidence >= 0.8

    def test_detect_node_frontend_nextjs(self, tmp_path: Path) -> None:
        """Test detection of Next.js project."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "next.config.js").write_text("module.exports = {}")

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "node-fe"
        assert "package.json" in result.signals
        assert "next.config.js" in result.signals
        assert result.confidence >= 0.7

    def test_detect_node_frontend_vite(self, tmp_path: Path) -> None:
        """Test detection of Vite project."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "vite.config.ts").write_text("export default {}")

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "node-fe"
        assert "vite.config.ts" in result.signals

    def test_detect_mobile_expo(self, tmp_path: Path) -> None:
        """Test detection of Expo mobile project."""
        (tmp_path / "app.json").write_text('{"expo": {"name": "test"}}')
        (tmp_path / "package.json").write_text('{"name": "test"}')

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "mobile"
        assert "app.json" in result.signals
        assert "expo config in app.json" in result.signals

    def test_detect_mobile_react_native(self, tmp_path: Path) -> None:
        """Test detection of React Native project with native dirs."""
        (tmp_path / "android").mkdir()
        (tmp_path / "ios").mkdir()
        (tmp_path / "metro.config.js").write_text("module.exports = {}")

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "mobile"
        assert "android/" in result.signals
        assert "ios/" in result.signals
        assert "metro.config.js" in result.signals

    def test_detect_rust(self, tmp_path: Path) -> None:
        """Test detection of Rust project."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.rs").write_text("fn main() {}")

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "rust"
        assert "Cargo.toml" in result.signals
        assert "src/main.rs" in result.signals
        assert result.confidence >= 0.89  # 0.7 + 0.2 with float precision

    def test_detect_go(self, tmp_path: Path) -> None:
        """Test detection of Go project."""
        (tmp_path / "go.mod").write_text("module test")
        (tmp_path / "main.go").write_text("package main")

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "go"
        assert "go.mod" in result.signals
        assert "main.go" in result.signals

    def test_detect_java_maven(self, tmp_path: Path) -> None:
        """Test detection of Java Maven project."""
        (tmp_path / "pom.xml").write_text("<project></project>")

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "java-maven"
        assert "pom.xml" in result.signals

    def test_detect_java_gradle(self, tmp_path: Path) -> None:
        """Test detection of Java Gradle project."""
        (tmp_path / "build.gradle").write_text("plugins {}")

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is not None
        assert result.project_type == "java-gradle"
        assert "build.gradle" in result.signals

    def test_detect_empty_directory(self, tmp_path: Path) -> None:
        """Test that empty directory returns None."""
        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        assert result is None

    def test_package_json_alone_not_frontend(self, tmp_path: Path) -> None:
        """Test that package.json alone is not detected as frontend."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        detector = ProjectDetector()
        result = detector.detect(tmp_path)

        # Should not be detected as node-fe without additional signals
        assert result is None


class TestWorkspaceScanner:
    """Tests for WorkspaceScanner class."""

    def test_scan_requires_brain(self, temp_workspace: Path) -> None:
        """Test that scan fails if brain directory doesn't exist."""
        config = BrainConfig(workspace_path=temp_workspace)
        scanner = WorkspaceScanner(config)

        result = scanner.scan()

        assert not result.success
        assert "not found" in result.error.lower()

    def test_scan_detects_python_project(
        self, temp_workspace_with_brain: Path
    ) -> None:
        """Test that scan detects Python projects."""
        # Create a Python project
        python_project = temp_workspace_with_brain / "my-python-app"
        python_project.mkdir()
        (python_project / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        config = BrainConfig(workspace_path=temp_workspace_with_brain)
        scanner = WorkspaceScanner(config)

        result = scanner.scan()

        assert result.success
        assert len(result.projects) == 1
        assert result.projects[0].name == "my-python-app"
        assert result.projects[0].project_type == "python-be"
        assert result.projects[0].confidence >= 0.5
        assert "pyproject.toml" in result.projects[0].signals

    def test_scan_detects_node_frontend(
        self, temp_workspace_with_brain: Path
    ) -> None:
        """Test that scan detects Node.js frontend projects."""
        node_project = temp_workspace_with_brain / "my-next-app"
        node_project.mkdir()
        (node_project / "package.json").write_text('{"name": "test"}')
        (node_project / "next.config.js").write_text("module.exports = {}")

        config = BrainConfig(workspace_path=temp_workspace_with_brain)
        scanner = WorkspaceScanner(config)

        result = scanner.scan()

        assert result.success
        assert len(result.projects) == 1
        assert result.projects[0].project_type == "node-fe"

    def test_scan_detects_mobile(
        self, temp_workspace_with_brain: Path
    ) -> None:
        """Test that scan detects mobile projects."""
        mobile_project = temp_workspace_with_brain / "my-app"
        mobile_project.mkdir()
        (mobile_project / "app.json").write_text('{"expo": {}}')

        config = BrainConfig(workspace_path=temp_workspace_with_brain)
        scanner = WorkspaceScanner(config)

        result = scanner.scan()

        assert result.success
        assert len(result.projects) == 1
        assert result.projects[0].project_type == "mobile"

    def test_scan_sorts_by_confidence(
        self, temp_workspace_with_brain: Path
    ) -> None:
        """Test that scan results are sorted by confidence."""
        # Create a low-confidence project
        project1 = temp_workspace_with_brain / "simple-py"
        project1.mkdir()
        (project1 / "requirements.txt").write_text("flask\n")

        # Create a high-confidence project
        project2 = temp_workspace_with_brain / "django-app"
        project2.mkdir()
        (project2 / "pyproject.toml").write_text("[project]\n")
        (project2 / "manage.py").write_text("#!/usr/bin/env python\n")

        config = BrainConfig(workspace_path=temp_workspace_with_brain)
        scanner = WorkspaceScanner(config)

        result = scanner.scan()

        assert result.success
        assert len(result.projects) == 2
        # Higher confidence should come first
        assert result.projects[0].confidence >= result.projects[1].confidence

    def test_scan_skips_node_modules(
        self, temp_workspace_with_brain: Path
    ) -> None:
        """Test that scan skips node_modules directory."""
        # Create a project with node_modules
        project = temp_workspace_with_brain / "project"
        project.mkdir()
        (project / "package.json").write_text('{"name": "test"}')
        (project / "next.config.js").write_text("module.exports = {}")

        # Create nested project in node_modules (should be skipped)
        node_modules = project / "node_modules" / "some-package"
        node_modules.mkdir(parents=True)
        (node_modules / "package.json").write_text('{"name": "nested"}')
        (node_modules / "vite.config.js").write_text("export default {}")

        config = BrainConfig(workspace_path=temp_workspace_with_brain)
        scanner = WorkspaceScanner(config)

        result = scanner.scan()

        assert result.success
        # Should only find the main project, not the one in node_modules
        assert len(result.projects) == 1
        assert result.projects[0].name == "project"

    def test_scan_updates_manifest_with_new_format(
        self, temp_workspace_with_brain: Path
    ) -> None:
        """Test that scan updates MANIFEST.yaml with new format."""
        python_project = temp_workspace_with_brain / "test-app"
        python_project.mkdir()
        (python_project / "pyproject.toml").write_text("[project]\n")

        config = BrainConfig(workspace_path=temp_workspace_with_brain)
        scanner = WorkspaceScanner(config)

        scanner.scan()

        manifest_content = config.manifest_path.read_text()
        assert "test-app" in manifest_content
        assert "type:" in manifest_content
        assert "confidence:" in manifest_content
        assert "signals:" in manifest_content
