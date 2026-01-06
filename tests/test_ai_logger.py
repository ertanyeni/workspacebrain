"""Tests for AI session logging module."""

from datetime import datetime
from pathlib import Path

import pytest

from workspacebrain.core.ai_logger import AISessionLogger
from workspacebrain.models import AISessionEntry, BrainConfig


@pytest.fixture
def workspace_with_logs(temp_workspace_with_brain: Path) -> Path:
    """Create workspace with LOGS directory."""
    logs_dir = temp_workspace_with_brain / "brain" / "LOGS"
    logs_dir.mkdir(exist_ok=True)
    return temp_workspace_with_brain


class TestAISessionLogger:
    """Tests for AISessionLogger class."""

    def test_log_session_creates_log_file(self, workspace_with_logs: Path) -> None:
        """Test that log_session creates a daily log file."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        logger = AISessionLogger(config)

        entry = AISessionEntry(
            project_name="backend",
            ai_tool="claude",
            summary="Added user authentication",
        )

        log_file = logger.log_session(entry)

        assert log_file.exists()
        content = log_file.read_text()
        assert "# Work Log -" in content
        assert "## Session:" in content
        assert "backend" in content
        assert "claude" in content
        assert "Added user authentication" in content

    def test_log_session_appends_to_existing(self, workspace_with_logs: Path) -> None:
        """Test that multiple sessions are appended to same daily file."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        logger = AISessionLogger(config)

        entry1 = AISessionEntry(
            project_name="backend",
            ai_tool="claude",
            summary="First session",
        )
        entry2 = AISessionEntry(
            project_name="frontend",
            ai_tool="cursor",
            summary="Second session",
        )

        log_file = logger.log_session(entry1)
        logger.log_session(entry2)

        content = log_file.read_text()
        assert "First session" in content
        assert "Second session" in content
        assert "backend" in content
        assert "frontend" in content

    def test_log_session_with_all_fields(self, workspace_with_logs: Path) -> None:
        """Test logging session with all optional fields."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        logger = AISessionLogger(config)

        entry = AISessionEntry(
            project_name="backend",
            ai_tool="claude",
            summary="Added JWT auth",
            what_was_done=["Created auth endpoint", "Added token validation"],
            reasoning="JWT for stateless auth, mobile app compatibility",
            related_projects={"frontend": "Will need to call this endpoint"},
            open_questions=["Use refresh tokens?", "Token expiry time?"],
            key_files=["auth/routes.py", "auth/jwt.py"],
        )

        log_file = logger.log_session(entry)
        content = log_file.read_text()

        assert "### What Was Done" in content
        assert "Created auth endpoint" in content
        assert "### AI Reasoning" in content
        assert "JWT for stateless auth" in content
        assert "### Related Projects" in content
        assert "**frontend**" in content
        assert "### Open Questions" in content
        assert "Use refresh tokens?" in content
        assert "### Key Files" in content
        assert "auth/routes.py" in content

    def test_parse_stdin_log_simple(self, workspace_with_logs: Path) -> None:
        """Test parsing simple heredoc-style input."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        logger = AISessionLogger(config)

        stdin_content = """## Summary
Added user authentication endpoint

## What Was Done
- Created login route
- Added JWT tokens

## AI Reasoning
Using JWT for stateless auth
"""

        result = logger.parse_stdin_log(stdin_content)

        assert result["summary"] == "Added user authentication endpoint"
        assert len(result["what_was_done"]) == 2
        assert "Created login route" in result["what_was_done"]
        assert result["reasoning"] == "Using JWT for stateless auth"

    def test_parse_stdin_log_with_related_projects(
        self, workspace_with_logs: Path
    ) -> None:
        """Test parsing related projects from stdin."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        logger = AISessionLogger(config)

        stdin_content = """## Summary
Added API endpoint

## Related Projects
- **frontend**: Will need to call this endpoint
- **mobile**: Same auth needed
"""

        result = logger.parse_stdin_log(stdin_content)

        assert "frontend" in result["related_projects"]
        assert "mobile" in result["related_projects"]
        assert "call this endpoint" in result["related_projects"]["frontend"]

    def test_create_entry_from_args(self, workspace_with_logs: Path) -> None:
        """Test creating entry from CLI arguments."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        logger = AISessionLogger(config)

        entry = logger.create_entry_from_args(
            summary="Added auth",
            project="backend",
            tool="claude",
            reasoning="JWT for mobile",
            related="frontend:needs update,mobile:same auth",
            questions="refresh tokens?,expiry time?",
            files="auth.py,routes.py",
        )

        assert entry.project_name == "backend"
        assert entry.ai_tool == "claude"
        assert entry.summary == "Added auth"
        assert entry.reasoning == "JWT for mobile"
        assert "frontend" in entry.related_projects
        assert len(entry.open_questions) == 2
        assert len(entry.key_files) == 2


class TestAISessionEntry:
    """Tests for AISessionEntry model."""

    def test_to_markdown_minimal(self) -> None:
        """Test markdown output with minimal fields."""
        entry = AISessionEntry(
            project_name="test",
            ai_tool="claude",
            summary="Test summary",
        )

        md = entry.to_markdown()

        assert "## Session:" in md
        assert "test" in md
        assert "claude" in md
        assert "### Summary" in md
        assert "Test summary" in md
        assert "---" in md

    def test_to_markdown_full(self) -> None:
        """Test markdown output with all fields."""
        entry = AISessionEntry(
            project_name="backend",
            ai_tool="cursor",
            summary="Full test",
            what_was_done=["Task 1", "Task 2"],
            reasoning="Good reasoning",
            related_projects={"frontend": "Related"},
            open_questions=["Question 1"],
            key_files=["file.py"],
            previous_context_used="Used previous context",
        )

        md = entry.to_markdown()

        assert "### What Was Done" in md
        assert "- Task 1" in md
        assert "### AI Reasoning" in md
        assert "Good reasoning" in md
        assert "### Related Projects" in md
        assert "**frontend**" in md
        assert "### Open Questions" in md
        assert "### Key Files" in md
        assert "`file.py`" in md
        assert "### Previous Context Used" in md
