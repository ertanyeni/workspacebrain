"""CLI entry point for WorkspaceBrain using Typer."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from workspacebrain import __version__
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.columns import Columns

from workspacebrain.core.ai_logger import AISessionLogger
from workspacebrain.core.context_generator import ContextGenerator
from workspacebrain.core.doctor import BrainDoctor, CheckStatus
from workspacebrain.core.installer import BrainInstaller
from workspacebrain.core.linker import AI_RULE_FILES, BrainLinker, unlink_project
from workspacebrain.core.log_parser import LogParser
from workspacebrain.core.relationship_manager import RelationshipManager
from workspacebrain.core.risk_scorer import RiskScorer
from workspacebrain.core.scanner import WorkspaceScanner
from workspacebrain.core.security_analyzer import SecurityAnalyzer
from workspacebrain.core.security_context_generator import SecurityContextGenerator
from workspacebrain.models import AISessionEntry, BrainConfig, SecurityAlert

app = typer.Typer(
    name="workspacebrain",
    help="Centralized knowledge and rules for multi-project workspaces.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold blue]workspacebrain[/] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """WorkspaceBrain - Manage your workspace's central brain."""
    pass


@app.command()
def init(
    workspace_path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to the workspace directory. Defaults to current directory.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force re-initialization, overwriting existing brain files.",
        ),
    ] = False,
) -> None:
    """Initialize a brain directory in the workspace.

    Creates the brain/ folder structure with README.md, MANIFEST.yaml,
    DECISIONS.md, and subdirectories for CONTRACTS/, HANDOFFS/, and RULES/.

    If no path is given, uses the current directory.
    """
    # Use current directory if no path specified
    if workspace_path is None:
        workspace_path = Path.cwd()
    else:
        workspace_path = workspace_path.resolve()

    if not workspace_path.exists():
        console.print(f"[bold red]✗[/] Directory not found: {workspace_path}")
        raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path, force=force)
    installer = BrainInstaller(config)

    with console.status("[bold green]Initializing brain..."):
        result = installer.install()

    if result.success:
        console.print(f"[bold green]✓[/] Brain initialized at [cyan]{config.brain_path}[/]")
        if result.created_paths:
            console.print("\n[dim]Created:[/]")
            for path in result.created_paths:
                console.print(f"  [dim]•[/] {path}")
        if result.skipped_paths:
            console.print("\n[dim]Skipped (already exist):[/]")
            for path in result.skipped_paths:
                console.print(f"  [dim]•[/] {path}")
    else:
        console.print(f"[bold red]✗[/] Failed to initialize brain: {result.error}")
        raise typer.Exit(code=1)


@app.command()
def scan(
    workspace_path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to the workspace directory. Defaults to current directory.",
        ),
    ] = None,
) -> None:
    """Scan workspace for projects and update MANIFEST.yaml.

    Detects projects by looking for common project markers like
    package.json, pyproject.toml, Cargo.toml, etc.

    If no path is given, uses the current directory.
    """
    # Use current directory if no path specified
    if workspace_path is None:
        workspace_path = Path.cwd()
    else:
        workspace_path = workspace_path.resolve()

    if not workspace_path.exists():
        console.print(f"[bold red]✗[/] Directory not found: {workspace_path}")
        raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    scanner = WorkspaceScanner(config)

    with console.status("[bold green]Scanning workspace..."):
        result = scanner.scan()

    if result.success:
        console.print(f"[bold green]✓[/] Scan complete for [cyan]{workspace_path}[/]")
        if result.projects:
            console.print(f"\n[bold]Found {len(result.projects)} project(s):[/]\n")
            for project in result.projects:
                console.print(
                    f"  [bold]{project.name}[/] "
                    f"[cyan]({project.project_type})[/]"
                )
                console.print(f"    [dim]path:[/] {project.path}")
                console.print(f"    [dim]signals:[/] {', '.join(project.signals)}")
                console.print()
        else:
            console.print("\n[dim]No projects detected.[/]")
    else:
        console.print(f"[bold red]✗[/] Scan failed: {result.error}")
        raise typer.Exit(code=1)


@app.command()
def link(
    workspace_path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to the workspace directory. Defaults to current directory.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force re-linking, overwriting existing files.",
        ),
    ] = False,
) -> None:
    """Link projects to the brain directory.

    Creates .brain symlink in each detected project pointing to the brain.
    Also generates AI rule files: CLAUDE.md, CURSOR_RULES.md, AI.md

    If no path is given, uses the current directory.
    """
    # Use current directory if no path specified
    if workspace_path is None:
        workspace_path = Path.cwd()
    else:
        workspace_path = workspace_path.resolve()

    if not workspace_path.exists():
        console.print(f"[bold red]✗[/] Directory not found: {workspace_path}")
        raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path, force=force)
    linker = BrainLinker(config)

    with console.status("[bold green]Linking projects..."):
        result = linker.link_all()

    if result.success:
        console.print(f"[bold green]✓[/] Projects linked to brain at [cyan]{config.brain_path}[/]")

        if result.linked_projects:
            console.print(f"\n[bold]Linked {len(result.linked_projects)} project(s):[/]")
            for project in result.linked_projects:
                if project in result.symlink_fallbacks:
                    console.print(f"  [yellow]•[/] {project} [dim](fallback: .brain/brain.link.json)[/]")
                else:
                    console.print(f"  [green]•[/] {project} [dim](.brain -> ../brain)[/]")

        if result.generated_files:
            console.print(f"\n[bold]Generated {len(result.generated_files)} AI rule file(s):[/]")
            for file in result.generated_files:
                console.print(f"  [dim]•[/] {file}")

        if result.skipped_projects:
            console.print(f"\n[dim]Skipped (already linked):[/]")
            for project in result.skipped_projects:
                console.print(f"  [dim]•[/] {project}")
    else:
        console.print(f"[bold red]✗[/] Linking failed: {result.error}")
        raise typer.Exit(code=1)


