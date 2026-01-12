"""Tests for security context generator module."""

from pathlib import Path

import pytest

from workspacebrain.core.security_context_generator import SecurityContextGenerator
from workspacebrain.models import BrainConfig, SecurityAlert, SecurityRiskAssessment


@pytest.fixture
def temp_workspace_with_brain(tmp_path: Path) -> Path:
    """Create a temporary workspace with brain initialized."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    brain = workspace / "brain"
    brain.mkdir()
    (brain / "CONTEXT").mkdir()

    return workspace


def test_security_context_generator_init(temp_workspace_with_brain: Path):
    """Test SecurityContextGenerator initialization."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    generator = SecurityContextGenerator(config)

    assert generator.config == config


def test_format_project_context(temp_workspace_with_brain: Path):
    """Test project context formatting."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    generator = SecurityContextGenerator(config)

    alert = SecurityAlert(
        package_name="requests",
        package_version="2.28.0",
        fixed_version="2.31.0",
        severity="critical",
        cvss_score=9.8,
        cve_id="CVE-2024-12345",
        source="pip-audit",
        project_name="backend",
        project_type="python-be",
    )

    from workspacebrain.core.risk_scorer import RiskScorer

    scorer = RiskScorer(config)
    assessment = scorer.assess_alert(alert)

    context = generator.generate_project_security_context("backend", [assessment])

    assert "Security Alerts" in context
    assert "CVE-2024-12345" in context or "requests" in context


def test_save_and_load_assessments(temp_workspace_with_brain: Path):
    """Test saving and loading assessments."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    generator = SecurityContextGenerator(config)

    alert = SecurityAlert(
        package_name="test-package",
        package_version="1.0.0",
        severity="high",
        source="test",
        project_name="test-project",
        project_type="python-be",
    )

    from workspacebrain.core.risk_scorer import RiskScorer

    scorer = RiskScorer(config)
    assessment = scorer.assess_alert(alert)

    # Save
    path = generator.save_assessments([assessment])
    assert path.exists()

    # Load
    loaded = generator.load_assessments()
    assert len(loaded) == 1
    assert loaded[0].alert.package_name == "test-package"
    assert loaded[0].priority == assessment.priority
