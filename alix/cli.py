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
from alix.shell_wrapper import ShellWrapper

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
@click.option("--detailed", "-d", is_flag=True, help="Show detailed usage analytics")
@click.option("--export", "-e", type=click.Path(), help="Export analytics to file")
def stats(detailed, export):
    """Show comprehensive statistics and usage analytics about your aliases"""
    aliases = storage.list_all()

    if not aliases:
        console.print("[yellow]No aliases yet![/] Start with 'alix add'")
        return

    # Get usage analytics
    analytics = storage.get_usage_analytics()
    
    # Basic statistics
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

    # Create enhanced stats panel
    stats_text = f"""
[bold cyan]📊 Alias Statistics & Analytics[/]

[yellow]Total Aliases:[/] {total}
[yellow]Total Uses:[/] {analytics['total_uses']:,}
[yellow]Characters Saved:[/] ~{total_chars_saved:,} keystrokes
[yellow]Average Command Length:[/] {avg_length:.1f} chars
[yellow]Average Usage per Alias:[/] {analytics['average_usage_per_alias']:.1f}
[yellow]Most Used:[/] {analytics['most_used_alias'] or 'N/A'} ({most_used.used_count if most_used else 0} times)
[yellow]Newest:[/] {newest.name if newest else 'N/A'}
[yellow]Unused Aliases:[/] {len(analytics['unused_aliases'])}
[yellow]Recently Used (7 days):[/] {len(analytics['recently_used'])}
[yellow]Storage:[/] {storage.storage_path.name}
[yellow]Backups:[/] {len(list(storage.backup_dir.glob('*.json')))} files"""

    console.print(Panel.fit(stats_text, border_style="cyan"))

    # Show detailed analytics if requested
    if detailed:
        console.print("\n[bold cyan]📈 Detailed Usage Analytics[/]")
        
        # Unused aliases
        if analytics['unused_aliases']:
            console.print(f"\n[yellow]⚠️  Unused Aliases ({len(analytics['unused_aliases'])}):[/]")
            for alias_name in analytics['unused_aliases'][:10]:  # Show first 10
                console.print(f"  • [dim]{alias_name}[/]")
            if len(analytics['unused_aliases']) > 10:
                console.print(f"  ... and {len(analytics['unused_aliases']) - 10} more")
        
        # Recently used aliases
        if analytics['recently_used']:
            console.print(f"\n[green]🔥 Recently Used (7 days):[/]")
            for alias_name in analytics['recently_used'][:10]:  # Show first 10
                alias = storage.get(alias_name)
                if alias:
                    console.print(f"  • [cyan]{alias_name}[/] - {alias.used_count} uses")
        
        # Most productive aliases
        if analytics['most_productive_aliases']:
            console.print(f"\n[bold]💪 Most Productive Aliases:[/]")
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Rank", style="dim", width=6)
            table.add_column("Alias", style="cyan")
            table.add_column("Chars Saved", style="green")
            table.add_column("Usage Count", style="yellow")
            
            for i, (alias_name, chars_saved) in enumerate(analytics['most_productive_aliases'][:10], 1):
                alias = storage.get(alias_name)
                usage_count = alias.used_count if alias else 0
                table.add_row(
                    f"{i}.",
                    alias_name,
                    str(chars_saved),
                    str(usage_count)
                )
            console.print(table)
        
        # Usage trends (last 7 days)
        if analytics['usage_trends']:
            console.print(f"\n[bold]📅 Usage Trends (Last 7 Days):[/]")
            recent_days = sorted(analytics['usage_trends'].items(), reverse=True)[:7]
            for date, count in recent_days:
                console.print(f"  {date}: {count} uses")

    # Show top 5 space savers
    console.print(f"\n[bold]🏆 Top Commands by Length Saved:[/]")
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
    
    # Export analytics if requested
    if export:
        output_path = Path(export)
        storage.usage_tracker.export_analytics(output_path)
        console.print(f"\n[green]✓[/] Analytics exported to: [cyan]{output_path}[/]")


@main.command()
@click.argument("alias_name")
@click.option("--context", "-c", help="Additional context for this usage")
def track(alias_name, context):
    """Manually track usage of an alias"""
    alias = storage.get(alias_name)
    if not alias:
        console.print(f"[red]✗[/] Alias '{alias_name}' not found!")
        return
    
    storage.track_usage(alias_name, context)
    console.print(f"[green]✓[/] Tracked usage of alias '{alias_name}'")
    
    # Show updated stats
    alias = storage.get(alias_name)  # Get updated alias
    console.print(f"[dim]Total uses: {alias.used_count}[/]")
    if alias.last_used:
        console.print(f"[dim]Last used: {alias.last_used.strftime('%Y-%m-%d %H:%M:%S')}[/]")