@app.command()
def setup(
    workspace_path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to the workspace directory. Defaults to current directory.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force re-initialization and re-linking.",
        ),
    ] = False,
) -> None:
    """One-command setup: init + scan + link.

    Initializes brain, scans for projects, and links them all in one go.
    This is the quickest way to get started with WorkspaceBrain.

    If no path is given, uses the current directory.
    """
    # Use current directory if no path specified
    if workspace_path is None:
        workspace_path = Path.cwd()
    else:
        workspace_path = workspace_path.resolve()

    if not workspace_path.exists():
        console.print(f"[bold red]✗[/] Directory not found: {workspace_path}")
        raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path, force=force)

    # Step 1: Init
    console.print(f"\n[bold blue]Step 1/3:[/] Initializing brain in [cyan]{workspace_path}[/]")
    installer = BrainInstaller(config)
    with console.status("[bold green]Initializing..."):
        init_result = installer.install()

    if not init_result.success:
        console.print(f"[bold red]✗[/] Init failed: {init_result.error}")
        raise typer.Exit(code=1)
    console.print(f"[green]✓[/] Brain initialized at [cyan]{config.brain_path}[/]")

    # Step 2: Scan
    console.print(f"\n[bold blue]Step 2/3:[/] Scanning for projects...")
    scanner = WorkspaceScanner(config)
    with console.status("[bold green]Scanning..."):
        scan_result = scanner.scan()

    if not scan_result.success:
        console.print(f"[bold red]✗[/] Scan failed: {scan_result.error}")
        raise typer.Exit(code=1)
    console.print(f"[green]✓[/] Found [bold]{len(scan_result.projects)}[/] project(s)")

    if scan_result.projects:
        for project in scan_result.projects:
            console.print(f"    [dim]•[/] {project.name} [cyan]({project.project_type})[/]")

    # Step 3: Link
    console.print(f"\n[bold blue]Step 3/3:[/] Linking projects to brain...")
    linker = BrainLinker(config)
    with console.status("[bold green]Linking..."):
        link_result = linker.link_all()

    if not link_result.success:
        console.print(f"[bold red]✗[/] Link failed: {link_result.error}")
        raise typer.Exit(code=1)

    if link_result.linked_projects:
        console.print(f"[green]✓[/] Linked [bold]{len(link_result.linked_projects)}[/] project(s)")
        for project in link_result.linked_projects:
            if project in link_result.symlink_fallbacks:
                console.print(f"    [dim]•[/] {project} [yellow](pointer)[/]")
            else:
                console.print(f"    [dim]•[/] {project} [green](symlink)[/]")

    # Final summary
    console.print()
    console.print(
        f"[bold green]✓ Setup complete![/] "
        f"Brain ready at [cyan]{config.brain_path}[/]"
    )
    console.print()
    console.print("[dim]Next steps:[/]")
    console.print("  • Run [cyan]wbrain doctor[/] to verify everything is healthy")
    console.print("  • Edit [cyan]brain/RULES/[/] to customize AI instructions")
    console.print("  • Add decisions to [cyan]brain/DECISIONS.md[/]")


@app.command()
def doctor(
    workspace_path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to the workspace directory. Defaults to current directory.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed information for all checks.",
        ),
    ] = False,
) -> None:
    """Check workspace brain health and report issues.

    Verifies brain structure, validates MANIFEST.yaml,
    checks project links, detects drift in generated files.

    If no path is given, uses the current directory.
    """
    # Use current directory if no path specified
    if workspace_path is None:
        workspace_path = Path.cwd()
    else:
        workspace_path = workspace_path.resolve()

    if not workspace_path.exists():
        console.print(f"[bold red]✗[/] Directory not found: {workspace_path}")
        raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    doctor_checker = BrainDoctor(config)

    console.print()
    console.print(
        Panel.fit(
            f"[bold]Brain Health Check[/]\n[dim]{workspace_path}[/]",
            border_style="blue",
        )
    )
    console.print()

    with console.status("[bold green]Running diagnostics..."):
        report = doctor_checker.diagnose()

    # Brain checks table
    brain_table = Table(
        title="[bold]Brain Directory[/]",
        show_header=True,
        header_style="bold",
        border_style="dim",
    )
    brain_table.add_column("Check", style="cyan")
    brain_table.add_column("Status", justify="center")
    brain_table.add_column("Details")

    for check in report.brain_checks:
        status_icon = _get_status_icon(check.status)
        details = check.message
        if verbose and check.details:
            details += "\n" + "\n".join(f"  [dim]{d}[/]" for d in check.details)
        brain_table.add_row(check.name, status_icon, details)

    console.print(brain_table)
    console.print()

    # Project checks
    if report.project_health:
        for project in report.project_health:
            project_table = Table(
                title=f"[bold]{project.name}[/] [dim]({project.project_type})[/]",
                show_header=True,
                header_style="bold",
                border_style="dim" if project.is_healthy else "yellow",
            )
            project_table.add_column("Check", style="cyan")
            project_table.add_column("Status", justify="center")
            project_table.add_column("Details")

            for check in project.checks:
                status_icon = _get_status_icon(check.status)
                details = check.message
                if verbose and check.details:
                    details += "\n" + "\n".join(f"  [dim]{d}[/]" for d in check.details)
                elif check.status == CheckStatus.WARNING and check.details:
                    # Always show first detail for warnings
                    details += f" [dim]({check.details[0]})[/]"
                project_table.add_row(check.name, status_icon, details)

            console.print(project_table)
            console.print()

    # Summary
    if report.is_healthy:
        console.print(
            Panel.fit(
                "[bold green]All checks passed![/] Brain is healthy.",
                border_style="green",
            )
        )
    else:
        summary_parts = []
        if report.total_errors > 0:
            summary_parts.append(f"[red]{report.total_errors} error(s)[/]")
        if report.total_warnings > 0:
            summary_parts.append(f"[yellow]{report.total_warnings} warning(s)[/]")

        console.print(
            Panel.fit(
                f"[bold]Issues found:[/] {', '.join(summary_parts)}\n"
                "[dim]Run with --verbose for more details[/]",
                border_style="yellow" if report.total_errors == 0 else "red",
            )
        )

        if report.total_errors > 0:
            raise typer.Exit(code=1)


def _get_status_icon(status: CheckStatus) -> str:
    """Get icon for check status."""
    icons = {
        CheckStatus.OK: "[green]✓[/]",
        CheckStatus.WARNING: "[yellow]![/]",
        CheckStatus.ERROR: "[red]✗[/]",
        CheckStatus.SKIPPED: "[dim]-[/]",
    }
    return icons.get(status, "[dim]?[/]")


