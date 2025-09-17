import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
    else:
        console.print(f"[red]✗[/] Alias '{name}' already exists!")


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


if __name__ == "__main__":
    main()