from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, Input, Button, Label, Static
from textual.binding import Binding
from textual.screen import Screen, ModalScreen

from alix import __version__
from alix.storage import AliasStorage
from alix.models import Alias
from alix.config import Config


class HelpScreen(ModalScreen):
    """Help screen showing keyboard shortcuts"""

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        width: 60;
        height: 20;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create help content"""
        help_text = """
[bold cyan]⌨️  Keyboard Shortcuts[/]

[yellow]Navigation:[/]
  ↑/↓     Navigate aliases
  Enter   Copy selected command
  Tab     Move between elements

[yellow]Actions:[/]
  a       Add new alias
  d       Delete selected alias
  s       Focus search box
  t       Cycle themes
  r       Refresh list

[yellow]General:[/]
  ?       Show this help
  ESC     Clear search / Close dialogs
  q       Quit application

[dim]Press ESC to close this help[/]
"""
        with Container(id="help-dialog"):
            yield Static(help_text)

    def on_key(self, event) -> None:
        """Close on any key press"""
        if event.key == "escape":
            self.dismiss()


class AliasManager(App):
    """Interactive alias manager TUI"""

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.theme_colors = self.config.get_theme()
        self.storage = AliasStorage()
        self.title = f"alix v{__version__}"
        self.selected_alias = None
        self.search_term = ""

    def get_css(self) -> str:
        """Dynamic CSS based on theme"""
        return f"""
        DataTable {{
            height: 1fr;
            border: solid {self.theme_colors['border_color']};
        }}

        #status-bar {{
            height: 3;
            border: solid {self.theme_colors['selected_color']};
            padding: 0 1;
        }}

        #footer-bar {{
            height: 3;
            dock: bottom;
            border: solid {self.theme_colors['success_color']};
            margin: 1 0;
            padding: 0 1;
        }}

        #search.active {{
            border: solid {self.theme_colors['search_color']};
        }}
        """

    CSS = property(get_css)

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "add_alias", "Add"),
        Binding("s", "focus_search", "Search"),
        Binding("d", "delete", "Delete"),
        Binding("t", "theme", "Theme"),
        Binding("?", "help", "Help"),
        Binding("escape", "clear", "Clear"),
    ]

    def compose(self) -> ComposeResult:
        """Create UI layout"""
        aliases_count = len(self.storage.list_all())
        yield Header()
        yield Container(
            DataTable(id="alias-table", cursor_type="row"),
            Label(
                f"[dim]{aliases_count} aliases | Theme: {self.config.get('theme')} | Press ? for help[/]",
                id="status-bar"
            ),
            Horizontal(
                Input(placeholder="🔍 Search aliases...", id="search"),
                Button("➕ Add", variant="primary"),
                Button("🗑️ Delete", variant="error"),
                id="footer-bar"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize when app starts"""
        table = self.query_one("#alias-table", DataTable)
        table.add_columns("Name", "Command", "Description")
        self.refresh_table()

        # Update subtitle with stats
        total = len(self.storage.list_all())
        self.sub_title = f"{total} aliases | v{__version__}"

    def refresh_table(self, search: str = "") -> None:
        """Refresh the alias table"""
        table = self.query_one("#alias-table", DataTable)
        table.clear()

        aliases = sorted(self.storage.list_all(), key=lambda a: a.name)

        if search:
            search_lower = search.lower()
            aliases = [a for a in aliases if search_lower in a.name.lower()
                       or search_lower in a.command.lower()]

        # Update status bar
        status = self.query_one("#status-bar", Label)
        if search:
            status.update(
                f"[yellow]Found {len(aliases)} matches[/] | Theme: {self.config.get('theme')} | Press ? for help")
        else:
            status.update(f"[dim]{len(aliases)} aliases | Theme: {self.config.get('theme')} | Press ? for help[/]")

        for alias in aliases:
            desc = alias.description[:30] + "..." if alias.description and len(alias.description) > 30 else (
                        alias.description or "")
            table.add_row(alias.name, alias.command, desc, key=alias.name)

    def action_help(self) -> None:
        """Show help screen"""
        self.push_screen(HelpScreen())

    def action_theme(self) -> None:
        """Cycle through themes"""
        themes = list(Config.THEMES.keys())
        current = self.config.get("theme", "default")
        next_idx = (themes.index(current) + 1) % len(themes)
        next_theme = themes[next_idx]

        self.config.set("theme", next_theme)
        self.theme_colors = self.config.get_theme()

        # Show theme change notification
        status = self.query_one("#status-bar", Label)
        status.update(f"[{self.theme_colors['success_color']}]✨ Theme changed to: {next_theme}[/]")
        self.refresh_table(self.search_term)

    def on_data_table_row_highlighted(self, event) -> None:
        """Handle row selection"""
        if event.row_key:
            self.selected_alias = self.storage.get(str(event.row_key.value))
            if self.selected_alias:
                # Update used count
                self.selected_alias.used_count += 1
                self.storage.save()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "search":
            self.search_term = event.value
            self.refresh_table(self.search_term)
            event.input.add_class("active") if event.value else event.input.remove_class("active")

    def action_focus_search(self) -> None:
        """Focus search input"""
        self.query_one("#search", Input).focus()

    def action_clear(self) -> None:
        """Clear search or close dialogs"""
        search = self.query_one("#search", Input)
        if search.value:
            search.value = ""
        self.refresh_table()