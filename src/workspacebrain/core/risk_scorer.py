"""Risk scorer module - analyzes security alerts and assigns priorities."""

import httpx
from dataclasses import dataclass
from typing import Optional

from ..models import BrainConfig, SecurityAlert, SecurityRiskAssessment


@dataclass
class ScoringContext:
    """Context for risk scoring."""

    project_type: str
    project_criticality: float = 1.0  # 0.0 to 1.0
    exploit_available: bool = False
    exploit_maturity: Optional[str] = None


class RiskScorer:
    """Scores security alerts and generates risk assessments."""

    # Project type criticality weights
    PROJECT_CRITICALITY = {
        "python-be": 1.0,  # Backend is most critical
        "node-fe": 0.7,  # Frontend is less critical
        "mobile": 0.8,  # Mobile is important
        "rust": 0.9,  # Rust projects often critical
        "go": 0.9,
        "java-maven": 1.0,
        "java-gradle": 1.0,
        "unknown": 0.5,
    }

    def __init__(self, config: BrainConfig):
        self.config = config

    def assess_alerts(
        self, alerts: list[SecurityAlert]
    ) -> list[SecurityRiskAssessment]:
        """Assess all alerts and generate risk assessments."""
        assessments: list[SecurityRiskAssessment] = []

        for alert in alerts:
            assessment = self.assess_alert(alert)
            assessments.append(assessment)

        # Sort by risk score (highest first)
        assessments.sort(key=lambda a: a.risk_score, reverse=True)

        return assessments

    def assess_alert(self, alert: SecurityAlert) -> SecurityRiskAssessment:
        """Assess a single alert and generate risk assessment."""
        # Get project criticality
        project_criticality = self.PROJECT_CRITICALITY.get(
            alert.project_type, 0.5
        )

        # Check exploit status
        exploit_info = self._check_exploit_status(alert)

        # Calculate base risk score
        base_score = self._calculate_base_score(alert, project_criticality)

        # Adjust for exploit
        if exploit_info["available"]:
            base_score *= 1.5  # Increase risk if exploit available
            if exploit_info["maturity"] == "weaponized":
                base_score *= 1.3
            elif exploit_info["maturity"] == "proof-of-concept":
                base_score *= 1.1

        # Cap at 10.0
        risk_score = min(base_score, 10.0)

        # Determine priority
        priority = self._determine_priority(risk_score, alert.severity)

        # Determine action
        action = self._determine_action(priority, risk_score, exploit_info)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            alert, risk_score, priority, exploit_info, project_criticality
        )

        # Generate impact analysis
        impact_analysis = self._generate_impact_analysis(alert, project_criticality)

        # Generate recommended fix
        recommended_fix = self._generate_recommended_fix(alert)

        return SecurityRiskAssessment(
            alert=alert,
            priority=priority,
            action=action,
            risk_score=risk_score,
            reasoning=reasoning,
            impact_analysis=impact_analysis,
            recommended_fix=recommended_fix,
        )

    def _calculate_base_score(
        self, alert: SecurityAlert, project_criticality: float
    ) -> float:
        """Calculate base risk score from CVSS and project criticality."""
        # Start with CVSS score if available
        if alert.cvss_score is not None:
            base = alert.cvss_score
        else:
            # Fallback to severity mapping
            severity_scores = {
                "critical": 9.0,
                "high": 7.0,
                "medium": 5.0,
                "low": 3.0,
            }
            base = severity_scores.get(alert.severity.lower(), 5.0)

        # Multiply by project criticality
        return base * project_criticality

    def _check_exploit_status(self, alert: SecurityAlert) -> dict:
        """Check if exploit is available for this CVE."""
        result = {
            "available": alert.exploit_available,
            "maturity": alert.exploit_maturity,
        }

        # If we already have exploit info from the alert, use it
        if alert.exploit_available:
            return result

        # Try to check NVD API for exploit status
        if alert.cve_id:
            try:
                nvd_info = self._check_nvd_exploit(alert.cve_id)
                if nvd_info:
                    result.update(nvd_info)
            except Exception:
                # API call failed, use default
                pass

        return result

    def _check_nvd_exploit(self, cve_id: str) -> Optional[dict]:
        """Check NVD API for exploit information."""
        try:
            # NVD API endpoint
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
            headers = {"Accept": "application/json"}

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code != 200:
                    return None

                data = response.json()
                if not data.get("vulnerabilities"):
                    return None

                vuln = data["vulnerabilities"][0].get("cve", {})
                metrics = vuln.get("metrics", {})

                # Check for exploit information
                exploit_available = False
                exploit_maturity = None

                # Check if there are known exploits (simplified check)
                # In reality, this would parse the CVE data more carefully
                if metrics:
                    exploit_available = True
                    exploit_maturity = "proof-of-concept"  # Default assumption

                return {
                    "available": exploit_available,
                    "maturity": exploit_maturity,
                }

        except Exception:
            return None

    def _determine_priority(self, risk_score: float, severity: str) -> str:
        """Determine priority level from risk score and severity."""
        if risk_score >= 9.0 or severity == "critical":
            return "CRITICAL"
        elif risk_score >= 7.0 or severity == "high":
            return "HIGH"
        elif risk_score >= 5.0 or severity == "medium":
            return "MEDIUM"
        else:
            return "LOW"

    def _determine_action(
        self, priority: str, risk_score: float, exploit_info: dict
    ) -> str:
        """Determine recommended action."""
        if priority == "CRITICAL" or (risk_score >= 8.0 and exploit_info["available"]):
            return "FIX_NOW"
        elif priority == "HIGH" or risk_score >= 7.0:
            return "FIX_SOON"
        else:
            return "MONITOR"

    def _generate_reasoning(
        self,
        alert: SecurityAlert,
        risk_score: float,
        priority: str,
        exploit_info: dict,
        project_criticality: float,
    ) -> str:
        """Generate AI-style reasoning for the assessment."""
        parts = []

        # Base reasoning
        parts.append(
            f"Risk score of {risk_score:.1f}/10.0 based on CVSS {alert.cvss_score or 'N/A'}"
        )

        # Project criticality
        if project_criticality >= 0.9:
            parts.append("high project criticality (backend/production system)")
        elif project_criticality >= 0.7:
            parts.append("moderate project criticality")

        # Exploit status
        if exploit_info["available"]:
            if exploit_info["maturity"] == "weaponized":
                parts.append("weaponized exploit available in the wild")
            elif exploit_info["maturity"] == "proof-of-concept":
                parts.append("proof-of-concept exploit available")
            else:
                parts.append("exploit available")
        else:
            parts.append("no known exploit at this time")

        # Package context
        if alert.fixed_version:
            parts.append(f"fixed version available: {alert.fixed_version}")

        return ". ".join(parts) + "."

    def _generate_impact_analysis(
        self, alert: SecurityAlert, project_criticality: float
    ) -> str:
        """Generate impact analysis for the vulnerability."""
        impact_parts = []

        # Severity-based impact
        if alert.severity == "critical":
            impact_parts.append("Critical severity vulnerability")
        elif alert.severity == "high":
            impact_parts.append("High severity vulnerability")

        # Project type specific
        if alert.project_type == "python-be":
            impact_parts.append("affects backend API endpoints")
        elif alert.project_type == "node-fe":
            impact_parts.append("affects frontend application")

        # Package context
        if "auth" in alert.package_name.lower() or "security" in alert.package_name.lower():
            impact_parts.append("security-sensitive package")

        if not impact_parts:
            impact_parts.append("standard dependency vulnerability")

        return " ".join(impact_parts) + "."

    def _generate_recommended_fix(self, alert: SecurityAlert) -> Optional[str]:
        """Generate recommended fix action."""
        if alert.fixed_version:
            return f"Update {alert.package_name} from {alert.package_version} to {alert.fixed_version}"
        else:
            return f"Review {alert.package_name} {alert.package_version} for security updates"
