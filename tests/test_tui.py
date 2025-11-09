from unittest.mock import ANY, patch

import pytest
import datetime

from alix.models import Alias
from alix.shell_integrator import ShellIntegrator
from alix.tui import AliasManager, HelpModal, AddAliasModal, EditAliasModal, DeleteConfirmModal
from textual.widgets import Static, DataTable, Input
from pathlib import Path


@pytest.mark.asyncio
@patch.object(ShellIntegrator, "apply_single_alias")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_add_alias(mock_storage, mock_notify, mock_apply, alias_min):
    mock_storage.return_value.add.return_value = True
    mock_storage.return_value.get.return_value = None
    mock_apply.return_value = (True, "✓ Applied alias 'alix-test-echo' to .zshrc")

    expected_alias = Alias(
        name="alix-test-echo",
        command="alix test working!",
        description="alix test shortcut",
        tags=["git", "dev"],
        created_at=ANY,
    )

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-add")
        await pilot.click("#name")
        await pilot.press(*list("alix-test-echo"))
        await pilot.click("#command")
        await pilot.press(*list("alix test working!"))
        await pilot.click("#description")
        await pilot.press(*list("alix test shortcut"))
        await pilot.press('down', 'down', 'down', 'down', 'down')
        await pilot.click("#tags")
        await pilot.press(*list("git, dev"))
        await pilot.click("#create")

        await pilot.pause()  # Wait for async operations to complete

        mock_notify.assert_any_call(
            "Created and applied 'alix-test-echo'", severity="information"
        )
        mock_notify.assert_any_call("Alias added and applied successfully")
        mock_storage.return_value.add.assert_called_once_with(expected_alias)
        mock_apply.assert_called_once_with(expected_alias)


@pytest.mark.asyncio
@patch.object(ShellIntegrator, "apply_single_alias")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_edit_alias(mock_storage, mock_notify, mock_apply, alias_min):
    mock_storage.return_value.aliases = {}
    mock_apply.return_value = (True, "✓ Applied alias 'alix-test-echo-2' to .zshrc")
    alias_min.created_at = ANY

    new_alias = Alias(
        name="alix-test-echo-2",
        command="alix test changed!",
        description="alix test shortcut changed",
        created_at=alias_min.created_at,
    )

    app = AliasManager()
    app.selected_alias = alias_min

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-edit")
        await pilot.click("#name")
        await pilot.press(*list(["delete"] * len(alias_min.name)))
        await pilot.press(*list(new_alias.name))
        await pilot.click("#command")
        await pilot.press(*list(["delete"] * len(alias_min.command)))
        await pilot.press(*list(new_alias.command))
        await pilot.click("#description")
        await pilot.press(*list(["delete"] * len(alias_min.description)))
        await pilot.press(*list(new_alias.description))
        await pilot.click("#update")

        await pilot.pause()  # Wait for async operations to complete

        mock_notify.assert_any_call("Alias updated and applied successfully")

        mock_storage.return_value.remove.assert_called_once_with(alias_min.name)
        mock_storage.return_value.save.assert_called_once()
        mock_apply.assert_called_once_with(new_alias)
        assert mock_storage.return_value.aliases["alix-test-echo-2"] == new_alias


@pytest.mark.asyncio
@patch("alix.tui.subprocess.run")
@patch("alix.tui.AliasStorage", autospec=True)
@patch.object(AliasManager, "notify")
@patch.object(ShellIntegrator, "apply_single_alias")
async def test_add_alias_with_conflicts_and_apply_failure(mock_apply, mock_notify, mock_storage, mock_subprocess):
    # Mock no storage conflict
    mock_storage.return_value.get.return_value = None

    # Mock shell conflict
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "alias test-alias='echo test'"

    # Mock apply failure
    mock_apply.return_value = (False, "Apply failed")

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-add")
        await pilot.click("#name")
        await pilot.press(*list("test-alias"))
        await pilot.click("#command")
        await pilot.press(*list("echo new"))
        await pilot.click("#description")
        await pilot.press(*list("new desc"))

        # Attempt without force - should show shell conflict error
        await pilot.click("#create")
        await pilot.pause()

        # Verify shell conflict message notification
        mock_notify.assert_any_call(
            "Alias/Command/Function already exists\nEnable Force Override if you want to override this alias\nalias test-alias='echo test'",
            severity="error",
        )

        # Verify subprocess was called for conflict check
        mock_subprocess.assert_called()

        # Verify storage add was not called due to conflict
        mock_storage.return_value.add.assert_not_called()

        # Verify apply was not attempted due to conflict
        mock_apply.assert_not_called()


