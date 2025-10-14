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
from alix.shell_detector import ShellType
from alix.scanner import AliasScanner
from alix.porter import AliasPorter
from alix.config import Config
from alix.history_manager import HistoryManager
from click.shell_completion import shell_complete as _click_shell_complete
from alix.shell_wrapper import ShellWrapper
import json
from alix.render import Render
from alix.template_manager import TemplateManager

console = Console()
storage = AliasStorage()
config = Config()
render = Render()


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
@click.option("--tags", "-t", help="Comma-separated tags for the alias")
@click.option("--no-apply", is_flag=True, help="Don't apply to shell immediately")
@click.option("--force", is_flag=True, help="Force apply new alias over existing aliases/commands")
def add(name, command, description, tags, no_apply, force):
    """Add a new alias to your collection and apply it immediately"""
    msg = None

    command_exists = False
    cmd = storage.get(name)
    if cmd is not None:
        command_exists = True
        msg = f"[red]✗[/] Alias '{name}' already exists in alix!\nEdit the alias to override it"

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
        if cmd.returncode == 0:
            command_exists = True
            msg = cmd.stdout

    if command_exists and not force:
        console.print("[red]Alias/Command/Function already exists. Add --force flag to override")
        console.print(msg)
        exit()

    # Parse tags if provided
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    alias = Alias(name=name, command=command, description=description, tags=tag_list)
    if storage.add(alias, record_history=True):
        console.print(f"[green]✔[/] Added alias: [cyan]{name}[/] = '{command}'")

        # Auto-apply to shell unless disabled
        if not no_apply:
            integrator = ShellIntegrator()
            success, message = integrator.apply_single_alias(alias)

            if success:
                console.print(f"[green]✔[/] {message}")
                console.print(f"[dim]💡 Alias '{name}' is now available in new shell sessions[/]")
                console.print(f"[dim]   For current session, run: source ~/{integrator.get_target_file().name}[/]")
            else:
                console.print(f"[yellow]⚠[/] Alias saved but not applied: {message}")
                console.print(f"[dim]   Run 'alix apply' to apply all aliases to shell[/]")
    else:
        console.print(f"[red]✗[/] Alias '{name}' already exists in alix!\nEdit the alias to override it")


@main.command()
@click.option("--name", "-n", prompt=True, help="Alias name")
@click.option("--command", "-c", prompt=True, help="Command to alias")
@click.option("--description", "-d", prompt=True, help="Description of the alias")
@click.option("--no-apply", is_flag=True, help="Don't apply to shell immediately")
def edit(name, command, description, no_apply):
    """Add a new alias to your collection and apply it immediately"""
    msg = None

    alias = storage.get(name)
    if alias is None:
        console.print(f"[red]x[/]The alias '{name}' does not exist in alix yet")
    else:
        # Store original state for history
        original_alias = Alias(
            name=alias.name,
            command=alias.command,
            description=alias.description,
            tags=alias.tags.copy(),
            group=alias.group,
            shell=alias.shell,
            created_at=alias.created_at,
            used_count=alias.used_count,
            last_used=alias.last_used,
            usage_history=alias.usage_history.copy()
        )

        # Update alias with new values
        if command:
            alias.command = command
        if description:
            alias.description = description

        storage.remove(alias.name, record_history=False)
        storage.add(alias, record_history=False)

        # Record history for edit operation
        history_op = {
            "type": "edit",
            "aliases": [original_alias.to_dict()],  # Original state
            "new_aliases": [alias.to_dict()],       # New state
            "timestamp": datetime.now().isoformat()
        }
        storage.history.push(history_op)

        console.print(f"[green]✔[/] Edited alias: [cyan]{name}[/] = '{alias.command}'")

        if not no_apply:
            integrator = ShellIntegrator()
            success, message = integrator.apply_single_alias(alias)

            if success:
                console.print(f"[green]✔[/] {message}")
                console.print(f"[dim]💡 Alias '{name}' is now available in new shell sessions[/]")
                console.print(f"[dim]   For current session, run: source ~/{integrator.get_target_file().name}[/]")
            else:
                console.print(f"[yellow]⚠[/] Alias saved but not applied: {message}")
                console.print(f"[dim]   Run 'alix apply' to apply all aliases to shell[/]")


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
@click.option("--tag", "-t", help="Add a tag to all imported aliases")
def scan(merge, source, file, tag):
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
                storage.remove(alias.name, record_history=True)

        # Add tag if specified
        if tag and tag not in alias.tags:
            alias.tags.append(tag)

        if storage.add(alias, record_history=True):
            imported_count += 1
            console.print(f"[green]✔[/] Imported: [cyan]{alias.name}[/]")

    # Summary
    console.print("\n[bold green]Import Complete![/]")
    console.print(f"  Imported: {imported_count} aliases")
    if skipped_count > 0:
        console.print(f"  Skipped: {skipped_count} existing aliases")

    console.print("\n[dim]💡 Run 'alix apply' to add these to your shell config[/]")


