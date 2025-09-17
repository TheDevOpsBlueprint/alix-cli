from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, DataTable, Input, Button, Label, Static, Pretty
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from rich.text import Text
from rich.panel import Panel
from datetime import datetime

from alix import __version__
from alix.storage import AliasStorage
from alix.models import Alias
from alix.config import Config


class AddAliasModal(ModalScreen[bool]):
    """Add alias modal - ALL fields visible"""

    DEFAULT_CSS = """
    AddAliasModal {
        align: center middle;
    }

    #add-modal {
        width: 55;
        height: 24;
        background: $panel;
        border: thick $primary;
        padding: 0;
    }

    #add-title {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 1;
    }

    #add-buttons {
        dock: bottom;
        height: 5;
        align: center middle;
        border-top: solid $primary;
        background: $panel;
        padding: 1;
    }

    #add-content {
        padding: 1 2;
        height: 100%;
    }

    #add-content Input {
        margin-bottom: 0;
        height: 3;
    }

    #add-content .field-label {
        margin: 0;
        color: $text-muted;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="add-modal"):
            yield Static("ADD NEW ALIAS", id="add-title")
            with Container(id="add-content"):
                yield Static("Alias Name:", classes="field-label")
                yield Input(placeholder="e.g., ll", id="name")
                yield Static("Command:", classes="field-label")
                yield Input(placeholder="e.g., ls -la", id="command")
                yield Static("Description (optional):", classes="field-label")
                yield Input(placeholder="What does this alias do?", id="description")
            with Horizontal(id="add-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            name = self.query_one("#name", Input).value.strip()
            command = self.query_one("#command", Input).value.strip()
            desc = self.query_one("#description", Input).value.strip()

            if name and command:
                storage = AliasStorage()
                alias = Alias(name=name, command=command, description=desc or None)
                if storage.add(alias):
                    self.dismiss(True)
                else:
                    self.query_one("#name", Input).placeholder = f"'{name}' already exists!"
                    self.query_one("#name", Input).value = ""
        else:
            self.dismiss(False)


class EditAliasModal(ModalScreen[bool]):
    """Edit alias modal - ALL fields visible"""

    DEFAULT_CSS = """
    EditAliasModal {
        align: center middle;
    }

    #edit-modal {
        width: 55;
        height: 24;
        background: $panel;
        border: thick $primary;
        padding: 0;
    }

    #edit-title {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 1;
    }

    #edit-buttons {
        dock: bottom;
        height: 5;
        align: center middle;
        border-top: solid $primary;
        background: $panel;
        padding: 1;
    }

    #edit-content {
        padding: 1 2;
        height: 100%;
    }

    #edit-content Input {
        margin-bottom: 0;
        height: 3;
    }

    #edit-content .field-label {
        margin: 0;
        color: $text-muted;
        height: 1;
    }
    """

    def __init__(self, alias: Alias):
        super().__init__()
        self.alias = alias

    def compose(self) -> ComposeResult:
        with Container(id="edit-modal"):
            yield Static("EDIT ALIAS", id="edit-title")
            with Container(id="edit-content"):
                yield Static("Alias Name:", classes="field-label")
                yield Input(value=self.alias.name, id="name")
                yield Static("Command:", classes="field-label")
                yield Input(value=self.alias.command, id="command")
                yield Static("Description:", classes="field-label")
                yield Input(
                    value=self.alias.description or "",
                    placeholder="Add a description",
                    id="description"
                )
            with Horizontal(id="edit-buttons"):
                yield Button("Update", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            name = self.query_one("#name", Input).value.strip()
            command = self.query_one("#command", Input).value.strip()
            desc = self.query_one("#description", Input).value.strip()

            if name and command:
                storage = AliasStorage()
                # Remove old if name changed
                if name != self.alias.name:
                    storage.remove(self.alias.name)

                updated = Alias(
                    name=name,
                    command=command,
                    description=desc or None,
                    created_at=self.alias.created_at,
                    used_count=self.alias.used_count
                )
                storage.aliases[name] = updated
                storage.save()
                self.dismiss(True)
        else:
            self.dismiss(False)


class ConfirmDeleteModal(ModalScreen[bool]):
    """Delete confirmation modal - compact size"""

    DEFAULT_CSS = """
    ConfirmDeleteModal {
        align: center middle;
    }

    #delete-modal {
        width: 45;
        height: 12;
        background: $panel;
        border: thick $error;
        padding: 0;
    }

    #delete-title {
        dock: top;
        height: 3;
        background: $error;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 1;
    }

    #delete-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
        border-top: solid $error;
        background: $panel;
    }

    #delete-content {
        padding: 1;
        align: center middle;
        height: 100%;
    }

    .delete-text {
        text-align: center;
        margin: 0;
    }

    .delete-warning {
        color: $warning;
        text-style: bold;
    }
    """

    def __init__(self, alias_name: str):
        super().__init__()
        self.alias_name = alias_name

    def compose(self) -> ComposeResult:
        with Container(id="delete-modal"):
            yield Static("DELETE CONFIRMATION", id="delete-title")
            with Container(id="delete-content"):
                yield Static(f"Delete '{self.alias_name}'?", classes="delete-text delete-warning")
                yield Static("This cannot be undone.", classes="delete-text")
            with Horizontal(id="delete-buttons"):
                yield Button("Delete", variant="error", id="delete")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "delete")


class HelpModal(ModalScreen):
    """Help modal - compact size"""

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
    }

    #help-modal {
        width: 55;
        height: 20;
        background: $panel;
        border: thick $primary;
        padding: 0;
    }

    #help-title {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 1;
    }

    #help-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
        border-top: solid $primary;
        background: $panel;
    }

    #help-content {
        padding: 1 2;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        help_text = """[yellow]NAVIGATION[/]: ↑/↓/j/k (move), Enter (details), Tab (focus)
