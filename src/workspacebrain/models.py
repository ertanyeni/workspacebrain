"""Pydantic models for WorkspaceBrain."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ProjectInfo(BaseModel):
    """Information about a detected project in the workspace."""

    name: str
    path: str
    project_type: str  # e.g., "python-be", "node-fe", "mobile"
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    signals: list[str] = Field(default_factory=list)  # Files/dirs that triggered detection
    detected_at: datetime = Field(default_factory=datetime.now)


class BrainManifest(BaseModel):
    """MANIFEST.yaml schema for the brain directory."""

    workspace_path: str
    brain_version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    detected_projects: list[ProjectInfo] = Field(default_factory=list)

    def to_yaml_dict(self) -> dict:
        """Convert to a dictionary suitable for YAML serialization."""
        return {
            "workspace_path": self.workspace_path,
            "brain_version": self.brain_version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "detected_projects": [
                {
                    "name": p.name,
                    "path": p.path,
                    "type": p.project_type,
                    "confidence": p.confidence,
                    "signals": p.signals,
                    "detected_at": p.detected_at.isoformat(),
                }
                for p in self.detected_projects
            ],
        }


class BrainConfig(BaseModel):
    """Configuration for WorkspaceBrain operations."""

    workspace_path: Path
    brain_dir_name: str = "brain"
    force: bool = False

    @property
    def brain_path(self) -> Path:
        """Get the full path to the brain directory."""
        return self.workspace_path / self.brain_dir_name

    @property
    def manifest_path(self) -> Path:
        """Get the path to MANIFEST.yaml."""
        return self.brain_path / "MANIFEST.yaml"

    @property
    def readme_path(self) -> Path:
        """Get the path to README.md."""
        return self.brain_path / "README.md"

    @property
    def decisions_path(self) -> Path:
        """Get the path to DECISIONS.md."""
        return self.brain_path / "DECISIONS.md"

    @property
    def contracts_path(self) -> Path:
        """Get the path to CONTRACTS directory."""
        return self.brain_path / "CONTRACTS"

    @property
    def handoffs_path(self) -> Path:
        """Get the path to HANDOFFS directory."""
        return self.brain_path / "HANDOFFS"

    @property
    def rules_path(self) -> Path:
        """Get the path to RULES directory."""
        return self.brain_path / "RULES"
