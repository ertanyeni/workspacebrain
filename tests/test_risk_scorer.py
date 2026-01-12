"""Tests for risk scorer module."""

from pathlib import Path

import pytest

from workspacebrain.core.risk_scorer import RiskScorer
from workspacebrain.models import BrainConfig, SecurityAlert


@pytest.fixture
def temp_workspace_with_brain(tmp_path: Path) -> Path:
    """Create a temporary workspace with brain initialized."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    brain = workspace / "brain"
    brain.mkdir()

    return workspace


def test_risk_scorer_init(temp_workspace_with_brain: Path):
    """Test RiskScorer initialization."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    scorer = RiskScorer(config)

    assert scorer.config == config


def test_calculate_base_score(temp_workspace_with_brain: Path):
    """Test base score calculation."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    scorer = RiskScorer(config)

    alert = SecurityAlert(
        package_name="test-package",
        package_version="1.0.0",
        severity="high",
        cvss_score=7.5,
        source="test",
        project_name="test-project",
        project_type="python-be",
    )

    score = scorer._calculate_base_score(alert, 1.0)
    assert score == 7.5

    # Test with project criticality
    score = scorer._calculate_base_score(alert, 0.7)
    assert score == 7.5 * 0.7


def test_determine_priority(temp_workspace_with_brain: Path):
    """Test priority determination."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    scorer = RiskScorer(config)

    assert scorer._determine_priority(9.5, "critical") == "CRITICAL"
    assert scorer._determine_priority(7.5, "high") == "HIGH"
    assert scorer._determine_priority(5.5, "medium") == "MEDIUM"
    assert scorer._determine_priority(3.0, "low") == "LOW"


def test_determine_action(temp_workspace_with_brain: Path):
    """Test action determination."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    scorer = RiskScorer(config)

    # Critical with exploit
    action = scorer._determine_action(
        "CRITICAL", 9.0, {"available": True, "maturity": "weaponized"}
    )
    assert action == "FIX_NOW"

    # High without exploit
    action = scorer._determine_action(
        "HIGH", 7.5, {"available": False, "maturity": None}
    )
    assert action == "FIX_SOON"

    # Medium
    action = scorer._determine_action(
        "MEDIUM", 5.0, {"available": False, "maturity": None}
    )
    assert action == "MONITOR"


def test_assess_alert(temp_workspace_with_brain: Path):
    """Test full alert assessment."""
    config = BrainConfig(workspace_path=temp_workspace_with_brain)
    scorer = RiskScorer(config)

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

    assessment = scorer.assess_alert(alert)

    assert assessment.alert == alert
    assert assessment.priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    assert assessment.action in ["FIX_NOW", "FIX_SOON", "MONITOR"]
    assert 0.0 <= assessment.risk_score <= 10.0
    assert assessment.reasoning is not None
    assert assessment.recommended_fix is not None
