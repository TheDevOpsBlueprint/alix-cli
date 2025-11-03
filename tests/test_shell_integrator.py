import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from alix.shell_integrator import ShellIntegrator
from alix.shell_detector import ShellDetector, ShellType
from alix.storage import AliasStorage
from alix.models import Alias


@pytest.fixture
def mock_detector():
    """Mock ShellDetector for testing"""
    detector = Mock(spec=ShellDetector)
    detector.detect_current_shell.return_value = ShellType.BASH
    detector.find_config_files.return_value = {
        ".bashrc": Path("/home/user/.bashrc"),
        ".bash_profile": Path("/home/user/.bash_profile")
    }
    return detector


@pytest.fixture
def mock_storage():
    """Mock AliasStorage for testing"""
    storage = Mock(spec=AliasStorage)
    storage.list_all.return_value = [
        Alias(name="test1", command="echo test1"),
        Alias(name="test2", command="echo test2")
    ]
    return storage


@pytest.fixture
def shell_integrator(mock_detector, mock_storage):
    """ShellIntegrator instance with mocked dependencies"""
    with patch('alix.shell_integrator.ShellDetector', return_value=mock_detector), \
         patch('alix.shell_integrator.AliasStorage', return_value=mock_storage):
        integrator = ShellIntegrator()
        return integrator