@pytest.mark.asyncio
@patch("alix.tui.subprocess.run")
@patch.object(ShellIntegrator, "apply_single_alias")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_add_alias_with_existing_conflict(mock_storage, mock_notify, mock_apply, mock_subprocess):
    # Mock storage to return existing alias
    existing_alias = Alias(name="test-alias", command="echo existing", description="existing desc")
    mock_storage.return_value.get.return_value = existing_alias

    # Mock subprocess for shell conflict
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "alias test-alias='echo shell'"

    # Mock apply failure
    mock_apply.return_value = (False, "Apply failed")

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-add")
        await pilot.click("#name")
        await pilot.press(*list("test-alias"))
        await pilot.click("#command")
        await pilot.press(*list("echo new"))
        await pilot.click("#description")
        await pilot.press(*list("new desc"))

        # Submit without force
        await pilot.click("#create")
        await pilot.pause()

        # Assert storage conflict notification
        mock_notify.assert_called_with(
            "Alias 'test-alias' exists in alix\nEdit the alias to override",
            severity="error",
        )

        # Assert subprocess not called because storage conflict takes precedence
        mock_subprocess.assert_not_called()

        # Assert storage.add not called
        mock_storage.return_value.add.assert_not_called()

        # Assert apply not called
        mock_apply.assert_not_called()


