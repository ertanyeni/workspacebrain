"""Brain health checker module - diagnoses workspace brain issues."""

import hashlib
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

from workspacebrain.core.linker import (
    AI_RULE_FILES,
    GENERATED_BANNER,
    BrainLinker,
    get_brain_link_type,
)
from workspacebrain.models import BrainConfig, ProjectInfo


class CheckStatus(Enum):
    """Status of a health check."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a single health check."""

    name: str
    status: CheckStatus
    message: str
    details: list[str] = field(default_factory=list)


@dataclass
class ProjectHealth:
    """Health status of a single project."""

    name: str
    path: str
    project_type: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(c.status == CheckStatus.ERROR for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.status == CheckStatus.WARNING for c in self.checks)

    @property
    def is_healthy(self) -> bool:
        return not self.has_errors and not self.has_warnings


@dataclass
class HealthReport:
    """Complete health report for the workspace."""

    workspace_path: str
    brain_checks: list[CheckResult] = field(default_factory=list)
    project_health: list[ProjectHealth] = field(default_factory=list)

    @property
    def total_errors(self) -> int:
        count = sum(1 for c in self.brain_checks if c.status == CheckStatus.ERROR)
        for ph in self.project_health:
            count += sum(1 for c in ph.checks if c.status == CheckStatus.ERROR)
        return count

    @property
    def total_warnings(self) -> int:
        count = sum(1 for c in self.brain_checks if c.status == CheckStatus.WARNING)
        for ph in self.project_health:
            count += sum(1 for c in ph.checks if c.status == CheckStatus.WARNING)
        return count

    @property
    def is_healthy(self) -> bool:
        return self.total_errors == 0 and self.total_warnings == 0


