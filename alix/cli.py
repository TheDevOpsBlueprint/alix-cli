import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from alix.models import Alias, TEST_ALIAS_NAME
from alix.storage import AliasStorage

console = Console()
storage = AliasStorage()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.0", prog_name="alix")
def main(ctx):
    """alix - Interactive alias manager for your shell 🚀"""
    if ctx.invoked_subcommand is None:
        # Launch interactive TUI
        from alix.tui import AliasManager
        app = AliasManager()
        app.run()


@main.command()
@click.option("--name", "-n", prompt=True, help="Alias name")
@click.option("--command", "-c", prompt=True, help="Command to alias")
@click.option("--description", "-d", help="Description of the alias")
def add(name, command, description):
    """Add a new alias"""
    alias = Alias(name=name, command=command, description=description)
    if storage.add(alias):
        console.print(f"[green]✓[/] Added alias: [cyan]{name}[/] = '{command}'")
        backup = storage.backup_dir / "backups"
        console.print(f"[dim]Backup created in {backup}[/]")
    else:
        console.print(f"[red]✗[/] Alias '{name}' already exists!")


@main.command()
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def remove(name, force):
    """Remove an alias"""
    alias = storage.get(name)
    if not alias:
        console.print(f"[red]✗[/] Alias '{name}' not found!")
        return

    if not force:
        if not Confirm.ask(f"Remove alias '{name}' ({alias.command})?"):
            console.print("[yellow]Cancelled[/]")
            return

    if storage.remove(name):
        console.print(f"[green]✓[/] Removed alias: [cyan]{name}[/]")
        console.print(f"[dim]Backup created. Use 'alix restore' if needed[/]")


@main.command()
def restore():
    """Restore from latest backup"""
    if storage.restore_latest_backup():
        console.print("[green]✓[/] Restored from latest backup")
        console.print(f"[cyan]{len(storage.list_all())}[/] aliases restored")
    else:
        console.print("[red]✗[/] No backups found!")


@main.command(name="list")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
def list_aliases(verbose):
    """List all aliases"""
    aliases = storage.list_all()
    if not aliases:
        console.print("[yellow]No aliases found.[/] Add one with 'alix add'")
        return

    table = Table(title="📋 Your Aliases")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Command", style="green")
    if verbose:
        table.add_column("Description", style="dim")

    for alias in sorted(aliases, key=lambda a: a.name):
        if verbose:
            table.add_row(alias.name, alias.command, alias.description or "")
        else:
            table.add_row(alias.name, alias.command)

    console.print(table)


@main.command()
def backup():
    """Create a manual backup"""
    backup_path = storage.create_backup()
    if backup_path:
        console.print(f"[green]✓[/] Backup created: {backup_path.name}")
    else:
        console.print("[yellow]No aliases to backup[/]")


if __name__ == "__main__":
    main()