# NEW COMMAND: apply
@main.command()
@click.argument("shell", required=False, type=click.Choice(["bash", "zsh", "fish"]))
@click.option("--install", is_flag=True, help="Install completion for the detected or specified shell")
def completion(shell, install):
    """Generate or install shell completion scripts for bash, zsh, fish.

    Examples:
      alix completion bash
      alix completion zsh --install
      alix completion fish
    """
    prog_name = "alix"

    integrator = ShellIntegrator()
    detected = integrator.shell_type

    target_shell = shell or (detected.value if detected else None)
    if not target_shell:
        console.print("[red]Unable to determine shell. Specify one of: bash, zsh, fish[/]")
        return

    # FIXED: Updated to use Click 8.x shell completion API
    instruction = f"{target_shell}_source"
    complete_var = "_ALIX_COMPLETE"

    # Get the shell completion script
    from click.shell_completion import get_completion

    # Get the appropriate completion class
    completion_cls = get_completion(target_shell, prog_name, complete_var)
    if not completion_cls:
        console.print(f"[red]Unsupported shell: {target_shell}[/]")
        return

    script = completion_cls.source()

    if install:
        try:
            success, message = integrator.install_completions(script, ShellType(target_shell))
        except ValueError:
            console.print(f"[red]Invalid shell: {target_shell}[/]")
            return
        if success:
            console.print(f"[green]✔[/] {message}")
            console.print("[dim]Restart your terminal or source your shell config to enable completions.[/]")
        else:
            console.print(f"[red]✗[/] {message}")
        return

    click.echo(script)


@main.command()
@click.option("--shell", "-s", help="Target shell (auto-detect if not specified)")
@click.option("--file", "-f", type=click.Path(), help="Custom config file path")
@click.option("--install-completions", is_flag=True, help="Also install shell completions for this shell")
@click.option("--dry-run", is_flag=True, help="Allow users to preview what changes before applying")
def apply(shell, file, install_completions, dry_run):
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

    # Preview what will be changes
    if dry_run:
        old_config, new_config = integrator.preview_aliases(target_file)
        render.side_by_side_diff(old_config, new_config)

    # Confirmation
    if not click.confirm("Apply all aliases to shell config?"):
        return

    console.print(f"[cyan]Applying {len(aliases)} aliases to: {target_file}[/]")

    # Apply aliases
    success, message = integrator.apply_aliases(target_file)

    if success:
        console.print(f"[green]✔[/] {message}")
        console.print("\n[bold]Next steps:[/]")
        console.print(f"  1. Restart your terminal, OR")
        console.print(f"  2. Run: [cyan]source {target_file}[/]")
        console.print(f"\n[dim]Your aliases are now ready to use![/]")
    else:
        console.print(f"[red]✗[/] {message}")
        return

    if install_completions:
        target_shell_str = integrator.shell_type.value if not shell else shell.lower()
        prog_name = "alix"
        complete_var = "_ALIX_COMPLETE"

        # FIXED: Updated to use Click 8.x shell completion API
        from click.shell_completion import get_completion

        completion_cls = get_completion(target_shell_str, prog_name, complete_var)
        if completion_cls:
            script = completion_cls.source()
            ok, msg = integrator.install_completions(script, ShellType(target_shell_str))
            if ok:
                console.print(f"[green]✔[/] {msg}")
            else:
                console.print(f"[yellow]⚠[/] {msg}")
        else:
            console.print(f"[yellow]⚠[/] Could not generate completions for {target_shell_str}")


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
        if analytics["unused_aliases"]:
            console.print(f"\n[yellow]⚠️  Unused Aliases ({len(analytics['unused_aliases'])}):[/]")
            for alias_name in analytics["unused_aliases"][:10]:  # Show first 10
                console.print(f"  • [dim]{alias_name}[/]")
            if len(analytics["unused_aliases"]) > 10:
                console.print(f"  ... and {len(analytics['unused_aliases']) - 10} more")

        # Recently used aliases
        if analytics["recently_used"]:
            console.print(f"\n[green]🔥 Recently Used (7 days):[/]")
            for alias_name in analytics["recently_used"][:10]:  # Show first 10
                alias = storage.get(alias_name)
                if alias:
                    console.print(f"  • [cyan]{alias_name}[/] - {alias.used_count} uses")

        # Most productive aliases
        if analytics["most_productive_aliases"]:
            console.print(f"\n[bold]💪 Most Productive Aliases:[/]")
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Rank", style="dim", width=6)
            table.add_column("Alias", style="cyan")
            table.add_column("Chars Saved", style="green")
            table.add_column("Usage Count", style="yellow")

            for i, (alias_name, chars_saved) in enumerate(analytics["most_productive_aliases"][:10], 1):
                alias = storage.get(alias_name)
                usage_count = alias.used_count if alias else 0
                table.add_row(f"{i}.", alias_name, str(chars_saved), str(usage_count))
            console.print(table)

        # Usage trends (last 7 days)
        if analytics["usage_trends"]:
            console.print(f"\n[bold]📅 Usage Trends (Last 7 Days):[/]")
            recent_days = sorted(analytics["usage_trends"].items(), reverse=True)[:7]
            for date, count in recent_days:
                console.print(f"  {date}: {count} uses")

    # Show top 5 space savers
    console.print(f"\n[bold]🏆 Top Commands by Length Saved:[/]")
    sorted_aliases = sorted(aliases, key=lambda a: len(a.command) - len(a.name), reverse=True)[:5]

    sorted_aliases = sorted(aliases, key=lambda a: len(a.command) - len(a.name), reverse=True)[:5]
    table = Table(show_header=False, box=None, padding=(0, 2))
    for i, alias in enumerate(sorted_aliases, 1):
        saved = len(alias.command) - len(alias.name)
        table.add_row(
            f"{i}.",
            f"[cyan]{alias.name}[/]",
            f"saves {saved} chars",
            (f"[dim]({alias.command[:30]}...)[/]" if len(alias.command) > 30 else f"[dim]({alias.command})[/]"),
        )
    console.print(table)

    # Export analytics if requested
    if export:
        output_path = Path(export)
        storage.usage_tracker.export_analytics(output_path)
        console.print(f"\n[green]✔[/] Analytics exported to: [cyan]{output_path}[/]")


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
    console.print(f"[green]✔[/] Tracked usage of alias '{alias_name}'")

    # Show updated stats
    alias = storage.get(alias_name)  # Get updated alias
    console.print(f"[dim]Total uses: {alias.used_count}[/]")
    if alias.last_used:
        console.print(f"[dim]Last used: {alias.last_used.strftime('%Y-%m-%d %H:%M:%S')}[/]")


