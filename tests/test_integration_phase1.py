"""Phase 1 Integration Tests for WorkspaceBrain.

These tests verify the complete workflow:
1. init - Creates brain directory structure
2. scan - Detects projects and updates MANIFEST
3. link - Creates .brain symlinks/pointers and AI rule files
4. doctor - Reports health status

All tests use tmp_path fixture to work on a real filesystem.
"""

import json
import os
from pathlib import Path

import pytest
import yaml

from workspacebrain.core.installer import BrainInstaller
from workspacebrain.core.scanner import WorkspaceScanner
from workspacebrain.core.linker import (
    BrainLinker,
    compute_relative_brain_path,
    get_brain_link_type,
    AI_RULE_FILES,
    GENERATED_BANNER,
)
from workspacebrain.core.doctor import BrainDoctor, CheckStatus
from workspacebrain.models import BrainConfig


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def workspace_with_api_web(tmp_path: Path) -> Path:
    """Create a workspace with backend-api (Python BE) and frontend-web (Node FE) projects.

    Structure:
        workspace/
        ├── backend-api/
        │   ├── pyproject.toml  (Python backend signal)
        │   └── requirements.txt
        └── frontend-web/
            ├── package.json    (Node frontend signal)
            ├── next.config.js  (Next.js signal)
            └── pages/          (Next.js pages dir)

    Note: Using names that won't trigger false positives at workspace root level.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # API project (Python backend)
    api_dir = workspace / "backend-api"
    api_dir.mkdir()
    (api_dir / "pyproject.toml").write_text(
        '[project]\nname = "backend-api"\nversion = "0.1.0"\n'
    )
    (api_dir / "requirements.txt").write_text("fastapi\nuvicorn\n")

    # Web project (Node frontend) - needs more signals for detection
    web_dir = workspace / "frontend-web"
    web_dir.mkdir()
    (web_dir / "package.json").write_text(
        '{"name": "frontend-web", "dependencies": {"react": "^18.0.0", "next": "^14.0.0"}}'
    )
    # Add next.config.js to trigger node-fe detection
    (web_dir / "next.config.js").write_text("module.exports = {};\n")
    # Add pages directory
    (web_dir / "pages").mkdir()

    return workspace


@pytest.fixture
def config_for_workspace(workspace_with_api_web: Path) -> BrainConfig:
    """Create a BrainConfig for the test workspace."""
    return BrainConfig(workspace_path=workspace_with_api_web)


# ============================================================================
# Test: init creates brain tree
# ============================================================================


class TestInitCreatesBrainTree:
    """Test that init command creates the complete brain directory structure."""

    def test_init_creates_brain_tree(self, workspace_with_api_web: Path):
        """init(workspace_path) should create brain directory with all required files."""
        config = BrainConfig(workspace_path=workspace_with_api_web)
        installer = BrainInstaller(config)

        # Run init
        result = installer.install()

        # Verify success
        assert result.success, f"Install failed: {result.error}"

        # Verify brain directory exists
        brain_path = workspace_with_api_web / "brain"
        assert brain_path.exists(), "brain/ directory not created"

        # Verify required files exist
        assert (brain_path / "README.md").exists(), "README.md not created"
        assert (brain_path / "MANIFEST.yaml").exists(), "MANIFEST.yaml not created"
        assert (brain_path / "DECISIONS.md").exists(), "DECISIONS.md not created"

        # Verify required directories exist
        assert (brain_path / "CONTRACTS").exists(), "CONTRACTS/ not created"
        assert (brain_path / "HANDOFFS").exists(), "HANDOFFS/ not created"
        assert (brain_path / "RULES").exists(), "RULES/ not created"

        # Verify RULES/INDEX.md exists
        assert (brain_path / "RULES" / "INDEX.md").exists(), "RULES/INDEX.md not created"

    def test_manifest_has_correct_structure(self, workspace_with_api_web: Path):
        """MANIFEST.yaml should have required fields after init."""
        config = BrainConfig(workspace_path=workspace_with_api_web)
        installer = BrainInstaller(config)
        installer.install()

        manifest_path = workspace_with_api_web / "brain" / "MANIFEST.yaml"
        content = manifest_path.read_text()
        data = yaml.safe_load(content)

        # Required fields
        assert "workspace_path" in data
        assert "brain_version" in data
        assert "created_at" in data
        assert "detected_projects" in data
        assert isinstance(data["detected_projects"], list)


# ============================================================================
# Test: init is idempotent
# ============================================================================


class TestInitIdempotent:
    """Test that running init twice does not cause errors or data loss."""

    def test_init_idempotent(self, workspace_with_api_web: Path):
        """Running init twice should not error and should preserve existing files."""
        config = BrainConfig(workspace_path=workspace_with_api_web)
        installer = BrainInstaller(config)

        # First install
        result1 = installer.install()
        assert result1.success

        # Modify a file to verify it's preserved
        readme_path = workspace_with_api_web / "brain" / "README.md"
        original_content = readme_path.read_text()

        # Second install (should skip existing)
        result2 = installer.install()
        assert result2.success, f"Second install failed: {result2.error}"

        # Verify file was NOT overwritten
        assert readme_path.read_text() == original_content

        # Verify skipped paths were reported
        assert len(result2.skipped_paths) > 0, "Should report skipped paths"

    def test_manifest_parseable_after_second_init(self, workspace_with_api_web: Path):
        """MANIFEST.yaml should still be parseable after second init."""
        config = BrainConfig(workspace_path=workspace_with_api_web)
        installer = BrainInstaller(config)

        installer.install()
        installer.install()

        manifest_path = workspace_with_api_web / "brain" / "MANIFEST.yaml"
        content = manifest_path.read_text()
        data = yaml.safe_load(content)

        assert data is not None
        assert "workspace_path" in data


# ============================================================================
# Test: scan detects projects and writes manifest
# ============================================================================


class TestScanDetectsProjects:
    """Test that scan correctly identifies projects and updates MANIFEST."""

    def test_scan_detects_projects_and_writes_manifest(
        self, workspace_with_api_web: Path
    ):
        """Scan should detect api (python) and web (node) projects."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        # First init
        installer = BrainInstaller(config)
        installer.install()

        # Then scan
        scanner = WorkspaceScanner(config)
        result = scanner.scan()

        assert result.success, f"Scan failed: {result.error}"
        assert len(result.projects) >= 2, f"Expected at least 2 projects, got {len(result.projects)}"

        # Verify project types
        project_names = {p.name: p for p in result.projects}

        assert "backend-api" in project_names, "backend-api project not detected"
        assert "frontend-web" in project_names, "frontend-web project not detected"

        # Verify backend-api is python-be
        api_project = project_names["backend-api"]
        assert api_project.project_type == "python-be", f"backend-api type should be python-be, got {api_project.project_type}"
        assert api_project.confidence > 0, "backend-api should have confidence > 0"
        assert len(api_project.signals) > 0, "backend-api should have signals"

        # Verify frontend-web is node-fe
        web_project = project_names["frontend-web"]
        assert web_project.project_type == "node-fe", f"frontend-web type should be node-fe, got {web_project.project_type}"
        assert web_project.confidence > 0, "frontend-web should have confidence > 0"

    def test_manifest_updated_after_scan(self, workspace_with_api_web: Path):
        """MANIFEST.yaml should contain detected projects after scan."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        installer = BrainInstaller(config)
        installer.install()

        scanner = WorkspaceScanner(config)
        scanner.scan()

        # Read manifest
        manifest_path = workspace_with_api_web / "brain" / "MANIFEST.yaml"
        data = yaml.safe_load(manifest_path.read_text())

        projects = data.get("detected_projects", [])
        assert len(projects) >= 2

        # Verify project data in manifest
        project_by_name = {p["name"]: p for p in projects}
        assert "backend-api" in project_by_name
        assert "frontend-web" in project_by_name

        # Check type field
        api_data = project_by_name["backend-api"]
        assert api_data.get("type") == "python-be" or api_data.get("project_type") == "python-be"


# ============================================================================
# Test: link creates brain reference (symlink or pointer)
# ============================================================================


class TestLinkCreatesBrainReference:
    """Test that link creates .brain symlink or pointer fallback."""

    def test_link_creates_brain_reference_symlink_or_pointer(
        self, workspace_with_api_web: Path
    ):
        """Link should create .brain reference in each project."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        # Init + Scan + Link
        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()
        result = BrainLinker(config).link_all()

        assert result.success, f"Link failed: {result.error}"

        # Check each project has .brain
        api_brain = workspace_with_api_web / "backend-api" / ".brain"
        web_brain = workspace_with_api_web / "frontend-web" / ".brain"

        assert api_brain.exists() or api_brain.is_symlink(), ".brain not created in backend-api/"
        assert web_brain.exists() or web_brain.is_symlink(), ".brain not created in frontend-web/"

    def test_symlink_has_correct_relative_path(self, workspace_with_api_web: Path):
        """If symlink is created, it should use correct relative path."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()
        BrainLinker(config).link_all()

        api_brain = workspace_with_api_web / "backend-api" / ".brain"

        if api_brain.is_symlink():
            target = os.readlink(api_brain)
            # Should be ../brain (relative to backend-api/)
            assert target == "../brain", f"Symlink target should be '../brain', got '{target}'"

            # Verify symlink resolves to correct location
            resolved = (workspace_with_api_web / "backend-api" / target).resolve()
            assert resolved == (workspace_with_api_web / "brain").resolve()

    def test_fallback_creates_pointer_json(self, workspace_with_api_web: Path):
        """If symlink fails, .brain/brain.link.json should be created."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()

        # Create a file at .brain to prevent symlink
        api_brain_blocker = workspace_with_api_web / "backend-api" / ".brain"
        api_brain_blocker.write_text("blocking file")

        # Force link to overwrite
        config_force = BrainConfig(workspace_path=workspace_with_api_web, force=True)
        result = BrainLinker(config_force).link_all()

        assert result.success

        # Verify symlink or fallback exists
        api_brain = workspace_with_api_web / "backend-api" / ".brain"
        link_type, link_data = get_brain_link_type(workspace_with_api_web / "backend-api")

        # Either symlink or pointer should work
        assert link_type in ('symlink', 'pointer'), f"Expected symlink or pointer, got {link_type}"

        if link_type == 'pointer':
            # Verify pointer json has required fields
            link_file = api_brain / "brain.link.json"
            assert link_file.exists(), "brain.link.json not created"

            data = json.loads(link_file.read_text())
            assert "brain_path" in data, "brain_path missing from brain.link.json"
            assert "brain_version" in data, "brain_version missing from brain.link.json"
            assert "created_at" in data, "created_at missing from brain.link.json"

    def test_get_brain_link_type_detects_symlink(self, workspace_with_api_web: Path):
        """get_brain_link_type should correctly identify symlinks."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()
        BrainLinker(config).link_all()

        link_type, link_data = get_brain_link_type(workspace_with_api_web / "backend-api")

        # On most systems (macOS, Linux), this should be symlink
        if link_type == 'symlink':
            assert link_data is not None
            assert 'target' in link_data
            assert 'valid' in link_data
            assert link_data['valid'] is True

    def test_get_brain_link_type_returns_none_when_missing(self, tmp_path: Path):
        """get_brain_link_type should return 'none' when no .brain exists."""
        empty_project = tmp_path / "empty_project"
        empty_project.mkdir()

        link_type, link_data = get_brain_link_type(empty_project)

        assert link_type == 'none'
        assert link_data is None


# ============================================================================
# Test: compute_relative_brain_path function
# ============================================================================


class TestComputeRelativeBrainPath:
    """Test the standalone relative path computation function."""

    def test_sibling_directory(self, tmp_path: Path):
        """Test relative path for sibling directories."""
        workspace = tmp_path / "workspace"
        project = workspace / "api"
        brain = workspace / "brain"

        project.mkdir(parents=True)
        brain.mkdir(parents=True)

        rel_path = compute_relative_brain_path(project, brain)
        assert rel_path == "../brain"

    def test_nested_project(self, tmp_path: Path):
        """Test relative path for nested project directory."""
        workspace = tmp_path / "workspace"
        project = workspace / "services" / "api"
        brain = workspace / "brain"

        project.mkdir(parents=True)
        brain.mkdir(parents=True)

        rel_path = compute_relative_brain_path(project, brain)
        assert rel_path == "../../brain"

    def test_deeply_nested(self, tmp_path: Path):
        """Test relative path for deeply nested project."""
        workspace = tmp_path / "workspace"
        project = workspace / "packages" / "services" / "api"
        brain = workspace / "brain"

        project.mkdir(parents=True)
        brain.mkdir(parents=True)

        rel_path = compute_relative_brain_path(project, brain)
        assert rel_path == "../../../brain"


# ============================================================================
# Test: doctor reports OK
# ============================================================================


class TestDoctorReportsOK:
    """Test that doctor correctly reports healthy workspace status."""

    def test_doctor_reports_ok(self, workspace_with_api_web: Path):
        """After init+scan+link, doctor should report OK status."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        # Full workflow
        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()
        BrainLinker(config).link_all()

        # Run doctor
        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        # Verify no errors
        assert report.total_errors == 0, f"Doctor reported {report.total_errors} errors"

        # Verify brain checks passed
        brain_ok_count = sum(1 for c in report.brain_checks if c.status == CheckStatus.OK)
        assert brain_ok_count > 0, "No OK brain checks"

        # Verify project checks
        for project_health in report.project_health:
            assert not project_health.has_errors, f"Project {project_health.name} has errors"

    def test_doctor_reports_symlink_or_pointer_ok(self, workspace_with_api_web: Path):
        """Doctor should report 'OK: symlink' or 'OK: pointer json'."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()
        BrainLinker(config).link_all()

        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        # Find .brain checks in project health
        for project_health in report.project_health:
            brain_checks = [c for c in project_health.checks if ".brain" in c.name]

            for check in brain_checks:
                if check.status == CheckStatus.OK:
                    # Should contain "OK: symlink" or "OK: pointer json"
                    assert (
                        "symlink" in check.message or "pointer" in check.message
                    ), f"Expected symlink or pointer OK message, got: {check.message}"

    def test_doctor_detects_missing_brain(self, tmp_path: Path):
        """Doctor should report error when brain is missing."""
        workspace = tmp_path / "empty_workspace"
        workspace.mkdir()

        config = BrainConfig(workspace_path=workspace)
        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        # Should have error for missing brain
        assert report.total_errors > 0
        error_messages = [c.message for c in report.brain_checks if c.status == CheckStatus.ERROR]
        assert any("Not found" in msg for msg in error_messages)


# ============================================================================
# Test: generated rules files
# ============================================================================


class TestGeneratedRulesFiles:
    """Test that AI rule files are generated correctly."""

    def test_rule_files_created(self, workspace_with_api_web: Path):
        """Link should create CLAUDE.md, CURSOR_RULES.md, AI.md in each project."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()
        BrainLinker(config).link_all()

        for project in ["backend-api", "frontend-web"]:
            project_path = workspace_with_api_web / project

            for rule_file in AI_RULE_FILES:
                file_path = project_path / rule_file
                assert file_path.exists(), f"{rule_file} not created in {project}/"

    def test_rule_files_have_generated_header(self, workspace_with_api_web: Path):
        """Generated rule files should have DO NOT EDIT header."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()
        BrainLinker(config).link_all()

        for project in ["backend-api", "frontend-web"]:
            project_path = workspace_with_api_web / project

            for rule_file in AI_RULE_FILES:
                file_path = project_path / rule_file
                content = file_path.read_text()

                # Check for generated banner
                assert "GENERATED BY WORKSPACEBRAIN" in content, f"{rule_file} missing GENERATED header"
                assert "DO NOT EDIT" in content, f"{rule_file} missing DO NOT EDIT warning"

    def test_rule_files_contain_project_context(self, workspace_with_api_web: Path):
        """Generated rule files should contain project type information."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()
        BrainLinker(config).link_all()

        # Check API project (python-be)
        api_claude = workspace_with_api_web / "backend-api" / "CLAUDE.md"
        content = api_claude.read_text()
        # Should contain project type somewhere in the content
        assert "python" in content.lower() or "backend" in content.lower()

    def test_rule_files_reference_brain_location(self, workspace_with_api_web: Path):
        """Generated rule files should reference brain location."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        BrainInstaller(config).install()
        WorkspaceScanner(config).scan()
        BrainLinker(config).link_all()

        api_claude = workspace_with_api_web / "backend-api" / "CLAUDE.md"
        content = api_claude.read_text()

        # Should reference brain directory or key files
        assert "brain" in content.lower()

    def test_custom_template_used_when_present(self, workspace_with_api_web: Path):
        """Custom templates from brain/RULES/ should be used if present."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        BrainInstaller(config).install()

        # Create custom template
        rules_path = workspace_with_api_web / "brain" / "RULES"
        custom_template = rules_path / "CLAUDE.md"
        custom_template.write_text("# Custom Claude Rules\n\nThis is a custom template.\n")

        WorkspaceScanner(config).scan()
        BrainLinker(config).link_all()

        # Check that custom template was used
        api_claude = workspace_with_api_web / "backend-api" / "CLAUDE.md"
        content = api_claude.read_text()

        assert "Custom Claude Rules" in content
        assert "custom template" in content.lower()