@app.command()
def log(
    message: Annotated[
        str,
        typer.Argument(help="Log message to record."),
    ],
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            "-p",
            help="Project name (auto-detected from current directory if not specified).",
        ),
    ] = None,
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path (searches parent directories if not specified).",
        ),
    ] = None,
) -> None:
    """Add a log entry to the brain's daily log.

    Logs are stored in brain/LOGS/YYYY-MM-DD.md files.
    Useful for tracking work progress across projects.

    Examples:
        wbrain log "Added user authentication"
        wbrain log "Fixed API bug" -p backend
        wbrain log "Refactored components" --project frontend
    """
    from datetime import datetime

    # Find workspace by looking for brain/ directory
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found. Run 'wbrain init' first or specify --workspace.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)

    if not config.brain_path.exists():
        console.print(f"[bold red]✗[/] Brain not found at {config.brain_path}")
        raise typer.Exit(code=1)

    # Auto-detect project from current directory
    if project is None:
        cwd = Path.cwd()
        # Check if cwd is inside workspace
        try:
            rel_path = cwd.relative_to(workspace_path)
            # Get first directory component as project name
            parts = rel_path.parts
            if parts and parts[0] != "brain":
                project = parts[0]
        except ValueError:
            pass  # cwd is not inside workspace

    # Create LOGS directory if needed
    logs_path = config.brain_path / "LOGS"
    logs_path.mkdir(exist_ok=True)

    # Get today's log file
    today = datetime.now()
    log_file = logs_path / f"{today.strftime('%Y-%m-%d')}.md"

    # Create or append to log file
    timestamp = today.strftime("%H:%M")
    project_tag = f"[{project}]" if project else "[general]"

    if not log_file.exists():
        # Create new daily log with header
        header = f"# Work Log - {today.strftime('%Y-%m-%d')}\n\n"
        log_file.write_text(header, encoding="utf-8")

    # Append log entry
    entry = f"- **{timestamp}** {project_tag} {message}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)

    console.print(f"[green]✓[/] Logged: {project_tag} {message}")
    console.print(f"  [dim]→ {log_file.relative_to(workspace_path)}[/]")


@app.command()
def logs(
    days: Annotated[
        int,
        typer.Option(
            "--days",
            "-d",
            help="Number of days to show.",
        ),
    ] = 7,
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path.",
        ),
    ] = None,
) -> None:
    """Show recent work logs.

    Displays log entries from the last N days.
    """
    from datetime import datetime, timedelta

    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    logs_path = config.brain_path / "LOGS"

    if not logs_path.exists():
        console.print("[dim]No logs yet. Use 'wbrain log \"message\"' to start logging.[/]")
        return

    # Get log files from last N days
    today = datetime.now()
    found_logs = False

    for i in range(days):
        date = today - timedelta(days=i)
        log_file = logs_path / f"{date.strftime('%Y-%m-%d')}.md"

        if log_file.exists():
            found_logs = True
            content = log_file.read_text(encoding="utf-8")
            console.print(content)
            console.print()

    if not found_logs:
        console.print(f"[dim]No logs in the last {days} days.[/]")


@app.command("ai-log")
def ai_log(
    summary: Annotated[
        Optional[str],
        typer.Option(
            "--summary",
            "-s",
            help="Summary of what was done.",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            "-p",
            help="Project name (auto-detected from current directory if not specified).",
        ),
    ] = None,
    tool: Annotated[
        str,
        typer.Option(
            "--tool",
            "-t",
            help="AI tool name (claude, cursor, windsurf, copilot, generic).",
        ),
    ] = "generic",
    reasoning: Annotated[
        Optional[str],
        typer.Option(
            "--reasoning",
            "-r",
            help="AI reasoning for decisions made.",
        ),
    ] = None,
    related: Annotated[
        Optional[str],
        typer.Option(
            "--related",
            help="Related projects (comma-separated, format: 'project:reason,project2:reason2').",
        ),
    ] = None,
    questions: Annotated[
        Optional[str],
        typer.Option(
            "--questions",
            "-q",
            help="Open questions (comma-separated).",
        ),
    ] = None,
    files: Annotated[
        Optional[str],
        typer.Option(
            "--files",
            "-f",
            help="Key files modified (comma-separated).",
        ),
    ] = None,
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path (searches parent directories if not specified).",
        ),
    ] = None,
) -> None:
    """Log an AI session with structured metadata for cross-project context.

    This command is designed to be called by AI assistants after completing work.
    It logs structured session data and automatically refreshes context files.

    Examples:
        wbrain ai-log -p backend -t claude -s "Added auth endpoint"
        wbrain ai-log -s "Fixed bug" -r "Used JWT instead of sessions" -f "auth.py,routes.py"

    AI assistants can also pipe structured input:
        wbrain ai-log -p backend -t claude << 'EOF'
        ## Summary
        Added user authentication

        ## AI Reasoning
        Chose JWT for stateless auth
        EOF
    """
    import sys

    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found. Run 'wbrain init' first.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)

    # Auto-detect project from current directory
    if project is None:
        cwd = Path.cwd()
        try:
            rel_path = cwd.relative_to(workspace_path)
            parts = rel_path.parts
            if parts and parts[0] != "brain":
                project = parts[0]
        except ValueError:
            pass

    if project is None:
        project = "general"

    # Check if there's stdin input (heredoc style)
    stdin_data = None
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read().strip()

    logger = AISessionLogger(config)

    if stdin_data:
        # Parse structured input from stdin
        parsed = logger.parse_stdin_log(stdin_data)
        entry = AISessionEntry(
            project_name=project,
            ai_tool=tool,
            summary=parsed.get("summary", summary or "AI session logged"),
            what_was_done=parsed.get("what_was_done", []),
            reasoning=parsed.get("reasoning") or reasoning,
            related_projects=parsed.get("related_projects", {}),
            open_questions=parsed.get("open_questions", []),
            key_files=parsed.get("key_files", []),
        )
    else:
        if not summary:
            console.print("[bold red]✗[/] Summary is required. Use --summary or -s.")
            raise typer.Exit(code=1)

        entry = logger.create_entry_from_args(
            summary=summary,
            project=project,
            tool=tool,
            reasoning=reasoning,
            related=related,
            questions=questions,
            files=files,
        )

    # Log the session
    log_file = logger.log_session(entry)

    console.print(f"[green]✓[/] AI session logged: [{entry.ai_tool}] {entry.summary}")
    console.print(f"  [dim]→ {log_file.relative_to(workspace_path)}[/]")

    # Auto-refresh context files (both global and project-specific)
    context_gen = ContextGenerator(config)
    with console.status("[dim]Refreshing context...[/]"):
        context_gen.refresh_all_project_contexts(days=3)

    console.print(f"  [dim]→ Context files updated (global + project-specific)[/]")


