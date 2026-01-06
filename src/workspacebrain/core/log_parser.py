"""Log file parsing module for extracting structured data from daily logs."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import AISessionEntry, BrainConfig


class LogParser:
    """Parses existing log files into structured data."""

    # Regex patterns for parsing
    SESSION_HEADER = re.compile(
        r"^##\s+Session:\s+(\d{1,2}:\d{2})\s+-\s+(.+?)\s+\((.+?)\)\s*$"
    )
    SECTION_HEADER = re.compile(r"^###\s+(.+?)\s*$")

    def __init__(self, config: BrainConfig):
        self.config = config

    def parse_daily_log(self, log_path: Path) -> list[AISessionEntry]:
        """Parse a daily log file into session entries."""
        if not log_path.exists():
            return []

        content = log_path.read_text()
        entries = []

        # Extract date from filename
        date_str = log_path.stem  # e.g., "2026-01-06"
        try:
            log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            log_date = datetime.now().date()

        # Split by session headers
        sessions = re.split(r"(?=^## Session:)", content, flags=re.MULTILINE)

        for session in sessions:
            if not session.strip() or not session.startswith("## Session:"):
                continue

            entry = self._parse_session(session, log_date)
            if entry:
                entries.append(entry)

        return entries

    def _parse_session(
        self, session_text: str, log_date: datetime
    ) -> Optional[AISessionEntry]:
        """Parse a single session block into an AISessionEntry."""
        lines = session_text.strip().split("\n")
        if not lines:
            return None

        # Parse header: ## Session: HH:MM - project (tool)
        header_match = self.SESSION_HEADER.match(lines[0])
        if not header_match:
            return None

        time_str = header_match.group(1)
        project_name = header_match.group(2)
        ai_tool = header_match.group(3)

        # Parse time
        try:
            hour, minute = map(int, time_str.split(":"))
            timestamp = datetime.combine(
                log_date, datetime.min.time().replace(hour=hour, minute=minute)
            )
        except ValueError:
            timestamp = datetime.now()

        # Parse sections
        sections = self._parse_sections(lines[1:])

        return AISessionEntry(
            timestamp=timestamp,
            project_name=project_name,
            ai_tool=ai_tool,
            summary=sections.get("summary", ""),
            what_was_done=sections.get("what_was_done", []),
            reasoning=sections.get("reasoning"),
            related_projects=sections.get("related_projects", {}),
            open_questions=sections.get("open_questions", []),
            key_files=sections.get("key_files", []),
            previous_context_used=sections.get("previous_context_used"),
        )

    def _parse_sections(self, lines: list[str]) -> dict:
        """Parse sections from session content."""
        result = {
            "summary": "",
            "what_was_done": [],
            "reasoning": None,
            "related_projects": {},
            "open_questions": [],
            "key_files": [],
            "previous_context_used": None,
        }

        current_section = None
        current_content = []

        for line in lines:
            # Check for section headers
            match = self.SECTION_HEADER.match(line)
            if match:
                # Save previous section
                if current_section:
                    self._save_section(result, current_section, current_content)
                current_section = match.group(1).lower().strip()
                current_content = []
            elif line.strip() == "---":
                # End of session
                break
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            self._save_section(result, current_section, current_content)

        return result

    def _save_section(self, result: dict, section: str, content: list[str]) -> None:
        """Save parsed section content to result dict."""
        text = "\n".join(content).strip()

        section_map = {
            "summary": "summary",
            "what was done": "what_was_done",
            "ai reasoning": "reasoning",
            "related projects": "related_projects",
            "open questions": "open_questions",
            "key files": "key_files",
            "previous context used": "previous_context_used",
        }

        key = section_map.get(section)
        if not key:
            return

        if key == "summary":
            result["summary"] = text
        elif key == "reasoning":
            result["reasoning"] = text if text else None
        elif key == "previous_context_used":
            result["previous_context_used"] = text if text else None
        elif key == "what_was_done":
            result["what_was_done"] = self._parse_bullet_list(content)
        elif key == "open_questions":
            result["open_questions"] = self._parse_bullet_list(content)
        elif key == "key_files":
            result["key_files"] = self._parse_file_list(content)
        elif key == "related_projects":
            result["related_projects"] = self._parse_related_projects(content)

    def _parse_bullet_list(self, lines: list[str]) -> list[str]:
        """Parse bullet list items."""
        items = []
        for line in lines:
            line = line.strip()
            if line.startswith("- "):
                items.append(line[2:].strip())
            elif line.startswith("* "):
                items.append(line[2:].strip())
        return items

    def _parse_related_projects(self, lines: list[str]) -> dict[str, str]:
        """Parse related projects from bullet list."""
        projects = {}
        pattern = re.compile(r"^-\s*\*\*([^*]+)\*\*:\s*(.+)$")

        for line in lines:
            line = line.strip()
            match = pattern.match(line)
            if match:
                projects[match.group(1).strip()] = match.group(2).strip()

        return projects

    def _parse_file_list(self, lines: list[str]) -> list[str]:
        """Parse file list, removing backticks and bullets."""
        files = []
        for line in lines:
            line = line.strip()
            if line.startswith("- "):
                file_part = line[2:].strip().strip("`")
                if " - " in file_part:
                    file_part = file_part.split(" - ")[0].strip()
                if file_part:
                    files.append(file_part)
        return files

    def get_logs_in_range(self, days: int = 3) -> list[AISessionEntry]:
        """Get all session entries from the last N days."""
        from datetime import timedelta

        logs_dir = self.config.logs_path
        if not logs_dir.exists():
            return []

        entries = []
        today = datetime.now().date()

        for i in range(days):
            date = today - timedelta(days=i)
            log_file = logs_dir / f"{date.strftime('%Y-%m-%d')}.md"
            if log_file.exists():
                entries.extend(self.parse_daily_log(log_file))

        # Sort by timestamp descending (newest first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries

    def extract_open_questions(
        self, entries: list[AISessionEntry]
    ) -> list[dict[str, str]]:
        """Extract all open questions with project attribution."""
        questions = []
        for entry in entries:
            for q in entry.open_questions:
                questions.append(
                    {
                        "project": entry.project_name,
                        "question": q,
                        "timestamp": entry.timestamp.isoformat(),
                        "ai_tool": entry.ai_tool,
                    }
                )
        return questions

    def extract_project_relationships(
        self, entries: list[AISessionEntry]
    ) -> dict[str, set[str]]:
        """Build project relationship graph from logs.

        Returns a dict mapping project -> set of related projects.
        """
        relationships: dict[str, set[str]] = {}

        for entry in entries:
            project = entry.project_name
            if project not in relationships:
                relationships[project] = set()

            for related in entry.related_projects.keys():
                relationships[project].add(related)

                # Add reverse relationship
                if related not in relationships:
                    relationships[related] = set()
                relationships[related].add(project)

        return relationships
