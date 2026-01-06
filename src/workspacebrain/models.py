"""Pydantic models for WorkspaceBrain."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ProjectRelationship(BaseModel):
    """Represents a relationship between two projects.

    Relationships are automatically discovered from log entries
    when one project mentions another in its related_projects field.
    """

    source_project: str  # Project that created the log entry
    target_project: str  # Project mentioned in related_projects
    reason: str  # Why they're related (from log entry)
    discovered_at: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "source": self.source_project,
            "target": self.target_project,
            "reason": self.reason,
            "discovered_at": self.discovered_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }


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

    @property
    def logs_path(self) -> Path:
        """Get the path to LOGS directory."""
        return self.brain_path / "LOGS"

    @property
    def context_path(self) -> Path:
        """Get the path to CONTEXT directory."""
        return self.brain_path / "CONTEXT"

    @property
    def context_projects_path(self) -> Path:
        """Get the path to project-specific context files."""
        return self.context_path / "projects"

    @property
    def relationships_path(self) -> Path:
        """Get the path to relationships.yaml file."""
        return self.brain_path / "relationships.yaml"


class AISessionEntry(BaseModel):
    """Structured AI session log entry for cross-project context sharing."""

    timestamp: datetime = Field(default_factory=datetime.now)
    project_name: str
    project_type: str = "unknown"
    ai_tool: str = "generic"  # claude, cursor, windsurf, copilot, generic
    summary: str
    what_was_done: list[str] = Field(default_factory=list)
    reasoning: Optional[str] = None
    related_projects: dict[str, str] = Field(default_factory=dict)  # project -> why
    open_questions: list[str] = Field(default_factory=list)
    key_files: list[str] = Field(default_factory=list)
    previous_context_used: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert session entry to markdown format for log file."""
        lines = [
            f"## Session: {self.timestamp.strftime('%H:%M')} - {self.project_name} ({self.ai_tool})",
            "",
            "### Summary",
            self.summary,
            "",
        ]

        if self.what_was_done:
            lines.extend(["### What Was Done"])
            for item in self.what_was_done:
                lines.append(f"- {item}")
            lines.append("")

        if self.reasoning:
            lines.extend(["### AI Reasoning", self.reasoning, ""])

        if self.related_projects:
            lines.append("### Related Projects")
            for project, reason in self.related_projects.items():
                lines.append(f"- **{project}**: {reason}")
            lines.append("")

        if self.open_questions:
            lines.append("### Open Questions")
            for q in self.open_questions:
                lines.append(f"- {q}")
            lines.append("")

        if self.key_files:
            lines.append("### Key Files")
            for f in self.key_files:
                lines.append(f"- `{f}`")
            lines.append("")

        if self.previous_context_used:
            lines.extend(["### Previous Context Used", self.previous_context_used, ""])

        lines.append("---")
        lines.append("")

        return "\n".join(lines)