@main.command()
@click.option("--id", type=int, help="Undo specific operation by ID (from history list)")
def undo(id):
    """Undo the last alias operation or a specific operation by ID."""
    if id is not None:
        # Selective undo by ID
        msg = storage.history.perform_undo_by_id(storage, id)
        console.print(msg)
    else:
        # Regular undo (last operation)
        msg = storage.history.perform_undo(storage)
        console.print(msg)


@main.command()
@click.option("--id", type=int, help="Redo specific operation by ID (from history list)")
def redo(id):
    """Redo the last undone alias operation or a specific operation by ID."""
    if id is not None:
        # Selective redo by ID
        msg = storage.history.perform_redo_by_id(storage, id)
        console.print(msg)
    else:
        # Regular redo (last undone operation)
        msg = storage.history.perform_redo(storage)
        console.print(msg)


@main.command()
def list_undo():
    """List the undo history."""
    undo_ops = storage.history.list_undo()
    if not undo_ops:
        console.print("[dim]📭 No undo history available.[/]")
        return

    console.print("[bold cyan]📚 Undo History (most recent last):[/]")
    console.print(f"[dim]Use 'alix undo --id <number>' to undo a specific operation[/]")

    for i, op in enumerate(undo_ops, 1):
        op_type = op.get("type", "unknown")
        aliases = [a.get("name", "N/A") for a in op.get("aliases", [])]
        timestamp = op.get("timestamp", "N/A")

        # Format timestamp for better readability
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_time = timestamp

        # Color code by operation type
        if op_type == "add":
            type_color = "green"
            type_icon = "➕"
        elif op_type == "remove":
            type_color = "red"
            type_icon = "➖"
        elif op_type == "edit":
            type_color = "yellow"
            type_icon = "✏️"
        elif op_type == "import":
            type_color = "blue"
            type_icon = "📥"
        elif op_type == "group_add":
            type_color = "cyan"
            type_icon = "📁➕"
        elif op_type == "group_remove":
            type_color = "cyan"
            type_icon = "📁➖"
        elif op_type == "group_delete":
            type_color = "red"
            type_icon = "📁✖️"
        elif op_type == "group_import":
            type_color = "blue"
            type_icon = "📁📥"
        elif op_type == "tag_add":
            type_color = "magenta"
            type_icon = "🏷️➕"
        elif op_type == "tag_remove":
            type_color = "magenta"
            type_icon = "🏷️➖"
        elif op_type == "tag_rename":
            type_color = "yellow"
            type_icon = "🏷️✏️"
        elif op_type == "tag_delete":
            type_color = "red"
            type_icon = "🏷️✖️"
        else:
            type_color = "white"
            type_icon = "🔧"

        aliases_str = ", ".join(aliases[:3])  # Show max 3 aliases
        if len(aliases) > 3:
            aliases_str += f" ... (+{len(aliases) - 3} more)"

        console.print(f"  [bold]{i}.[/] [{type_color}]{type_icon} {op_type.upper()}[/] {aliases_str}")
        console.print(f"      [dim]at {formatted_time}[/]")

    console.print(f"\n[dim]💡 Tip: Use 'alix undo --id 1' for most recent, 'alix undo --id {len(undo_ops)}' for oldest[/]")


