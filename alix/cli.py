import click
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
import json  # Add this import
from datetime import datetime  # Add this import

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
def add(name, command, description, no_apply):
    """Add a new alias to your collection and apply it immediately"""
    alias = Alias(name=name, command=command, description=description)

    if storage.add(alias):
        console.print(f"[green]✓[/] Added alias: [cyan]{name}[/] = '{command}'")

        # Auto-apply to shell unless disabled
        if not no_apply:
            integrator = ShellIntegrator()
            success, message = integrator.apply_single_alias(alias)

            if success:
                console.print(f"[green]✓[/] {message}")
                console.print(f"[dim]💡 Alias '{name}' is now available in new shell sessions[/]")
                console.print(f"[dim]   For current session, run: source ~/{integrator.get_target_file().name}[/]")
            else:
                console.print(f"[yellow]⚠[/] Alias saved but not applied: {message}")
                console.print(f"[dim]   Run 'alix apply' to apply all aliases to shell[/]")
    else:
        console.print(f"[red]✗[/] Alias '{name}' already exists!")


@main.command()
@click.option("--merge/--replace", default=True, help="Merge with existing or replace")
@click.option("--source", "-s", type=click.Choice(['system', 'active', 'file']),
              default='system', help="Import source")
@click.option("--file", "-f", type=click.Path(exists=True), help="File to import from")
def scan(merge, source, file):
    """Scan and import existing aliases from your system"""
    scanner = AliasScanner()
    imported_count = 0
    skipped_count = 0

    if source == 'file' and file:
        # Import from specific file
        filepath = Path(file)
        aliases = scanner.scan_file(filepath)
        console.print(f"[cyan]Found {len(aliases)} aliases in {filepath.name}[/]")
    elif source == 'active':
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
    sorted_aliases = sorted(aliases, key=lambda a: len(a.command) - len(a.name), reverse=True)[:5]
    table = Table(show_header=False, box=None, padding=(0, 2))
    for i, alias in enumerate(sorted_aliases, 1):
        saved = len(alias.command) - len(alias.name)
        table.add_row(
            f"{i}.",
            f"[cyan]{alias.name}[/]",
            f"saves {saved} chars",
            f"[dim]({alias.command[:30]}...)[/]" if len(alias.command) > 30 else f"[dim]({alias.command})[/]"
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
    console.print(f"\n[dim]💡 Tip: Run 'alix' for interactive mode![/]")

@main.group()
def group():
    """Manage alias groups"""
    pass

@group.command()
@click.option("--name", "-n", prompt=True, help="Group name")
def create(name):
    """Create a new group (shows existing aliases that can be assigned)"""
    aliases = storage.list_all()
    ungrouped_aliases = [a for a in aliases if not a.group]
    
    if not ungrouped_aliases:
        console.print(f"[yellow]No ungrouped aliases found to assign to group '{name}'[/]")
        return
    
    console.print(f"[cyan]Creating group '{name}'[/]")
    console.print(f"[dim]Found {len(ungrouped_aliases)} ungrouped aliases[/]")
    
    # Show ungrouped aliases
    table = Table(title=f"Ungrouped Aliases")
    table.add_column("Name", style="cyan")
    table.add_column("Command", style="white")
    table.add_column("Description", style="dim")
    
    for alias in ungrouped_aliases:
        table.add_row(
            alias.name,
            alias.command[:50] + "..." if len(alias.command) > 50 else alias.command,
            alias.description or "—"
        )
    
    console.print(table)
    console.print(f"\n[dim]💡 Use 'alix group add {name} <alias_name>' to add aliases to this group[/]")

@group.command()
def list():
    """List all groups and their aliases"""
    aliases = storage.list_all()
    groups = {}
    
    # Group aliases by their group
    for alias in aliases:
        group_name = alias.group or "Ungrouped"
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(alias)
    
    if not groups:
        console.print("[yellow]No groups found[/]")
        return
    
    for group_name, group_aliases in sorted(groups.items()):
        console.print(f"\n[bold cyan]📁 {group_name}[/] ({len(group_aliases)} aliases)")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", width=20)
        table.add_column("Command", style="white", width=40)
        table.add_column("Description", style="dim", width=30)
        
        for alias in sorted(group_aliases, key=lambda a: a.name):
            table.add_row(
                alias.name,
                alias.command[:40] + "..." if len(alias.command) > 40 else alias.command,
                alias.description or "—"
            )
        
        console.print(table)

@group.command()
@click.argument("group_name")
@click.argument("alias_name")
def add(group_name, alias_name):
    """Add an alias to a group"""
    alias = storage.get(alias_name)
    if not alias:
        console.print(f"[red]✗[/] Alias '{alias_name}' not found!")
        return
    
    if alias.group == group_name:
        console.print(f"[yellow]⚠[/] Alias '{alias_name}' is already in group '{group_name}'")
        return
    
    # Update the alias with the new group
    alias.group = group_name
    storage.aliases[alias_name] = alias
    storage.save()
    
    console.print(f"[green]✓[/] Added '{alias_name}' to group '{group_name}'")

@group.command()
@click.argument("group_name")
@click.argument("alias_name")
def remove(group_name, alias_name):
    """Remove an alias from a group"""
    alias = storage.get(alias_name)
    if not alias:
        console.print(f"[red]✗[/] Alias '{alias_name}' not found!")
        return
    
    if alias.group != group_name:
        console.print(f"[yellow]⚠[/] Alias '{alias_name}' is not in group '{group_name}'")
        return
    
    # Remove the group from the alias
    alias.group = None
    storage.aliases[alias_name] = alias
    storage.save()
    
    console.print(f"[green]✓[/] Removed '{alias_name}' from group '{group_name}'")

@group.command()
@click.argument("group_name")
@click.option("--reassign", help="Reassign aliases to this group instead of deleting")
@click.confirmation_option(prompt="Are you sure you want to delete this group?")
def delete(group_name, reassign):
    """Delete a group and optionally reassign aliases"""
    aliases = storage.list_all()
    group_aliases = [a for a in aliases if a.group == group_name]
    
    if not group_aliases:
        console.print(f"[yellow]⚠[/] Group '{group_name}' not found or is empty")
        return
    
    console.print(f"[cyan]Found {len(group_aliases)} aliases in group '{group_name}'[/]")
    
    if reassign:
        # Reassign to another group
        new_group = reassign
        for alias in group_aliases:
            alias.group = new_group
            storage.aliases[alias.name] = alias
        storage.save()
        console.print(f"[green]✓[/] Reassigned {len(group_aliases)} aliases to group '{new_group}'")
    else:
        # Remove group from aliases (set to None)
        for alias in group_aliases:
            alias.group = None
            storage.aliases[alias.name] = alias
        storage.save()
        console.print(f"[green]✓[/] Removed group '{group_name}' from {len(group_aliases)} aliases")

@group.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--group", "-g", help="Import to specific group (overrides file group)")
def import_group(file, group):
    """Import aliases from a group export file"""
    try:
        with open(file, 'r') as f:
            data = json.load(f)
        
        if "aliases" not in data:
            console.print(f"[red]✗[/] Invalid group export file")
            return
        
        target_group = group or data.get("group", "imported")
        imported_count = 0
        skipped_count = 0
        
        for alias_name, alias_data in data["aliases"].items():
            if alias_name in storage.aliases:
                skipped_count += 1
                continue
            
            alias = Alias.from_dict(alias_data)
            alias.group = target_group
            storage.aliases[alias_name] = alias
            imported_count += 1
        
        storage.save()
        
        console.print(f"[green]✓[/] Imported {imported_count} aliases to group '{target_group}'")
        if skipped_count > 0:
            console.print(f"[yellow]⚠[/] Skipped {skipped_count} existing aliases")
            
    except Exception as e:
        console.print(f"[red]✗[/] Failed to import: {e}")

@group.command()
@click.argument("group_name")
@click.option("--apply", is_flag=True, help="Apply all aliases in group to shell")
def apply(group_name, apply):
    """Apply all aliases in a group to shell"""
    aliases = storage.list_all()
    group_aliases = [a for a in aliases if a.group == group_name]
    
    if not group_aliases:
        console.print(f"[yellow]⚠[/] Group '{group_name}' not found or is empty")
        return
    
    console.print(f"[cyan]Applying {len(group_aliases)} aliases from group '{group_name}'[/]")
    
    integrator = ShellIntegrator()
    success_count = 0
    
    for alias in group_aliases:
        success, message = integrator.apply_single_alias(alias)
        if success:
            success_count += 1
            console.print(f"[green]✓[/] Applied: {alias.name}")
        else:
            console.print(f"[red]✗[/] Failed: {alias.name} - {message}")
    
    console.print(f"\n[bold]Summary:[/] {success_count}/{len(group_aliases)} aliases applied successfully")
    
    if success_count > 0:
        target_file = integrator.get_target_file()
        if target_file:
            console.print(f"\n[dim]💡 Run 'source {target_file}' to activate in current session[/]")

if __name__ == "__main__":
    main()