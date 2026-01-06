"""Relationship management module for tracking project dependencies.

This module handles:
1. Discovering relationships from log entries
2. Persisting relationships to relationships.yaml
3. Building a relationship graph for context filtering
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from ..models import BrainConfig, ProjectRelationship
from .log_parser import LogParser


class RelationshipManager:
    """Manages project relationships discovered from logs."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self.parser = LogParser(config)
        self._relationships: dict[str, list[ProjectRelationship]] = {}
        self._load_relationships()

    def _load_relationships(self) -> None:
        """Load relationships from relationships.yaml."""
        if not self.config.relationships_path.exists():
            self._relationships = {}
            return

        try:
            content = self.config.relationships_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content) or {}

            for source, targets in data.get("relationships", {}).items():
                self._relationships[source] = []
                for target_data in targets:
                    self._relationships[source].append(
                        ProjectRelationship(
                            source_project=source,
                            target_project=target_data["target"],
                            reason=target_data.get("reason", ""),
                            discovered_at=datetime.fromisoformat(
                                target_data.get(
                                    "discovered_at", datetime.now().isoformat()
                                )
                            ),
                            last_seen=datetime.fromisoformat(
                                target_data.get("last_seen", datetime.now().isoformat())
                            ),
                        )
                    )
        except (yaml.YAMLError, KeyError, ValueError):
            self._relationships = {}

    def save_relationships(self) -> None:
        """Save relationships to relationships.yaml."""
        data = {"relationships": {}, "updated_at": datetime.now().isoformat()}

        for source, rels in self._relationships.items():
            data["relationships"][source] = [
                {
                    "target": r.target_project,
                    "reason": r.reason,
                    "discovered_at": r.discovered_at.isoformat(),
                    "last_seen": r.last_seen.isoformat(),
                }
                for r in rels
            ]

        self.config.relationships_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.relationships_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    def refresh_from_logs(self, days: int = 7) -> dict[str, set[str]]:
        """Refresh relationships from recent logs.

        Returns the updated relationship graph.
        """
        entries = self.parser.get_logs_in_range(days)
        now = datetime.now()

        for entry in entries:
            source = entry.project_name
            if source not in self._relationships:
                self._relationships[source] = []

            for target, reason in entry.related_projects.items():
                # Check if relationship already exists
                existing = self._find_relationship(source, target)
                if existing:
                    existing.last_seen = now
                    existing.reason = reason  # Update with latest reason
                else:
                    self._relationships[source].append(
                        ProjectRelationship(
                            source_project=source,
                            target_project=target,
                            reason=reason,
                            discovered_at=entry.timestamp,
                            last_seen=now,
                        )
                    )

        self.save_relationships()
        return self.get_relationship_graph()

    def _find_relationship(
        self, source: str, target: str
    ) -> Optional[ProjectRelationship]:
        """Find an existing relationship between source and target."""
        for rel in self._relationships.get(source, []):
            if rel.target_project == target:
                return rel
        return None

    def get_relationship_graph(self) -> dict[str, set[str]]:
        """Build bidirectional relationship graph.

        Returns a dict mapping project -> set of related projects.
        Both directions are included (A->B means B is in A's set AND A is in B's set).
        """
        graph: dict[str, set[str]] = {}

        for source, rels in self._relationships.items():
            if source not in graph:
                graph[source] = set()

            for rel in rels:
                target = rel.target_project
                graph[source].add(target)

                # Add reverse relationship
                if target not in graph:
                    graph[target] = set()
                graph[target].add(source)

        return graph

    def get_related_projects(self, project_name: str) -> set[str]:
        """Get all projects related to the given project.

        Returns a set of project names that are directly related.
        """
        graph = self.get_relationship_graph()
        return graph.get(project_name, set())

    def get_context_projects(self, project_name: str) -> list[str]:
        """Get list of projects whose context should be included.

        This returns the project itself plus all directly related projects.
        Order: self first, then related projects alphabetically.
        """
        related = self.get_related_projects(project_name)
        result = [project_name]
        result.extend(sorted(related))
        return result

    def get_all_relationships(self) -> list[tuple[str, str, str]]:
        """Get all relationships as (source, target, reason) tuples."""
        result = []
        for source, rels in self._relationships.items():
            for rel in rels:
                result.append((source, rel.target_project, rel.reason))
        return result

    def add_relationship(
        self, source: str, target: str, reason: str = ""
    ) -> ProjectRelationship:
        """Manually add a relationship between projects."""
        if source not in self._relationships:
            self._relationships[source] = []

        existing = self._find_relationship(source, target)
        if existing:
            existing.last_seen = datetime.now()
            if reason:
                existing.reason = reason
            return existing

        rel = ProjectRelationship(
            source_project=source,
            target_project=target,
            reason=reason,
        )
        self._relationships[source].append(rel)
        self.save_relationships()
        return rel

    def remove_relationship(self, source: str, target: str) -> bool:
        """Remove a relationship between projects."""
        if source not in self._relationships:
            return False

        original_len = len(self._relationships[source])
        self._relationships[source] = [
            r for r in self._relationships[source] if r.target_project != target
        ]

        if len(self._relationships[source]) < original_len:
            self.save_relationships()
            return True
        return False