@pytest.fixture
def temp_dir():
    """Temporary directory for file operations"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def temp_config_file(temp_dir):
    """Temporary config file for testing"""
    config_file = temp_dir / ".bashrc"
    config_file.write_text("# Test config\n")
    return config_file


class TestShellIntegratorInit:
    """Test ShellIntegrator initialization"""

    def test_init_creates_detector_and_storage(self):
        """Test that __init__ creates detector and storage instances"""
        with patch('alix.shell_integrator.ShellDetector') as mock_detector_class, \
             patch('alix.shell_integrator.AliasStorage') as mock_storage_class:

            mock_detector_instance = Mock()
            mock_storage_instance = Mock()
            mock_detector_class.return_value = mock_detector_instance
            mock_storage_class.return_value = mock_storage_instance

            integrator = ShellIntegrator()

            mock_detector_class.assert_called_once()
            mock_storage_class.assert_called_once()
            assert integrator.detector == mock_detector_instance
            assert integrator.storage == mock_storage_instance
            mock_detector_instance.detect_current_shell.assert_called_once()

    def test_init_detects_shell_type(self, mock_detector):
        """Test that shell_type is set from detector"""
        with patch('alix.shell_integrator.ShellDetector', return_value=mock_detector):
            integrator = ShellIntegrator()
            assert integrator.shell_type == ShellType.BASH


class TestGetTargetFile:
    """Test get_target_file method"""

    def test_get_target_file_with_priority_match(self, shell_integrator, mock_detector):
        """Test selecting priority file when available"""
        mock_detector.find_config_files.return_value = {
            ".bash_aliases": Path("/home/user/.bash_aliases"),
            ".bashrc": Path("/home/user/.bashrc")
        }
        shell_integrator.shell_type = ShellType.BASH

        result = shell_integrator.get_target_file()
        assert result == Path("/home/user/.bash_aliases")

    def test_get_target_file_no_priority_match(self, shell_integrator, mock_detector):
        """Test selecting first available when no priority match"""
        mock_detector.find_config_files.return_value = {
            ".profile": Path("/home/user/.profile"),
            ".bashrc": Path("/home/user/.bashrc")
        }
        shell_integrator.shell_type = ShellType.BASH

        result = shell_integrator.get_target_file()
        # Should return first item (order not guaranteed in dict)
        assert result in [Path("/home/user/.profile"), Path("/home/user/.bashrc")]

    def test_get_target_file_no_configs(self, shell_integrator, mock_detector):
        """Test returning None when no config files found"""
        mock_detector.find_config_files.return_value = {}
        result = shell_integrator.get_target_file()
        assert result is None

    def test_get_target_file_zsh_priority(self, shell_integrator, mock_detector):
        """Test ZSH priority order"""
        mock_detector.find_config_files.return_value = {
            ".zshrc": Path("/home/user/.zshrc"),
            ".zsh_aliases": Path("/home/user/.zsh_aliases")
        }
        shell_integrator.shell_type = ShellType.ZSH

        result = shell_integrator.get_target_file()
        assert result == Path("/home/user/.zsh_aliases")

    def test_get_target_file_fish_config(self, shell_integrator, mock_detector):
        """Test FISH config selection"""
        mock_detector.find_config_files.return_value = {
            ".config/fish/config.fish": Path("/home/user/.config/fish/config.fish")
        }
        shell_integrator.shell_type = ShellType.FISH

        result = shell_integrator.get_target_file()
        assert result == Path("/home/user/.config/fish/config.fish")


class TestBackupShellConfig:
    """Test backup_shell_config method"""

    def test_backup_shell_config_creates_backup(self, shell_integrator, temp_config_file):
        """Test creating backup with timestamp"""
        with patch('alix.shell_integrator.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "20230101_120000"
            mock_datetime.now.return_value = mock_now

            backup_path = shell_integrator.backup_shell_config(temp_config_file)

            expected_backup = temp_config_file.parent / f"{temp_config_file.name}.alix_backup_20230101_120000"
            assert backup_path == expected_backup
            assert backup_path.exists()

    def test_backup_shell_config_copies_content(self, shell_integrator, temp_config_file):
        """Test that backup contains original content"""
        original_content = temp_config_file.read_text()
        backup_path = shell_integrator.backup_shell_config(temp_config_file)

        backup_content = backup_path.read_text()
        assert backup_content == original_content

    @patch('shutil.copy2')
    def test_backup_shell_config_copy_failure(self, mock_copy2, shell_integrator, temp_config_file):
        """Test handling of copy failure"""
        mock_copy2.side_effect = Exception("Copy failed")

        with pytest.raises(Exception):
            shell_integrator.backup_shell_config(temp_config_file)


class TestExportAliases:
    """Test export_aliases method"""

    @pytest.mark.parametrize("shell_type,expected_format", [
        (ShellType.BASH, "alias test1='echo hello'\nalias test2='ls -la'"),
        (ShellType.ZSH, "alias test1='echo hello'\nalias test2='ls -la'"),
        (ShellType.FISH, "alias test1='echo hello'\nalias test2='ls -la'"),
        (ShellType.UNKNOWN, "alias test1='echo hello'\nalias test2='ls -la'"),
    ])
    def test_export_aliases_formats(self, shell_integrator, mock_storage, shell_type, expected_format):
        """Test exporting aliases in different shell formats"""
        aliases = [
            Alias(name="test1", command="echo hello"),
            Alias(name="test2", command="ls -la")
        ]
        mock_storage.list_all.return_value = aliases
        result = shell_integrator.export_aliases(shell_type)
        assert result == expected_format


    def test_export_aliases_fish_format(self, shell_integrator, mock_storage):
        """Test exporting aliases in fish format"""
        aliases = [Alias(name="test", command="echo fish")]
        mock_storage.list_all.return_value = aliases

        result = shell_integrator.export_aliases(ShellType.FISH)
        assert result == "alias test='echo fish'"

    def test_export_aliases_empty_list(self, shell_integrator, mock_storage):
        """Test exporting when no aliases exist"""
        mock_storage.list_all.return_value = []
        result = shell_integrator.export_aliases(ShellType.BASH)
        assert result == ""

    def test_export_aliases_with_quotes_in_command(self, shell_integrator, mock_storage):
        """Test handling commands with quotes"""
        aliases = [Alias(name="test", command="echo 'hello world'")]
        mock_storage.list_all.return_value = aliases

        result = shell_integrator.export_aliases(ShellType.BASH)
        assert result == "alias test='echo 'hello world''"



class TestPreviewAliases:
    """Test preview_aliases method"""

    def test_preview_aliases_no_target_file(self, shell_integrator):
        """Test preview when no target file provided"""
        old_alix, new_section = shell_integrator.preview_aliases(None)
        assert old_alix == ""
        assert "# === ALIX MANAGED ALIASES START ===" in new_section
        assert "# === ALIX MANAGED ALIASES END ===" in new_section

    def test_preview_aliases_with_target_file(self, shell_integrator, temp_config_file):
        """Test preview with existing config file"""
        temp_config_file.write_text("existing content\n")

        old_alix, new_section = shell_integrator.preview_aliases(temp_config_file)
        assert old_alix == ""
        assert "existing content" in new_section

    def test_preview_aliases_with_existing_alix_section(self, shell_integrator, temp_config_file):
        """Test preview when alix section already exists"""
        content = """# Some config
