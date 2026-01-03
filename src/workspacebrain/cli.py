"""CLI entry point for WorkspaceBrain using Typer."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from workspacebrain import __version__
from rich.panel import Panel
from rich.table import Table

from workspacebrain.core.doctor import BrainDoctor, CheckStatus
from workspacebrain.core.installer import BrainInstaller
from workspacebrain.core.linker import BrainLinker
from workspacebrain.core.scanner import WorkspaceScanner
from workspacebrain.models import BrainConfig

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
                # Confidence color based on value
                if project.confidence >= 0.8:
                    conf_color = "green"
                elif project.confidence >= 0.5:
                    conf_color = "yellow"
                else:
                    conf_color = "red"

                conf_pct = int(project.confidence * 100)
                console.print(
                    f"  [bold]{project.name}[/] "
                    f"[cyan]({project.project_type})[/] "
                    f"[{conf_color}]{conf_pct}%[/]"
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
            conf_pct = int(project.confidence * 100)
            console.print(f"    [dim]•[/] {project.name} [cyan]({project.project_type})[/] {conf_pct}%")

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


if __name__ == "__main__":
    app()
