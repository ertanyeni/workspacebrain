"""Workspace scanner module - detects projects in the workspace."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from workspacebrain.models import BrainConfig, BrainManifest, ProjectInfo


@dataclass
class DetectionResult:
    """Result of project type detection for a directory."""

    project_type: str
    confidence: float
    signals: list[str]


# Directories to skip during scanning
SKIP_DIRS: set[str] = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "target",
    "build",
    "dist",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    "brain",  # Skip the brain directory itself
}


class ProjectDetector:
    """Detects project type using heuristics."""

    def detect(self, directory: Path) -> Optional[DetectionResult]:
        """Detect project type for a directory.

        Returns DetectionResult if a project is detected, None otherwise.
        Checks in priority order: Mobile > Node FE > Python BE > Other
        """
        # Try each detector in priority order
        # More specific detectors first (Rust, Go, Java have unique markers)
        # Then generic ones (Python, Node)
        detectors = [
            self._detect_mobile,
            self._detect_rust,
            self._detect_go,
            self._detect_java,
            self._detect_node_frontend,
            self._detect_python_backend,
        ]

        for detector in detectors:
            result = detector(directory)
            if result:
                return result

        return None

    def _detect_python_backend(self, directory: Path) -> Optional[DetectionResult]:
        """Detect Python backend project."""
        signals: list[str] = []
        confidence = 0.0

        # Primary markers
        if (directory / "pyproject.toml").exists():
            signals.append("pyproject.toml")
            confidence += 0.5
        if (directory / "requirements.txt").exists():
            signals.append("requirements.txt")
            confidence += 0.3
        if (directory / "setup.py").exists():
            signals.append("setup.py")
            confidence += 0.3
        if (directory / "setup.cfg").exists():
            signals.append("setup.cfg")
            confidence += 0.2

        # Backend-specific markers (boost confidence)
        if (directory / "manage.py").exists():
            signals.append("manage.py (Django)")
            confidence += 0.3
        if (directory / "app.py").exists():
            signals.append("app.py (Flask/FastAPI)")
            confidence += 0.2
        if (directory / "main.py").exists():
            signals.append("main.py")
            confidence += 0.1
        if (directory / "api").is_dir():
            signals.append("api/")
            confidence += 0.1
        if (directory / "src").is_dir():
            signals.append("src/")
            confidence += 0.1

        if signals:
            return DetectionResult(
                project_type="python-be",
                confidence=min(confidence, 1.0),
                signals=signals,
            )
        return None

    def _detect_node_frontend(self, directory: Path) -> Optional[DetectionResult]:
        """Detect Node.js frontend project."""
        signals: list[str] = []
        confidence = 0.0

        # Must have package.json
        if not (directory / "package.json").exists():
            return None

        signals.append("package.json")
        confidence += 0.3

        # Next.js detection
        next_configs = list(directory.glob("next.config.*"))
        if next_configs:
            signals.append(next_configs[0].name)
            confidence += 0.4

        # Vite detection
        vite_configs = list(directory.glob("vite.config.*"))
        if vite_configs:
            signals.append(vite_configs[0].name)
            confidence += 0.4

        # React/Vue/Angular markers
        if (directory / "src" / "App.tsx").exists():
            signals.append("src/App.tsx")
            confidence += 0.3
        elif (directory / "src" / "App.jsx").exists():
            signals.append("src/App.jsx")
            confidence += 0.3
        elif (directory / "src" / "App.vue").exists():
            signals.append("src/App.vue")
            confidence += 0.3

        # Additional frontend markers
        if (directory / "public").is_dir():
            signals.append("public/")
            confidence += 0.1
        if (directory / "pages").is_dir():
            signals.append("pages/")
            confidence += 0.2
        if (directory / "app").is_dir() and next_configs:
            signals.append("app/ (Next.js App Router)")
            confidence += 0.2
        if (directory / "components").is_dir():
            signals.append("components/")
            confidence += 0.1

        # tsconfig.json is common in frontend
        if (directory / "tsconfig.json").exists():
            signals.append("tsconfig.json")
            confidence += 0.1

        # tailwind.config.* is a frontend marker
        tailwind_configs = list(directory.glob("tailwind.config.*"))
        if tailwind_configs:
            signals.append(tailwind_configs[0].name)
            confidence += 0.1

        if len(signals) > 1:  # Need more than just package.json
            return DetectionResult(
                project_type="node-fe",
                confidence=min(confidence, 1.0),
                signals=signals,
            )
        return None

    def _detect_mobile(self, directory: Path) -> Optional[DetectionResult]:
        """Detect mobile project (React Native, Expo, Native)."""
        signals: list[str] = []
        confidence = 0.0

        # Expo detection (highest priority for RN)
        if (directory / "app.json").exists():
            signals.append("app.json")
            confidence += 0.3

            # Check if it's Expo
            try:
                app_json = (directory / "app.json").read_text()
                if "expo" in app_json.lower():
                    signals.append("expo config in app.json")
                    confidence += 0.3
            except Exception:
                pass

        if (directory / "expo.json").exists():
            signals.append("expo.json")
            confidence += 0.4

        # React Native with Expo
        if (directory / "app.config.js").exists():
            signals.append("app.config.js (Expo)")
            confidence += 0.3
        if (directory / "app.config.ts").exists():
            signals.append("app.config.ts (Expo)")
            confidence += 0.3

        # Native directories
        if (directory / "android").is_dir():
            signals.append("android/")
            confidence += 0.3
            # Check for build.gradle
            if (directory / "android" / "build.gradle").exists():
                signals.append("android/build.gradle")
                confidence += 0.1

        if (directory / "ios").is_dir():
            signals.append("ios/")
            confidence += 0.3
            # Check for Xcode project
            xcodeproj = list((directory / "ios").glob("*.xcodeproj"))
            if xcodeproj:
                signals.append(f"ios/{xcodeproj[0].name}")
                confidence += 0.1

        # React Native specific
        if (directory / "metro.config.js").exists():
            signals.append("metro.config.js")
            confidence += 0.2

        if (directory / "react-native.config.js").exists():
            signals.append("react-native.config.js")
            confidence += 0.2

        # Flutter detection
        if (directory / "pubspec.yaml").exists():
            signals.append("pubspec.yaml (Flutter/Dart)")
            confidence += 0.5

        if signals:
            return DetectionResult(
                project_type="mobile",
                confidence=min(confidence, 1.0),
                signals=signals,
            )
        return None

    def _detect_rust(self, directory: Path) -> Optional[DetectionResult]:
        """Detect Rust project."""
        if (directory / "Cargo.toml").exists():
            signals = ["Cargo.toml"]
            confidence = 0.7

            if (directory / "src" / "main.rs").exists():
                signals.append("src/main.rs")
                confidence += 0.2
            if (directory / "src" / "lib.rs").exists():
                signals.append("src/lib.rs")
                confidence += 0.1

            return DetectionResult(
                project_type="rust",
                confidence=min(confidence, 1.0),
                signals=signals,
            )
        return None

    def _detect_go(self, directory: Path) -> Optional[DetectionResult]:
        """Detect Go project."""
        if (directory / "go.mod").exists():
            signals = ["go.mod"]
            confidence = 0.7

            if (directory / "main.go").exists():
                signals.append("main.go")
                confidence += 0.2
            if (directory / "go.sum").exists():
                signals.append("go.sum")
                confidence += 0.1

            return DetectionResult(
                project_type="go",
                confidence=min(confidence, 1.0),
                signals=signals,
            )
        return None

    def _detect_java(self, directory: Path) -> Optional[DetectionResult]:
        """Detect Java/Kotlin project."""
        signals: list[str] = []
        confidence = 0.0

        if (directory / "pom.xml").exists():
            signals.append("pom.xml")
            confidence += 0.6
        if (directory / "build.gradle").exists():
            signals.append("build.gradle")
            confidence += 0.5
        if (directory / "build.gradle.kts").exists():
            signals.append("build.gradle.kts")
            confidence += 0.5

        if signals:
            project_type = "java-maven" if "pom.xml" in signals else "java-gradle"
            return DetectionResult(
                project_type=project_type,
                confidence=min(confidence, 1.0),
                signals=signals,
            )
        return None


@dataclass
class ScanResult:
    """Result of a workspace scan operation."""

    success: bool
    error: Optional[str] = None
    projects: list[ProjectInfo] = field(default_factory=list)


class WorkspaceScanner:
    """Scans workspace to detect projects."""

    def __init__(self, config: BrainConfig) -> None:
        self.config = config
        self.detector = ProjectDetector()

    def scan(self, max_depth: int = 3) -> ScanResult:
        """Scan the workspace for projects.

        Looks for project markers (package.json, pyproject.toml, etc.)
        and updates MANIFEST.yaml with detected projects.

        Args:
            max_depth: Maximum directory depth to scan (default 3)
        """
        result = ScanResult(success=True)

        try:
            # Check if brain exists
            if not self.config.brain_path.exists():
                result.success = False
                result.error = f"Brain not found at {self.config.brain_path}. Run 'init' first."
                return result

            # Scan for projects
            projects = self._scan_directory(
                self.config.workspace_path,
                current_depth=0,
                max_depth=max_depth,
            )

            # Sort by confidence (highest first)
            projects.sort(key=lambda p: p.confidence, reverse=True)
            result.projects = projects

            # Update manifest
            self._update_manifest(projects)

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _scan_directory(
        self,
        directory: Path,
        current_depth: int,
        max_depth: int,
    ) -> list[ProjectInfo]:
        """Recursively scan directory for projects."""
        projects: list[ProjectInfo] = []

        if current_depth > max_depth:
            return projects

        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return projects

        # Check if this directory is a project
        detection = self.detector.detect(directory)
        if detection:
            projects.append(
                ProjectInfo(
                    name=directory.name,
                    path=str(directory),
                    project_type=detection.project_type,
                    confidence=detection.confidence,
                    signals=detection.signals,
                    detected_at=datetime.now(),
                )
            )
            # Don't scan subdirectories of detected projects
            return projects

        # Recursively scan subdirectories
        for entry in entries:
            if entry.is_dir() and entry.name not in SKIP_DIRS:
                sub_projects = self._scan_directory(
                    entry,
                    current_depth + 1,
                    max_depth,
                )
                projects.extend(sub_projects)

        return projects

    def _update_manifest(self, projects: list[ProjectInfo]) -> None:
        """Update MANIFEST.yaml with detected projects."""
        # Load existing manifest or create new
        manifest = self._load_manifest()
        if manifest is None:
            manifest = BrainManifest(
                workspace_path=str(self.config.workspace_path),
            )

        # Update projects and timestamp
        manifest.detected_projects = projects
        manifest.updated_at = datetime.now()

        # Write manifest
        content = yaml.dump(
            manifest.to_yaml_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        self.config.manifest_path.write_text(content, encoding="utf-8")

    def _load_manifest(self) -> Optional[BrainManifest]:
        """Load existing MANIFEST.yaml if present."""
        if not self.config.manifest_path.exists():
            return None

        try:
            content = self.config.manifest_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if data is None:
                return None

            created_at = data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            return BrainManifest(
                workspace_path=data["workspace_path"],
                brain_version=data.get("brain_version", "1.0"),
                created_at=created_at or datetime.now(),
                detected_projects=[],  # Will be replaced
            )

        except (yaml.YAMLError, KeyError, TypeError):
            return None