# === ALIX MANAGED ALIASES START ===
# old alix content
# === ALIX MANAGED ALIASES END ===
# More config
"""
        temp_config_file.write_text(content)

        old_alix, new_section = shell_integrator.preview_aliases(temp_config_file)
        assert "old alix content" in old_alix
        assert "# old alix content" not in new_section

    def test_preview_aliases_partial_markers(self, shell_integrator, temp_config_file):
        """Test handling of partial alix markers"""
        content = """# Config
# === ALIX MANAGED ALIASES START ===
incomplete section
"""
        temp_config_file.write_text(content)

        old_alix, new_section = shell_integrator.preview_aliases(temp_config_file)
        assert old_alix == ""
        # Since only start marker exists, content after it should be removed
        assert "# Config" in new_section
        assert "incomplete section" not in new_section

    def test_preview_aliases_only_end_marker(self, shell_integrator, temp_config_file):
        """Test handling when only end marker exists"""
        content = """# Config
incomplete section
# === ALIX MANAGED ALIASES END ===
# More config
"""
        temp_config_file.write_text(content)

        old_alix, new_section = shell_integrator.preview_aliases(temp_config_file)
        assert old_alix == ""
        assert "# Config" in new_section
        assert "incomplete section" not in new_section
        assert "# More config" in new_section

    @patch('alix.shell_integrator.datetime')
    def test_preview_aliases_timestamp_format(self, mock_datetime, shell_integrator):
        """Test timestamp formatting in generated section"""
        mock_now = Mock()
        mock_now.strftime.return_value = "2023-01-01 12:00:00"
        mock_datetime.now.return_value = mock_now

        _, new_section = shell_integrator.preview_aliases()
        assert "# Generated by alix on 2023-01-01 12:00:00" in new_section


class TestApplyAliases:
    """Test apply_aliases method"""

    def test_apply_aliases_no_target_file(self, shell_integrator, mock_detector):
        """Test apply_aliases when no target file found"""
        mock_detector.find_config_files.return_value = {}

        success, message = shell_integrator.apply_aliases()
        assert not success
        assert "No shell configuration file found" in message

    def test_apply_aliases_success(self, shell_integrator, temp_config_file, mock_detector):
        """Test successful alias application"""
        mock_detector.find_config_files.return_value = {".bashrc": temp_config_file}

        with patch.object(shell_integrator, 'backup_shell_config') as mock_backup:
            mock_backup.return_value = temp_config_file.parent / "backup"

            success, message = shell_integrator.apply_aliases(temp_config_file)
            assert success
            assert "Applied 2 aliases" in message
            mock_backup.assert_called_once_with(temp_config_file)

    def test_apply_aliases_with_existing_alix_section(self, shell_integrator, temp_config_file):
        """Test applying aliases when alix section already exists"""
        original_content = """# Config
