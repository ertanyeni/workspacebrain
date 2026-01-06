"""Tests for context generation module."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from workspacebrain.core.context_generator import ContextGenerator
from workspacebrain.models import BrainConfig


@pytest.fixture
def workspace_with_logs(temp_workspace_with_brain: Path) -> Path:
    """Create workspace with LOGS directory and sample logs."""
    logs_dir = temp_workspace_with_brain / "brain" / "LOGS"
    logs_dir.mkdir(exist_ok=True)

    context_dir = temp_workspace_with_brain / "brain" / "CONTEXT"
    context_dir.mkdir(exist_ok=True)

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
Using JWT for stateless auth

### Related Projects
- **frontend**: Will need to implement token storage

### Open Questions
- Should we use refresh tokens?

### Key Files
- `auth/routes.py`

---

## Session: 16:00 - frontend (cursor)

### Summary
Started login form

### Related Projects
- **backend**: Using auth endpoint

---

""".format(date=today.strftime('%Y-%m-%d')))

    return temp_workspace_with_brain


class TestContextGenerator:
    """Tests for ContextGenerator class."""

    def test_refresh_all_context(self, workspace_with_logs: Path) -> None:
        """Test generating all context files."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        generator = ContextGenerator(config)

        generated = generator.refresh_all_context(days=3)

        assert "recent_activity" in generated
        assert "open_questions" in generated
        assert generated["recent_activity"].exists()
        assert generated["open_questions"].exists()

    def test_generate_recent_activity(self, workspace_with_logs: Path) -> None:
        """Test generating RECENT_ACTIVITY.md content."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        generator = ContextGenerator(config)

        content = generator.generate_recent_activity(days=3)

        assert "# Recent Workspace Activity" in content
        assert "Auto-generated" in content
        assert "backend" in content
        assert "frontend" in content
        assert "JWT authentication" in content
        assert "Project Relationships" in content
        assert "Open Questions" in content

    def test_generate_recent_activity_empty(
        self, temp_workspace_with_brain: Path
    ) -> None:
        """Test generating activity when no logs exist."""
        config = BrainConfig(workspace_path=temp_workspace_with_brain)
        generator = ContextGenerator(config)

        content = generator.generate_recent_activity(days=3)

        assert "No recent AI sessions" in content
        assert "wbrain ai-log" in content

    def test_generate_open_questions(self, workspace_with_logs: Path) -> None:
        """Test generating OPEN_QUESTIONS.md content."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        generator = ContextGenerator(config)

        content = generator.generate_open_questions(days=3)

        assert "# Open Questions" in content
        assert "refresh tokens" in content
        assert "backend" in content

    def test_generate_open_questions_empty(
        self, temp_workspace_with_brain: Path
    ) -> None:
        """Test generating questions when none exist."""
        config = BrainConfig(workspace_path=temp_workspace_with_brain)
        generator = ContextGenerator(config)

        content = generator.generate_open_questions(days=3)

        assert "No open questions" in content

    def test_get_context_for_project(self, workspace_with_logs: Path) -> None:
        """Test getting context specific to a project."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        generator = ContextGenerator(config)

        context = generator.get_context_for_project("backend", days=3)

        assert context is not None
        assert "backend" in context
        assert "JWT" in context

    def test_get_context_for_related_project(self, workspace_with_logs: Path) -> None:
        """Test getting context for a project that's mentioned in related."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        generator = ContextGenerator(config)

        context = generator.get_context_for_project("frontend", days=3)

        assert context is not None
        assert "frontend" in context

    def test_get_context_for_unknown_project(self, workspace_with_logs: Path) -> None:
        """Test getting context for a project with no activity."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        generator = ContextGenerator(config)

        context = generator.get_context_for_project("unknown-project", days=3)

        assert context is None

    def test_context_files_location(self, workspace_with_logs: Path) -> None:
        """Test that context files are created in correct location."""
        config = BrainConfig(workspace_path=workspace_with_logs)
        generator = ContextGenerator(config)

        generated = generator.refresh_all_context(days=3)

        assert generated["recent_activity"].parent == config.context_path
        assert generated["open_questions"].parent == config.context_path
        assert generated["recent_activity"].name == "RECENT_ACTIVITY.md"
        assert generated["open_questions"].name == "OPEN_QUESTIONS.md"