@app.command()
def context(
    days: Annotated[
        int,
        typer.Option(
            "--days",
            "-d",
            help="Number of days to include in context.",
        ),
    ] = 3,
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path.",
        ),
    ] = None,
    project_only: Annotated[
        bool,
        typer.Option(
            "--project-only",
            help="Only generate project-specific context files.",
        ),
    ] = False,
) -> None:
    """Generate/refresh context files from recent logs.

    Creates/updates:
    - brain/CONTEXT/RECENT_ACTIVITY.md - Summary of recent work across all projects
    - brain/CONTEXT/OPEN_QUESTIONS.md - Aggregated open questions
    - brain/CONTEXT/projects/{project}.md - Project-specific filtered context

    Project-specific context files only include activity from related projects,
    saving tokens and reducing noise for AI assistants.
    """
    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    context_gen = ContextGenerator(config)

    with console.status("[bold green]Generating context files..."):
        if project_only:
            generated = context_gen.refresh_project_contexts(days=days)
        else:
            generated = context_gen.refresh_all_project_contexts(days=days)

    console.print(f"[bold green]✓[/] Context files generated from last {days} days")

    # Separate global and project-specific files
    global_files = {k: v for k, v in generated.items() if not k.startswith("project:")}
    project_files = {k: v for k, v in generated.items() if k.startswith("project:")}

    if global_files:
        console.print("\n[bold]Global context:[/]")
        for name, path in global_files.items():
            console.print(f"  [dim]•[/] {path.relative_to(workspace_path)}")

    if project_files:
        console.print("\n[bold]Project-specific context:[/]")
        for name, path in project_files.items():
            project_name = name.replace("project:", "")
            console.print(f"  [dim]•[/] {path.relative_to(workspace_path)} [cyan]({project_name})[/]")


@app.command()
def status(
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path.",
        ),
    ] = None,
    days: Annotated[
        int,
        typer.Option(
            "--days",
            "-d",
            help="Number of days to show.",
        ),
    ] = 3,
) -> None:
    """Show cross-project status summary.

    Displays recent activity, open questions, and project relationships
    from AI session logs.
    """
    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    parser = LogParser(config)

    console.print()
    console.print(
        Panel.fit(
            f"[bold]Workspace Status[/]\n[dim]Last {days} days[/]",
            border_style="blue",
        )
    )
    console.print()

    entries = parser.get_logs_in_range(days)

    if not entries:
        console.print("[dim]No AI sessions logged in this period.[/]")
        console.print("[dim]Use 'wbrain ai-log' to log AI sessions.[/]")
        return

    # Group by project
    by_project: dict[str, list] = {}
    for entry in entries:
        if entry.project_name not in by_project:
            by_project[entry.project_name] = []
        by_project[entry.project_name].append(entry)

    # Show activity by project
    console.print("[bold]Recent Activity[/]")
    console.print()

    for project, project_entries in by_project.items():
        console.print(f"[cyan]{project}[/]")
        for entry in project_entries[:3]:  # Show last 3 per project
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M")
            console.print(f"  [dim]{timestamp}[/] ({entry.ai_tool}) {entry.summary}")
        if len(project_entries) > 3:
            console.print(f"  [dim]... and {len(project_entries) - 3} more[/]")
        console.print()

    # Show relationships
    relationships = parser.extract_project_relationships(entries)
    if relationships:
        console.print("[bold]Project Relationships[/]")
        console.print()
        for project, related in relationships.items():
            if related:
                console.print(f"  [cyan]{project}[/] ↔ {', '.join(related)}")
        console.print()

    # Show open questions
    questions = parser.extract_open_questions(entries)
    if questions:
        console.print("[bold]Open Questions[/]")
        console.print()
        for q in questions[:5]:  # Show first 5
            console.print(f"  [yellow]?[/] [{q['project']}] {q['question']}")
        if len(questions) > 5:
            console.print(f"  [dim]... and {len(questions) - 5} more[/]")
        console.print()


@app.command()
def relationships(
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path.",
        ),
    ] = None,
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            "-r",
            help="Refresh relationships from logs.",
        ),
    ] = False,
    days: Annotated[
        int,
        typer.Option(
            "--days",
            "-d",
            help="Number of days to scan for relationships.",
        ),
    ] = 7,
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            "-p",
            help="Show relationships for a specific project.",
        ),
    ] = None,
) -> None:
    """Show and manage project relationships.

    Relationships are automatically discovered from AI session logs
    when one project mentions another in its related_projects field.

    Examples:
        wbrain relationships              # Show all relationships
        wbrain relationships -r           # Refresh from logs
        wbrain relationships -p backend   # Show backend's relationships
    """
    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    manager = RelationshipManager(config)

    console.print()
    console.print(
        Panel.fit(
            "[bold]Project Relationships[/]\n"
            "[dim]Auto-discovered from AI session logs[/]",
            border_style="blue",
        )
    )
    console.print()

    if refresh:
        with console.status("[bold green]Refreshing relationships from logs..."):
            manager.refresh_from_logs(days=days)
        console.print(f"[green]✓[/] Relationships refreshed from last {days} days of logs")
        console.print()

    graph = manager.get_relationship_graph()

    if not graph:
        console.print("[dim]No relationships discovered yet.[/]")
        console.print()
        console.print("[dim]Relationships are created when AI sessions log related projects:[/]")
        console.print('[cyan]wbrain ai-log -s "..." --related "project:reason"[/]')
        return

    if project:
        # Show specific project's relationships
        related = manager.get_related_projects(project)
        if not related:
            console.print(f"[dim]No relationships found for {project}.[/]")
            return

        console.print(f"[bold cyan]{project}[/] is related to:")
        console.print()

        # Show with reasons
        all_rels = manager.get_all_relationships()
        for source, target, reason in all_rels:
            if source == project:
                console.print(f"  [green]→[/] [bold]{target}[/]")
                if reason:
                    console.print(f"    [dim]{reason}[/]")
            elif target == project:
                # Find reverse relationship
                for s2, t2, r2 in all_rels:
                    if s2 == target and t2 == project:
                        console.print(f"  [yellow]←[/] [bold]{target}[/]")
                        if r2:
                            console.print(f"    [dim]{r2}[/]")
                        break
                else:
                    console.print(f"  [yellow]←[/] [bold]{target}[/] [dim](reverse)[/]")
    else:
        # Show all relationships
        table = Table(show_header=True, header_style="bold")
        table.add_column("Project", style="cyan")
        table.add_column("Related To", style="green")
        table.add_column("Context Files", style="dim")

        for proj, related in sorted(graph.items()):
            related_str = ", ".join(sorted(related)) if related else "-"
            context_file = f".brain/CONTEXT/projects/{proj}.md"
            table.add_row(proj, related_str, context_file)

        console.print(table)
        console.print()

        # Show total stats
        total_projects = len(graph)
        total_relationships = sum(len(v) for v in graph.values()) // 2  # Divide by 2 since bidirectional
        console.print(f"[dim]Total: {total_projects} projects, {total_relationships} relationships[/]")


