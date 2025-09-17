from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, DataTable, Input, Button, Label
from textual.binding import Binding

from alix.storage import AliasStorage


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
    
    #search.active {
        border: solid magenta;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("a", "focus_add", "Add", priority=True),
        Binding("s", "focus_search", "Search", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "clear_search", "Clear"),
        Binding("enter", "copy_selected", "Copy"),
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
                Input(placeholder="Search aliases... (press 's')", id="search"),
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

    def refresh_table(self, search: str = "") -> None:
        """Refresh the alias table with optional search filter"""
        table = self.query_one("#alias-table", DataTable)
        table.clear()

        aliases = sorted(self.storage.list_all(), key=lambda a: a.name)

        # Filter aliases based on search term
        if search:
            search_lower = search.lower()
            aliases = [
                a for a in aliases
                if search_lower in a.name.lower()
                or search_lower in a.command.lower()
                or (a.description and search_lower in a.description.lower())
                or any(search_lower in tag.lower() for tag in a.tags)
            ]

        # Update subtitle with count
        self.sub_title = f"{len(aliases)} aliases" + (f" (filtered)" if search else "")

        # Add rows to table
        for alias in aliases:
            tags = ", ".join(alias.tags) if alias.tags else "-"
            table.add_row(alias.name, alias.command, tags, key=alias.name)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "search":
            self.search_term = event.value
            self.refresh_table(self.search_term)
            if event.value:
                event.input.add_class("active")
            else:
                event.input.remove_class("active")

    def on_data_table_row_highlighted(self, event) -> None:
        """Handle row selection"""
        if event.row_key:
            self.selected_alias = self.storage.get(str(event.row_key.value))
            if self.selected_alias:
                details = self.query_one("#details", Label)
                desc = self.selected_alias.description or "No description"
                details.update(f"[cyan]{self.selected_alias.name}[/]: {desc}")

    def action_focus_search(self) -> None:
        """Focus search input"""
        self.query_one("#search", Input).focus()

    def action_clear_search(self) -> None:
        """Clear search and refresh"""
        search_input = self.query_one("#search", Input)
        search_input.value = ""
        self.refresh_table()
        search_input.remove_class("active")

    def action_copy_selected(self) -> None:
        """Show selected command"""
        if self.selected_alias:
            details = self.query_one("#details", Label)
            details.update(f"[green]Ready:[/] {self.selected_alias.command}")

    def action_focus_add(self) -> None:
        """Focus add input (placeholder)"""
        self.query_one("#search", Input).focus()