"""Tests for log parsing module."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from workspacebrain.core.log_parser import LogParser
from workspacebrain.models import BrainConfig


@pytest.fixture
def workspace_with_logs(temp_workspace_with_brain: Path) -> Path:
    """Create workspace with LOGS directory and sample logs."""
    logs_dir = temp_workspace_with_brain / "brain" / "LOGS"
    logs_dir.mkdir(exist_ok=True)

    # Create today's log
    today = datetime.now()
    today_log = logs_dir / f"{today.strftime('%Y-%m-%d')}.md"
    today_log.write_text("""# Work Log - {date}

## Session: 14:30 - backend (claude)

### Summary
Added JWT authentication endpoint

### What Was Done
- Created /api/auth/login endpoint
- Added token validation

### AI Reasoning
Using JWT for stateless auth because mobile app needs it

### Related Projects
- **frontend**: Will need to implement token storage

### Open Questions
- Should we use refresh tokens?
- What token expiry time?

### Key Files
- `auth/routes.py`
- `auth/jwt_handler.py`

---

## Session: 16:00 - frontend (cursor)

### Summary
Started login form implementation

### What Was Done
- Created LoginForm component

### Related Projects
- **backend**: Using the new auth endpoint

---

""".format(date=today.strftime('%Y-%m-%d')))

    # Create yesterday's log
    yesterday = today - timedelta(days=1)
    yesterday_log = logs_dir / f"{yesterday.strftime('%Y-%m-%d')}.md"
    yesterday_log.write_text("""# Work Log - {date}

## Session: 10:00 - backend (claude)

### Summary
Set up project structure

### What Was Done
- Initialized FastAPI app
- Added database models

---

""".format(date=yesterday.strftime('%Y-%m-%d')))

    return temp_workspace_with_brain


class TestLogParser:
    """Tests for LogParser class."""

    def test_parse_daily_log(self, workspace_with_logs: Path) -> None:
        """Test parsing a daily log file."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        parser = LogParser(config)

        today = datetime.now()
        log_file = config.logs_path / f"{today.strftime('%Y-%m-%d')}.md"

        entries = parser.parse_daily_log(log_file)

        assert len(entries) == 2

        # Check first entry
        assert entries[0].project_name == "backend"
        assert entries[0].ai_tool == "claude"
        assert "JWT authentication" in entries[0].summary
        assert len(entries[0].what_was_done) == 2
        assert entries[0].reasoning is not None
        assert "frontend" in entries[0].related_projects
        assert len(entries[0].open_questions) == 2
        assert len(entries[0].key_files) == 2

        # Check second entry
        assert entries[1].project_name == "frontend"
        assert entries[1].ai_tool == "cursor"

    def test_get_logs_in_range(self, workspace_with_logs: Path) -> None:
        """Test getting logs from multiple days."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        parser = LogParser(config)

        entries = parser.get_logs_in_range(days=3)

        # Should have entries from both today and yesterday
        assert len(entries) >= 3

        # Check entries are sorted by timestamp (newest first)
        for i in range(len(entries) - 1):
            assert entries[i].timestamp >= entries[i + 1].timestamp

    def test_extract_open_questions(self, workspace_with_logs: Path) -> None:
        """Test extracting open questions from entries."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        parser = LogParser(config)

        entries = parser.get_logs_in_range(days=3)
        questions = parser.extract_open_questions(entries)

        assert len(questions) >= 2
        assert any("refresh tokens" in q["question"] for q in questions)
        assert all("project" in q for q in questions)
        assert all("timestamp" in q for q in questions)

    def test_extract_project_relationships(self, workspace_with_logs: Path) -> None:
        """Test extracting project relationships from entries."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        parser = LogParser(config)

        entries = parser.get_logs_in_range(days=3)
        relationships = parser.extract_project_relationships(entries)

        assert "backend" in relationships
        assert "frontend" in relationships
        # Check bidirectional relationship
        assert "frontend" in relationships["backend"]
        assert "backend" in relationships["frontend"]

    def test_parse_nonexistent_file(self, workspace_with_logs: Path) -> None:
        """Test parsing a file that doesn't exist."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        parser = LogParser(config)

        nonexistent = config.logs_path / "2000-01-01.md"
        entries = parser.parse_daily_log(nonexistent)

        assert entries == []

    def test_parse_empty_logs_directory(self, temp_workspace_with_brain: Path) -> None:
        """Test getting logs when directory is empty."""
        config = BrainConfig(workspace_path=temp_workspace_with_brain)
        parser = LogParser(config)

        entries = parser.get_logs_in_range(days=7)

        assert entries == []
