"""Security context generator - creates AI-friendly security context files."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from ..models import BrainConfig, SecurityAlert, SecurityRiskAssessment, SecurityContext


class SecurityContextGenerator:
    """Generates security context files for AI assistants."""

    def __init__(self, config: BrainConfig):
        self.config = config

    def generate_global_security_context(
        self, assessments: list[SecurityRiskAssessment]
    ) -> Path:
        """Generate global security context file (brain/CONTEXT/SECURITY.md)."""
        context_path = self.config.context_path / "SECURITY.md"
        context_path.parent.mkdir(parents=True, exist_ok=True)

        content = self._format_global_context(assessments)
        context_path.write_text(content, encoding="utf-8")

        return context_path

    def generate_project_security_context(
        self, project_name: str, assessments: list[SecurityRiskAssessment]
    ) -> str:
        """Generate project-specific security context section."""
        # Filter assessments for this project
        project_assessments = [
            a for a in assessments if a.alert.project_name == project_name
        ]

        if not project_assessments:
            return ""

        return self._format_project_context(project_assessments)

    def _format_global_context(
        self, assessments: list[SecurityRiskAssessment]
    ) -> str:
        """Format global security context markdown."""
        now = datetime.now()

        lines = [
            "# Security Context",
            f"*Last Updated: {now.strftime('%Y-%m-%d %H:%M')}*",
            "",
        ]

        # Group by action
        fix_now = [a for a in assessments if a.action == "FIX_NOW"]
        fix_soon = [a for a in assessments if a.action == "FIX_SOON"]
        monitor = [a for a in assessments if a.action == "MONITOR"]

        # Critical Issues (Fix Now)
        if fix_now:
            lines.extend([
                "## Critical Issues (Fix Now)",
                "",
            ])

            # Group by project
            by_project: dict[str, list[SecurityRiskAssessment]] = {}
            for assessment in fix_now:
                project = assessment.alert.project_name
                if project not in by_project:
                    by_project[project] = []
                by_project[project].append(assessment)

            for project, project_assessments in sorted(by_project.items()):
                project_type = project_assessments[0].alert.project_type
                lines.append(f"### {project} ({project_type})")
                lines.append("")

                for assessment in project_assessments[:5]:  # Limit to 5 per project
                    lines.extend(
                        self._format_assessment(assessment, include_project=False)
                    )
                    lines.append("")

        # High Priority (Fix Soon)
        if fix_soon:
            lines.extend([
                "## High Priority (Fix Soon)",
                "",
            ])

            by_project: dict[str, list[SecurityRiskAssessment]] = {}
            for assessment in fix_soon:
                project = assessment.alert.project_name
                if project not in by_project:
                    by_project[project] = []
                by_project[project].append(assessment)

            for project, project_assessments in sorted(by_project.items()):
                project_type = project_assessments[0].alert.project_type
                lines.append(f"### {project} ({project_type})")
                lines.append("")

                for assessment in project_assessments[:3]:  # Limit to 3 per project
                    lines.extend(
                        self._format_assessment(assessment, include_project=False)
                    )
                    lines.append("")

        # Monitoring
        if monitor:
            lines.extend([
                "## Monitoring",
                "",
                f"*{len(monitor)} lower-priority issues being monitored*",
                "",
            ])

        # Summary
        total = len(assessments)
        lines.extend([
            "---",
            f"## Summary",
            "",
            f"- **Total Alerts**: {total}",
            f"- **Fix Now**: {len(fix_now)}",
            f"- **Fix Soon**: {len(fix_soon)}",
            f"- **Monitor**: {len(monitor)}",
            "",
            "*Run `wbrain security status` for detailed view.*",
        ])

        return "\n".join(lines)

    def _format_project_context(
        self, assessments: list[SecurityRiskAssessment]
    ) -> str:
        """Format project-specific security context section."""
        lines = [
            "## Security Alerts",
            "",
        ]

        # Count by priority
        critical = len([a for a in assessments if a.priority == "CRITICAL"])
        high = len([a for a in assessments if a.priority == "HIGH"])
        medium = len([a for a in assessments if a.priority == "MEDIUM"])
        low = len([a for a in assessments if a.priority == "LOW"])

        fix_now = len([a for a in assessments if a.action == "FIX_NOW"])
        fix_soon = len([a for a in assessments if a.action == "FIX_SOON"])

        # Summary line
        summary_parts = []
        if critical > 0:
            summary_parts.append(f"{critical} Critical")
        if high > 0:
            summary_parts.append(f"{high} High")
        if medium > 0:
            summary_parts.append(f"{medium} Medium")
        if low > 0:
            summary_parts.append(f"{low} Low")

        if summary_parts:
            lines.append(f"**{', '.join(summary_parts)} priority issues**")
            lines.append("")

        # List top issues
        top_issues = sorted(assessments, key=lambda a: a.risk_score, reverse=True)[:5]
        for assessment in top_issues:
            alert = assessment.alert
            cve_str = f"{alert.cve_id}: " if alert.cve_id else ""
            lines.append(
                f"- {cve_str}{assessment.recommended_fix or f'Review {alert.package_name}'} "
                f"({assessment.priority})"
            )

        lines.append("")

        return "\n".join(lines)

    def _format_assessment(
        self, assessment: SecurityRiskAssessment, include_project: bool = True
    ) -> list[str]:
        """Format a single assessment for markdown."""
        alert = assessment.alert
        lines = []

        # Header
        cve_str = f"**{alert.cve_id}**" if alert.cve_id else "**Vulnerability**"
        package_str = f"`{alert.package_name}=={alert.package_version}`"
        cvss_str = f" (CVSS {alert.cvss_score:.1f})" if alert.cvss_score else ""

        if include_project:
            lines.append(f"- {cve_str} in {package_str}{cvss_str} - *{alert.project_name}*")
        else:
            lines.append(f"- {cve_str} in {package_str}{cvss_str}")

        # Action
        lines.append(f"  - **Action**: {assessment.recommended_fix or 'Review package'}")
        lines.append(f"  - **Reason**: {assessment.reasoning}")

        # Impact
        if assessment.impact_analysis:
            lines.append(f"  - **Impact**: {assessment.impact_analysis}")

        return lines

    def save_alerts(
        self, alerts: list[SecurityAlert]
    ) -> Path:
        """Save alerts to ALERTS.yaml."""
        alerts_path = self.config.security_alerts_path
        alerts_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "alerts": [alert.to_dict() for alert in alerts],
            "last_updated": datetime.now().isoformat(),
        }

        content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        alerts_path.write_text(content, encoding="utf-8")

        return alerts_path

    def save_assessments(
        self, assessments: list[SecurityRiskAssessment]
    ) -> Path:
        """Save risk assessments to RISK_ASSESSMENT.yaml."""
        assessment_path = self.config.security_path / "RISK_ASSESSMENT.yaml"
        assessment_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "assessments": [a.to_dict() for a in assessments],
            "last_updated": datetime.now().isoformat(),
        }

        content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        assessment_path.write_text(content, encoding="utf-8")

        return assessment_path

    def load_assessments(self) -> list[SecurityRiskAssessment]:
        """Load risk assessments from RISK_ASSESSMENT.yaml."""
        assessment_path = self.config.security_path / "RISK_ASSESSMENT.yaml"

        if not assessment_path.exists():
            return []

        try:
            content = assessment_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if not data or "assessments" not in data:
                return []

            assessments = []
            for a_data in data["assessments"]:
                # Reconstruct SecurityAlert from dict
                alert_data = a_data["alert"].copy()
                # Parse datetime if it's a string
                if "detected_at" in alert_data and isinstance(
                    alert_data["detected_at"], str
                ):
                    alert_data["detected_at"] = datetime.fromisoformat(
                        alert_data["detected_at"]
                    )
                alert = SecurityAlert(**alert_data)

                # Reconstruct SecurityRiskAssessment
                assessed_at = datetime.now()
                if "assessed_at" in a_data and isinstance(a_data["assessed_at"], str):
                    assessed_at = datetime.fromisoformat(a_data["assessed_at"])

                assessment = SecurityRiskAssessment(
                    alert=alert,
                    priority=a_data["priority"],
                    action=a_data["action"],
                    risk_score=a_data["risk_score"],
                    reasoning=a_data["reasoning"],
                    impact_analysis=a_data.get("impact_analysis"),
                    recommended_fix=a_data.get("recommended_fix"),
                    assessed_at=assessed_at,
                )
                assessments.append(assessment)

            return assessments

        except (yaml.YAMLError, KeyError, TypeError):
            return []