def _find_workspace_with_brain(start_path: Path) -> Optional[Path]:
    """Find workspace by searching for brain/ directory in current and parent directories."""
    current = start_path.resolve()

    # Check current and parent directories
    for _ in range(10):  # Max 10 levels up
        brain_path = current / "brain"
        if brain_path.exists() and brain_path.is_dir():
            # Verify it's our brain (has MANIFEST.yaml)
            if (brain_path / "MANIFEST.yaml").exists():
                return current

        parent = current.parent
        if parent == current:  # Reached root
            break
        current = parent

    return None


@app.command()
def uninstall(
    workspace_path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to the workspace directory. Defaults to current directory.",
        ),
    ] = None,
    keep_brain: Annotated[
        bool,
        typer.Option(
            "--keep-brain",
            help="Keep the brain/ directory (only remove project links and AI files).",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip confirmation prompt.",
        ),
    ] = False,
) -> None:
    """Uninstall WorkspaceBrain from workspace.

    Removes all generated files:
    - .brain symlinks from all projects
    - AI rule files (CLAUDE.md, .cursorrules, .windsurfrules, AI.md)
    - brain/ directory (unless --keep-brain is specified)

    After running this command, run 'pipx uninstall workspacebrain'
    to remove the CLI tool itself.
    """
    import shutil
    import yaml

    # Use current directory if no path specified
    if workspace_path is None:
        workspace_path = Path.cwd()
    else:
        workspace_path = workspace_path.resolve()

    if not workspace_path.exists():
        console.print(f"[bold red]✗[/] Directory not found: {workspace_path}")
        raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)

    if not config.brain_path.exists():
        console.print(f"[bold red]✗[/] No brain found at {config.brain_path}")
        console.print("[dim]Nothing to uninstall.[/]")
        raise typer.Exit(code=1)

    # Load projects from manifest
    projects = []
    if config.manifest_path.exists():
        try:
            content = config.manifest_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if data and "detected_projects" in data:
                projects = [p["path"] for p in data["detected_projects"]]
        except Exception:
            pass

    # Show what will be removed
    console.print()
    console.print(
        Panel.fit(
            f"[bold]Uninstall WorkspaceBrain[/]\n[dim]{workspace_path}[/]",
            border_style="yellow",
        )
    )
    console.print()

    console.print("[bold]The following will be removed:[/]")
    console.print()

    # List project files that will be removed
    files_to_remove = []
    for project_path_str in projects:
        project_path = Path(project_path_str)
        if project_path.exists():
            # Check for .brain symlink
            brain_link = project_path / ".brain"
            if brain_link.exists() or brain_link.is_symlink():
                files_to_remove.append(str(brain_link))

            # Check for AI rule files
            for rule_file in AI_RULE_FILES:
                rule_path = project_path / rule_file
                if rule_path.exists():
                    files_to_remove.append(str(rule_path))

    if files_to_remove:
        console.print("[cyan]Project files:[/]")
        for f in files_to_remove[:10]:  # Show first 10
            console.print(f"  • {f}")
        if len(files_to_remove) > 10:
            console.print(f"  [dim]... and {len(files_to_remove) - 10} more files[/]")
        console.print()

    if not keep_brain:
        console.print(f"[cyan]Brain directory:[/]")
        console.print(f"  • {config.brain_path}")
        console.print()

    # Confirm
    if not force:
        confirm = typer.confirm("Are you sure you want to proceed?", default=False)
        if not confirm:
            console.print("[dim]Aborted.[/]")
            raise typer.Exit(code=0)

    console.print()

    # Remove project links and files
    removed_count = 0
    for project_path_str in projects:
        project_path = Path(project_path_str)
        if project_path.exists():
            if unlink_project(project_path):
                removed_count += 1
                console.print(f"[green]✓[/] Cleaned: {project_path.name}")

    # Remove brain directory
    if not keep_brain and config.brain_path.exists():
        shutil.rmtree(config.brain_path)
        console.print(f"[green]✓[/] Removed: {config.brain_path}")

    console.print()
    console.print(
        Panel.fit(
            f"[bold green]Uninstall complete![/]\n\n"
            f"Cleaned {removed_count} project(s)\n"
            f"{'Brain directory preserved' if keep_brain else 'Brain directory removed'}\n\n"
            "[dim]To remove the CLI tool:[/]\n"
            "[cyan]pipx uninstall workspacebrain[/]",
            border_style="green",
        )
    )


# Security commands group
security_app = typer.Typer(
    name="security",
    help="Security analysis and vulnerability management.",
)