# ============================================================================
# Full workflow integration test
# ============================================================================


class TestFullWorkflow:
    """Test complete init -> scan -> link -> doctor workflow."""

    def test_complete_workflow(self, workspace_with_api_web: Path):
        """Test the complete Phase 1 workflow end-to-end."""
        config = BrainConfig(workspace_path=workspace_with_api_web)

        # Step 1: Init
        install_result = BrainInstaller(config).install()
        assert install_result.success

        # Step 2: Scan
        scan_result = WorkspaceScanner(config).scan()
        assert scan_result.success
        assert len(scan_result.projects) >= 2

        # Step 3: Link
        link_result = BrainLinker(config).link_all()
        assert link_result.success
        assert len(link_result.linked_projects) >= 2

        # Step 4: Doctor
        doctor = BrainDoctor(config)
        report = doctor.diagnose()

        # Final assertions
        assert report.is_healthy or report.total_errors == 0
        assert len(report.project_health) >= 2

        # Verify file structure
        brain_path = workspace_with_api_web / "brain"
        assert brain_path.exists()
        assert (brain_path / "MANIFEST.yaml").exists()

        for project in ["backend-api", "frontend-web"]:
            project_path = workspace_with_api_web / project
            assert (project_path / ".brain").exists() or (project_path / ".brain").is_symlink()
            assert (project_path / "CLAUDE.md").exists()
            assert (project_path / "CURSOR_RULES.md").exists()
            assert (project_path / "AI.md").exists()