# === ALIX MANAGED ALIASES START ===
# old content
# === ALIX MANAGED ALIASES END ===
# More config
"""
        temp_config_file.write_text(original_content)

        success, message = shell_integrator.apply_aliases(temp_config_file)
        assert success

        new_content = temp_config_file.read_text()
        assert "# old content" not in new_content
        assert "# === ALIX MANAGED ALIASES START ===" in new_content

    def test_apply_aliases_file_write_error(self, shell_integrator, temp_config_file):
        """Test handling of file write errors"""
        temp_config_file.chmod(0o444)

        with pytest.raises(PermissionError):
            shell_integrator.apply_aliases(temp_config_file)

    @pytest.mark.parametrize("error_type,expected_exception", [
        ("read_only", PermissionError),
        ("nonexistent", FileNotFoundError),
    ])
    def test_apply_aliases_file_errors(self, shell_integrator, temp_config_file, error_type, expected_exception):
        """Test apply_aliases with various file access errors"""
        if error_type == "read_only":
            temp_config_file.chmod(0o444)
        elif error_type == "nonexistent":
            temp_config_file.unlink()
        with pytest.raises(expected_exception):
            shell_integrator.apply_aliases(temp_config_file)

    @patch('alix.shell_integrator.datetime')
    def test_apply_aliases_timestamp_in_output(self, mock_datetime, shell_integrator, temp_config_file):
        """Test timestamp inclusion in applied aliases"""
        mock_now = Mock()
        mock_now.strftime.return_value = "2023-01-01 12:00:00"
        mock_datetime.now.return_value = mock_now

        shell_integrator.apply_aliases(temp_config_file)
        content = temp_config_file.read_text()
        assert "# Generated by alix on 2023-01-01 12:00:00" in content


class TestApplySingleAlias:
    """Test apply_single_alias method"""

    def test_apply_single_alias_no_target_file(self, shell_integrator, mock_detector):
        """Test apply_single_alias when no target file found"""
        mock_detector.find_config_files.return_value = {}
        alias = Alias(name="test", command="echo test")

        success, message = shell_integrator.apply_single_alias(alias)
        assert not success
        assert "No shell configuration file found" in message

    def test_apply_single_alias_new_section(self, shell_integrator, temp_config_file):
        """Test applying single alias creating new alix section"""
        alias = Alias(name="test", command="echo test")

        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            success, message = shell_integrator.apply_single_alias(alias)
            assert success
            assert "Applied alias 'test'" in message

            content = temp_config_file.read_text()
            assert "alias test='echo test'" in content
            assert "# === ALIX MANAGED ALIASES START ===" in content

    def test_apply_single_alias_existing_section_add(self, shell_integrator, temp_config_file):
        """Test adding alias to existing alix section"""
        original_content = """# Config
# === ALIX MANAGED ALIASES START ===
alias existing='echo existing'
# === ALIX MANAGED ALIASES END ===
"""
        temp_config_file.write_text(original_content)
        alias = Alias(name="new", command="echo new")

        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            success, message = shell_integrator.apply_single_alias(alias)
            assert success

            content = temp_config_file.read_text()
            assert "alias existing='echo existing'" in content
            assert "alias new='echo new'" in content

    def test_apply_single_alias_existing_alias_update(self, shell_integrator, temp_config_file):
        """Test that existing alias is not duplicated"""
        original_content = """# Config
# === ALIX MANAGED ALIASES START ===
alias test='echo old'
# === ALIX MANAGED ALIASES END ===
"""
        temp_config_file.write_text(original_content)
        alias = Alias(name="test", command="echo new")

        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            success, message = shell_integrator.apply_single_alias(alias)
            assert success

            content = temp_config_file.read_text()
            # Should not add duplicate
            assert content.count("alias test=") == 1
            assert "alias test='echo old'" in content

    def test_apply_single_alias_auto_reload_true(self, shell_integrator, temp_config_file):
        """Test auto_reload functionality"""
        alias = Alias(name="test", command="echo test")

        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file), \
             patch.object(shell_integrator, 'reload_shell_config') as mock_reload:
            mock_reload.return_value = True
            shell_integrator.apply_single_alias(alias)
            mock_reload.assert_called_once()

    def test_apply_single_alias_auto_reload_false(self, shell_integrator, temp_config_file):
        """Test disabling auto_reload"""
        alias = Alias(name="test", command="echo test")

        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file), \
             patch.object(shell_integrator, 'reload_shell_config') as mock_reload:
            shell_integrator.apply_single_alias(alias, auto_reload=False)
            mock_reload.assert_not_called()

    @patch('alix.shell_integrator.datetime')
    def test_apply_single_alias_timestamp(self, mock_datetime, shell_integrator, temp_config_file):
        """Test timestamp in new section creation"""
        mock_now = Mock()
        mock_now.strftime.return_value = "2023-01-01 12:00:00"
        mock_datetime.now.return_value = mock_now

        alias = Alias(name="test", command="echo test")
        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            shell_integrator.apply_single_alias(alias)

            content = temp_config_file.read_text()
            assert "# Generated by alix on 2023-01-01 12:00:00" in content


class TestReloadShellConfig:
    """Test reload_shell_config method"""

    def test_reload_shell_config_no_target_file(self, shell_integrator, mock_detector):
        """Test reload when no target file found"""
        mock_detector.find_config_files.return_value = {}

        result = shell_integrator.reload_shell_config()
        assert not result

    @patch('subprocess.run')
    def test_reload_shell_config_success(self, mock_run, shell_integrator, temp_config_file):
        """Test successful shell reload"""
        mock_process = Mock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        result = shell_integrator.reload_shell_config()
        assert result
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_reload_shell_config_failure(self, mock_run, shell_integrator, temp_config_file):
        """Test reload failure"""
        mock_process = Mock()
        mock_process.returncode = 1
        mock_run.return_value = mock_process

        result = shell_integrator.reload_shell_config()
        assert not result

    @patch('subprocess.run')
    def test_reload_shell_config_exception(self, mock_run, shell_integrator, temp_config_file):
        """Test reload with subprocess exception"""
        mock_run.side_effect = Exception("Subprocess error")

        result = shell_integrator.reload_shell_config()
        assert not result


class TestInstallCompletions:
    """Test install_completions method"""

    def test_install_completions_fish_success(self, shell_integrator):
        """Test successful fish completions installation"""
        script_content = "complete -c alix -f"

        with patch('pathlib.Path.home', return_value=Path("/tmp")), \
              patch('pathlib.Path.mkdir') as mock_mkdir, \
              patch('pathlib.Path.write_text') as mock_write:

            success, message = shell_integrator.install_completions(script_content, ShellType.FISH)
            assert success
            assert "Installed fish completions" in message

    def test_install_completions_bash_success(self, shell_integrator, temp_config_file):
        """Test successful bash completions installation"""
        script_content = "complete -F _alix alix"

        with patch('pathlib.Path.home') as mock_home, \
             patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.write_text') as mock_write:

            mock_home.return_value = Path("/home/user")
            mock_config_file = Mock()
            mock_config_file.read_text.return_value = "# Config"
            mock_config_file.write_text = Mock()

            with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
                success, message = shell_integrator.install_completions(script_content, ShellType.BASH)
                assert success
                assert "Installed bash completions" in message

    def test_install_completions_no_config_file(self, shell_integrator):
        """Test installation when no config file found"""
        with patch.object(shell_integrator, 'get_target_file', return_value=None):
            success, message = shell_integrator.install_completions("script", ShellType.BASH)
            assert not success
            assert "No shell configuration file found" in message

    def test_install_completions_existing_completion_section(self, shell_integrator, temp_config_file):
        """Test updating existing completion section"""
        original_content = """# Config
