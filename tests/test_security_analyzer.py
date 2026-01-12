"""Tests for security analyzer module."""

from pathlib import Path

import pytest

from workspacebrain.core.security_analyzer import SecurityAnalyzer
from workspacebrain.models import BrainConfig


@pytest.fixture
def temp_workspace_with_brain(tmp_path: Path) -> Path:
    """Create a temporary workspace with brain initialized."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create brain structure
    brain = workspace / "brain"
    brain.mkdir()
    (brain / "MANIFEST.yaml").write_text(
        """
workspace_path: "{}"
brain_version: "1.0"
detected_projects: []
""".format(
            str(workspace)
        )
    )

    return workspace


def test_security_analyzer_init(temp_workspace_with_brain: Path):
    """Test SecurityAnalyzer initialization."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    analyzer = SecurityAnalyzer(config)

    assert analyzer.config == config
    assert analyzer.github_token is None


def test_get_github_token_from_env(monkeypatch, temp_workspace_with_brain: Path):
    """Test getting GitHub token from environment variable."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    analyzer = SecurityAnalyzer(config)

    token = analyzer._get_github_token()
    assert token == "test_token_123"


def test_load_projects_empty_manifest(temp_workspace_with_brain: Path):
    """Test loading projects from empty manifest."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    analyzer = SecurityAnalyzer(config)

    projects = analyzer._load_projects()
    assert projects == []


def test_parse_npm_vulnerability(temp_workspace_with_brain: Path):
    """Test parsing npm audit vulnerability."""
    from workspacebrain.models import ProjectInfo

    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    analyzer = SecurityAnalyzer(config)

    project = ProjectInfo(
        name="test-project",
        path=str(temp_workspace_with_brain),
        project_type="node-fe",
        confidence=0.9,
    )

    vuln_data = {
        "severity": "high",
        "cves": ["CVE-2024-12345"],
        "cvss": {"score": 7.5},
        "title": "Test vulnerability",
        "range": "1.0.0 - 2.0.0",
        "fixAvailable": {"version": "2.1.0"},
    }

    alert = analyzer._parse_npm_vulnerability("test-package", vuln_data, project)

    assert alert is not None
    assert alert.package_name == "test-package"
    assert alert.severity == "high"
    assert alert.cve_id == "CVE-2024-12345"
    assert alert.cvss_score == 7.5
    assert alert.fixed_version == "2.1.0"
    assert alert.source == "npm-audit"


def test_parse_pip_vulnerability(temp_workspace_with_brain: Path):
    """Test parsing pip-audit vulnerability."""
    from workspacebrain.models import ProjectInfo

    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    analyzer = SecurityAnalyzer(config)

    project = ProjectInfo(
        name="test-project",
        path=str(temp_workspace_with_brain),
        project_type="python-be",
        confidence=0.9,
    )

    vuln_data = {
        "id": "CVE-2024-67890",
        "name": "requests",
        "installed_version": "2.28.0",
        "fix_versions": ["2.31.0"],
        "severity": "CRITICAL",
        "cvss": {"score": 9.8},
        "description": "Critical vulnerability",
    }

    alert = analyzer._parse_pip_vulnerability(vuln_data, project)

    assert alert is not None
    assert alert.package_name == "requests"
    assert alert.package_version == "2.28.0"
    assert alert.fixed_version == "2.31.0"
    assert alert.severity == "critical"
    assert alert.cve_id == "CVE-2024-67890"
    assert alert.cvss_score == 9.8
    assert alert.source == "pip-audit"
