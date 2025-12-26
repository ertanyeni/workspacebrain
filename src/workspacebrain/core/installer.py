"""Brain installation module - creates and manages brain directory structure."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from workspacebrain.models import BrainConfig, BrainManifest
from workspacebrain.templates.content import (
    get_decisions_template,
    get_readme_template,
    get_rules_index_template,
)


@dataclass
class InstallResult:
    """Result of a brain installation operation."""

    success: bool
    error: Optional[str] = None
    created_paths: list[str] = field(default_factory=list)
    skipped_paths: list[str] = field(default_factory=list)


class BrainInstaller:
    """Handles brain directory creation and initialization."""

    def __init__(self, config: BrainConfig) -> None:
        self.config = config

    def install(self) -> InstallResult:
        """Install the brain directory structure.

        Creates:
        - brain/README.md
        - brain/MANIFEST.yaml
        - brain/DECISIONS.md
        - brain/CONTRACTS/
        - brain/HANDOFFS/
        - brain/RULES/

        If force=False, existing files/directories are skipped (idempotent).
        If force=True, existing files are overwritten.
        """
        result = InstallResult(success=True)

        try:
            # Create brain directory
            self._create_directory(self.config.brain_path, result)

            # Create subdirectories
            self._create_directory(self.config.contracts_path, result)
            self._create_directory(self.config.handoffs_path, result)
            self._create_directory(self.config.rules_path, result)

            # Create files
            self._create_readme(result)
            self._create_manifest(result)
            self._create_decisions(result)
            self._create_rules_index(result)

            # Create .gitkeep files in empty directories
            self._create_gitkeep(self.config.contracts_path, result)
            self._create_gitkeep(self.config.handoffs_path, result)

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _create_directory(self, path: Path, result: InstallResult) -> None:
        """Create a directory if it doesn't exist."""
        if path.exists():
            result.skipped_paths.append(str(path.relative_to(self.config.workspace_path)))
        else:
            path.mkdir(parents=True, exist_ok=True)
            result.created_paths.append(str(path.relative_to(self.config.workspace_path)))

    def _create_file(
        self, path: Path, content: str, result: InstallResult
    ) -> None:
        """Create a file with content, respecting force flag."""
        relative_path = str(path.relative_to(self.config.workspace_path))

        if path.exists() and not self.config.force:
            result.skipped_paths.append(relative_path)
            return

        path.write_text(content, encoding="utf-8")
        result.created_paths.append(relative_path)

    def _create_readme(self, result: InstallResult) -> None:
        """Create README.md with template content."""
        content = get_readme_template(self.config.workspace_path.name)
        self._create_file(self.config.readme_path, content, result)

    def _create_manifest(self, result: InstallResult) -> None:
        """Create MANIFEST.yaml with initial content."""
        # If manifest exists and not forcing, check if we should update
        if self.config.manifest_path.exists() and not self.config.force:
            result.skipped_paths.append(
                str(self.config.manifest_path.relative_to(self.config.workspace_path))
            )
            return

        manifest = BrainManifest(
            workspace_path=str(self.config.workspace_path),
        )

        content = yaml.dump(
            manifest.to_yaml_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        self._create_file(self.config.manifest_path, content, result)

    def _create_decisions(self, result: InstallResult) -> None:
        """Create DECISIONS.md with template content."""
        content = get_decisions_template()
        self._create_file(self.config.decisions_path, content, result)

    def _create_rules_index(self, result: InstallResult) -> None:
        """Create RULES/INDEX.md with template content."""
        index_path = self.config.rules_path / "INDEX.md"
        content = get_rules_index_template()
        self._create_file(index_path, content, result)

    def _create_gitkeep(self, dir_path: Path, result: InstallResult) -> None:
        """Create .gitkeep file in empty directory."""
        gitkeep_path = dir_path / ".gitkeep"
        if not gitkeep_path.exists():
            gitkeep_path.touch()
            result.created_paths.append(
                str(gitkeep_path.relative_to(self.config.workspace_path))
            )
