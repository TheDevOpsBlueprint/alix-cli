"""Interactive TUI for alix using Textual"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, Input, Button
from textual.binding import Binding

from alix.storage import AliasStorage
from alix.models import Alias


class AliasManager(App):
    """Interactive alias manager TUI"""

    CSS = """
    DataTable {
        height: 1fr;
        border: solid cyan;
    }

    #input-container {
        height: 3;
        dock: bottom;
        border: solid green;
        margin: 1 0;
    }

    Input {
        width: 1fr;
    }

    Button {
        width: 10;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("a", "focus_add", "Add", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
    ]

    def __init__(self):
        super().__init__()
        self.storage = AliasStorage()
        self.title = "alix - Alias Manager"
        self.sub_title = f"{len(self.storage.list_all())} aliases"

    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header()
        yield Container(
            DataTable(id="alias-table"),
            Horizontal(
                Input(placeholder="Search aliases...", id="search"),
                Button("Add", id="add-btn", variant="primary"),
                id="input-container"
            ),
            id="main"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize when app starts"""
        table = self.query_one("#alias-table", DataTable)
        table.add_columns("Name", "Command", "Description")
        self.refresh_table()

    def refresh_table(self) -> None:
        """Refresh the alias table"""
        table = self.query_one("#alias-table", DataTable)
        table.clear()
        aliases = sorted(self.storage.list_all(), key=lambda a: a.name)
        for alias in aliases:
            table.add_row(alias.name, alias.command, alias.description or "")

    def action_focus_add(self) -> None:
        """Focus the search/add input"""
        self.query_one("#search", Input).focus()