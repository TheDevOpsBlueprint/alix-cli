import click
import subprocess
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from rich.markdown import Markdown

from alix import __version__
from alix.models import Alias
from alix.storage import AliasStorage
from alix.shell_integrator import ShellIntegrator
from alix.shell_detector import ShellType  # NEW IMPORT
from alix.scanner import AliasScanner
from alix.porter import AliasPorter
from alix.config import Config

console = Console()
storage = AliasStorage()
config = Config()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="alix")
def main(ctx):
    """alix - Interactive alias manager for your shell 🚀

    Run without commands to launch interactive TUI mode.
    """
    if ctx.invoked_subcommand is None:
        from alix.tui import AliasManager

        app = AliasManager()
        app.run()


@main.command()
@click.option("--name", "-n", prompt=True, help="Alias name")
@click.option("--command", "-c", prompt=True, help="Command to alias")
@click.option("--description", "-d", help="Description of the alias")
@click.option("--no-apply", is_flag=True, help="Don't apply to shell immediately")
@click.option(
    "--force", is_flag=True, help="Force apply new alias over existing aliases/commands"
)
def add(name, command, description, no_apply, force):
    """Add a new alias to your collection and apply it immediately"""
    msg = None

    command_exists = False
    cmd = storage.get(name)
    if cmd is not None:
        command_exists = True
        msg = f"Alias exists in alix\n{cmd.name}={cmd.command}"

    if not command_exists:
        cmd = subprocess.run(
            [
                "bash",
                "-i",
                "-c",
                f"(alias; declare -f) | /usr/bin/which --tty-only --read-alias --read-functions --show-tilde --show-dot {name}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        print(cmd)
        if cmd.returncode == 0:
            command_exists = True
            msg = cmd.stdout

    if command_exists and not force:
        console.print(
            "[red]Alias/Command/Function already exists. Add --force flag to override"
        )
        console.print(msg)
        exit()

    alias = Alias(name=name, command=command, description=description)
    if storage.add(alias):
        console.print(f"[green]✓[/] Added alias: [cyan]{name}[/] = '{command}'")

        # Auto-apply to shell unless disabled
        if not no_apply:
            integrator = ShellIntegrator()
            success, message = integrator.apply_single_alias(alias)

            if success:
                console.print(f"[green]✓[/] {message}")
                console.print(
                    f"[dim]💡 Alias '{name}' is now available in new shell sessions[/]"
                )
                console.print(
                    f"[dim]   For current session, run: source ~/{integrator.get_target_file().name}[/]"
                )
            else:
                console.print(f"[yellow]⚠[/] Alias saved but not applied: {message}")
                console.print(
                    f"[dim]   Run 'alix apply' to apply all aliases to shell[/]"
                )
    else:
        console.print(f"[red]✗[/] Alias '{name}' already exists!")


@main.command()
@click.option("--merge/--replace", default=True, help="Merge with existing or replace")
@click.option(
    "--source",
    "-s",
    type=click.Choice(["system", "active", "file"]),
    default="system",
    help="Import source",
)
@click.option("--file", "-f", type=click.Path(exists=True), help="File to import from")
def scan(merge, source, file):
    """Scan and import existing aliases from your system"""
    scanner = AliasScanner()
    imported_count = 0
    skipped_count = 0

    if source == "file" and file:
        # Import from specific file
        filepath = Path(file)
        aliases = scanner.scan_file(filepath)
        console.print(f"[cyan]Found {len(aliases)} aliases in {filepath.name}[/]")
    elif source == "active":
        # Import currently active aliases
        aliases = scanner.get_active_aliases()
        console.print(f"[cyan]Found {len(aliases)} active aliases[/]")
    else:
        # Import from all system files
        results = scanner.scan_system()
        aliases = []
        for filename, file_aliases in results.items():
            console.print(f"[dim]  {filename}: {len(file_aliases)} aliases[/]")
            aliases.extend(file_aliases)
        console.print(f"[cyan]Found {len(aliases)} total aliases in system files[/]")

    if not aliases:
        console.print("[yellow]No aliases found to import[/]")
        return

    # Import aliases
    for alias in aliases:
        if alias.name in storage.aliases:
            if merge:
                skipped_count += 1
                continue
            else:
                storage.remove(alias.name)

        if storage.add(alias):
            imported_count += 1
            console.print(f"[green]✓[/] Imported: [cyan]{alias.name}[/]")

    # Summary
    console.print("\n[bold green]Import Complete![/]")
    console.print(f"  Imported: {imported_count} aliases")
    if skipped_count > 0:
        console.print(f"  Skipped: {skipped_count} existing aliases")

    console.print("\n[dim]💡 Run 'alix apply' to add these to your shell config[/]")


# NEW COMMAND: apply
@main.command()
@click.option("--shell", "-s", help="Target shell (auto-detect if not specified)")
@click.option("--file", "-f", type=click.Path(), help="Custom config file path")
@click.confirmation_option(prompt="Apply all aliases to shell config?")
def apply(shell, file):
    """Apply all aliases to your shell configuration"""
    integrator = ShellIntegrator()

    # Override shell type if specified
    if shell:
        try:
            integrator.shell_type = ShellType(shell.lower())
        except ValueError:
            console.print(f"[red]Invalid shell type: {shell}[/]")
            console.print("[dim]Valid options: bash, zsh, fish, sh[/]")
            return

    # Get target file
    if file:
        target_file = Path(file)
        if not target_file.exists():
            console.print(f"[red]File not found: {file}[/]")
            return
    else:
        target_file = integrator.get_target_file()

    if not target_file:
        console.print("[red]No shell configuration file found![/]")
        console.print("[dim]Try specifying a file with --file option[/]")
        return

    # Show what will be done
    aliases = storage.list_all()
    console.print(f"[cyan]Applying {len(aliases)} aliases to: {target_file}[/]")

    # Apply aliases
    success, message = integrator.apply_aliases(target_file)

    if success:
        console.print(f"[green]✓[/] {message}")
        console.print("\n[bold]Next steps:[/]")
        console.print(f"  1. Restart your terminal, OR")
        console.print(f"  2. Run: [cyan]source {target_file}[/]")
        console.print(f"\n[dim]Your aliases are now ready to use![/]")
    else:
        console.print(f"[red]✗[/] {message}")


@main.command()
def stats():
    """Show statistics about your aliases"""
    aliases = storage.list_all()

    if not aliases:
        console.print("[yellow]No aliases yet![/] Start with 'alix add'")
        return

    # Calculate statistics
    total = len(aliases)
    total_chars_saved = sum(len(a.command) - len(a.name) for a in aliases)
    avg_length = sum(len(a.command) for a in aliases) / total if total > 0 else 0
    most_used = max(aliases, key=lambda a: a.used_count) if aliases else None
    newest = max(aliases, key=lambda a: a.created_at) if aliases else None

    # Shell distribution
    shells = {}
    for alias in aliases:
        shell = alias.shell or "unspecified"
        shells[shell] = shells.get(shell, 0) + 1

    # Create stats panel
    stats_text = f"""
[bold cyan]📊 Alias Statistics[/]

[yellow]Total Aliases:[/] {total}
[yellow]Characters Saved:[/] ~{total_chars_saved:,} keystrokes
[yellow]Average Command Length:[/] {avg_length:.1f} chars
[yellow]Most Used:[/] {most_used.name if most_used else 'N/A'} ({most_used.used_count} times)
[yellow]Newest:[/] {newest.name if newest else 'N/A'}
[yellow]Storage:[/] {storage.storage_path.name}
[yellow]Backups:[/] {len(list(storage.backup_dir.glob('*.json')))} files

[bold]Top Commands by Length Saved:[/]"""

    console.print(Panel.fit(stats_text, border_style="cyan"))

    # Show top 5 space savers
    sorted_aliases = sorted(
        aliases, key=lambda a: len(a.command) - len(a.name), reverse=True
    )[:5]
    table = Table(show_header=False, box=None, padding=(0, 2))
    for i, alias in enumerate(sorted_aliases, 1):
        saved = len(alias.command) - len(alias.name)
        table.add_row(
            f"{i}.",
            f"[cyan]{alias.name}[/]",
            f"saves {saved} chars",
            (
                f"[dim]({alias.command[:30]}...)[/]"
                if len(alias.command) > 30
                else f"[dim]({alias.command})[/]"
            ),
        )
    console.print(table)


@main.command()
def about():
    """About alix and quick help"""
    about_text = f"""
# 🚀 alix v{__version__}

**Interactive alias manager for your shell**

## Quick Start
- Run `alix` to launch interactive TUI
- Press `?` in TUI for keyboard shortcuts
- Use `alix add` to add aliases from CLI
- Use `alix apply` to update your shell config

## Key Features
✨ Interactive TUI with search and filtering
🎨 Beautiful themes (press 't' in TUI)
💾 Auto-backup before changes
📤 Export/import alias collections
🚀 Multi-shell support (bash, zsh, fish)

## Commands
- `alix` - Launch interactive TUI
- `alix add` - Add new alias
- `alix list` - List all aliases
- `alix remove` - Remove an alias
- `alix apply` - Apply to shell config
- `alix export/import` - Share collections
- `alix stats` - View statistics
- `alix config` - Manage settings

## Learn More
GitHub: https://github.com/TheDevOpsBlueprint/alix-cli
    """
    console.print(Markdown(about_text))


@main.command(name="list")
def list_aliases():
    """List all aliases in a beautiful table"""
    aliases = storage.list_all()
    if not aliases:
        console.print("[yellow]No aliases found.[/] Add one with 'alix add'")
        return

    theme = config.get_theme()
    table = Table(title=f"📋 Your Aliases ({len(aliases)} total)")
    table.add_column("Name", style=theme["header_color"], no_wrap=True)
    table.add_column("Command", style=theme["success_color"])

    if config.get("show_descriptions", True):
        table.add_column("Description", style="dim")
        for alias in sorted(aliases, key=lambda a: a.name):
            table.add_row(alias.name, alias.command, alias.description or "")
    else:
        for alias in sorted(aliases, key=lambda a: a.name):
            table.add_row(alias.name, alias.command)

    console.print(table)
    console.print(f"\n[dim]💡 Tip: Run 'alix' for interactive mode![/]")


if __name__ == "__main__":
    main()
