"""Interactive TUI for alix using Textual"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, Input, Button, Label
from textual.binding import Binding
from textual.events import Key

from alix.storage import AliasStorage
from alix.models import Alias


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
        Binding("enter", "copy_selected", "Copy"),
        Binding("?", "help", "Help"),
    ]

    def __init__(self):
        super().__init__()
        self.storage = AliasStorage()
        self.title = "alix - Alias Manager"
        self.selected_alias = None

    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header()
        yield Container(
            DataTable(id="alias-table", cursor_type="row"),
            Label("[dim]Select an alias to see details[/]", id="details"),
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
        table.add_columns("Name", "Command", "Tags")
        self.refresh_table()
        self.sub_title = f"{len(self.storage.list_all())} aliases"

    def refresh_table(self) -> None:
        """Refresh the alias table"""
        table = self.query_one("#alias-table", DataTable)
        table.clear()
        aliases = sorted(self.storage.list_all(), key=lambda a: a.name)
        for alias in aliases:
            tags = ", ".join(alias.tags) if alias.tags else "-"
            table.add_row(alias.name, alias.command, tags, key=alias.name)

    def on_data_table_row_highlighted(self, event) -> None:
        """Handle row selection"""
        if event.row_key:
            self.selected_alias = self.storage.get(str(event.row_key.value))
            if self.selected_alias:
                details = self.query_one("#details", Label)
                desc = self.selected_alias.description or "No description"
                count = self.selected_alias.used_count
                details.update(f"[cyan]{self.selected_alias.name}[/]: {desc} [dim](used {count} times)[/]")

    def action_copy_selected(self) -> None:
        """Copy selected alias command to clipboard (placeholder)"""
        if self.selected_alias:
            details = self.query_one("#details", Label)
            details.update(f"[green]Ready to use:[/] {self.selected_alias.command}")

    def action_focus_add(self) -> None:
        """Focus the search/add input"""
        self.query_one("#search", Input).focus()