@security_app.command("scan")
def security_scan(
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path (searches parent directories if not specified).",
        ),
    ] = None,
) -> None:
    """Scan all projects for security vulnerabilities.

    Collects alerts from:
    - GitHub Dependabot (if GitHub token available)
    - npm audit (Node.js projects)
    - pip-audit (Python projects)
    - cargo audit (Rust projects)
    """
    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    analyzer = SecurityAnalyzer(config)

    with console.status("[bold green]Scanning for security vulnerabilities..."):
        result = analyzer.scan_all()

    if not result.success:
        console.print(f"[bold red]✗[/] Scan failed: {result.error}")
        raise typer.Exit(code=1)

    if not result.alerts:
        console.print("[green]✓[/] No security vulnerabilities found.")
        return

    console.print(f"[green]✓[/] Found [bold]{len(result.alerts)}[/] security alert(s)")

    # Save alerts
    context_gen = SecurityContextGenerator(config)
    alerts_path = context_gen.save_alerts(result.alerts)
    console.print(f"  [dim]→ Saved to {alerts_path.relative_to(workspace_path)}[/]")

    # Show summary in table
    by_severity: dict[str, int] = {}
    for alert in result.alerts:
        severity = alert.severity
        by_severity[severity] = by_severity.get(severity, 0) + 1

    if by_severity:
        summary_table = Table(
            title="[bold]Summary by Severity[/]",
            show_header=True,
            header_style="bold",
            border_style="dim",
        )
        summary_table.add_column("Severity", style="bold", width=12)
        summary_table.add_column("Count", justify="right", width=8)

        severity_icons = {
            "critical": ("🔴", "red"),
            "high": ("🟡", "yellow"),
            "medium": ("🔵", "blue"),
            "low": ("⚪", "dim"),
        }

        for severity in ["critical", "high", "medium", "low"]:
            count = by_severity.get(severity, 0)
            if count > 0:
                icon, color = severity_icons.get(severity, ("○", "white"))
                summary_table.add_row(
                    f"[{color}]{icon} {severity.upper()}[/]",
                    f"[bold]{count}[/]",
                )

        console.print()
        console.print(summary_table)
        console.print()


@security_app.command("analyze")
def security_analyze(
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path.",
        ),
    ] = None,
) -> None:
    """Analyze security alerts and generate risk assessments.

    Performs risk scoring, prioritization, and generates AI-friendly context.
    """
    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)

    # Load alerts
    context_gen = SecurityContextGenerator(config)
    alerts_path = config.security_alerts_path

    if not alerts_path.exists():
        console.print(
            "[bold yellow]![/] No alerts found. Run 'wbrain security scan' first."
        )
        raise typer.Exit(code=1)

    # Load alerts from YAML
    import yaml
    from datetime import datetime

    alerts_data = yaml.safe_load(alerts_path.read_text(encoding="utf-8"))
    alerts = []
    for alert_data in alerts_data.get("alerts", []):
        # Parse datetime if it's a string
        if "detected_at" in alert_data and isinstance(alert_data["detected_at"], str):
            alert_data["detected_at"] = datetime.fromisoformat(alert_data["detected_at"])
        alerts.append(SecurityAlert(**alert_data))

    if not alerts:
        console.print("[green]✓[/] No alerts to analyze.")
        return

    # Analyze
    scorer = RiskScorer(config)
    with console.status("[bold green]Analyzing risks..."):
        assessments = scorer.assess_alerts(alerts)

    # Save assessments
    assessment_path = context_gen.save_assessments(assessments)
    console.print(f"[green]✓[/] Risk assessment complete")
    console.print(f"  [dim]→ Saved to {assessment_path.relative_to(workspace_path)}[/]")

    # Generate context
    security_path = context_gen.generate_global_security_context(assessments)
    console.print(f"  [dim]→ Context: {security_path.relative_to(workspace_path)}[/]")

    # Show summary
    fix_now = len([a for a in assessments if a.action == "FIX_NOW"])
    fix_soon = len([a for a in assessments if a.action == "FIX_SOON"])
    monitor = len([a for a in assessments if a.action == "MONITOR"])

    # Show action summary in table
    action_table = Table(
        title="[bold]Action Summary[/]",
        show_header=True,
        header_style="bold",
        border_style="dim",
    )
    action_table.add_column("Action", style="bold", width=12)
    action_table.add_column("Count", justify="right", width=8)
    action_table.add_column("Icon", width=4)

    if fix_now > 0:
        action_table.add_row("[red]⚡ FIX_NOW[/]", f"[bold red]{fix_now}[/]", "[red]⚡[/]")
    if fix_soon > 0:
        action_table.add_row("[yellow]⚠ FIX_SOON[/]", f"[bold yellow]{fix_soon}[/]", "[yellow]⚠[/]")
    if monitor > 0:
        action_table.add_row("[dim]👁 MONITOR[/]", f"[bold]{monitor}[/]", "[dim]👁[/]")

    console.print()
    console.print(action_table)
    console.print()


@security_app.command("status")
def security_status(
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path.",
        ),
    ] = None,
) -> None:
    """Show security status summary."""
    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    context_gen = SecurityContextGenerator(config)

    assessments = context_gen.load_assessments()

    if not assessments:
        console.print("[dim]No security assessments found.[/]")
        console.print("[dim]Run 'wbrain security scan' and 'wbrain security analyze' first.[/]")
        return

    # Create status table
    status_table = Table(
        title="[bold]Security Status[/]",
        show_header=True,
        header_style="bold",
        border_style="blue",
        row_styles=["", "dim"],
    )

    status_table.add_column("Project", style="cyan", width=20)
    status_table.add_column("Type", style="dim", width=12)
    status_table.add_column("Total", justify="right", width=8)
    status_table.add_column("⚡ Fix Now", justify="right", width=10, style="red")
    status_table.add_column("⚠ Fix Soon", justify="right", width=10, style="yellow")
    status_table.add_column("👁 Monitor", justify="right", width=10, style="dim")

    # Group by project
    by_project: dict[str, list] = {}
    for assessment in assessments:
        project = assessment.alert.project_name
        if project not in by_project:
            by_project[project] = []
        by_project[project].append(assessment)

    # Add rows
    for project, project_assessments in sorted(by_project.items()):
        project_type = project_assessments[0].alert.project_type
        total = len(project_assessments)
        fix_now = len([a for a in project_assessments if a.action == "FIX_NOW"])
        fix_soon = len([a for a in project_assessments if a.action == "FIX_SOON"])
        monitor = len([a for a in project_assessments if a.action == "MONITOR"])

        status_table.add_row(
            project,
            project_type,
            f"[bold]{total}[/]",
            f"[red]{fix_now}[/]" if fix_now > 0 else "[dim]0[/]",
            f"[yellow]{fix_soon}[/]" if fix_soon > 0 else "[dim]0[/]",
            f"[dim]{monitor}[/]" if monitor > 0 else "[dim]0[/]",
        )

    # Overall totals
    fix_now_total = len([a for a in assessments if a.action == "FIX_NOW"])
    fix_soon_total = len([a for a in assessments if a.action == "FIX_SOON"])
    monitor_total = len([a for a in assessments if a.action == "MONITOR"])

    status_table.add_row(
        "[bold]TOTAL[/]",
        "",
        f"[bold]{len(assessments)}[/]",
        f"[bold red]{fix_now_total}[/]" if fix_now_total > 0 else "[dim]0[/]",
        f"[bold yellow]{fix_soon_total}[/]" if fix_soon_total > 0 else "[dim]0[/]",
        f"[bold dim]{monitor_total}[/]" if monitor_total > 0 else "[dim]0[/]",
        style="bold",
    )

    console.print()
    console.print(status_table)
    console.print()

    if fix_now_total > 0:
        console.print(
            Panel.fit(
                f"[bold red]⚡ {fix_now_total} issue(s) require immediate attention[/]",
                border_style="red",
            )
        )
        console.print()


