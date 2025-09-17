import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt

from alix.models import Alias
from alix.storage import AliasStorage
from alix.shell_integrator import ShellIntegrator
from alix.porter import AliasPorter
from alix.config import Config

console = Console()
storage = AliasStorage()
config = Config()


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
    if not force and config.get("confirm_delete", True):
        if not Confirm.ask(f"Remove alias '{name}'?"):
            return

    if storage.remove(name):
        console.print(f"[green]✓[/] Removed alias: [cyan]{name}[/]")


@main.command(name="config")
@click.option("--list", "list_config", is_flag=True, help="List all settings")
@click.option("--set", "set_key", help="Setting to change")
@click.option("--value", help="New value for setting")
@click.option("--themes", is_flag=True, help="List available themes")
def configure(list_config, set_key, value, themes):
    """Manage alix configuration"""
    if themes:
        table = Table(title="Available Themes")
        table.add_column("Theme", style="cyan")
        table.add_column("Description", style="dim")

        themes_info = {
            "default": "Classic cyan theme",
            "ocean": "Blue ocean colors",
            "forest": "Green forest theme",
            "monochrome": "Black and white"
        }

        current = config.get("theme", "default")
        for theme_name, desc in themes_info.items():
            if theme_name == current:
                table.add_row(f"► {theme_name}", f"{desc} [current]")
            else:
                table.add_row(f"  {theme_name}", desc)

        console.print(table)
        console.print("\n[dim]Change theme in TUI with 't' key or:[/]")
        console.print("alix config --set theme --value ocean")

    elif list_config:
        table = Table(title="Current Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")

        descriptions = {
            "theme": "Color theme for TUI",
            "auto_backup": "Create backups automatically",
            "confirm_delete": "Ask before deleting",
            "show_descriptions": "Show descriptions in TUI",
            "max_backups": "Maximum backup files to keep"
        }

        for key, value in config.config.items():
            desc = descriptions.get(key, "")
            table.add_row(key, str(value), desc)

        console.print(table)

    elif set_key and value is not None:
        # Type conversion for known boolean/int settings
        if set_key in ["auto_backup", "confirm_delete", "show_descriptions"]:
            value = value.lower() in ["true", "yes", "1", "on"]
        elif set_key == "max_backups":
            value = int(value)

        config.set(set_key, value)
        console.print(f"[green]✓[/] Set {set_key} = {value}")

        if set_key == "theme":
            console.print("[dim]Restart TUI to see theme changes[/]")

    else:
        console.print("Use --list to see settings or --set with --value to change")


@main.command(name="list")
def list_aliases():
    """List all aliases"""
    aliases = storage.list_all()
    if not aliases:
        console.print("[yellow]No aliases found.[/] Add one with 'alix add'")
        return

    theme = config.get_theme()
    table = Table(title=f"📋 Your Aliases ({len(aliases)} total)")
    table.add_column("Name", style=theme['header_color'], no_wrap=True)
    table.add_column("Command", style=theme['success_color'])

    if config.get("show_descriptions", True):
        table.add_column("Description", style="dim")
        for alias in sorted(aliases, key=lambda a: a.name):
            table.add_row(alias.name, alias.command, alias.description or "")
    else:
        for alias in sorted(aliases, key=lambda a: a.name):
            table.add_row(alias.name, alias.command)

    console.print(table)


if __name__ == "__main__":
    main()