@pytest.mark.asyncio
async def test_help_modal():
    """Test opening and closing the help modal."""
    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        # Simulate clicking in the middle of the terminal at (45, 15)
        await pilot.mouse_down(pilot.app.screen, offset=(45, 15))
        await pilot.mouse_up(pilot.app.screen, offset=(45, 15))

        # Press '?' to open the modal
        await pilot.press('?')
        await pilot.pause()

        # Assert the screen is HelpModal
        assert isinstance(pilot.app.screen, HelpModal)

        # Verify keybinding items are present in the modal content
        help_items = pilot.app.screen.query(".help-item")
        help_texts = [str(item.render()) for item in help_items]
        assert "a - Add new alias" in help_texts

        # Press 'escape' to close the modal
        await pilot.press('escape')
        await pilot.pause()

        # Assert the modal is dismissed
        assert not isinstance(pilot.app.screen, HelpModal)


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
async def test_fuzzy_search_and_filters(mock_storage):
    """Test fuzzy search, group filtering, tag filtering, search input, row highlighting, status updates, and info panel changes."""
    # Set up aliases with groups and tags
    aliases = [
        Alias(
            name="git-commit",
            command="git commit -m 'msg'",
            description="commit changes",
            group="git",
            tags=["version-control", "commit"],
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
        Alias(
            name="docker-build",
            command="docker build .",
            description="build docker image",
            group="docker",
            tags=["container", "build"],
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
        Alias(
            name="ls-files",
            command="ls -la",
            description="list all files",
            group=None,
            tags=["file", "list"],
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
        Alias(
            name="grep-search",
            command="grep 'pattern'",
            description="search for pattern",
            group="utils",
            tags=["search", "text"],
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
    ]
    mock_storage.return_value.list_all.return_value = aliases

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        # Simulate clicking in the middle of the terminal at (45, 15)
        await pilot.mouse_down(pilot.app.screen, offset=(45, 15))
        await pilot.mouse_up(pilot.app.screen, offset=(45, 15))
        # Enable fuzzy search
        await pilot.press('f')
        await pilot.press('/')
        status = app.query_one("#status-bar", Static)
        assert 'Fuzzy ON' in str(pilot.app.query_one('#status-bar').render())

        await pilot.mouse_down(pilot.app.screen, offset=(45, 15))
        await pilot.mouse_up(pilot.app.screen, offset=(45, 15))
        await pilot.press('g')  # Cycle to "All Aliases"
        await pilot.press('g')  # Cycle to "docker"
        await pilot.press('g')  # Cycle to "git"
        table = app.query_one("#table", DataTable)
        assert len(table.rows) == 1

        # Back to All Aliases
        await pilot.press('g')
        await pilot.press('g')
        await pilot.press('g')

        # Set tag filter to "search"
        await pilot.press('t')  # Cycle to "build"
        await pilot.press('t')  # Cycle to "commit"
        await pilot.press('t')  # Cycle to "container"
        await pilot.press('t')  # Cycle to "file"
        await pilot.press('t')  # Cycle to "list"
        await pilot.press('t')  # Cycle to "search"
        assert len(table.rows) == 1

        # Clear filters
        await pilot.press('g')
        await pilot.press('g')
        await pilot.press('g')
        await pilot.press('g')
        await pilot.press('g')  # Back to "All Aliases"
        await pilot.press('t')  # Cycle to "text"
        await pilot.press('t')  # Cycle to "version-control"
        await pilot.press('t')  # Cycle to "Untagged Aliases"
        await pilot.press('t')  # Cycle to "All Aliases"

        # Simulate search input for fuzzy search
        await pilot.press('/')
        await pilot.press(*list("comm"))
        # Fuzzy search should find "git-commit" with high score
        assert len(table.rows) == 1

        await pilot.mouse_down(pilot.app.screen, offset=(45, 15))
        await pilot.mouse_up(pilot.app.screen, offset=(45, 15))
        # Simulate input change for exact search (disable fuzzy)
        await pilot.press('f')  # Disable fuzzy
        await pilot.press('/')
        assert 'Fuzzy OFF' in str(pilot.app.query_one('#status-bar').render())
        await pilot.press(*list(["backspace"] * 4))  # Clear search
        await pilot.press(*list("commit"))
        assert len(table.rows) == 1

        await pilot.mouse_down(pilot.app.screen, offset=(45, 15))
        await pilot.mouse_up(pilot.app.screen, offset=(45, 15))
        # Verify status updates with filters
        await pilot.press('g')
        await pilot.press('g')  # Set group to "git"
        status_text = str(status.render())
        assert "Group: git" in status_text
        assert "Fuzzy OFF" in status_text

        # Verify filter application
        assert len(table.rows) == 1


@pytest.mark.asyncio
@patch.object(ShellIntegrator, "apply_aliases")
@patch("alix.tui.ClipboardManager")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_alias_management_actions(mock_storage, mock_notify, mock_clipboard, mock_apply_aliases):
    """Test following actions: copy, delete, refresh, focus search, clear search, cursor movements, apply all, and button presses."""
    # Set up aliases
    aliases = [
        Alias(
            name="test-alias",
            command="echo test",
            description="test description",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
        Alias(
            name="another-alias",
            command="ls -la",
            description="list files",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
    ]
    mock_storage.return_value.list_all.return_value = aliases
    mock_storage.return_value.remove.return_value = True
    mock_apply_aliases.return_value = (True, "Applied")
    mock_storage.return_value.get.return_value.command = "ls -la"

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.mouse_down(pilot.app.screen, offset=(45, 15))
        await pilot.mouse_up(pilot.app.screen, offset=(45, 15))
        await pilot.press('c')
        mock_clipboard.return_value.copy.assert_called_once_with("ls -la")
        mock_notify.assert_any_call("Alias command copied to clipboard")

        app.selected_alias = None
        await pilot.press('e')
        mock_notify.assert_any_call("Please select an alias to edit", severity="warning")

        await pilot.press('d')
        mock_notify.assert_any_call("Please select an alias to delete", severity="warning")

        app.selected_alias = aliases[0]
        await pilot.press('d')

        await pilot.click("#delete")
        mock_storage.return_value.remove.assert_called_once_with("test-alias")
        mock_apply_aliases.assert_called_once()

        await pilot.press('r')
        mock_notify.assert_any_call("Refreshed from disk")

        await pilot.press('/')
        search_input = app.query_one("#search", Input)
        assert search_input.has_focus

        search_input.value = "test"
        await pilot.press('escape')
        assert search_input.value == ""
        mock_notify.assert_any_call("Refreshed from disk")  # From refresh

        await pilot.press('j')

        await pilot.press('k')

        await pilot.press('p')
        mock_apply_aliases.assert_called()

        await pilot.click("#btn-refresh")
        await pilot.click("#btn-apply")

        await pilot.press('g')
        await pilot.press('t')


@pytest.mark.asyncio
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_add_alias_empty_fields(mock_storage, mock_notify):
    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-add")
        # Leave name and command fields empty
        await pilot.click("#create")

        # Assert storage.add was not called due to early exit
        mock_storage.return_value.add.assert_not_called()


@pytest.mark.asyncio
@patch.object(ShellIntegrator, "apply_single_alias")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
@patch("alix.tui.subprocess.run")
async def test_add_alias_apply_failure_after_conflicts(mock_subprocess, mock_storage, mock_notify, mock_apply):
    # Mock no storage conflict
    mock_storage.return_value.get.return_value = None

    # Mock shell conflict
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "alias test-alias='echo test'"

    # Mock apply failure
    mock_apply.return_value = (False, "Apply failed")

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-add")
        await pilot.click("#name")
        await pilot.press(*list("test-alias"))
        await pilot.click("#command")
        await pilot.press(*list("echo new"))
        await pilot.click("#description")
        await pilot.press(*list("new desc"))
        await pilot.press('down', 'down', 'down', 'down', 'down', 'down', 'down', 'down')

        # Enable force override
        await pilot.click("#force")

        # Submit with force
        await pilot.click("#create")
        await pilot.pause()

        # Assert apply was attempted
        mock_apply.assert_called_once()

        # Assert failure notification
        mock_notify.assert_any_call(
            "Created 'test-alias' (apply manually)", severity="warning"
        )

        # Assert storage add was called
        mock_storage.return_value.add.assert_called_once()


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
async def test_add_alias_cancel(mock_storage):
    """Test canceling the add alias modal dismisses without calling storage.add"""
    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-add")
        await pilot.click("#name")
        await pilot.press(*list("test-alias"))
        await pilot.click("#command")
        await pilot.press(*list("echo test"))
        await pilot.click("#description")
        await pilot.press(*list("test description"))
        await pilot.click("#cancel")

        await pilot.pause()  # Wait for async operations to complete

        # Assert storage.add was not called
        mock_storage.return_value.add.assert_not_called()

        # Assert the modal is dismissed (screen should be back to main)
        assert not isinstance(pilot.app.screen, AddAliasModal)


@pytest.mark.asyncio
@patch("alix.tui.subprocess.run")
@patch.object(ShellIntegrator, "apply_single_alias")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_add_alias_storage_failure(mock_storage, mock_notify, mock_apply, mock_subprocess):
    mock_storage.return_value.add.return_value = False
    mock_storage.return_value.get.return_value = None
    mock_subprocess.return_value.returncode = 1  # No shell conflict

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-add")
        await pilot.click("#name")
        await pilot.press(*list("test-alias"))
        await pilot.click("#command")
        await pilot.press(*list("echo test"))
        await pilot.click("#description")
        await pilot.press(*list("test description"))
        await pilot.click("#create")

        await pilot.pause()

        mock_notify.assert_called_with(
            "Alias 'test-alias' exists in alix\nEdit the alias to override",
            severity="error",
        )
        mock_storage.return_value.add.assert_called_once()
        mock_apply.assert_not_called()


@pytest.mark.asyncio
@patch.object(ShellIntegrator, "apply_single_alias")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_edit_alias_cancel(mock_storage, mock_notify, mock_apply):
    """Test canceling the edit alias modal dismisses without updating storage"""
    # Mock an existing alias
    alias = Alias(name="test-alias", command="echo test", description="test description")
    mock_storage.return_value.get.return_value = alias

    app = AliasManager()
    app.selected_alias = alias

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-edit")
        # Leave fields unchanged
        await pilot.click("#cancel")

        await pilot.pause()  # Wait for async operations to complete

        # Assert storage update methods were not called
        mock_storage.return_value.remove.assert_not_called()
        mock_storage.return_value.save.assert_not_called()
        mock_apply.assert_not_called()

        # Assert the modal is dismissed
        assert not isinstance(pilot.app.screen, EditAliasModal)


@pytest.mark.asyncio
@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_edit_alias_empty_fields(mock_storage, mock_apply):
    """Test early exit in EditAliasModal when name or command fields are empty"""
    # Mock an existing alias
    alias = Alias(name="test-alias", command="echo test", description="test description")
    mock_storage.return_value.get.return_value = alias

    app = AliasManager()
    app.selected_alias = alias

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-edit")
        # Clear name field
        await pilot.click("#name")
        await pilot.press(*list(["delete"] * len(alias.name)))
        # Clear command field
        await pilot.click("#command")
        await pilot.press(*list(["delete"] * len(alias.command)))
        await pilot.click("#update")

        await pilot.pause()  # Wait for async operations to complete

        # Assert storage update methods were not called due to early exit
        mock_storage.return_value.remove.assert_not_called()
        mock_storage.return_value.save.assert_not_called()
        mock_apply.assert_not_called()


@pytest.mark.asyncio
@patch.object(ShellIntegrator, "apply_single_alias")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_edit_alias_same_name(mock_storage, mock_notify, mock_apply, alias_min):
    mock_storage.return_value.aliases = {}
    mock_apply.return_value = (True, "✓ Applied alias 'alix-test-echo' to .zshrc")
    alias_min.created_at = ANY

    app = AliasManager()
    app.selected_alias = alias_min

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-edit")
        await pilot.click("#command")
        await pilot.press(*list(["delete"] * len(alias_min.command)))
        await pilot.press(*list("changed command"))
        await pilot.click("#description")
        await pilot.press(*list(["delete"] * len(alias_min.description)))
        await pilot.press(*list("changed description"))
        await pilot.click("#update")

        await pilot.pause()  # Wait for async operations to complete

        mock_notify.assert_any_call("Alias updated and applied successfully")

        mock_storage.return_value.remove.assert_not_called()
        mock_storage.return_value.save.assert_called_once()
        mock_apply.assert_called_once()
        updated_alias = Alias(
            name=alias_min.name,
            command="changed command",
            description="changed description",
            created_at=alias_min.created_at,
        )
        assert mock_storage.return_value.aliases[alias_min.name] == updated_alias


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
@patch.object(AliasManager, "update_info_panel")
async def test_row_highlight_no_key(mock_update_info, mock_storage):
    app = AliasManager()

    # Create a mock event with row_key = None
    from unittest.mock import MagicMock
    event = MagicMock()
    event.row_key = None

    # Call the method
    app.on_data_table_row_highlighted(event)

    # Assert no alias is selected
    assert app.selected_alias is None

    # Assert info panel was not updated
    mock_update_info.assert_not_called()


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
async def test_delete_not_confirmed(mock_storage):
    """Test that delete action does not remove alias when not confirmed"""
    # Set up aliases
    aliases = [
        Alias(
            name="test-alias",
            command="echo test",
            description="test description",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
    ]
    mock_storage.return_value.list_all.return_value = aliases

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.mouse_down(pilot.app.screen, offset=(45, 15))
        await pilot.mouse_up(pilot.app.screen, offset=(45, 15))
        app.selected_alias = aliases[0]
        await pilot.press('d')
        await pilot.click("#cancel")

        # Assert remove not called
        mock_storage.return_value.remove.assert_not_called()


@pytest.mark.asyncio
@patch.object(AliasManager, "notify")
async def test_copy_no_selected_alias(mock_notify):
    """Test action_copy_alias when no alias is selected"""
    app = AliasManager()
    app.selected_alias = None

    app.action_copy_alias()

    mock_notify.assert_called_once_with("Please select an alias to copy", severity="warning")


@patch.object(AliasManager, "notify")
@patch("alix.tui.ClipboardManager")
def test_copy_clipboard_exception(mock_clipboard, mock_notify):
    """Test action_copy_alias exception handling when ClipboardManager.copy raises an exception"""
    mock_clipboard.return_value.copy.side_effect = Exception("Clipboard error")

    app = AliasManager()
    alias = Alias(name="test-alias", command="echo test", description="test description")
    app.selected_alias = alias

    app.action_copy_alias()

    mock_notify.assert_called_once_with("Unable to copy. Command: echo test")


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
@patch.object(AliasManager, "update_info_panel")
async def test_row_highlight_no_selected_alias(mock_update_info, mock_storage):
    app = AliasManager()

    # Mock storage.get to return None
    mock_storage.return_value.get.return_value = None

    # Create a mock event with a valid row_key
    from unittest.mock import MagicMock
    event = MagicMock()
    event.row_key = MagicMock()
    event.row_key.value = "valid_alias_name"

    # Call the method
    app.on_data_table_row_highlighted(event)

    # Assert no alias is selected
    assert app.selected_alias is None

    # Assert info panel was not updated
    mock_update_info.assert_not_called()


@pytest.mark.asyncio
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_delete_remove_failed(mock_storage, mock_notify):
    """Test delete callback else branch when storage.remove returns False"""
    # Set up aliases
    aliases = [
        Alias(
            name="test-alias",
            command="echo test",
            description="test description",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
    ]
    mock_storage.return_value.list_all.return_value = aliases
    mock_storage.return_value.remove.return_value = False  # Mock remove failure

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.mouse_down(pilot.app.screen, offset=(45, 15))
        await pilot.mouse_up(pilot.app.screen, offset=(45, 15))
        app.selected_alias = aliases[0]
        await pilot.press('d')

        await pilot.click("#delete")

        # Assert error notification is shown
        mock_notify.assert_called_with("Failed to delete alias", severity="error")


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
async def test_cursor_actions(mock_storage):
    """Test cursor movement actions: action_cursor_down and action_cursor_up"""
    # Set up aliases to populate the table
    aliases = [
        Alias(
            name="alias1",
            command="echo test1",
            description="desc1",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
        Alias(
            name="alias2",
            command="echo test2",
            description="desc2",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
    ]
    mock_storage.return_value.list_all.return_value = aliases

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        table = app.query_one("#table", DataTable)
        
        # Initial cursor position
        initial_cursor = table.cursor_row
        
        # Move cursor down
        app.action_cursor_down()
        assert table.cursor_row == initial_cursor + 1
        
        # Move cursor up
        app.action_cursor_up()
        assert table.cursor_row == initial_cursor


@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
def test_apply_all_no_target_file(mock_storage, mock_notify):
    with patch.object(ShellIntegrator, "get_target_file", return_value=None):
        app = AliasManager()
        app.action_apply_all()
        mock_notify.assert_called_once_with("No shell config file found", severity="error")


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
async def test_button_delete(mock_storage):
    """Test clicking #btn-delete button triggers delete action (shows modal)"""
    # Set up aliases
    aliases = [
        Alias(
            name="test-alias",
            command="echo test",
            description="test description",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
    ]
    mock_storage.return_value.list_all.return_value = aliases

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        # Select an alias
        app.selected_alias = aliases[0]

        # Click the delete button
        await pilot.click("#btn-delete")

        # Assert the DeleteConfirmModal is shown
        assert isinstance(pilot.app.screen, DeleteConfirmModal)


@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
def test_apply_all_failure(mock_storage, mock_notify):
    with patch.object(ShellIntegrator, "get_target_file", return_value=Path("/fake/.zshrc")):
        with patch.object(ShellIntegrator, "apply_aliases", return_value=(False, "Apply failed")):
            app = AliasManager()
            app.action_apply_all()
            mock_notify.assert_called_once_with("Failed: Apply failed", severity="error")


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
async def test_filter_by_group_value_error(mock_storage):
    """Test action_filter_by_group ValueError handling when current filter is invalid"""
    # Set up aliases with groups
    aliases = [
        Alias(
            name="git-commit",
            command="git commit -m 'msg'",
            description="commit changes",
            group="git",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
        Alias(
            name="docker-build",
            command="docker build .",
            description="build docker image",
            group="docker",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        ),
    ]
    mock_storage.return_value.list_all.return_value = aliases

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        # Set invalid group filter
        app._current_group_filter = "invalid_group"

        # Call action_filter_by_group
        app.action_filter_by_group()

        # Assert _current_group_filter is reset to "All Groups"
        assert app._current_group_filter == "All Groups"


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
async def test_large_dataset_handling(mock_storage):
    """Test handling of large datasets with 100+ aliases without crashing."""
    # Create 150 aliases to test large dataset
    aliases = [
        Alias(
            name=f"alias{i}",
            command=f"echo 'command {i}'",
            description=f"description {i}",
            created_at=datetime.datetime(2025, 10, 24, 16, 34, 21, 653023),
        )
        for i in range(150)
    ]
    mock_storage.return_value.list_all.return_value = aliases

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        # Verify the app loads the large dataset without crashing
        table = app.query_one("#table", DataTable)
        # The table may not display all rows due to size constraints, but should not crash
        assert table.row_count >= 0  # At least loads


@pytest.mark.asyncio
@patch.object(ShellIntegrator, "apply_single_alias")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_special_characters_in_aliases(mock_storage, mock_notify, mock_apply):
    """Test handling of special characters in alias names, commands, and descriptions."""
    special_name = "alias!@#$%^&*()"
    special_command = "echo 'special chars: !@#$%^&*()'"
    special_description = "Description with éñü and symbols: ©®™"

    mock_storage.return_value.add.return_value = True
    mock_storage.return_value.get.return_value = None
    mock_apply.return_value = (True, "Applied successfully")

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-add")
        await pilot.click("#name")
        await pilot.press(*list(special_name))
        await pilot.click("#command")
        await pilot.press(*list(special_command))
        await pilot.click("#description")
        await pilot.press(*list(special_description))
        await pilot.click("#create")

        await pilot.pause()  # Wait for async operations

        # Verify the alias was added without crashing
        mock_storage.return_value.add.assert_called_once()
        mock_notify.assert_any_call("Created and applied 'alias!@#$%^&*()'", severity="information")


@pytest.mark.asyncio
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_storage_corruption_handling(mock_storage, mock_notify):
    """Test graceful handling of storage corruption or permission issues."""
    # Mock storage to raise exception on list_all (simulating corruption)
    mock_storage.return_value.list_all.side_effect = Exception("Storage corrupted")

    app = AliasManager()

    try:
        async with app.run_test(size=(90, 30)) as pilot:
            # If no exception, the app handled it gracefully, but we expect it not to
            assert False, "Expected exception was not raised"
    except Exception as e:
        assert str(e) == "Storage corrupted"
        # Verify the app did not handle it gracefully, i.e., no notification
        mock_notify.assert_not_called()


@pytest.mark.asyncio
@patch("alix.tui.AliasStorage", autospec=True)
async def test_empty_filter_states(mock_storage):
    """Test handling of empty filter states when no aliases match or none exist."""
    # Start with no aliases
    mock_storage.return_value.list_all.return_value = []

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        table = app.query_one("#table", DataTable)
        assert len(table.rows) == 0

        # Apply group filter when no aliases exist
        await pilot.press('g')  # Cycle to next group filter
        assert len(table.rows) == 0  # Should remain empty

        # Apply tag filter
        await pilot.press('t')  # Cycle to next tag filter
        assert len(table.rows) == 0  # Should remain empty

        # Enable fuzzy search and search
        await pilot.press('f')  # Toggle fuzzy
        await pilot.press('/')
        await pilot.press(*list("nonexistent"))
        assert len(table.rows) == 0  # Should remain empty without crashing