@main.command()
def list_redo():
    """List the redo history."""
    redo_ops = storage.history.list_redo()
    if not redo_ops:
        console.print("[dim]📭 No redo history available.[/]")
        return

    console.print("[bold cyan]🔄 Redo History (most recent last):[/]")
    console.print(f"[dim]Use 'alix redo --id <number>' to redo a specific operation[/]")

    for i, op in enumerate(redo_ops, 1):
        op_type = op.get("type", "unknown")
        aliases = [a.get("name", "N/A") for a in op.get("aliases", [])]
        timestamp = op.get("timestamp", "N/A")

        # Format timestamp for better readability
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_time = timestamp

        # Color code by operation type
        if op_type == "add":
            type_color = "green"
            type_icon = "➕"
        elif op_type == "remove":
            type_color = "red"
            type_icon = "➖"
        elif op_type == "edit":
            type_color = "yellow"
            type_icon = "✏️"
        elif op_type == "import":
            type_color = "blue"
            type_icon = "📥"
        elif op_type == "group_add":
            type_color = "cyan"
            type_icon = "📁➕"
        elif op_type == "group_remove":
            type_color = "cyan"
            type_icon = "📁➖"
        elif op_type == "group_delete":
            type_color = "red"
            type_icon = "📁✖️"
        elif op_type == "group_import":
            type_color = "blue"
            type_icon = "📁📥"
        elif op_type == "tag_add":
            type_color = "magenta"
            type_icon = "🏷️➕"
        elif op_type == "tag_remove":
            type_color = "magenta"
            type_icon = "🏷️➖"
        elif op_type == "tag_rename":
            type_color = "yellow"
            type_icon = "🏷️✏️"
        elif op_type == "tag_delete":
            type_color = "red"
            type_icon = "🏷️✖️"
        else:
            type_color = "white"
            type_icon = "🔧"

        aliases_str = ", ".join(aliases[:3])  # Show max 3 aliases
        if len(aliases) > 3:
            aliases_str += f" ... (+{len(aliases) - 3} more)"

        console.print(f"  [bold]{i}.[/] [{type_color}]{type_icon} {op_type.upper()}[/] {aliases_str}")
        console.print(f"      [dim]at {formatted_time}[/]")

    console.print(f"\n[dim]💡 Tip: Use 'alix redo --id 1' for most recent, 'alix redo --id {len(redo_ops)}' for oldest[/]")


@main.command()
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
                date = datetime.fromisoformat(record["date"])
                console.print(f"  {date.strftime('%Y-%m-%d %H:%M')}")
        else:
            console.print("[dim]No usage history found[/]")
    else:
        # Show overall usage trends
        analytics = storage.get_usage_analytics()
        console.print(f"[bold cyan]📊 Overall Usage Trends ({days} days)[/]")

        if analytics["usage_trends"]:
            recent_days = sorted(analytics["usage_trends"].items(), reverse=True)[:days]
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
            console.print(f"[green]✔[/] Standalone tracking script created: [cyan]{output}[/]")
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
            console.print(f"[green]✔[/] Usage tracking installed in: [cyan]{config_file}[/]")
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
    table.add_column("Name", style=theme["header_color"], no_wrap=True)
    table.add_column("Command", style=theme["success_color"])

    if config.get("show_descriptions", True):
        table.add_column("Description", style="dim")
        table.add_column("Tags", style="yellow")
        for alias in sorted(aliases, key=lambda a: a.name):
            tags_str = ", ".join(alias.tags) if alias.tags else "—"
            table.add_row(alias.name, alias.command, alias.description or "", tags_str)
    else:
        table.add_column("Tags", style="yellow")
        for alias in sorted(aliases, key=lambda a: a.name):
            tags_str = ", ".join(alias.tags) if alias.tags else "—"
            table.add_row(alias.name, alias.command, tags_str)

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
            alias.description or "—",
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
                alias.description or "—",
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
    old_group = alias.group
    alias.group = group_name
    storage.aliases[alias_name] = alias
    storage.save()

    # Record history for group_add operation
    from alix.history_manager import HistoryManager
    history_op = {
        "type": "group_add",
        "aliases": [alias.to_dict()],
        "group_name": group_name,
        "old_group": old_group,
        "timestamp": datetime.now().isoformat()
    }
    storage.history.push(history_op)

    console.print(f"[green]✔[/] Added '{alias_name}' to group '{group_name}'")


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
    old_group = alias.group
    alias.group = None
    storage.aliases[alias_name] = alias
    storage.save()

    # Record history for group_remove operation
    history_op = {
        "type": "group_remove",
        "aliases": [alias.to_dict()],
        "group_name": group_name,
        "old_group": old_group,
        "timestamp": datetime.now().isoformat()
    }
    storage.history.push(history_op)

    console.print(f"[green]✔[/] Removed '{alias_name}' from group '{group_name}'")


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

        # Record history for group_delete with reassignment
        history_op = {
            "type": "group_delete",
            "aliases": [alias.to_dict() for alias in group_aliases],
            "group_name": group_name,
            "reassign_to": new_group,
            "timestamp": datetime.now().isoformat()
        }
        storage.history.push(history_op)

        console.print(f"[green]✔[/] Reassigned {len(group_aliases)} aliases to group '{new_group}'")
    else:
        # Remove group from aliases (set to None)
        for alias in group_aliases:
            alias.group = None
            storage.aliases[alias.name] = alias

        storage.save()

        # Record history for group_delete
        history_op = {
            "type": "group_delete",
            "aliases": [alias.to_dict() for alias in group_aliases],
            "group_name": group_name,
            "reassign_to": None,
            "timestamp": datetime.now().isoformat()
        }
        storage.history.push(history_op)

        console.print(f"[green]✔[/] Removed group '{group_name}' from {len(group_aliases)} aliases")


