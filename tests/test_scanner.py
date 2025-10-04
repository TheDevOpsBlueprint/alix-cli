from alix.scanner import AliasScanner
from alix.shell_detector import ShellDetector, ShellType
from unittest.mock import patch, Mock
from pathlib import Path


@patch.object(ShellDetector, "find_config_files")
@patch.object(ShellDetector, "detect_current_shell")
def test_scan_system(
    mock_detect_current_shell, mock_find_config_files, shell_file_data
):
    mock_detect_current_shell.return_value = ShellType.ZSH
    mock_path = Mock(spec=Path)
    mock_path.name = ".zshrc"
    mock_path.exists.return_value = True
    mock_path.read_text.return_value = shell_file_data
    mock_find_config_files.return_value = {".zshrc": mock_path}

    scanner = AliasScanner()
    results = scanner.scan_system()

    assert ".zshrc" in results
    assert len(results) == 1
    assert results[".zshrc"][0].name == "alix-test-echo"
    assert results[".zshrc"][0].command == "alix test working!"
    assert results[".zshrc"][0].description == "Imported from .zshrc"


@patch.object(ShellDetector, "find_config_files")
@patch.object(ShellDetector, "detect_current_shell")
def test_scan_system__no_aliases(mock_detect_current_shell, mock_find_config_files):
    mock_detect_current_shell.return_value = ShellType.ZSH
    mock_path = Mock(spec=Path)
    mock_path.exists.return_value = False
    mock_find_config_files.return_value = {".zshrc": mock_path}

    scanner = AliasScanner()
    results = scanner.scan_system()

    assert results == {}


@patch("alix.scanner.subprocess")
@patch.object(ShellDetector, "detect_current_shell")
def test_get_active_aliases(
    mock_detect_current_shell, mock_subprocess, shell_file_data
):
    mock_detect_current_shell.return_value = ShellType.ZSH
    mock_stdout = f"{shell_file_data}\n{shell_file_data}"
    mock_subprocess.run.return_value.returncode = 0
    mock_subprocess.run.return_value.stdout = mock_stdout

    scanner = AliasScanner()
    results = scanner.get_active_aliases()

    assert len(results) == 2
    assert results[0].name == "alix-test-echo"
    assert results[0].command == "alix test working!"
    assert results[0].description == "Active system alias"


@patch("alix.scanner.subprocess")
@patch.object(ShellDetector, "detect_current_shell")
def test_get_active_aliases__unknown_shell(mock_detect_current_shell, mock_subprocess):
    mock_detect_current_shell.return_value = ShellType.UNKNOWN

    scanner = AliasScanner()
    results = scanner.get_active_aliases()

    assert len(results) == 0
    mock_subprocess.run.assert_not_called()


@patch("alix.scanner.subprocess")
@patch.object(ShellDetector, "detect_current_shell")
def test_get_active_aliases__failed_run(mock_detect_current_shell, mock_subprocess):
    mock_detect_current_shell.return_value = ShellType.ZSH
    mock_subprocess.run.return_value.returncode = 1

    scanner = AliasScanner()
    results = scanner.get_active_aliases()

    assert len(results) == 0
