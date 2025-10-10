from unittest.mock import ANY, patch

from click.testing import CliRunner

from alix.cli import main
from alix.shell_integrator import ShellIntegrator


@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.cli.subprocess")
@patch("alix.cli.storage")
def test_cli_add(mock_storage, mock_subprocess, mock_apply, alias):
    mock_storage.add.return_value = True
    mock_storage.get.return_value = None
    mock_subprocess.run.return_value.returncode = 1
    mock_apply.return_value = (True, "✓ Applied alias 'alix-test-echo' to .zshrc")
    alias.created_at = ANY
    alias.shell = ANY

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
            "--tags",
            "a, b"
        ],
    )

    assert result.exit_code == 0

    mock_storage.get.assert_called_with("alix-test-echo")
    mock_subprocess.run.assert_called()
    mock_storage.add.assert_called_with(alias, record_history=True)

    assert "✔ Added alias: alix-test-echo = 'alix test working!'" in result.output
    assert (
        "💡 Alias 'alix-test-echo' is now available in new shell sessions"
        in result.output
    )
    assert "For current session, run: source" in result.output


@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.cli.storage")
def test_cli_add__already_in_storage(mock_storage, mock_apply):
    mock_storage.get.return_value = "alix-test-echo"

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
    mock_storage.add.assert_not_called()
    mock_apply.assert_not_called()

    assert "Alias/Command/Function already exists. Add --force flag to override" in result.output
    assert "Added alias: alix-test-echo = 'alix test working!'" not in result.output
    assert "✓ Applied alias 'alix-test-echo' to" not in result.output


@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.cli.subprocess")
@patch("alix.cli.storage")
def test_cli_add__already_an_alias(mock_storage, mock_subprocess, mock_apply):
    mock_storage.get.return_value = None
    mock_subprocess.run.return_value.returncode = 0
    mock_subprocess.run.return_value.stdout = "Edit the alias to override it"

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
    mock_storage.add.assert_not_called()
    mock_apply.assert_not_called()

    assert "Alias/Command/Function already exists. Add --force flag to override" in result.output
    assert "Added alias: alix-test-echo = 'alix test working!'" not in result.output
    assert "✓ Applied alias 'alix-test-echo' to" not in result.output


@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.cli.storage")
def test_cli_add__apply_failed(mock_storage, mock_apply, alias):
    mock_storage.add.return_value = True
    mock_storage.get.return_value = None
    mock_apply.return_value = (False, "No shell configuration file found")
    alias.created_at = ANY
    alias.shell = ANY

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
            "--tags",
            "a, b"
        ],
    )

    assert result.exit_code == 0
    mock_storage.add.assert_called_with(alias, record_history=True)
    mock_apply.assert_called_with(alias)

    assert "Added alias: alix-test-echo = 'alix test working!'" in result.output
    assert (
        "⚠ Alias saved but not applied: No shell configuration file found"
        in result.output
    )
    assert "   Run 'alix apply' to apply all aliases to shell" in result.output

    assert "✓ Applied alias 'alix-test-echo' to" not in result.output


@patch.object(ShellIntegrator, "apply_single_alias")
@patch("alix.cli.storage")
def test_cli_add__no_apply(mock_storage, mock_apply, alias):
    mock_storage.get.return_value = None
    mock_storage.add.return_value = True
    alias.created_at = ANY
    alias.shell = ANY

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
            "--tags",
            "a, b"
        ],
    )

    assert result.exit_code == 0
    mock_storage.get.assert_called_with("alix-test-echo")
    mock_storage.add.assert_called_with(alias, record_history=True)
    mock_apply.assert_not_called()

    assert "Added alias: alix-test-echo = 'alix test working!'" in result.output
    assert "✓ Applied alias 'alix-test-echo' to" not in result.output
    assert (
        "⚠ Alias saved but not applied: alix-test-echo = 'alix test working!'"
        not in result.output
    )