@group.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--group", "-g", help="Import to specific group (overrides file group)")
def import_group(file, group):
    """Import aliases from a group export file"""
    try:
        with open(file, "r") as f:
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
            old_group = alias.group
            alias.group = target_group
            storage.aliases[alias_name] = alias
            imported_count += 1

        storage.save()

        # Record history for group import operation
        imported_aliases = [storage.get(alias_name) for alias_name in [alias_name for alias_name, _ in data["aliases"].items() if alias_name not in storage.aliases or storage.aliases[alias_name].group != target_group]]
        if imported_aliases:
            history_op = {
                "type": "group_import",
                "aliases": [alias.to_dict() for alias in imported_aliases],
                "group_name": target_group,
                "timestamp": datetime.now().isoformat()
            }
            storage.history.push(history_op)

        console.print(f"[green]✔[/] Imported {imported_count} aliases to group '{target_group}'")
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
            console.print(f"[green]✔[/] Applied: {alias.name}")
        else:
            console.print(f"[red]✗[/] Failed: {alias.name} - {message}")

    console.print(f"\n[bold]Summary:[/] {success_count}/{len(group_aliases)} aliases applied successfully")

    if success_count > 0:
        target_file = integrator.get_target_file()
        if target_file:
            console.print(f"\n[dim]💡 Run 'source {target_file}' to activate in current session[/]")


@main.group()
def tag():
    """Manage alias tags"""
    pass


@tag.command()
def list():
    """List all tags and their usage"""
    aliases = storage.list_all()
    tag_counts = {}

    # Count aliases per tag
    for alias in aliases:
        for tag in alias.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if not tag_counts:
        console.print("[yellow]No tags found[/]")
        return

    console.print(f"[bold cyan]📋 Tags ({len(tag_counts)} total)[/]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Tag", style="cyan", width=20)
    table.add_column("Count", style="yellow", width=10)
    table.add_column("Aliases", style="white", width=50)

    for tag, count in sorted(tag_counts.items()):
        # Get aliases with this tag
        tagged_aliases = [a.name for a in aliases if tag in a.tags]
        aliases_str = ", ".join(tagged_aliases[:5])  # Show first 5
        if len(tagged_aliases) > 5:
            aliases_str += f" ... (+{len(tagged_aliases) - 5} more)"

        table.add_row(tag, str(count), aliases_str)

    console.print(table)


@tag.command()
@click.argument("tag_name")
def show(tag_name):
    """Show all aliases with a specific tag"""
    aliases = storage.list_all()
    tagged_aliases = [a for a in aliases if tag_name in a.tags]

    if not tagged_aliases:
        console.print(f"[yellow]No aliases found with tag '{tag_name}'[/]")
        return

    console.print(f"[bold cyan]📋 Aliases with tag '{tag_name}' ({len(tagged_aliases)} total)[/]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", width=20)
    table.add_column("Command", style="white", width=40)
    table.add_column("Description", style="dim", width=30)
    table.add_column("Tags", style="yellow", width=20)

    for alias in sorted(tagged_aliases, key=lambda a: a.name):
        tags_str = ", ".join(alias.tags) if alias.tags else "—"
        table.add_row(
            alias.name,
            alias.command[:40] + "..." if len(alias.command) > 40 else alias.command,
            alias.description or "—",
            tags_str,
        )

    console.print(table)


@tag.command()
@click.argument("alias_name")
@click.argument("tags", nargs=-1, required=True)
def add(alias_name, tags):
    """Add tags to an alias"""
    alias = storage.get(alias_name)
    if not alias:
        console.print(f"[red]✗[/] Alias '{alias_name}' not found!")
        return

    # Add new tags (avoid duplicates)
    original_count = len(alias.tags)
    original_tags = alias.tags.copy()
    added_tags = []
    for tag in tags:
        if tag not in alias.tags:
            alias.tags.append(tag)
            added_tags.append(tag)

    if len(alias.tags) > original_count:
        storage.aliases[alias_name] = alias
        storage.save()

        # Record history for tag_add operation
        history_op = {
            "type": "tag_add",
            "aliases": [alias.to_dict()],
            "added_tags": added_tags,
            "timestamp": datetime.now().isoformat()
        }
        storage.history.push(history_op)

        added_count = len(alias.tags) - original_count
        console.print(f"[green]✓[/] Added {added_count} tag(s) to '{alias_name}'")
        console.print(f"[dim]Current tags: {', '.join(alias.tags)}[/]")
    else:
        console.print(f"[yellow]⚠[/] All specified tags already exist for '{alias_name}'")


