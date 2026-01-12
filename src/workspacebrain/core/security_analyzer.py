"""Security analyzer module - collects security alerts from various sources."""

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import yaml

from ..models import BrainConfig, ProjectInfo, SecurityAlert


@dataclass
class ScanResult:
    """Result of a security scan operation."""

    success: bool
    error: Optional[str] = None
    alerts: list[SecurityAlert] = field(default_factory=list)


class SecurityAnalyzer:
    """Collects security alerts from Dependabot, npm audit, pip-audit, cargo audit."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self.github_token: Optional[str] = None

    def scan_all(self) -> ScanResult:
        """Scan all projects for security alerts.

        Combines alerts from:
        - Dependabot (GitHub API)
        - npm audit (Node.js projects)
        - pip-audit (Python projects)
        - cargo audit (Rust projects)
        """
        result = ScanResult(success=True)

        try:
            # Load projects from manifest
            projects = self._load_projects()
            if not projects:
                result.error = "No projects found. Run 'wbrain scan' first."
                result.success = False
                return result

            # Get GitHub token
            self.github_token = self._get_github_token()

            # Scan each project
            all_alerts: list[SecurityAlert] = []
            for project in projects:
                project_path = Path(project.path)
                if not project_path.exists():
                    continue

                # Scan based on project type
                if project.project_type == "node-fe":
                    alerts = self._scan_npm_audit(project_path, project)
                    all_alerts.extend(alerts)
                elif project.project_type == "python-be":
                    alerts = self._scan_pip_audit(project_path, project)
                    all_alerts.extend(alerts)
                elif project.project_type == "rust":
                    alerts = self._scan_cargo_audit(project_path, project)
                    all_alerts.extend(alerts)

                # Try Dependabot for all projects (if GitHub repo)
                if self.github_token:
                    alerts = self._scan_dependabot(project_path, project)
                    all_alerts.extend(alerts)

            result.alerts = all_alerts

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _get_github_token(self) -> Optional[str]:
        """Get GitHub token from git config or environment variable."""
        # Try environment variable first
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token

        # Try git config
        try:
            result = subprocess.run(
                ["git", "config", "--get", "github.token"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # Try alternative git config keys
        for key in ["credential.helper", "url.https://github.com/.insteadOf"]:
            try:
                result = subprocess.run(
                    ["git", "config", "--get", key],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                # This is a fallback - might not work for all setups
            except Exception:
                pass

        return None

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

    def _scan_dependabot(
        self, project_path: Path, project: ProjectInfo
    ) -> list[SecurityAlert]:
        """Scan Dependabot alerts via GitHub API."""
        alerts: list[SecurityAlert] = []

        if not self.github_token:
            return alerts

        # Try to detect GitHub repo
        repo_info = self._detect_github_repo(project_path)
        if not repo_info:
            return alerts

        owner, repo = repo_info

        try:
            # Use GitHub API to get Dependabot alerts
            url = f"https://api.github.com/repos/{owner}/{repo}/dependabot/alerts"
            headers = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.github_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 404:
                    # Dependabot might not be enabled
                    return alerts
                response.raise_for_status()

                data = response.json()
                for alert_data in data:
                    alert = self._parse_dependabot_alert(alert_data, project)
                    if alert:
                        alerts.append(alert)

        except httpx.HTTPError:
            # API call failed, skip Dependabot for this project
            pass
        except Exception:
            # Other errors, skip
            pass

        return alerts

    def _detect_github_repo(self, project_path: Path) -> Optional[tuple[str, str]]:
        """Detect GitHub owner/repo from git remote."""
        try:
            result = subprocess.run(
                ["git", "-C", str(project_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode != 0:
                return None

            url = result.stdout.strip()
            # Parse git@github.com:owner/repo.git or https://github.com/owner/repo.git
            if "github.com" in url:
                if url.startswith("git@"):
                    # git@github.com:owner/repo.git
                    parts = url.split(":")[-1].replace(".git", "").split("/")
                    if len(parts) >= 2:
                        return (parts[-2], parts[-1])
                elif "github.com" in url:
                    # https://github.com/owner/repo.git
                    parts = url.split("github.com/")[-1].replace(".git", "").split("/")
                    if len(parts) >= 2:
                        return (parts[0], parts[1])

        except Exception:
            pass

        return None

    def _parse_dependabot_alert(
        self, alert_data: dict, project: ProjectInfo
    ) -> Optional[SecurityAlert]:
        """Parse a Dependabot alert into SecurityAlert."""
        try:
            # Extract CVE if available
            cve_id = None
            if "security_advisory" in alert_data:
                cves = alert_data["security_advisory"].get("cves", [])
                if cves:
                    cve_id = cves[0].get("cve_id")

            # Extract package info
            dependency = alert_data.get("dependency", {})
            package_name = dependency.get("package", {}).get("name", "unknown")
            package_version = dependency.get("package", {}).get("ecosystem", "unknown")

            # Extract severity
            severity_map = {
                "critical": "critical",
                "high": "high",
                "moderate": "medium",
                "low": "low",
            }
            severity = severity_map.get(
                alert_data.get("security_advisory", {}).get("severity", "low").lower(),
                "low",
            )

            # Extract CVSS
            cvss_score = None
            cvss_vector = None
            if "security_advisory" in alert_data:
                cvss = alert_data["security_advisory"].get("cvss", {})
                cvss_score = cvss.get("score")
                cvss_vector = cvss.get("vector_string")

            # Extract description
            description = alert_data.get("security_advisory", {}).get("summary")

            # Extract fixed version
            fixed_version = None
            if "security_vulnerability" in alert_data:
                first_patched = alert_data["security_vulnerability"].get(
                    "first_patched_version"
                )
                if first_patched:
                    fixed_version = first_patched.get("identifier")

            return SecurityAlert(
                cve_id=cve_id,
                package_name=package_name,
                package_version=package_version,
                fixed_version=fixed_version,
                severity=severity,
                cvss_score=cvss_score,
                cvss_vector=cvss_vector,
                description=description,
                source="dependabot",
                project_name=project.name,
                project_type=project.project_type,
                detected_at=datetime.now(),
                advisory_url=alert_data.get("html_url"),
            )

        except (KeyError, TypeError):
            return None

    def _scan_npm_audit(
        self, project_path: Path, project: ProjectInfo
    ) -> list[SecurityAlert]:
        """Scan npm audit for Node.js projects."""
        alerts: list[SecurityAlert] = []

        package_json = project_path / "package.json"
        if not package_json.exists():
            return alerts

        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0 and result.returncode != 1:
                # Exit code 1 means vulnerabilities found, which is OK
                return alerts

            data = json.loads(result.stdout)
            vulnerabilities = data.get("vulnerabilities", {})

            for package_name, vuln_data in vulnerabilities.items():
                alert = self._parse_npm_vulnerability(
                    package_name, vuln_data, project
                )
                if alert:
                    alerts.append(alert)

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # npm not installed or audit failed
            pass
        except Exception:
            pass

        return alerts

    def _parse_npm_vulnerability(
        self, package_name: str, vuln_data: dict, project: ProjectInfo
    ) -> Optional[SecurityAlert]:
        """Parse npm audit vulnerability into SecurityAlert."""
        try:
            severity_map = {
                "critical": "critical",
                "high": "high",
                "moderate": "medium",
                "low": "low",
            }

            severity = severity_map.get(
                vuln_data.get("severity", "low").lower(), "low"
            )

            # Get CVE if available
            cve_id = None
            if "cves" in vuln_data and vuln_data["cves"]:
                cve_id = vuln_data["cves"][0]

            # Get CVSS
            cvss_score = vuln_data.get("cvss", {}).get("score")
            cvss_vector = None

            # Get fixed version
            fixed_version = None
            if "fixAvailable" in vuln_data and vuln_data["fixAvailable"]:
                if isinstance(vuln_data["fixAvailable"], dict):
                    fixed_version = vuln_data["fixAvailable"].get("version")

            return SecurityAlert(
                cve_id=cve_id,
                package_name=package_name,
                package_version=vuln_data.get("range", "unknown"),
                fixed_version=fixed_version,
                severity=severity,
                cvss_score=cvss_score,
                cvss_vector=cvss_vector,
                description=vuln_data.get("title"),
                source="npm-audit",
                project_name=project.name,
                project_type=project.project_type,
                detected_at=datetime.now(),
            )

        except (KeyError, TypeError):
            return None

    def _scan_pip_audit(
        self, project_path: Path, project: ProjectInfo
    ) -> list[SecurityAlert]:
        """Scan pip-audit for Python projects."""
        alerts: list[SecurityAlert] = []

        # Check for requirements files
        req_files = [
            project_path / "requirements.txt",
            project_path / "pyproject.toml",
            project_path / "setup.py",
        ]
        if not any(f.exists() for f in req_files):
            return alerts

        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return alerts

            data = json.loads(result.stdout)
            vulns = data.get("vulnerabilities", [])

            for vuln in vulns:
                alert = self._parse_pip_vulnerability(vuln, project)
                if alert:
                    alerts.append(alert)

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # pip-audit not installed or failed
            pass
        except Exception:
            pass

        return alerts

    def _parse_pip_vulnerability(
        self, vuln_data: dict, project: ProjectInfo
    ) -> Optional[SecurityAlert]:
        """Parse pip-audit vulnerability into SecurityAlert."""
        try:
            severity_map = {
                "CRITICAL": "critical",
                "HIGH": "high",
                "MEDIUM": "medium",
                "LOW": "low",
            }

            severity = severity_map.get(
                vuln_data.get("severity", "LOW").upper(), "low"
            )

            cve_id = vuln_data.get("id")
            package_name = vuln_data.get("name", "unknown")
            installed_version = vuln_data.get("installed_version", "unknown")
            fixed_version = vuln_data.get("fix_versions", [None])[0]

            # Extract CVSS if available
            cvss_score = None
            if "cvss" in vuln_data:
                cvss_score = vuln_data["cvss"].get("score")

            return SecurityAlert(
                cve_id=cve_id,
                package_name=package_name,
                package_version=installed_version,
                fixed_version=fixed_version,
                severity=severity,
                cvss_score=cvss_score,
                description=vuln_data.get("description"),
                source="pip-audit",
                project_name=project.name,
                project_type=project.project_type,
                detected_at=datetime.now(),
            )

        except (KeyError, TypeError):
            return None

    def _scan_cargo_audit(
        self, project_path: Path, project: ProjectInfo
    ) -> list[SecurityAlert]:
        """Scan cargo audit for Rust projects."""
        alerts: list[SecurityAlert] = []

        if not (project_path / "Cargo.toml").exists():
            return alerts

        try:
            result = subprocess.run(
                ["cargo", "audit", "--json"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0 and result.returncode != 1:
                return alerts

            data = json.loads(result.stdout)
            vulns = data.get("vulnerabilities", {}).get("list", [])

            for vuln in vulns:
                alert = self._parse_cargo_vulnerability(vuln, project)
                if alert:
                    alerts.append(alert)

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # cargo-audit not installed or failed
            pass
        except Exception:
            pass

        return alerts

    def _parse_cargo_vulnerability(
        self, vuln_data: dict, project: ProjectInfo
    ) -> Optional[SecurityAlert]:
        """Parse cargo audit vulnerability into SecurityAlert."""
        try:
            advisory = vuln_data.get("advisory", {})
            package = vuln_data.get("package", {})

            cve_id = advisory.get("id")
            package_name = package.get("name", "unknown")
            package_version = package.get("version", "unknown")

            severity_map = {
                "critical": "critical",
                "high": "high",
                "medium": "medium",
                "low": "low",
            }
            severity = severity_map.get(
                advisory.get("severity", "low").lower(), "low"
            )

            # Get CVSS
            cvss_score = advisory.get("cvss")
            cvss_vector = None

            return SecurityAlert(
                cve_id=cve_id,
                package_name=package_name,
                package_version=package_version,
                severity=severity,
                cvss_score=cvss_score,
                cvss_vector=cvss_vector,
                description=advisory.get("title"),
                source="cargo-audit",
                project_name=project.name,
                project_type=project.project_type,
                detected_at=datetime.now(),
            )

        except (KeyError, TypeError):
            return None
