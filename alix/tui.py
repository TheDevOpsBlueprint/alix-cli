from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Grid
from textual.widgets import Header, Footer, DataTable, Input, Button, Label
from textual.binding import Binding
from textual.screen import ModalScreen

from alix.storage import AliasStorage
from alix.models import Alias


class AddAliasScreen(ModalScreen):
    """Modal screen for adding a new alias"""

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

    #dialog Input {
        margin: 1 0;
    }

    #dialog Button {
        margin: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create add alias form"""
        with Container(id="dialog"):
            yield Label("[bold cyan]Add New Alias[/]")
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
                    self.query_one("#name", Input).placeholder = f"'{name}' already exists!"
        else:
            self.dismiss(False)


class AliasManager(App):
    """Interactive alias manager TUI"""

    CSS = """
    DataTable {
        height: 1fr;
        border: solid cyan;
    }

    #details {
        height: 3;
        border: solid yellow;
        padding: 0 1;
    }

    #footer-bar {
        height: 3;
        dock: bottom;
        border: solid green;
        margin: 1 0;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "add_alias", "Add"),
        Binding("s", "focus_search", "Search"),
        Binding("d", "delete_alias", "Delete"),
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "clear_search", "Clear"),
    ]

    def __init__(self):
        super().__init__()
        self.storage = AliasStorage()
        self.title = "alix - Alias Manager"
        self.selected_alias = None
        self.search_term = ""

    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header()
        yield Container(
            DataTable(id="alias-table", cursor_type="row"),
            Label("[dim]Select an alias to see details[/]", id="details"),
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

        self.sub_title = f"{len(aliases)} aliases" + (f" (filtered)" if search else "")

        for alias in aliases:
            table.add_row(alias.name, alias.command, alias.description or "-", key=alias.name)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "search":
            self.search_term = event.value
            self.refresh_table(self.search_term)

    def on_data_table_row_highlighted(self, event) -> None:
        """Handle row selection"""
        if event.row_key:
            self.selected_alias = self.storage.get(str(event.row_key.value))
            if self.selected_alias:
                details = self.query_one("#details", Label)
                details.update(f"[cyan]{self.selected_alias.name}[/]: {self.selected_alias.command}")

    def action_add_alias(self) -> None:
        """Show add alias dialog"""

        def check_result(result: bool) -> None:
            if result:
                self.refresh_table(self.search_term)

        self.push_screen(AddAliasScreen(), check_result)

    def action_delete_alias(self) -> None:
        """Delete selected alias"""
        if self.selected_alias:
            if self.storage.remove(self.selected_alias.name):
                self.refresh_table(self.search_term)
                details = self.query_one("#details", Label)
                details.update(f"[red]Deleted:[/] {self.selected_alias.name}")
                self.selected_alias = None

    def action_focus_search(self) -> None:
        """Focus search input"""
        self.query_one("#search", Input).focus()

    def action_clear_search(self) -> None:
        """Clear search"""
        self.query_one("#search", Input).value = ""