@tag.command()
@click.argument("alias_name")
@click.argument("tags", nargs=-1, required=True)
def remove(alias_name, tags):
    """Remove tags from an alias"""
    alias = storage.get(alias_name)
    if not alias:
        console.print(f"[red]✗[/] Alias '{alias_name}' not found!")
        return

    # Remove specified tags
    original_count = len(alias.tags)
    original_tags = alias.tags.copy()
    removed_tags = []
    for tag in tags:
        if tag in alias.tags:
            alias.tags.remove(tag)
            removed_tags.append(tag)

    if len(alias.tags) < original_count:
        storage.aliases[alias_name] = alias
        storage.save()

        # Record history for tag_remove operation
        history_op = {
            "type": "tag_remove",
            "aliases": [alias.to_dict()],
            "removed_tags": removed_tags,
            "timestamp": datetime.now().isoformat()
        }
        storage.history.push(history_op)

        removed_count = original_count - len(alias.tags)
        console.print(f"[green]✓[/] Removed {removed_count} tag(s) from '{alias_name}'")
        if alias.tags:
            console.print(f"[dim]Remaining tags: {', '.join(alias.tags)}[/]")
        else:
            console.print(f"[dim]No tags remaining[/]")
    else:
        console.print(f"[yellow]⚠[/] None of the specified tags exist for '{alias_name}'")


@tag.command()
@click.argument("old_tag")
@click.argument("new_tag")
@click.option("--dry-run", is_flag=True, help="Show what would be changed without making changes")
def rename(old_tag, new_tag, dry_run):
    """Rename a tag across all aliases"""
    aliases = storage.list_all()
    affected_aliases = [a for a in aliases if old_tag in a.tags]

    if not affected_aliases:
        console.print(f"[yellow]No aliases found with tag '{old_tag}'[/]")
        return

    console.print(f"[cyan]Found {len(affected_aliases)} aliases with tag '{old_tag}'[/]")

    if dry_run:
        console.print(f"[bold]Would rename tag '{old_tag}' to '{new_tag}' in:[/]")
        for alias in affected_aliases:
            console.print(f"  • {alias.name}")
        return

    # Confirm the change
    if not click.confirm(f"Rename tag '{old_tag}' to '{new_tag}' in {len(affected_aliases)} aliases?"):
        return

    # Perform the rename
    updated_count = 0
    updated_aliases = []
    for alias in affected_aliases:
        if old_tag in alias.tags:
            # Replace old tag with new tag
            alias.tags = [new_tag if tag == old_tag else tag for tag in alias.tags]
            storage.aliases[alias.name] = alias
            updated_aliases.append(alias.to_dict())
            updated_count += 1

    storage.save()

    # Record history for tag_rename operation
    if updated_aliases:
        history_op = {
            "type": "tag_rename",
            "aliases": updated_aliases,
            "old_tag": old_tag,
            "new_tag": new_tag,
            "timestamp": datetime.now().isoformat()
        }
        storage.history.push(history_op)

    console.print(f"[green]✓[/] Renamed tag in {updated_count} aliases")


@tag.command()
@click.argument("tag_name")
@click.option("--dry-run", is_flag=True, help="Show what would be changed without making changes")
def delete(tag_name, dry_run):
    """Delete a tag from all aliases"""
    aliases = storage.list_all()
    affected_aliases = [a for a in aliases if tag_name in a.tags]

    if not affected_aliases:
        console.print(f"[yellow]No aliases found with tag '{tag_name}'[/]")
        return

    console.print(f"[cyan]Found {len(affected_aliases)} aliases with tag '{tag_name}'[/]")

    if dry_run:
        console.print(f"[bold]Would remove tag '{tag_name}' from:[/]")
        for alias in affected_aliases:
            console.print(f"  • {alias.name}")
        return

    # Confirm the deletion
    if not click.confirm(f"Remove tag '{tag_name}' from {len(affected_aliases)} aliases?"):
        return

    # Remove the tag
    updated_count = 0
    updated_aliases = []
    for alias in affected_aliases:
        if tag_name in alias.tags:
            alias.tags.remove(tag_name)
            storage.aliases[alias.name] = alias
            updated_aliases.append(alias.to_dict())
            updated_count += 1

    storage.save()

    # Record history for tag_delete operation
    if updated_aliases:
        history_op = {
            "type": "tag_delete",
            "aliases": updated_aliases,
            "deleted_tag": tag_name,
            "timestamp": datetime.now().isoformat()
        }
        storage.history.push(history_op)

    console.print(f"[green]✓[/] Removed tag from {updated_count} aliases")