@security_app.command("fix-now")
def security_fix_now(
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path.",
        ),
    ] = None,
) -> None:
    """List all issues that need immediate fixing."""
    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    context_gen = SecurityContextGenerator(config)

    assessments = context_gen.load_assessments()
    fix_now = [a for a in assessments if a.action == "FIX_NOW"]

    if not fix_now:
        console.print("[green]✓[/] No critical issues requiring immediate fix.")
        return

    # Create fix-now table
    fix_now_table = Table(
        title=f"[bold red]⚡ Fix Now: {len(fix_now)} Critical Issues[/]",
        show_header=True,
        header_style="bold",
        border_style="red",
        row_styles=["", "dim"],
    )

    fix_now_table.add_column("#", style="dim", width=3, justify="right")
    fix_now_table.add_column("Project", style="cyan", width=15)
    fix_now_table.add_column("CVE/Package", style="bold", width=25)
    fix_now_table.add_column("Version", width=25)
    fix_now_table.add_column("Risk", justify="right", width=8, style="red")
    fix_now_table.add_column("Fix", style="green", width=30)

    # Group by project
    by_project: dict[str, list] = {}
    for assessment in fix_now:
        project = assessment.alert.project_name
        if project not in by_project:
            by_project[project] = []
        by_project[project].append(assessment)

    row_num = 1
    for project, project_assessments in sorted(by_project.items()):
        for assessment in sorted(
            project_assessments, key=lambda a: a.risk_score, reverse=True
        ):
            alert = assessment.alert
            cve_str = f"[bold]{alert.cve_id}[/]" if alert.cve_id else "[dim]Vulnerability[/]"
            package_str = f"{cve_str}\n[dim]{alert.package_name}[/]"

            if alert.fixed_version:
                version_str = f"[red]{alert.package_version}[/] → [green]{alert.fixed_version}[/]"
            else:
                version_str = f"[red]{alert.package_version}[/]"

            risk_str = f"[bold red]{assessment.risk_score:.1f}[/]"
            fix_str = assessment.recommended_fix or "[dim]Review needed[/]"

            fix_now_table.add_row(
                str(row_num),
                project,
                package_str,
                version_str,
                risk_str,
                fix_str,
            )
            row_num += 1

    console.print()
    console.print(fix_now_table)
    console.print()


@security_app.command("list")
def security_list(
    workspace_path: Annotated[
        Optional[Path],
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace path.",
        ),
    ] = None,
    priority: Annotated[
        Optional[str],
        typer.Option(
            "--priority",
            "-p",
            help="Filter by priority: CRITICAL, HIGH, MEDIUM, LOW",
        ),
    ] = None,
    action: Annotated[
        Optional[str],
        typer.Option(
            "--action",
            "-a",
            help="Filter by action: FIX_NOW, FIX_SOON, MONITOR",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            help="Filter by project name",
        ),
    ] = None,
    compact: Annotated[
        bool,
        typer.Option(
            "--compact",
            "-c",
            help="Show compact table view instead of detailed view",
        ),
    ] = False,
) -> None:
    """List all security issues with detailed information.

    Shows comprehensive details about each security alert including:
    - CVE ID and description
    - Package name and versions
    - Risk score and priority
    - Recommended fix
    - Impact analysis
    """
    # Find workspace
    if workspace_path is None:
        workspace_path = _find_workspace_with_brain(Path.cwd())
        if workspace_path is None:
            console.print("[bold red]✗[/] No brain found.")
            raise typer.Exit(code=1)

    config = BrainConfig(workspace_path=workspace_path)
    context_gen = SecurityContextGenerator(config)

    assessments = context_gen.load_assessments()

    if not assessments:
        console.print("[dim]No security assessments found.[/]")
        console.print("[dim]Run 'wbrain security scan' and 'wbrain security analyze' first.[/]")
        return

    # Apply filters
    filtered = assessments
    if priority:
        filtered = [a for a in filtered if a.priority.upper() == priority.upper()]
    if action:
        filtered = [a for a in filtered if a.action.upper() == action.upper()]
    if project:
        filtered = [a for a in filtered if a.alert.project_name == project]

    if not filtered:
        console.print("[dim]No issues found matching the filters.[/]")
        return

    # Sort by risk score (highest first)
    filtered.sort(key=lambda a: a.risk_score, reverse=True)

    if compact:
        # Compact table view
        _show_compact_list(filtered)
    else:
        # Detailed tree view
        _show_detailed_list(filtered)


