import subprocess
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Center, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Input,
    Button,
    Label,
    Static,
    Checkbox,
)
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from datetime import datetime
from rapidfuzz import fuzz, process

from alix import __version__
from alix.storage import AliasStorage
from alix.models import Alias
from alix.config import Config
from alix.shell_integrator import ShellIntegrator  # NEW IMPORT
from alix.clipboard import ClipboardManager
from alix.parameters import ParameterParser


class AddAliasModal(ModalScreen[bool]):
    """Clean modal for adding aliases"""

    CSS = """
    AddAliasModal {
        align: center middle;
        background: $background 80%;
    }

    #modal-container {
        width: 60;
        height: 30;
        background: #1a1a1a;
        border: solid #0088cc;
    }

    #modal-header {
        background: #0088cc;
        padding: 1;
        text-align: center;
        text-style: bold;
        color: white;
        height: 3;
    }

    #modal-body {
        padding: 2 3;
        background: #1a1a1a;
        height: 21;
    }

    .field-label {
        color: #0088cc;
        margin-bottom: 0;
    }

    Input {
        width: 100%;
        background: #2a2a2a;
        border: solid #0088cc;
        color: white;
        margin-bottom: 1;
    }

    Input#description {
        height: 7;
        content-align: left top;
    }

    Input:focus {
        background: #333333;
    }

    #button-row {
        padding: 1 3;
        align: center middle;
        background: #1a1a1a;
        height: 6;
    }

    Button {
        width: 14;
        margin: 0 1;
        border: none;
    }

    #cancel {
        background: #4a4a4a;
        color: white;
    }

    #create {
        background: #0088cc;
        color: white;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="modal-container"):
            yield Static("ADD NEW ALIAS", id="modal-header")

            with VerticalScroll(id="modal-body"):
                yield Label("Name", classes="field-label")
                yield Input(placeholder="Enter alias name", id="name")

                yield Label("Command", classes="field-label")
                yield Input(placeholder="Enter full command", id="command")

                yield Label("Description", classes="field-label")
                yield Input(placeholder="Optional description", id="description")

                yield Checkbox("Force Override", id="force")

            with Horizontal(id="button-row"):
                yield Button("Cancel", id="cancel")
                yield Button("Create", id="create")

    # MODIFIED METHOD: Added auto-apply functionality and parameter validation
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            name = self.query_one("#name", Input).value.strip()
            command = self.query_one("#command", Input).value.strip()
            desc = self.query_one("#description", Input).value.strip()
            force = self.query_one("#force", Checkbox).value

            if name and command:
                # Validate parameters
                is_valid, error_msg = ParameterParser.validate_parameters(command)
                if not is_valid:
                    self.app.notify(
                        f"Parameter validation error: {error_msg}",
                        severity="error",
                    )
                    return
                
                storage = AliasStorage()
                command_exists = False
                msg = None
                cmd = storage.get(name)
                if cmd is not None:
                    command_exists = True
                    msg = f"Alias '{name}' exists in alix\nEdit the alias to override"
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
                        msg = (
                            "Alias/Command/Function already exists\nEnable Force Override if you want to override this alias\n"
                            + cmd.stdout
                        )
                if command_exists and not force:
                    self.app.notify(
                        msg,
                        severity="error",
                    )
                else:
                    # Auto-detect parameter descriptions
                    parameters = ParameterParser.auto_detect_parameter_descriptions(command)
                    
                    alias = Alias(name=name, command=command, description=desc or None, parameters=parameters)
                    if storage.add(alias):
                        # Auto-apply the alias
                        integrator = ShellIntegrator()
                        success, message = integrator.apply_single_alias(alias)

                        # Show parameter info in notification
                        notify_msg = f"Created and applied '{name}'"
                        if ParameterParser.has_parameters(command):
                            param_count = len(ParameterParser.extract_parameters(command))
                            notify_msg += f" ({param_count} params)"
                        
                        if success:
                            self.app.notify(notify_msg, severity="information")
                        else:
                            self.app.notify(
                                f"Created '{name}' (apply manually)", severity="warning"
                            )

                        self.dismiss(True)
                    else:
                        self.app.notify(
                            f"Alias '{name}' exists in alix\nEdit the alias to override",
                            severity="error",
                        )
        else:
            self.dismiss(False)


class EditAliasModal(ModalScreen[bool]):
    """Clean modal for editing aliases"""

    CSS = """
    EditAliasModal {
        align: center middle;
        background: $background 80%;
    }

    #modal-container {
        width: 60;
        height: 30;
        background: #1a1a1a;
        border: solid #ff9800;
    }

    #modal-header {
        background: #ff9800;
        padding: 1;
        text-align: center;
        text-style: bold;
        color: white;
        height: 3;
    }

    #modal-body {
        padding: 2 3;
        background: #1a1a1a;
        height: 21;
    }

    .field-label {
        color: #ff9800;
        margin-bottom: 0;
    }

    Input {
        width: 100%;
        background: #2a2a2a;
        border: solid #ff9800;
        color: white;
        margin-bottom: 1;
    }

    Input#description {
        height: 6;
        content-align: left top;
    }

    Input:focus {
        background: #333333;
    }

    #button-row {
        padding: 1 3;
        align: center middle;
        background: #1a1a1a;
        height: 6;
    }

    Button {
        width: 14;
        margin: 0 1;
        border: none;
    }

    #cancel {
        background: #4a4a4a;
        color: white;
    }

    #update {
        background: #ff9800;
        color: white;
        text-style: bold;
    }
    """

    def __init__(self, alias: Alias):
        super().__init__()
        self.alias = alias

    def compose(self) -> ComposeResult:
        with Container(id="modal-container"):
            yield Static("EDIT ALIAS", id="modal-header")

            with Container(id="modal-body"):
                yield Label("Name", classes="field-label")
                yield Input(value=self.alias.name, id="name")

                yield Label("Command", classes="field-label")
                yield Input(value=self.alias.command, id="command")

                yield Label("Description", classes="field-label")
                yield Input(
                    value=self.alias.description or "",
                    placeholder="Optional description",
                    id="description",
                )

            with Horizontal(id="button-row"):
                yield Button("Cancel", id="cancel")
                yield Button("Update", id="update")

    # MODIFIED METHOD: Added auto-apply for edits
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "update":
            name = self.query_one("#name", Input).value.strip()
            command = self.query_one("#command", Input).value.strip()
            desc = self.query_one("#description", Input).value.strip()

            if name and command:
                storage = AliasStorage()
                if name != self.alias.name:
                    storage.remove(self.alias.name)

                updated = Alias(
                    name=name,
                    command=command,
                    description=desc or None,
                    created_at=self.alias.created_at,
                    used_count=self.alias.used_count,
                )
                storage.aliases[name] = updated
                storage.save()

                # Auto-apply the updated alias
                integrator = ShellIntegrator()
                integrator.apply_single_alias(updated)

                self.dismiss(True)
        else:
            self.dismiss(False)


class DeleteConfirmModal(ModalScreen[bool]):
    """Confirmation modal for deletion"""

    CSS = """
    DeleteConfirmModal {
        align: center middle;
        background: $background 80%;
    }

    #modal-container {
        width: 50;
        background: #1a1a1a;
        border: solid #ff4444;
    }

    #modal-header {
        background: #ff4444;
        padding: 1;
        text-align: center;
        text-style: bold;
        color: white;
    }

    #modal-body {
        padding: 3;
        text-align: center;
        background: #1a1a1a;
    }

    .delete-text {
        color: white;
        margin-bottom: 1;
    }

    .warning-text {
        color: #ff4444;
        text-style: italic;
    }

    #button-row {
        padding: 2 3;
        align: center middle;
        background: #1a1a1a;
    }

    Button {
        width: 14;
        margin: 0 1;
        border: none;
    }

    #cancel {
        background: #4a4a4a;
        color: white;
    }

    #delete {
        background: #ff4444;
        color: white;
        text-style: bold;
    }
    """

    def __init__(self, alias_name: str):
        super().__init__()
        self.alias_name = alias_name

    def compose(self) -> ComposeResult:
        with Container(id="modal-container"):
            yield Static("DELETE CONFIRMATION", id="modal-header")

            with Container(id="modal-body"):
                yield Static(
                    f"Delete alias '{self.alias_name}'?", classes="delete-text"
                )
                yield Static("This action cannot be undone", classes="warning-text")

            with Horizontal(id="button-row"):
                yield Button("Cancel", id="cancel")
                yield Button("Delete", id="delete")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "delete")


class HelpModal(ModalScreen):
    """A modal screen to display help information."""

    CSS = """
    HelpModal {
        align: center middle;
        background: $background 80%;
    }

    #help-container {
        width: 70;
        height: 25;
        background: $surface;
        border: thick $primary-lighten-2;
    }

    #help-header {
        background: $primary;
        padding: 1;
        text-align: center;
        text-style: bold;
        color: $text;
    }

    #help-body {
        padding: 1 2;
    }

    .help-category {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
    }

    .help-item {
        margin-left: 2;
    }
    """

    BINDINGS = [Binding("escape", "close_help", "Close", show=True)]

    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            yield Static("KEYBOARD SHORTCUTS", id="help-header")
            with VerticalScroll(id="help-body"):
                yield Static("NAVIGATION", classes="help-category")
                yield Static("j / ↓ - Move cursor down", classes="help-item")
                yield Static("k / ↑ - Move cursor up", classes="help-item")
                yield Static("/ - Focus search bar", classes="help-item")
                yield Static("esc - Clear search / Close modal", classes="help-item")

                yield Static("ALIAS ACTIONS", classes="help-category")
                yield Static("a - Add new alias", classes="help-item")
                yield Static("e - Edit selected alias", classes="help-item")
                yield Static("d - Delete selected alias", classes="help-item")
                yield Static("c - Copy alias command", classes="help-item")
                yield Static(
                    "p - Apply all aliases to shell config", classes="help-item"
                )

                yield Static("APPLICATION", classes="help-category")
                yield Static("r - Refresh alias list from disk", classes="help-item")
                yield Static("? - Show this help overlay", classes="help-item")
                yield Static("q - Quit the application", classes="help-item")

    def action_close_help(self) -> None:
        """Close the help modal."""
        self.dismiss()


class AliasManager(App):
    """Clean and modern alias manager"""

    CSS = """
    Screen {
        background: $surface-darken-2;
    }

    #header-container {
        height: 5;
        background: $surface;
        border: solid $primary-lighten-3;
        margin: 1;
        padding: 1;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
    }

    #search-row {
        align: center middle;
        height: 3;
    }

    #search {
        width: 50%;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
        margin: 0 1;
    }

    #table-wrapper {
        width: 3fr;
        padding: 1;
        background: $surface;
        border: solid $primary-lighten-3;
        margin-right: 1;
    }

    DataTable {
        height: 100%;
    }

    DataTable > .datatable--header {
        background: $primary 10%;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $secondary 70%;
    }

    DataTable > .datatable--hover {
        background: $primary 10%;
    }

    #sidebar {
        width: 20;
        layout: vertical;
    }

    #action-buttons {
        height: auto;
        padding: 1;
        background: $surface;
        border: solid $primary-lighten-3;
        margin-bottom: 1;
    }

    #action-buttons Button {
        width: 100%;
        margin-bottom: 1;
    }

    #action-buttons Button:last-child {
        margin-bottom: 0;
    }

    #info-panel {
        height: 1fr;
        padding: 1;
        background: $surface;
        border: solid $primary-lighten-3;
    }

    #info-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #info-content {
        color: $text-muted;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $surface-darken-3;
        color: $text-muted;
        padding: 0 2;
    }

    .highlight {
        color: $secondary;
    }
    """

    # MODIFIED: Added 'p' binding for apply all and 'f' for fuzzy search
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True, priority=True),
        Binding(
            "c", "copy_alias", "Copy", show=True
        ),  # copy the alias command to clipboard
        Binding("a", "add_alias", "Add", show=True),
        Binding("e", "edit_alias", "Edit", show=True),
        Binding("d", "delete_alias", "Delete", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("p", "apply_all", "Apply All", show=True),  # NEW BINDING
        Binding("f", "toggle_fuzzy", "Fuzzy", show=True),  # NEW FUZZY SEARCH BINDING
        Binding("/", "focus_search", "Search", show=True),
        Binding("escape", "clear_search", "Clear", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("?", "show_help", "Help", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.storage = AliasStorage()
        self.config = Config()
        self.selected_alias = None
        self.fuzzy_search_enabled = False  # NEW: Fuzzy search toggle

    def compose(self) -> ComposeResult:
        # Header
        with Container(id="header-container"):
            yield Static(f"ALIX v{__version__} - Alias Manager", id="title")
            with Horizontal(id="search-row"):
                yield Input(placeholder="Search aliases...", id="search")

        # Main content area
        with Container(id="main-container"):
            # Table
            with Container(id="table-wrapper"):
                yield DataTable(id="table", cursor_type="row", zebra_stripes=True)

            # Sidebar
            with Container(id="sidebar"):
                # Action buttons - MODIFIED to include Apply All button
                with Container(id="action-buttons"):
                    yield Button("Add New", variant="success", id="btn-add")
                    yield Button("Edit", variant="warning", id="btn-edit")
                    yield Button("Delete", variant="error", id="btn-delete")
                    yield Button(
                        "Apply All", variant="primary", id="btn-apply"
                    )  # NEW BUTTON
                    yield Button("Refresh", variant="default", id="btn-refresh")

                # Info panel
                with Container(id="info-panel"):
                    yield Static("DETAILS", id="info-title")
                    yield Static("Select an alias", id="info-content")

        # Status bar
        yield Static("Ready", id="status-bar")

        # Footer with keybindings
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.add_column("Name", width=15)
        table.add_column("Command", width=40)
        table.add_column("Description", width=30)
        table.add_column("Group", width=15)

        self.refresh_table()
        self.update_status()

    def refresh_table(self, search_term: str = "") -> None:
        table = self.query_one("#table", DataTable)
        table.clear()

        aliases = sorted(self.storage.list_all(), key=lambda a: a.name)

        current_filter = getattr(self, '_current_group_filter', None)
        if current_filter and current_filter not in ["All Groups"]:
            if current_filter == "Ungrouped":
                aliases = [a for a in aliases if not a.group]
            else:
                aliases = [a for a in aliases if a.group == current_filter]


        if search_term:
            if self.fuzzy_search_enabled:
                # Fuzzy search with scoring
                results = []
                for alias in aliases:
                    # Search across name, command, and description
                    name_score = fuzz.partial_ratio(
                        search_term.lower(), alias.name.lower()
                    )
                    cmd_score = fuzz.partial_ratio(
                        search_term.lower(), alias.command.lower()
                    )
                    desc_score = (
                        fuzz.partial_ratio(
                            search_term.lower(), alias.description.lower()
                        )
                        if alias.description
                        else 0
                    )

                    # Use the highest score
                    max_score = max(name_score, cmd_score, desc_score)

                    # Only include if score is above threshold (60%)
                    if max_score >= 60:
                        results.append((alias, max_score))

                # Sort by score (highest first)
                results.sort(key=lambda x: x[1], reverse=True)
                aliases = [alias for alias, score in results]
            else:
                # Original exact substring search
                search_lower = search_term.lower()
                aliases = [
                    a
                    for a in aliases
                    if search_lower in a.name.lower()
                    or search_lower in a.command.lower()
                    or (a.description and search_lower in a.description.lower())
                ]

        for alias in aliases:
            # Add parameter badge if alias has parameters
            name_display = f"[bold cyan]{alias.name}[/]"
            if ParameterParser.has_parameters(alias.command):
                param_count = ParameterParser.extract_parameters(alias.command)
                name_display = f"[bold cyan]{alias.name}[/] [yellow]({len(param_count)} params)[/]"
            
            table.add_row(
                name_display,
                alias.command,
                alias.description or "[dim]—[/]",
                key=alias.name,
            )

        self.update_status(len(aliases))

    def update_status(self, shown: int = None) -> None:
        status = self.query_one("#status-bar", Static)
        total = len(self.storage.list_all())

        # Add fuzzy search indicator
        fuzzy_status = (
            "[green]Fuzzy ON[/]" if self.fuzzy_search_enabled else "[dim]Fuzzy OFF[/]"
        )

        if shown is not None:
            status.update(
                f"Showing {shown} of {total} aliases | {fuzzy_status} | Press 'p' to apply all"
            )
        else:
            status.update(
                f"Total: {total} aliases | {fuzzy_status} | Press 'p' to apply all"
            )

    def update_info_panel(self, alias: Alias) -> None:
        info = self.query_one("#info-content", Static)
        # Escape any markup characters in the alias data
        from rich.text import Text

        name = Text(alias.name or "")
        command = Text(alias.command or "")
        description = Text(alias.description or "None")

        # Build the info text
        parts = [
            ("Name: ", "bold"),
            name,
            "\n",
            ("Command: ", "bold"),
            command,
            "\n",
            ("Description: ", "bold"),
            description,
            "\n",
        ]
        
        # Add parameter information if present
        if ParameterParser.has_parameters(alias.command):
            params = ParameterParser.extract_parameters(alias.command)
            parts.extend([
                ("Parameters: ", "bold green"),
                f"{len(params)} ",
                ("(", "dim"),
            ])
            
            # Show parameter hints
            param_hints = []
            for param in params:
                if param in alias.parameters:
                    param_hints.append(f"{param}={alias.parameters[param]}")
                else:
                    param_hints.append(param)
            parts.append((", ".join(param_hints), "cyan"))
            parts.append((")", "dim"))
            parts.append("\n")
            
            # Show usage example
            usage = alias.get_usage_example()
            parts.extend([
                ("Usage: ", "bold"),
                (usage, "yellow"),
                "\n",
            ])
        
        parts.extend([
            ("Used: ", "bold"),
            f"{alias.used_count} times\n",
            ("Created: ", "bold"),
            f"{alias.created_at.strftime('%Y-%m-%d')}",
        ])

        info.update(Text.assemble(*parts))

    def on_data_table_row_highlighted(self, event) -> None:
        if event.row_key:
            self.selected_alias = self.storage.get(str(event.row_key.value))
            if self.selected_alias:
                self.update_info_panel(self.selected_alias)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self.refresh_table(event.value)

    def action_add_alias(self) -> None:
        def callback(success: bool):
            if success:
                self.refresh_table()
                self.notify("Alias added and applied successfully")

        self.push_screen(AddAliasModal(), callback)

    def action_copy_alias(self) -> None:
        clipboard = ClipboardManager()
        if self.selected_alias is None:
            return

        alias_cmd = self.selected_alias.command

        try:
            clipboard.copy(alias_cmd)
            self.notify("Alias command copied to clipboard")
        except:
            self.notify(f"Unable to copy. Command: {alias_cmd}")

    def action_edit_alias(self) -> None:
        if self.selected_alias:

            def callback(success: bool):
                if success:
                    self.refresh_table()
                    self.notify("Alias updated and applied successfully")

            self.push_screen(EditAliasModal(self.selected_alias), callback)
        else:
            self.notify("Please select an alias to edit", severity="warning")

    def action_delete_alias(self) -> None:
        if self.selected_alias:

            def callback(confirmed: bool):
                if confirmed:
                    if self.storage.remove(self.selected_alias.name):
                        self.refresh_table()
                        self.notify(f"Deleted '{self.selected_alias.name}'")
                        self.selected_alias = None
                        self.query_one("#info-content", Static).update(
                            "Select an alias"
                        )
                        # Reapply all to remove deleted alias from shell
                        integrator = ShellIntegrator()
                        integrator.apply_aliases()

            self.push_screen(DeleteConfirmModal(self.selected_alias.name), callback)
        else:
            self.notify("Please select an alias to delete", severity="warning")

    def action_refresh(self) -> None:
        self.storage.load()
        self.refresh_table()
        self.notify("Refreshed from disk")

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_clear_search(self) -> None:
        search = self.query_one("#search", Input)
        search.value = ""
        self.refresh_table()

    def action_cursor_down(self) -> None:
        table = self.query_one("#table", DataTable)
        table.action_cursor_down()

    def action_cursor_up(self) -> None:
        table = self.query_one("#table", DataTable)
        table.action_cursor_up()

    def action_show_help(self) -> None:
        """Show the help modal."""
        self.push_screen(HelpModal())

    # NEW METHOD: Toggle fuzzy search
    def action_toggle_fuzzy(self) -> None:
        """Toggle fuzzy search on/off"""
        self.fuzzy_search_enabled = not self.fuzzy_search_enabled
        mode = "enabled" if self.fuzzy_search_enabled else "disabled"
        self.notify(f"Fuzzy search {mode}", severity="information")

        # Re-run search with current search term
        search = self.query_one("#search", Input)
        self.refresh_table(search.value)
        self.update_status()

    # NEW METHOD: Apply all aliases to shell
    def action_apply_all(self) -> None:
        """Apply all aliases to shell configuration"""
        integrator = ShellIntegrator()
        target_file = integrator.get_target_file()

        if not target_file:
            self.notify("No shell config file found", severity="error")
            return

        success, message = integrator.apply_aliases(target_file)

        if success:
            self.notify(
                f"Applied all aliases to {target_file.name}", severity="success"
            )
            self.update_status()
        else:
            self.notify(f"Failed: {message}", severity="error")

    # MODIFIED: Added btn-apply case
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-add":
            self.action_add_alias()
        elif event.button.id == "btn-edit":
            self.action_edit_alias()
        elif event.button.id == "btn-delete":
            self.action_delete_alias()
        elif event.button.id == "btn-apply":  # NEW CASE
            self.action_apply_all()
        elif event.button.id == "btn-refresh":
            self.action_refresh()
    
    def action_filter_by_group(self) -> None:
        """Filter aliases by group"""
        aliases = self.storage.list_all()
        groups = set()
        
        # Collect all unique groups
        for alias in aliases:
            if alias.group:
                groups.add(alias.group)
        
        if not groups:
            self.notify("No groups found. Create some aliases with groups first.", severity="warning")
            return
        
        # Create a simple group selection dialog
        groups_list = sorted(list(groups))
        groups_list.insert(0, "All Groups")  # Add option to show all
        groups_list.append("Ungrouped")      # Add option to show ungrouped
        
        # For now, we'll use a simple approach - cycle through groups
        # In a more advanced implementation, you could create a proper selection modal
        current_filter = getattr(self, '_current_group_filter', None)
        
        if current_filter is None:
            # Start with first group
            selected_group = groups_list[0]
        else:
            # Find current group and move to next
            try:
                current_index = groups_list.index(current_filter)
                next_index = (current_index + 1) % len(groups_list)
                selected_group = groups_list[next_index]
            except ValueError:
                selected_group = groups_list[0]
        
        self._current_group_filter = selected_group
        
        # Apply the filter
        if selected_group == "All Groups":
            self.notify("Showing all aliases", severity="information")
        elif selected_group == "Ungrouped":
            self.notify("Showing ungrouped aliases", severity="information")
        else:
            self.notify(f"Showing aliases in group: {selected_group}", severity="information")
        
        # Refresh the table with the current filter
        self.refresh_table()

    def update_status(self, shown: int = None) -> None:
        status = self.query_one("#status-bar", Static)
        total = len(self.storage.list_all())

        current_filter = getattr(self, '_current_group_filter', None)
        filter_text = ""
        if current_filter and current_filter != "All Groups":
            filter_text = f" | Filter: {current_filter}"

        if shown is not None:
            status.update(f"Showing {shown} of {total} aliases{filter_text} | Press 'g' to filter by group")
        else:
            status.update(f"Total: {total} aliases{filter_text} | Press 'g' to filter by group")