@tag.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--tag", "-t", help="Import only aliases with specific tag")
def import_tag(file, tag):
    """Import aliases from a file, optionally filtered by tag"""
    try:
        with open(file, "r") as f:
            data = json.load(f)

        if "aliases" not in data:
            console.print(f"[red]✗[/] Invalid export file")
            return

        imported = 0
        skipped = 0
        tag_filtered = 0

        for alias_data in data["aliases"]:
            alias = Alias.from_dict(alias_data)

            # Apply tag filter if specified
            if tag and tag not in alias.tags:
                tag_filtered += 1
                continue

            if alias.name not in storage.aliases:
                storage.aliases[alias.name] = alias
                imported += 1
            else:
                skipped += 1

        storage.save()

        console.print(f"[green]✓[/] Imported {imported} aliases")
        if skipped > 0:
            console.print(f"[yellow]⚠[/] Skipped {skipped} existing aliases")
        if tag_filtered > 0:
            console.print(f"[dim]Filtered out {tag_filtered} aliases (didn't match tag '{tag}')[/]")

    except Exception as e:
        console.print(f"[red]✗[/] Failed to import: {e}")


@tag.command()
@click.argument("tag_name")
@click.option("--file", "-f", type=click.Path(), help="Output file path")
@click.option("--format", type=click.Choice(["json", "yaml"]), default="json", help="Export format")
def export(tag_name, file, format):
    """Export all aliases with a specific tag"""
    aliases = storage.list_all()
    tagged_aliases = [a for a in aliases if tag_name in a.tags]

    if not tagged_aliases:
        console.print(f"[yellow]No aliases found with tag '{tag_name}'[/]")
        return

    # Generate filename if not provided
    if not file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file = f"alix_tag_{tag_name}_{timestamp}.{format}"

    filepath = Path(file)

    # Export data
    export_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "tag": tag_name,
        "count": len(tagged_aliases),
        "aliases": [alias.to_dict() for alias in tagged_aliases],
    }

    try:
        if format == "yaml":
            import yaml

            with open(filepath, "w") as f:
                yaml.dump(export_data, f, default_flow_style=False, sort_keys=False)
        else:  # json
            with open(filepath, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

        console.print(f"[green]✓[/] Exported {len(tagged_aliases)} aliases with tag '{tag_name}' to {filepath.name}")

    except Exception as e:
        console.print(f"[red]✗[/] Export failed: {e}")


@tag.command()
@click.argument("tags", nargs=-1, required=True)
@click.option("--file", "-f", type=click.Path(), help="Output file path")
@click.option("--format", type=click.Choice(["json", "yaml"]), default="json", help="Export format")
@click.option("--match-all", is_flag=True, help="Match aliases that have ALL tags (default: match ANY)")
def export_multi(tags, file, format, match_all):
    """Export aliases matching multiple tags"""
    if not file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        match_type = "all" if match_all else "any"
        file = f"alix_tags_{match_type}_{timestamp}.{format}"

    filepath = Path(file)

    porter = AliasPorter()
    success, message = porter.export_by_tags(tags, filepath, format, match_all)

    if success:
        console.print(f"[green]✓[/] {message}")
    else:
        console.print(f"[red]✗[/] {message}")


@tag.command()
def stats():
    """Show comprehensive tag statistics"""
    porter = AliasPorter()
    stats = porter.get_tag_statistics()

    console.print(f"[bold cyan]📊 Tag Statistics[/]")
    console.print(f"Total tags: {stats['total_tags']}")
    console.print(f"Total aliases: {stats['total_aliases']}")
    console.print(f"Tagged aliases: {stats['tagged_aliases']}")
    console.print(f"Untagged aliases: {stats['untagged_aliases']}")

    if stats["tag_counts"]:
        console.print(f"\n[bold]Most Used Tags:[/]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Tag", style="cyan", width=20)
        table.add_column("Count", style="yellow", width=10)
        table.add_column("Percentage", style="green", width=12)

        for tag, count in list(stats["tag_counts"].items())[:10]:
            percentage = (count / stats["total_aliases"]) * 100
            table.add_row(tag, str(count), f"{percentage:.1f}%")

        console.print(table)

    if stats["tag_combinations"]:
        console.print(f"\n[bold]Most Common Tag Combinations:[/]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Tags", style="cyan", width=30)
        table.add_column("Count", style="yellow", width=10)

        for combo, count in list(stats["tag_combinations"].items())[:10]:
            tags_str = " + ".join(combo)
            table.add_row(tags_str, str(count))

        console.print(table)


@main.group()
def templates():
    """Manage alias templates

    Browse and import pre-defined alias collections for common development tools.

    Examples:
      alix templates list                    # Show available templates
      alix templates add git                 # Import all git aliases
      alix templates add docker --dry-run    # Preview docker aliases
      alix templates add git --aliases gs,ga # Import specific git aliases
      alix templates add-category k8s       # Import all k8s templates
    """
    pass


@templates.command()
def list():
    """List available templates"""
    template_manager = TemplateManager()

    # Show categories first
    categories = template_manager.get_categories()
    if categories:
        console.print(f"[bold cyan]📋 Available Categories:[/]")
        for category in categories:
            templates = template_manager.list_templates(category)
            console.print(f"  [bold]{category}[/] ({len(templates)} templates)")
        console.print()

    # Show all templates
    all_templates = template_manager.list_templates()
    if not all_templates:
        console.print("[yellow]No templates found.[/]")
        return

    console.print(f"[bold cyan]📋 Available Templates ({len(all_templates)} total):[/]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", width=15)
    table.add_column("Category", style="yellow", width=12)
    table.add_column("Description", style="white", width=40)
    table.add_column("Aliases", style="green", width=8)

    for template in all_templates:
        table.add_row(
            template.name,
            template.category,
            template.description[:40] + "..." if len(template.description) > 40 else template.description,
            str(len(template.aliases)),
        )

    console.print(table)
    console.print(f"\n[dim]💡 Use 'alix templates add <template>' to import a template[/]")


@templates.command(name="add")
@click.argument("template_name")
@click.option("--aliases", "-a", help="Comma-separated list of specific aliases to import")
@click.option("--dry-run", is_flag=True, help="Show what would be imported without importing")
def add_template(template_name, aliases, dry_run):
    """Import aliases from a template"""
    template_manager = TemplateManager()

    template = template_manager.get_template(template_name)
    if not template:
        console.print(f"[red]✗[/] Template '{template_name}' not found!")
        return

    # Parse alias filter if provided
    alias_names = None
    if aliases:
        alias_names = [name.strip() for name in aliases.split(",") if name.strip()]

    if dry_run:
        console.print(f"[bold cyan]📋 Preview: Would import from '{template_name}'[/]")
        console.print(f"[dim]Category: {template.category}[/]")
        console.print(f"[dim]Description: {template.description}[/]")
        console.print(f"[dim]Total aliases: {len(template.aliases)}[/]")

        if alias_names:
            filtered_aliases = [a for a in template.aliases if a.name in alias_names]
            console.print(f"\n[bold]Filtered aliases ({len(filtered_aliases)}):[/]")
        else:
            filtered_aliases = template.aliases
            console.print(f"\n[bold]All aliases ({len(filtered_aliases)}):[/]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", width=15)
        table.add_column("Command", style="white", width=40)
        table.add_column("Description", style="dim", width=30)
        table.add_column("Tags", style="yellow", width=15)

        for alias in filtered_aliases:
            tags_str = ", ".join(alias.tags) if alias.tags else "—"
            table.add_row(
                alias.name,
                alias.command[:40] + "..." if len(alias.command) > 40 else alias.command,
                alias.description or "—",
                tags_str,
            )

        console.print(table)
        return

    # Import the template
    success, message = template_manager.import_template(template_name, alias_names)

    if success:
        console.print(f"[green]✔[/] {message}")
        console.print(f"\n[dim]💡 Run 'alix apply' to add these to your shell config[/]")
    else:
        console.print(f"[red]✗[/] {message}")


@templates.command(name="add-category")
@click.argument("category")
@click.option("--aliases", "-a", help="Comma-separated list of specific aliases to import")
@click.option("--dry-run", is_flag=True, help="Show what would be imported without importing")
def add_category(category, aliases, dry_run):
    """Import all aliases from a category"""
    template_manager = TemplateManager()

    categories = template_manager.get_categories()
    if category not in categories:
        console.print(f"[red]✗[/] Category '{category}' not found!")
        console.print(f"[dim]Available categories: {', '.join(categories)}[/]")
        return

    # Parse alias filter if provided
    alias_names = None
    if aliases:
        alias_names = [name.strip() for name in aliases.split(",") if name.strip()]

    if dry_run:
        templates = template_manager.list_templates(category)
        total_aliases = sum(len(t.aliases) for t in templates)

        console.print(f"[bold cyan]📋 Preview: Would import from category '{category}'[/]")
        console.print(f"[dim]Templates: {len(templates)}[/]")
        console.print(f"[dim]Total aliases: {total_aliases}[/]")

        if alias_names:
            console.print(f"[dim]Filtered aliases: {len(alias_names)}[/]")

        console.print(f"\n[bold]Templates in category:[/]")
        for template in templates:
            console.print(f"  • [cyan]{template.name}[/] - {template.description} ({len(template.aliases)} aliases)")
        return

    # Import from category
    success, message = template_manager.import_by_category(category, alias_names)

    if success:
        console.print(f"[green]✔[/] {message}")
        console.print(f"\n[dim]💡 Run 'alix apply' to add these to your shell config[/]")
    else:
        console.print(f"[red]✗[/] {message}")


if __name__ == "__main__":
    main()