def _show_compact_list(assessments: list) -> None:
    """Show compact table view of security issues."""
    table = Table(
        title=f"[bold]Security Issues[/] [dim]({len(assessments)} total)[/]",
        show_header=True,
        header_style="bold",
        border_style="blue",
        row_styles=["", "dim"],
    )

    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Priority", width=10)
    table.add_column("Action", width=10)
    table.add_column("CVE/Package", style="cyan", width=25)
    table.add_column("Version", width=20)
    table.add_column("Risk", width=8, justify="right")
    table.add_column("Project", style="blue", width=15)

    for i, assessment in enumerate(assessments, 1):
        alert = assessment.alert

        # Priority badge
        priority_colors = {
            "CRITICAL": ("red", "🔴"),
            "HIGH": ("yellow", "🟡"),
            "MEDIUM": ("blue", "🔵"),
            "LOW": ("dim", "⚪"),
        }
        priority_color, priority_icon = priority_colors.get(assessment.priority, ("white", "○"))
        priority_text = f"[{priority_color}]{priority_icon} {assessment.priority}[/]"

        # Action badge
        action_colors = {
            "FIX_NOW": ("red", "⚡"),
            "FIX_SOON": ("yellow", "⚠"),
            "MONITOR": ("dim", "👁"),
        }
        action_color, action_icon = action_colors.get(assessment.action, ("white", "○"))
        action_text = f"[{action_color}]{action_icon} {assessment.action}[/]"

        # CVE/Package
        if alert.cve_id:
            cve_package = f"[bold]{alert.cve_id}[/]\n[dim]{alert.package_name}[/]"
        else:
            cve_package = f"[bold]{alert.package_name}[/]"

        # Version
        if alert.fixed_version:
            version_text = f"[red]{alert.package_version}[/] → [green]{alert.fixed_version}[/]"
        else:
            version_text = f"[red]{alert.package_version}[/]"

        # Risk score
        risk_color = "red" if assessment.risk_score >= 8.0 else "yellow" if assessment.risk_score >= 5.0 else "dim"
        risk_text = f"[{risk_color}]{assessment.risk_score:.1f}[/]"

        table.add_row(
            str(i),
            priority_text,
            action_text,
            cve_package,
            version_text,
            risk_text,
            alert.project_name,
        )

    console.print()
    console.print(table)
    console.print()

    # Summary
    fix_now = len([a for a in assessments if a.action == "FIX_NOW"])
    fix_soon = len([a for a in assessments if a.action == "FIX_SOON"])
    monitor = len([a for a in assessments if a.action == "MONITOR"])

    summary_cols = []
    if fix_now > 0:
        summary_cols.append(f"[red]⚡ Fix Now: {fix_now}[/]")
    if fix_soon > 0:
        summary_cols.append(f"[yellow]⚠ Fix Soon: {fix_soon}[/]")
    if monitor > 0:
        summary_cols.append(f"[dim]👁 Monitor: {monitor}[/]")

    if summary_cols:
        console.print(Columns(summary_cols, equal=True, expand=True))
        console.print()


def _show_detailed_list(assessments: list) -> None:
    """Show detailed tree view of security issues."""
    console.print()
    console.print(
        Panel.fit(
            f"[bold]Security Issues[/] [dim]({len(assessments)} total)[/]",
            border_style="blue",
        )
    )
    console.print()

    # Group by project
    by_project: dict[str, list] = {}
    for assessment in assessments:
        project_name = assessment.alert.project_name
        if project_name not in by_project:
            by_project[project_name] = []
        by_project[project_name].append(assessment)

    # Create tree structure
    root = Tree("[bold cyan]Security Issues[/]")

    for project_name, project_assessments in sorted(by_project.items()):
        project_type = project_assessments[0].alert.project_type
        project_branch = root.add(
            f"[bold cyan]{project_name}[/] [dim]({project_type})[/] [dim]- {len(project_assessments)} issue(s)[/]"
        )

        for assessment in project_assessments:
            alert = assessment.alert

            # Priority and action badges
            priority_colors = {
                "CRITICAL": ("red", "🔴"),
                "HIGH": ("yellow", "🟡"),
                "MEDIUM": ("blue", "🔵"),
                "LOW": ("dim", "⚪"),
            }
            priority_color, priority_icon = priority_colors.get(assessment.priority, ("white", "○"))
            priority_text = f"[{priority_color}]{priority_icon} {assessment.priority}[/]"

            action_colors = {
                "FIX_NOW": ("red", "⚡"),
                "FIX_SOON": ("yellow", "⚠"),
                "MONITOR": ("dim", "👁"),
            }
            action_color, action_icon = action_colors.get(assessment.action, ("white", "○"))
            action_text = f"[{action_color}]{action_icon} {assessment.action}[/]"

            # Issue header
            if alert.cve_id:
                issue_header = f"{priority_text} {action_text} [bold]{alert.cve_id}[/] in [cyan]{alert.package_name}[/]"
            else:
                issue_header = f"{priority_text} {action_text} [cyan]{alert.package_name}[/]"

            issue_branch = project_branch.add(issue_header)

            # Details table
            details_table = Table(show_header=False, box=None, padding=(0, 1))
            details_table.add_column("Label", style="bold", width=18)
            details_table.add_column("Value", style="")

            # Version info
            if alert.fixed_version:
                version_info = f"[red]{alert.package_version}[/] → [green]{alert.fixed_version}[/]"
            else:
                version_info = f"[red]{alert.package_version}[/] [dim](no fix available)[/]"
            details_table.add_row("Version", version_info)

            # Risk score
            risk_color = "red" if assessment.risk_score >= 8.0 else "yellow" if assessment.risk_score >= 5.0 else "dim"
            details_table.add_row("Risk Score", f"[{risk_color}]{assessment.risk_score:.1f}/10.0[/]")

            # CVSS
            if alert.cvss_score:
                details_table.add_row("CVSS", f"{alert.cvss_score:.1f}")

            # Severity
            severity_colors = {
                "critical": "red",
                "high": "yellow",
                "medium": "blue",
                "low": "dim",
            }
            severity_color = severity_colors.get(alert.severity.lower(), "white")
            details_table.add_row("Severity", f"[{severity_color}]{alert.severity.upper()}[/]")

            # Source
            details_table.add_row("Source", alert.source)

            # Description (truncated)
            if alert.description:
                desc = alert.description
                if len(desc) > 150:
                    desc = desc[:150] + "..."
                details_table.add_row("Description", desc)

            # Recommended fix
            if assessment.recommended_fix:
                details_table.add_row("Fix", f"[green]{assessment.recommended_fix}[/]")

            # Exploit warning
            if alert.exploit_available:
                exploit_maturity = alert.exploit_maturity or "available"
                details_table.add_row("⚠ Exploit", f"[bold red]{exploit_maturity}[/]")

            # Add table to branch
            issue_branch.add(details_table)

    console.print(root)
    console.print()

    # Summary
    total = len(assessments)
    fix_now = len([a for a in assessments if a.action == "FIX_NOW"])
    fix_soon = len([a for a in assessments if a.action == "FIX_SOON"])
    monitor = len([a for a in assessments if a.action == "MONITOR"])

    summary_parts = [f"[bold]Total: {total}[/]"]
    if fix_now > 0:
        summary_parts.append(f"[red]⚡ Fix Now: {fix_now}[/]")
    if fix_soon > 0:
        summary_parts.append(f"[yellow]⚠ Fix Soon: {fix_soon}[/]")
    if monitor > 0:
        summary_parts.append(f"[dim]👁 Monitor: {monitor}[/]")

    console.print(Columns(summary_parts, equal=True, expand=True))
    console.print()


# Register security subcommands
app.add_typer(security_app)


if __name__ == "__main__":
    app()
