"""CLI interface for alix - Interactive alias manager"""

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.0", prog_name="alix")
def main(ctx):
    """alix - Interactive alias manager for your shell 🚀"""
    if ctx.invoked_subcommand is None:
        # Launch interactive TUI (placeholder for now)
        console.print(Panel.fit(
            "[bold cyan]Interactive mode coming soon![/]\n"
            "Use 'alix --help' to see available commands.",
            title="🚀 alix",
            border_style="cyan"
        ))


@main.command()
@click.option("--name", "-n", prompt=True, help="Alias name")
@click.option("--command", "-c", prompt=True, help="Command to alias")
def add(name, command):
    """Add a new alias"""
    console.print(f"[green]✓[/] Would add alias: [cyan]{name}[/] = '{command}'")
    console.print("[dim]Storage implementation coming soon[/]")


@main.command(name="list")
def list_aliases():
    """List all aliases"""
    console.print("[yellow]📋 Aliases list coming soon![/]")


@main.command()
@click.argument("pattern")
def search(pattern):
    """Search aliases by pattern"""
    console.print(f"[blue]🔍 Would search for:[/] {pattern}")
    console.print("[dim]Search implementation coming soon[/]")


if __name__ == "__main__":
    main()