# === ALIX MANAGED COMPLETIONS START ===
# old completion
# === ALIX MANAGED COMPLETIONS END ===
"""
        temp_config_file.write_text(original_content)

        with patch('pathlib.Path.home', return_value=Path("/tmp")), \
              patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):

            success, message = shell_integrator.install_completions("source /tmp/.config/alix/completions/alix.bash", ShellType.BASH)
            assert success

            content = temp_config_file.read_text()
            assert "# old completion" not in content
            assert "source /tmp/.config/alix/completions/alix.bash" in content

    def test_install_completions_write_error(self, shell_integrator, temp_config_file):
        """Test handling of write errors"""
        temp_config_file.chmod(0o444)  # Read-only

        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            success, message = shell_integrator.install_completions("script", ShellType.BASH)
            assert not success
            assert "Failed to install completions" in message

    def test_install_completions_zsh_success(self, shell_integrator, temp_config_file):
        """Test successful zsh completions installation"""
        script_content = "# Zsh completion script"

        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            success, message = shell_integrator.install_completions(script_content, ShellType.ZSH)
            assert success
            assert "Installed zsh completions" in message

    @patch('alix.shell_integrator.datetime')
    def test_install_completions_timestamp(self, mock_datetime, shell_integrator, temp_config_file):
        """Test timestamp in completion block"""
        mock_now = Mock()
        mock_now.strftime.return_value = "2023-01-01 12:00:00"
        mock_datetime.now.return_value = mock_now

        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            shell_integrator.install_completions("script", ShellType.BASH)

            content = temp_config_file.read_text()
            assert "# Generated by alix on 2023-01-01 12:00:00" in content
    def test_export_aliases_unknown_shell_type_defaults_to_bash(self, shell_integrator, mock_storage):
        """Test that unknown shell type defaults to bash format"""
        aliases = [Alias(name="test", command="echo test")]
        mock_storage.list_all.return_value = aliases

        result = shell_integrator.export_aliases(ShellType.UNKNOWN)
        assert result == "alias test='echo test'"






    def test_install_completions_fish_directory_creation_failure(self, shell_integrator):
        """Test fish completions when directory creation fails"""
        script_content = "complete script"

        with patch('pathlib.Path.home') as mock_home, \
             patch('pathlib.Path.mkdir') as mock_mkdir:

            mock_home.return_value = Path("/home/user")
            mock_mkdir.side_effect = PermissionError("Cannot create directory")

            success, message = shell_integrator.install_completions(script_content, ShellType.FISH)
            assert not success
            assert "Failed to install completions" in message


    def test_get_target_file_unknown_shell_type(self, shell_integrator, mock_detector):
        """Test get_target_file with unknown shell type"""
        mock_detector.find_config_files.return_value = {".profile": Path("/home/user/.profile")}
        shell_integrator.shell_type = ShellType.UNKNOWN

        result = shell_integrator.get_target_file()
        assert result == Path("/home/user/.profile")  # Should return first available

    def test_export_aliases_special_characters_in_command(self, shell_integrator, mock_storage):
        """Test export_aliases with special characters in commands"""
        aliases = [Alias(name="test", command="echo 'hello $USER && ls'")]
        mock_storage.list_all.return_value = aliases

        result = shell_integrator.export_aliases(ShellType.BASH)
        expected = "alias test='echo 'hello $USER && ls''"
        assert result == expected

    def test_apply_aliases_empty_content_file(self, shell_integrator, temp_config_file):
        """Test apply_aliases with completely empty config file"""
        temp_config_file.write_text("")  # Empty file

        success, message = shell_integrator.apply_aliases(temp_config_file)
        assert success

        content = temp_config_file.read_text()
        assert "# === ALIX MANAGED ALIASES START ===" in content
        assert "# === ALIX MANAGED ALIASES END ===" in content

    def test_preview_aliases_multiple_alix_sections(self, shell_integrator, temp_config_file):
        """Test preview with multiple alix sections (should handle first one)"""
        content = """# Config
