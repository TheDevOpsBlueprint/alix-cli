import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from alix.models import Alias
from alix.storage import AliasStorage
from alix.shell_integrator import ShellIntegrator
from alix.porter import AliasPorter

console = Console()
storage = AliasStorage()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.0", prog_name="alix")
def main(ctx):
    """alix - Interactive alias manager for your shell 🚀"""
    if ctx.invoked_subcommand is None:
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


@main.command(name="export")
@click.argument("filename", type=click.Path())
@click.option("--format", type=click.Choice(["json", "yaml"]), default="json")
def export_aliases(filename, format):
    """Export aliases to a file"""
    porter = AliasPorter()
    filepath = Path(filename)

    if filepath.suffix == "":
        filepath = filepath.with_suffix(f".{format}")

    success, message = porter.export_to_file(filepath, format)
    if success:
        console.print(f"[green]✓[/] {message}")
        console.print(f"[dim]Share this file to share your aliases![/]")
    else:
        console.print(f"[red]✗[/] {message}")


@main.command(name="import")
@click.argument("filename", type=click.Path(exists=True))
@click.option("--merge", is_flag=True, help="Merge with existing aliases")
def import_aliases(filename, merge):
    """Import aliases from a file"""
    porter = AliasPorter()
    filepath = Path(filename)

    # Show preview
    console.print(f"[cyan]Importing from:[/] {filepath.name}")

    if not merge and storage.list_all():
        console.print("[yellow]Warning:[/] This will replace existing aliases!")
        if not Confirm.ask("Continue?"):
            console.print("[red]Import cancelled[/]")
            return

    success, message = porter.import_from_file(filepath, merge)
    if success:
        console.print(f"[green]✓[/] {message}")
        console.print(f"[dim]Run 'alix list' to see imported aliases[/]")
    else:
        console.print(f"[red]✗[/] {message}")


@main.command(name="list")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
def list_aliases(verbose):
    """List all aliases"""
    aliases = storage.list_all()
    if not aliases:
        console.print("[yellow]No aliases found.[/] Add one with 'alix add'")
        return

    table = Table(title=f"📋 Your Aliases ({len(aliases)} total)")
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