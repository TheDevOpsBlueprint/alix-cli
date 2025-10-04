from unittest.mock import patch

from click.testing import CliRunner

from alix.cli import main
from alix.shell_integrator import ShellIntegrator


@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.cli.storage")
def test_cli_add(mock_storage, mock_apply):
    mock_storage.add.return_value = True
    mock_storage.get.return_value = None
    mock_apply.return_value = (True, "✓ Applied alias 'alix-test-echo' to .zshrc")

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "add",
            "-n",
            "alix-test-echo",
            "-c",
            "alix test working!",
            "-d",
            "alix test shortcut",
        ],
    )

    assert result.exit_code == 0

    assert "✔ Added alias: alix-test-echo = 'alix test working!'" in result.output
    assert (
        "💡 Alias 'alix-test-echo' is now available in new shell sessions"
        in result.output
    )
    assert "For current session, run: source ~/.zshrc" in result.output


@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.cli.storage")
def test_cli_add__already_present(mock_storage, mock_apply):
    mock_storage.add.return_value = False

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "add",
            "-n",
            "alix-test-echo",
            "-c",
            "alix test working!",
            "-d",
            "alix test shortcut",
        ],
    )

    assert result.exit_code == 0
    mock_apply.assert_not_called()

    assert "Alias/Command/Function already exists. Add --force flag to override" in result.output
    assert "Added alias: alix-test-echo = 'alix test working!'" not in result.output
    assert "✓ Applied alias 'alix-test-echo' to .zshrc" not in result.output


@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.cli.storage")
def test_cli_add__apply_failed(mock_storage, mock_apply):
    mock_storage.add.return_value = True
    mock_storage.get.return_value = None
    mock_apply.return_value = (False, "No shell configuration file found")

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "add",
            "-n",
            "alix-test-echo",
            "-c",
            "alix test working!",
            "-d",
            "alix test shortcut",
        ],
    )

    assert result.exit_code == 0

    assert "Added alias: alix-test-echo = 'alix test working!'" in result.output
    assert (
        "⚠ Alias saved but not applied: No shell configuration file found"
        in result.output
    )
    assert "   Run 'alix apply' to apply all aliases to shell" in result.output

    assert "✓ Applied alias 'alix-test-echo' to .zshrc" not in result.output


@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.cli.storage")
def test_cli_add__no_apply(mock_storage, mock_apply):
    mock_storage.get.return_value = None
    mock_storage.add.return_value = True

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "add",
            "--no-apply",
            "-n",
            "alix-test-echo",
            "-c",
            "alix test working!",
            "-d",
            "alix test shortcut",
        ],
    )

    assert result.exit_code == 0
    mock_apply.assert_not_called()

    assert "Added alias: alix-test-echo = 'alix test working!'" in result.output
    assert "✓ Applied alias 'alix-test-echo' to .zshrc" not in result.output
    assert (
        "⚠ Alias saved but not applied: alix-test-echo = 'alix test working!'"
        not in result.output
    )
