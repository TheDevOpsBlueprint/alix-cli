from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, DataTable, Input, Button, Label
from textual.binding import Binding
from textual.screen import ModalScreen

from alix.storage import AliasStorage
from alix.models import Alias
from alix.config import Config


class AddAliasScreen(ModalScreen):
    """Modal screen for adding a new alias"""

    def __init__(self, theme_colors):
        super().__init__()
        self.theme_colors = theme_colors

    CSS = """
    AddAliasScreen {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: 11;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create add alias form"""
        with Container(id="dialog"):
            yield Label(f"[bold {self.theme_colors['header_color']}]Add New Alias[/]")
            yield Input(placeholder="Alias name (e.g., ll)", id="name")
            yield Input(placeholder="Command (e.g., ls -la)", id="command")
            yield Input(placeholder="Description (optional)", id="description")
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        if event.button.id == "save":
            name = self.query_one("#name", Input).value
            command = self.query_one("#command", Input).value
            if name and command:
                storage = AliasStorage()
                alias = Alias(name=name, command=command,
                              description=self.query_one("#description", Input).value or None)
                if storage.add(alias):
                    self.dismiss(True)
        else:
            self.dismiss(False)


class AliasManager(App):
    """Interactive alias manager TUI"""

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.theme_colors = self.config.get_theme()  # Changed from self.theme
        self.storage = AliasStorage()
        self.title = "alix - Alias Manager"
        self.selected_alias = None
        self.search_term = ""

    def get_css(self) -> str:
        """Dynamic CSS based on theme"""
        return f"""
        DataTable {{
            height: 1fr;
            border: solid {self.theme_colors['border_color']};
        }}

        #details {{
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
        Binding("d", "delete_alias", "Delete"),
        Binding("t", "cycle_theme", "Theme"),
        Binding("escape", "clear_search", "Clear"),
    ]

    def compose(self) -> ComposeResult:
        """Create UI layout"""
        theme_name = self.config.get("theme", "default")
        yield Header()
        yield Container(
            DataTable(id="alias-table", cursor_type="row"),
            Label(f"[dim]Theme: {theme_name} | Press 't' to change[/]", id="details"),
            Horizontal(
                Input(placeholder="Search (press 's')...", id="search"),
                Button("Add (a)", id="add-btn", variant="primary"),
                Button("Delete (d)", id="del-btn", variant="error"),
                id="footer-bar"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize when app starts"""
        table = self.query_one("#alias-table", DataTable)
        table.add_columns("Name", "Command", "Description")
        self.refresh_table()

    def refresh_table(self, search: str = "") -> None:
        """Refresh the alias table with optional search filter"""
        table = self.query_one("#alias-table", DataTable)
        table.clear()

        aliases = sorted(self.storage.list_all(), key=lambda a: a.name)

        if search:
            search_lower = search.lower()
            aliases = [a for a in aliases if search_lower in a.name.lower()
                       or search_lower in a.command.lower()]

        self.sub_title = f"{len(aliases)} aliases | Theme: {self.config.get('theme')}"

        for alias in aliases:
            desc = alias.description[:30] + "..." if alias.description and len(alias.description) > 30 else (
                        alias.description or "-")
            table.add_row(alias.name, alias.command, desc, key=alias.name)

    def action_add_alias(self) -> None:
        """Show add alias dialog"""

        def check_result(result: bool) -> None:
            if result:
                self.refresh_table(self.search_term)

        self.push_screen(AddAliasScreen(self.theme_colors), check_result)

    def action_delete_alias(self) -> None:
        """Delete selected alias"""
        if self.selected_alias and self.storage.remove(self.selected_alias.name):
            self.refresh_table(self.search_term)

    def action_cycle_theme(self) -> None:
        """Cycle through available themes"""
        themes = list(Config.THEMES.keys())
        current = self.config.get("theme", "default")
        next_idx = (themes.index(current) + 1) % len(themes)
        next_theme = themes[next_idx]

        self.config.set("theme", next_theme)
        self.theme_colors = self.config.get_theme()  # Changed from self.theme

        details = self.query_one("#details", Label)
        details.update(f"[{self.theme_colors['success_color']}]Theme changed to: {next_theme}[/]")
        self.refresh_table(self.search_term)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "search":
            self.search_term = event.value
            self.refresh_table(self.search_term)

    def on_data_table_row_highlighted(self, event) -> None:
        """Handle row selection"""
        if event.row_key:
            self.selected_alias = self.storage.get(str(event.row_key.value))

    def action_focus_search(self) -> None:
        """Focus search input"""
        self.query_one("#search", Input).focus()

    def action_clear_search(self) -> None:
        """Clear search"""
        self.query_one("#search", Input).value = ""