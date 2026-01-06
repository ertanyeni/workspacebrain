"""AI session logging module for cross-project context sharing."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import AISessionEntry, BrainConfig


class AISessionLogger:
    """Handles structured AI session logging."""

    def __init__(self, config: BrainConfig):
        self.config = config

    def log_session(self, entry: AISessionEntry) -> Path:
        """Append session entry to daily log file.

        Returns the path to the log file.
        """
        logs_dir = self.config.logs_path
        logs_dir.mkdir(parents=True, exist_ok=True)

        date_str = entry.timestamp.strftime("%Y-%m-%d")
        log_file = logs_dir / f"{date_str}.md"

        # Create daily header if file doesn't exist
        if not log_file.exists():
            header = f"# Work Log - {date_str}\n\n"
            log_file.write_text(header)

        # Append session entry
        with log_file.open("a") as f:
            f.write(entry.to_markdown())

        return log_file

    def parse_stdin_log(self, stdin_content: str) -> dict:
        """Parse heredoc-style log input from stdin.

        Expected format:
        ## Summary
        Some summary text

        ## What Was Done
        - Item 1
        - Item 2

        ## AI Reasoning
        Reasoning text

        ## Related Projects
        - **project1**: reason1

        ## Open Questions
        - Question 1

        ## Key Files
        - file1.py
        """
        result = {
            "summary": "",
            "what_was_done": [],
            "reasoning": None,
            "related_projects": {},
            "open_questions": [],
            "key_files": [],
        }

        current_section = None
        current_content = []

        for line in stdin_content.strip().split("\n"):
            # Check for section headers
            if line.startswith("## "):
                # Save previous section
                if current_section:
                    self._save_section(result, current_section, current_content)
                current_section = line[3:].strip().lower()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            self._save_section(result, current_section, current_content)

        return result

    def _save_section(self, result: dict, section: str, content: list[str]) -> None:
        """Save parsed section content to result dict."""
        text = "\n".join(content).strip()

        if section == "summary":
            result["summary"] = text
        elif section in ("what was done", "what_was_done"):
            result["what_was_done"] = self._parse_bullet_list(content)
        elif section in ("ai reasoning", "reasoning"):
            result["reasoning"] = text if text else None
        elif section in ("related projects", "related_projects"):
            result["related_projects"] = self._parse_related_projects(content)
        elif section in ("open questions", "open_questions"):
            result["open_questions"] = self._parse_bullet_list(content)
        elif section in ("key files", "key_files"):
            result["key_files"] = self._parse_file_list(content)

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
        """Parse related projects from bullet list.

        Format: - **project**: reason
        """
        projects = {}
        pattern = re.compile(r"^-\s*\*\*([^*]+)\*\*:\s*(.+)$")

        for line in lines:
            line = line.strip()
            match = pattern.match(line)
            if match:
                projects[match.group(1).strip()] = match.group(2).strip()
            elif line.startswith("- "):
                # Simple format: - project: reason
                if ":" in line:
                    parts = line[2:].split(":", 1)
                    projects[parts[0].strip()] = parts[1].strip()

        return projects

    def _parse_file_list(self, lines: list[str]) -> list[str]:
        """Parse file list, removing backticks and bullets."""
        files = []
        for line in lines:
            line = line.strip()
            if line.startswith("- "):
                file_part = line[2:].strip()
                # Remove backticks
                file_part = file_part.strip("`")
                # Remove description after " - "
                if " - " in file_part:
                    file_part = file_part.split(" - ")[0].strip()
                if file_part:
                    files.append(file_part)
        return files

    def create_entry_from_args(
        self,
        summary: str,
        project: str,
        tool: str = "generic",
        project_type: str = "unknown",
        reasoning: Optional[str] = None,
        related: Optional[str] = None,
        questions: Optional[str] = None,
        files: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> AISessionEntry:
        """Create an AISessionEntry from CLI arguments."""
        # Parse comma-separated values
        what_was_done = [summary]  # Summary is the main action

        related_projects = {}
        if related:
            for item in related.split(","):
                item = item.strip()
                if ":" in item:
                    proj, reason = item.split(":", 1)
                    related_projects[proj.strip()] = reason.strip()
                else:
                    related_projects[item] = "Related"

        open_questions = []
        if questions:
            open_questions = [q.strip() for q in questions.split(",") if q.strip()]

        key_files = []
        if files:
            key_files = [f.strip() for f in files.split(",") if f.strip()]

        tag_list = []
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        return AISessionEntry(
            project_name=project,
            project_type=project_type,
            ai_tool=tool,
            summary=summary,
            what_was_done=what_was_done,
            reasoning=reasoning,
            related_projects=related_projects,
            open_questions=open_questions,
            key_files=key_files,
            tags=tag_list,
        )