@main.command()
@click.option("--days", "-d", default=30, help="Number of days to show history for")
@click.option("--alias", "-a", help="Show history for specific alias only")
def history(days, alias):
    """Show usage history and trends"""
    if alias:
        # Show history for specific alias
        alias_obj = storage.get(alias)
        if not alias_obj:
            console.print(f"[red]✗[/] Alias '{alias}' not found!")
            return
        
        console.print(f"[bold cyan]📈 Usage History for '{alias}'[/]")
        console.print(f"Total uses: {alias_obj.used_count}")
        if alias_obj.last_used:
            console.print(f"Last used: {alias_obj.last_used.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show recent usage history
        history = storage.usage_tracker.get_alias_usage_history(alias, days)
        if history:
            console.print(f"\n[bold]Recent Usage ({days} days):[/]")
            for record in history[-10:]:  # Show last 10 records
                date = datetime.fromisoformat(record['date'])
                console.print(f"  {date.strftime('%Y-%m-%d %H:%M')}")
        else:
            console.print("[dim]No usage history found[/]")
    else:
        # Show overall usage trends
        analytics = storage.get_usage_analytics()
        console.print(f"[bold cyan]📊 Overall Usage Trends ({days} days)[/]")
        
        if analytics['usage_trends']:
            recent_days = sorted(analytics['usage_trends'].items(), reverse=True)[:days]
            total_recent_usage = sum(count for _, count in recent_days)
            console.print(f"Total usage in last {days} days: {total_recent_usage}")
            
            console.print(f"\n[bold]Daily Breakdown:[/]")
            for date, count in recent_days:
                console.print(f"  {date}: {count} uses")
        else:
            console.print("[dim]No usage data available[/]")


@main.command()
@click.option("--shell", "-s", help="Target shell (auto-detect if not specified)")
@click.option("--file", "-f", type=click.Path(), help="Custom config file path")
@click.option("--standalone", is_flag=True, help="Create standalone tracking script")
@click.option("--output", "-o", type=click.Path(), help="Output path for standalone script")
def setup_tracking(shell, file, standalone, output):
    """Set up automatic usage tracking for aliases"""
    wrapper = ShellWrapper()
    
    # Determine shell type
    if shell:
        try:
            shell_type = ShellType(shell.lower())
        except ValueError:
            console.print(f"[red]Invalid shell type: {shell}[/]")
            console.print("[dim]Valid options: bash, zsh, fish[/]")
            return
    else:
        # Auto-detect shell
        from alix.shell_detector import ShellDetector, ShellType
        detector = ShellDetector()
        shell_type = detector.detect_current_shell()
        if not shell_type or shell_type == ShellType.UNKNOWN:
            console.print("[red]Could not detect shell type. Please specify with --shell[/]")
            return
    
    if standalone:
        # Create standalone tracking script
        if not output:
            output = Path.home() / f".alix_tracking_{shell_type.value}.sh"
        
        success = wrapper.create_standalone_tracking_script(Path(output), shell_type.value)
        if success:
            console.print(f"[green]✓[/] Standalone tracking script created: [cyan]{output}[/]")
            console.print(f"[dim]To use: source {output}[/]")
        else:
            console.print(f"[red]✗[/] Failed to create tracking script")
    else:
        # Install into shell config
        if file:
            config_file = Path(file)
        else:
            integrator = ShellIntegrator()
            config_file = integrator.get_target_file()
        
        if not config_file or not config_file.exists():
            console.print(f"[red]✗[/] Shell config file not found: {config_file}")
            return
        
        success = wrapper.install_tracking_integration(config_file, shell_type.value)
        if success:
            console.print(f"[green]✓[/] Usage tracking installed in: [cyan]{config_file}[/]")
            console.print(f"[dim]Restart your shell or run: source {config_file}[/]")
        else:
            console.print(f"[red]✗[/] Failed to install tracking integration")


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
- `alix stats` - View statistics with usage analytics
- `alix track` - Manually track alias usage
- `alix history` - Show usage history and trends
- `alix setup-tracking` - Set up automatic usage tracking
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


if __name__ == "__main__":
    main()