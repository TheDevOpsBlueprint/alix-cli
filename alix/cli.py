import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from alix.models import Alias
from alix.storage import AliasStorage
from alix.shell_integrator import ShellIntegrator

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
        console.print(f"[dim]Run 'alix apply' to update your shell[/]")
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
        console.print(f"[dim]Run 'alix apply' to update your shell[/]")


@main.command()
@click.option("--dry-run", is_flag=True, help="Show what would be applied")
def apply(dry_run):
    """Apply aliases to your shell configuration"""
    integrator = ShellIntegrator()

    if dry_run:
        aliases = storage.list_all()
        console.print(Panel.fit(
            f"[cyan]Would apply {len(aliases)} aliases to {integrator.shell_type.value}[/]\n"
            f"Target file: {integrator.get_target_file() or 'None'}",
            title="Dry Run"
        ))
        for alias in aliases[:5]:  # Show first 5
            console.print(f"  alias {alias.name}='{alias.command}'")
        if len(aliases) > 5:
            console.print(f"  ... and {len(aliases) - 5} more")
        return

    success, message = integrator.apply_aliases()
    if success:
        console.print(f"[green]✓[/] {message}")
        console.print("[yellow]Restart your shell or run:[/] source ~/.*rc")
    else:
        console.print(f"[red]✗[/] {message}")


@main.command()
def export():
    """Export aliases in shell format"""
    integrator = ShellIntegrator()
    aliases_text = integrator.export_aliases(integrator.shell_type)

    if aliases_text:
        console.print(Panel(aliases_text, title=f"Aliases for {integrator.shell_type.value}"))
    else:
        console.print("[yellow]No aliases to export[/]")


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