# === ALIX MANAGED ALIASES START ===
first section
# === ALIX MANAGED ALIASES END ===
# More config
# === ALIX MANAGED ALIASES START ===
second section
# === ALIX MANAGED ALIASES END ===
"""
        temp_config_file.write_text(content)

        old_alix, new_section = shell_integrator.preview_aliases(temp_config_file)
        assert "first section" in old_alix
        # Since method only handles the first section, second section should remain in the file
        assert "second section" in new_section

    def test_install_completions_partial_completion_markers(self, shell_integrator, temp_config_file):
        """Test install_completions with partial completion markers"""
        original_content = """# Config
# === ALIX MANAGED COMPLETIONS START ===
incomplete completion
"""
        temp_config_file.write_text(original_content)

        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            success, message = shell_integrator.install_completions("new script", ShellType.BASH)
            assert success

            content = temp_config_file.read_text()
            assert "incomplete completion" in content  # Should remain since markers are incomplete

    def test_backup_shell_config_nonexistent_file(self, shell_integrator):
        """Test backup_shell_config with nonexistent file"""
        nonexistent_file = Path("/tmp/nonexistent")

        with pytest.raises(FileNotFoundError):
            shell_integrator.backup_shell_config(nonexistent_file)

    def test_reload_shell_config_with_test_alias_check(self, shell_integrator, temp_config_file):
        """Test that reload_shell_config checks for test alias"""
        with patch('subprocess.run') as mock_run, \
             patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            mock_process = Mock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            result = shell_integrator.reload_shell_config()
            assert result

            # Verify the command structure matches actual implementation
            call_args = mock_run.call_args
            args, kwargs = call_args
            command = args[0] if args else kwargs.get('args', [])
            assert command == ["bash", "-c", f"source {temp_config_file}"]

    def test_apply_single_alias_whitespace_handling(self, shell_integrator, temp_config_file):
        """Test apply_single_alias with trailing whitespace in config"""
        original_content = "# Config\n    \n\t\n"  # Only whitespace
        temp_config_file.write_text(original_content)

        alias = Alias(name="test", command="echo test")
        with patch.object(shell_integrator, 'get_target_file', return_value=temp_config_file):
            success, message = shell_integrator.apply_single_alias(alias)
            assert success

            content = temp_config_file.read_text()
            # Should strip trailing whitespace before appending
            assert content.startswith("# Config")
            assert "# === ALIX MANAGED ALIASES START ===" in content