[yellow]ACTIONS[/]: a (add), e (edit), d (delete), s or / (search)
           r (refresh), t (theme)
[yellow]GENERAL[/]: ? (help), Esc (clear/close), q (quit)"""

        with Container(id="help-modal"):
            yield Static("KEYBOARD SHORTCUTS", id="help-title")
            with Container(id="help-content"):
                yield Static(help_text)
            with Horizontal(id="help-buttons"):
                yield Button("Close", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()


class AliasManager(App):
    """Modern alias manager TUI"""

    CSS = """
    Screen {
        background: $surface-darken-2;
    }

    #container {
        height: 100%;
    }

    /* Header area */
    #header-area {
        height: 8;
        background: $surface-darken-1;
        border: solid $primary-lighten-2;
        padding: 1;
        margin: 0 1 1 1;
    }

    #title-label {
        text-align: center;
        text-style: bold;
        color: $text;
        width: 100%;
    }

    #search-row {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    #search-label {
        margin-right: 1;
        width: 8;
    }

    #search {
        width: 50%;
    }

    #button-group {
        dock: right;
    }

    #button-group Button {
        margin-left: 1;
    }

    /* Main content */
    #main-content {
        height: 1fr;
        margin: 0 1;
    }

    #table-container {
        height: 100%;
        border: solid $primary-lighten-3;
        background: $surface;
    }

    DataTable {
        height: 100%;
    }

    DataTable > .datatable--header {
        background: $primary 30%;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $secondary 50%;
    }

    DataTable > .datatable--hover {
        background: $primary 20%;
    }

    /* Details panel */
    #details-panel {
        height: 11;
        background: $surface-darken-1;
        border: solid $primary-lighten-3;
        padding: 1;
        margin: 1 1 0 1;
    }

    #details-title {
        text-style: bold;
        color: $secondary;
        border-bottom: solid $primary-lighten-3;
        padding-bottom: 1;
        margin-bottom: 1;
    }

    #details-content {
        color: $text;
    }

    /* Status bar */
    #status-bar {
        height: 1;
        background: $surface-darken-3;
        dock: bottom;
        padding: 0 2;
        color: $text-muted;
    }

    /* Modal styling - FIXED HEIGHTS FOR PROPER DISPLAY */
    ModalScreen {
        align: center middle;
    }

    .modal-container {
        width: 65;
        height: 26;  /* Fixed height to ensure buttons visible */
        background: $surface;
        border: thick $primary;
    }

    .modal-inner {
        height: 100%;
        layout: vertical;
    }

    .modal-title {
        text-align: center;
        text-style: bold;
        background: $primary;
        color: $text;
        padding: 1;
        width: 100%;
        height: 3;
    }

    .modal-content {
        height: 1fr;  /* Takes remaining space */
        padding: 2;
    }

    .delete-modal {
        height: 18;  /* Smaller for delete confirmation */
        border: thick $error;
    }

    .delete-content {
        height: 8;
    }

    .delete-title {
        background: $error;
    }

    .help-modal {
        height: 28;
    }

    .help-content {
        padding: 2;
    }

    .label {
        color: $text-muted;
        margin-bottom: 0;
    }

    .input-field {
        margin-bottom: 1;
    }

    .button-row {
        height: 5;  /* Fixed height for buttons */
        align: center middle;
        padding: 1;
        border-top: solid $primary-lighten-3;
    }

    .button-row Button {
        margin: 0 1;
        min-width: 14;
        height: 3;
    }

    .center {
        text-align: center;
    }

    .bold {
        text-style: bold;
        color: $warning;
    }

    .warning {
        color: $error;
        text-style: italic;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "add_alias", "Add", show=True),
        Binding("e", "edit_alias", "Edit", show=True),
        Binding("d", "delete_alias", "Delete", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("t", "theme", "Theme", show=True),
        Binding("?", "help", "Help", show=True),
        Binding("s,slash", "focus_search", "Search", show=False),
        Binding("escape", "clear", "Clear", show=False),
        Binding("j", "move_down", description="", show=False),
        Binding("k", "move_up", description="", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.storage = AliasStorage()
        self.config = Config()
        self.selected_alias = None
        self.dark = True

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="container"):
            # Header area with search
            with Container(id="header-area"):
                yield Static(f"ALIX v{__version__} - Interactive Alias Manager", id="title-label")
                with Horizontal(id="search-row"):
                    yield Label("Search:", id="search-label")
                    yield Input(placeholder="Type to filter aliases...", id="search")
                    with Horizontal(id="button-group"):
                        yield Button("Add", variant="success", id="btn-add")
                        yield Button("Edit", variant="warning", id="btn-edit")
                        yield Button("Delete", variant="error", id="btn-delete")

            # Main table
            with Container(id="main-content"):
                with Container(id="table-container"):
                    yield DataTable(id="alias-table", cursor_type="row")

            # Details panel
            with Container(id="details-panel"):
                yield Static("ALIAS DETAILS", id="details-title")
                yield Static("Select an alias to view details", id="details-content")

            # Status bar
            yield Static("Ready", id="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app"""
        table = self.query_one("#alias-table", DataTable)
        table.add_column("Alias", width=20)
        table.add_column("Command", width=40)
        table.add_column("Description", width=30)

        self.refresh_table()
        self.update_status()

    def refresh_table(self, search_term: str = "") -> None:
        """Refresh the alias table"""
        table = self.query_one("#alias-table", DataTable)
        table.clear()

        aliases = sorted(self.storage.list_all(), key=lambda a: a.name)

        # Filter if search term
        if search_term:
            search_lower = search_term.lower()
            aliases = [
                a for a in aliases
                if search_lower in a.name.lower()
                   or search_lower in a.command.lower()
                   or (a.description and search_lower in a.description.lower())
            ]

        # Add rows
        for alias in aliases:
            desc = alias.description if alias.description else "-"
            table.add_row(
                alias.name,
                alias.command,
                desc,
                key=alias.name
            )

        self.update_status(len(aliases))

    def update_status(self, shown: int = None) -> None:
        """Update status bar"""
        status = self.query_one("#status-bar", Static)
        total = len(self.storage.list_all())
        theme = self.config.get("theme", "default")

        if shown is not None:
            status.update(f"Showing {shown}/{total} aliases | Theme: {theme}")
        else:
            status.update(f"Total: {total} aliases | Theme: {theme}")

    def on_data_table_row_highlighted(self, event) -> None:
        """Handle row selection"""
        if event.row_key:
            self.selected_alias = self.storage.get(str(event.row_key.value))
            if self.selected_alias:
                details = self.query_one("#details-content", Static)

                text = f"""[b]Name:[/] {self.selected_alias.name}
[b]Command:[/] {self.selected_alias.command}
[b]Description:[/] {self.selected_alias.description or '[dim]Not set[/dim]'}
[b]Used:[/] {self.selected_alias.used_count} times
[b]Created:[/] {self.selected_alias.created_at.strftime('%Y-%m-%d %H:%M')}"""

                details.update(text)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input"""
        if event.input.id == "search":
            self.refresh_table(event.value)

    def action_add_alias(self) -> None:
        """Add new alias"""

        def callback(success: bool) -> None:
            if success:
                self.refresh_table()
                self.notify("Alias added successfully!")

        self.push_screen(AddAliasModal(), callback)

    def action_edit_alias(self) -> None:
        """Edit selected alias"""
        if self.selected_alias:
            def callback(success: bool) -> None:
                if success:
                    self.refresh_table()
                    self.notify("Alias updated successfully!")

            self.push_screen(EditAliasModal(self.selected_alias), callback)
        else:
            self.notify("Please select an alias to edit", severity="warning")

    def action_delete_alias(self) -> None:
        """Delete selected alias"""
        if self.selected_alias:
            def callback(confirmed: bool) -> None:
                if confirmed:
                    if self.storage.remove(self.selected_alias.name):
                        self.refresh_table()
                        self.notify(f"Deleted '{self.selected_alias.name}'")
                        self.selected_alias = None
                        # Reset details
                        details = self.query_one("#details-content", Static)
                        details.update("Select an alias to view details")

            self.push_screen(ConfirmDeleteModal(self.selected_alias.name), callback)
        else:
            self.notify("Please select an alias to delete", severity="warning")

    def action_refresh(self) -> None:
        """Refresh from disk"""
        self.storage.load()
        search_val = self.query_one("#search", Input).value
        self.refresh_table(search_val)
        self.notify("Refreshed from disk")

    def action_theme(self) -> None:
        """Cycle themes"""
        themes = list(Config.THEMES.keys())
        current = self.config.get("theme", "default")
        next_idx = (themes.index(current) + 1) % len(themes)
        next_theme = themes[next_idx]

        self.config.set("theme", next_theme)
        self.notify(f"Theme changed to: {next_theme}")
        self.update_status()

    def action_help(self) -> None:
        """Show help"""
        self.push_screen(HelpModal())

    def action_focus_search(self) -> None:
        """Focus search input"""
        self.query_one("#search", Input).focus()

    def action_clear(self) -> None:
        """Clear search"""
        search = self.query_one("#search", Input)
        if search.value:
            search.value = ""

    def action_move_down(self) -> None:
        """Move cursor down"""
        table = self.query_one("#alias-table", DataTable)
        table.action_cursor_down()

    def action_move_up(self) -> None:
        """Move cursor up"""
        table = self.query_one("#alias-table", DataTable)
        table.action_cursor_up()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "btn-add":
            self.action_add_alias()
        elif event.button.id == "btn-edit":
            self.action_edit_alias()
        elif event.button.id == "btn-delete":
            self.action_delete_alias()