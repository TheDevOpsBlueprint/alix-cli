from unittest.mock import ANY, patch

import pytest

from alix.models import Alias
from alix.shell_integrator import ShellIntegrator
from alix.tui import AliasManager


@pytest.mark.asyncio
@patch.object(ShellIntegrator, "apply_single_alias")
@patch.object(AliasManager, "notify")
@patch("alix.tui.AliasStorage", autospec=True)
async def test_add_alias(mock_storage, mock_notify, mock_apply, alias_min):
    mock_storage.return_value.add.return_value = True
    mock_storage.return_value.get.return_value = None
    mock_apply.return_value = (True, "✓ Applied alias 'alix-test-echo' to .zshrc")
    alias_min.created_at = ANY

    app = AliasManager()

    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.click("#btn-add")
        await pilot.click("#name")
        await pilot.press(*list("alix-test-echo"))
        await pilot.click("#command")
        await pilot.press(*list("alix test working!"))
        await pilot.click("#description")
        await pilot.press(*list("alix test shortcut"))
        await pilot.click("#create")

        await pilot.pause()  # Wait for async operations to complete

        mock_notify.assert_any_call(
            "Created and applied 'alix-test-echo'", severity="information"
        )
        mock_notify.assert_any_call("Alias added and applied successfully")
        mock_storage.return_value.add.assert_called_once_with(alias_min)
        mock_apply.assert_called_once_with(alias_min)


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