class BrainDoctor:
    """Diagnoses workspace brain health issues."""

    def __init__(self, config: BrainConfig) -> None:
        self.config = config

    def diagnose(self) -> HealthReport:
        """Run all health checks and return a complete report."""
        report = HealthReport(workspace_path=str(self.config.workspace_path))

        # Brain-level checks
        report.brain_checks.extend(self._check_brain_exists())

        # If brain doesn't exist, skip other checks
        if any(c.status == CheckStatus.ERROR for c in report.brain_checks):
            return report

        report.brain_checks.extend(self._check_manifest())
        report.brain_checks.extend(self._check_brain_structure())
        report.brain_checks.extend(self._check_rules_files())

        # Project-level checks
        projects = self._load_projects()
        for project in projects:
            project_health = self._check_project(project)
            report.project_health.append(project_health)

        return report

    def _check_brain_exists(self) -> list[CheckResult]:
        """Check if brain directory exists."""
        results = []

        if self.config.brain_path.exists():
            results.append(
                CheckResult(
                    name="Brain Directory",
                    status=CheckStatus.OK,
                    message=f"Found at {self.config.brain_path}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="Brain Directory",
                    status=CheckStatus.ERROR,
                    message=f"Not found at {self.config.brain_path}",
                    details=["Run 'workspacebrain init' to create the brain directory"],
                )
            )

        return results

    def _check_manifest(self) -> list[CheckResult]:
        """Check if MANIFEST.yaml exists and is valid."""
        results = []
        manifest_path = self.config.manifest_path

        if not manifest_path.exists():
            results.append(
                CheckResult(
                    name="MANIFEST.yaml",
                    status=CheckStatus.ERROR,
                    message="File not found",
                    details=["Run 'workspacebrain init' to create MANIFEST.yaml"],
                )
            )
            return results

        # Try to parse
        try:
            content = manifest_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if data is None:
                results.append(
                    CheckResult(
                        name="MANIFEST.yaml",
                        status=CheckStatus.ERROR,
                        message="File is empty",
                    )
                )
                return results

            # Check required fields
            missing_fields = []
            for field in ["workspace_path", "brain_version"]:
                if field not in data:
                    missing_fields.append(field)

            if missing_fields:
                results.append(
                    CheckResult(
                        name="MANIFEST.yaml",
                        status=CheckStatus.WARNING,
                        message="Missing fields",
                        details=[f"Missing: {', '.join(missing_fields)}"],
                    )
                )
            else:
                project_count = len(data.get("detected_projects", []))
                results.append(
                    CheckResult(
                        name="MANIFEST.yaml",
                        status=CheckStatus.OK,
                        message=f"Valid ({project_count} projects registered)",
                    )
                )

        except yaml.YAMLError as e:
            results.append(
                CheckResult(
                    name="MANIFEST.yaml",
                    status=CheckStatus.ERROR,
                    message="Parse error",
                    details=[str(e)],
                )
            )

        return results

    def _check_brain_structure(self) -> list[CheckResult]:
        """Check brain directory structure."""
        results = []

        # Required files
        required_files = [
            ("README.md", self.config.readme_path),
            ("DECISIONS.md", self.config.decisions_path),
        ]

        for name, path in required_files:
            if path.exists():
                results.append(
                    CheckResult(
                        name=name,
                        status=CheckStatus.OK,
                        message="Present",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name=name,
                        status=CheckStatus.WARNING,
                        message="Missing",
                        details=[f"Expected at {path}"],
                    )
                )

        # Required directories
        required_dirs = [
            ("CONTRACTS/", self.config.contracts_path),
            ("HANDOFFS/", self.config.handoffs_path),
            ("RULES/", self.config.rules_path),
        ]

        for name, path in required_dirs:
            if path.exists():
                file_count = len(list(path.iterdir()))
                results.append(
                    CheckResult(
                        name=name,
                        status=CheckStatus.OK,
                        message=f"Present ({file_count} items)",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name=name,
                        status=CheckStatus.WARNING,
                        message="Missing",
                        details=[f"Expected at {path}"],
                    )
                )

        return results

    def _check_rules_files(self) -> list[CheckResult]:
        """Check for rule template files in RULES/."""
        results = []
        rules_path = self.config.rules_path

        if not rules_path.exists():
            return results

        # Check for INDEX.md
        index_path = rules_path / "INDEX.md"
        if index_path.exists():
            results.append(
                CheckResult(
                    name="RULES/INDEX.md",
                    status=CheckStatus.OK,
                    message="Present",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="RULES/INDEX.md",
                    status=CheckStatus.WARNING,
                    message="Missing",
                    details=["Consider adding INDEX.md to document your rules"],
                )
            )

        # Check for AI rule templates
        for rule_file in AI_RULE_FILES:
            template_path = rules_path / rule_file
            if template_path.exists():
                results.append(
                    CheckResult(
                        name=f"RULES/{rule_file}",
                        status=CheckStatus.OK,
                        message="Custom template present",
                    )
                )

        return results

    def _load_projects(self) -> list[ProjectInfo]:
        """Load projects from MANIFEST.yaml."""
        if not self.config.manifest_path.exists():
            return []

        try:
            content = self.config.manifest_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if data is None:
                return []

            projects = []
            for p in data.get("detected_projects", []):
                project_type = p.get("type") or p.get("project_type") or "unknown"
                projects.append(
                    ProjectInfo(
                        name=p["name"],
                        path=p["path"],
                        project_type=project_type,
                        confidence=p.get("confidence", 0.5),
                        signals=p.get("signals", []),
                    )
                )
            return projects

        except (yaml.YAMLError, KeyError, TypeError):
            return []

    def _check_project(self, project: ProjectInfo) -> ProjectHealth:
        """Run health checks for a single project."""
        health = ProjectHealth(
            name=project.name,
            path=project.path,
            project_type=project.project_type,
        )

        project_path = Path(project.path)

        # Check if project exists
        if not project_path.exists():
            health.checks.append(
                CheckResult(
                    name="Project Directory",
                    status=CheckStatus.ERROR,
                    message="Not found",
                    details=[f"Path: {project.path}"],
                )
            )
            return health

        # Check .brain symlink
        health.checks.extend(self._check_brain_link(project_path))

        # Check AI rule files and drift
        health.checks.extend(
            self._check_ai_rule_files(project_path, project.project_type)
        )

        return health

    def _check_brain_link(self, project_path: Path) -> list[CheckResult]:
        """Check .brain symlink or fallback in project.

        Reports status as:
        - "OK: symlink" - Valid symlink to brain
        - "OK: pointer json" - Valid brain.link.json fallback
        - "ERROR: broken link" - Symlink target doesn't exist
        - "ERROR: missing json" - .brain dir exists but no brain.link.json
        - "ERROR: brain bulunamadı" - brain_path in json doesn't exist
        """
        results = []

        link_type, link_data = get_brain_link_type(project_path)

        if link_type == 'symlink':
            if link_data and link_data.get('valid'):
                results.append(
                    CheckResult(
                        name=".brain",
                        status=CheckStatus.OK,
                        message=f"OK: symlink ({link_data['target']})",
                    )
                )
            else:
                target = link_data.get('target', 'unknown') if link_data else 'unknown'
                resolved = link_data.get('resolved', 'unknown') if link_data else 'unknown'
                results.append(
                    CheckResult(
                        name=".brain",
                        status=CheckStatus.ERROR,
                        message="ERROR: broken link",
                        details=[
                            f"Points to: {target}",
                            f"Resolved: {resolved} (not found)",
                            "Run 'workspacebrain link --force' to fix",
                        ],
                    )
                )

        elif link_type == 'pointer':
            if link_data and link_data.get('valid'):
                brain_path = link_data.get('brain_path', 'unknown')
                results.append(
                    CheckResult(
                        name=".brain",
                        status=CheckStatus.OK,
                        message=f"OK: pointer json",
                        details=[f"brain_path: {brain_path}"],
                    )
                )
            elif link_data and link_data.get('error'):
                results.append(
                    CheckResult(
                        name=".brain",
                        status=CheckStatus.ERROR,
                        message="ERROR: invalid json",
                        details=[link_data.get('error', 'Parse error')],
                    )
                )
            else:
                brain_path = link_data.get('brain_path', 'unknown') if link_data else 'unknown'
                results.append(
                    CheckResult(
                        name=".brain",
                        status=CheckStatus.ERROR,
                        message="ERROR: brain bulunamadı",
                        details=[
                            f"brain_path: {brain_path}",
                            "Brain directory does not exist at specified path",
                        ],
                    )
                )

        else:  # 'none'
            # Check if .brain exists as a directory without json
            brain_pointer = project_path / ".brain"
            if brain_pointer.is_dir():
                results.append(
                    CheckResult(
                        name=".brain",
                        status=CheckStatus.ERROR,
                        message="ERROR: missing json",
                        details=[
                            ".brain directory exists but brain.link.json is missing",
                            "Run 'workspacebrain link --force' to fix",
                        ],
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name=".brain",
                        status=CheckStatus.WARNING,
                        message="Not found",
                        details=["Run 'workspacebrain link' to create"],
                    )
                )

        return results

    def _check_ai_rule_files(
        self, project_path: Path, project_type: str
    ) -> list[CheckResult]:
        """Check AI rule files and detect drift."""
        results = []

        for rule_file in AI_RULE_FILES:
            file_path = project_path / rule_file

            if not file_path.exists():
                results.append(
                    CheckResult(
                        name=rule_file,
                        status=CheckStatus.WARNING,
                        message="Not found",
                        details=["Run 'workspacebrain link' to generate"],
                    )
                )
                continue

            content = file_path.read_text(encoding="utf-8")

            # Check if it's a generated file
            if "GENERATED BY WORKSPACEBRAIN" not in content:
                results.append(
                    CheckResult(
                        name=rule_file,
                        status=CheckStatus.OK,
                        message="Manual file (not managed)",
                    )
                )
                continue

            # Check for drift - compare with what would be generated
            drift_result = self._check_drift(
                file_path, content, rule_file, project_type
            )
            results.append(drift_result)

        return results

    def _check_drift(
        self,
        file_path: Path,
        current_content: str,
        rule_file: str,
        project_type: str,
    ) -> CheckResult:
        """Check if generated file has drifted from template."""
        # Get expected content
        linker = BrainLinker(self.config)
        template_content = linker._load_rule_template(rule_file, project_type)
        expected_content = GENERATED_BANNER + template_content

        # Compare checksums
        current_hash = hashlib.md5(current_content.encode()).hexdigest()[:8]
        expected_hash = hashlib.md5(expected_content.encode()).hexdigest()[:8]

        if current_hash == expected_hash:
            return CheckResult(
                name=rule_file,
                status=CheckStatus.OK,
                message=f"In sync (#{current_hash})",
            )
        else:
            return CheckResult(
                name=rule_file,
                status=CheckStatus.WARNING,
                message=f"Drift detected",
                details=[
                    f"Current: #{current_hash}",
                    f"Expected: #{expected_hash}",
                    "File was modified or template changed",
                    "Run 'workspacebrain link --force' to regenerate",
                ],
            )

    def _compute_file_hash(self, path: Path) -> str:
        """Compute MD5 hash of file content."""
        content = path.read_text(encoding="utf-8")
        return hashlib.md5(content.encode()).hexdigest()[:8]
