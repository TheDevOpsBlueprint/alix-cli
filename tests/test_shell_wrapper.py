"""Tests for shell wrapper functionality"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from alix.shell_wrapper import ShellWrapper


class TestShellWrapper:
    """Test ShellWrapper functionality"""

    def test_generate_tracking_function_nonexistent_alias(self):
        """Test generate_tracking_function with non-existent alias"""
        wrapper = ShellWrapper()

        # Mock storage to return None for non-existent alias
        wrapper.storage.get = Mock(return_value=None)

        result = wrapper.generate_tracking_function("nonexistent")

        # Should return empty string for non-existent alias
        assert result == ""

    def test_generate_shell_integration_script_unsupported_shell(self):
        """Test generate_shell_integration_script with unsupported shell"""
        wrapper = ShellWrapper()

        result = wrapper.generate_shell_integration_script("unsupported_shell")

        # Should default to bash integration for unsupported shells
        assert "#!/bin/bash" in result
        assert "Alix CLI Usage Tracking Integration" in result

    def test_generate_zsh_integration(self):
        """Test _generate_zsh_integration method"""
        wrapper = ShellWrapper()

        # Mock storage to return some aliases
        mock_alias = Mock()
        mock_alias.name = "test_alias"
        mock_alias.command = "echo hello"
        wrapper.storage.list_all = Mock(return_value=[mock_alias])
        wrapper.storage.get = Mock(return_value=mock_alias)

        result = wrapper._generate_zsh_integration()

        assert "#!/bin/zsh" in result
        assert "Alix CLI Usage Tracking Integration for Zsh" in result
        # The function name should be in the generated script
        assert "test_alias" in result
        assert "echo hello" in result

    def test_generate_fish_integration(self):
        """Test _generate_fish_integration method"""
        wrapper = ShellWrapper()

        # Mock storage to return some aliases
        mock_alias = Mock()
        mock_alias.name = "test_alias"
        mock_alias.command = "echo hello"
        wrapper.storage.list_all = Mock(return_value=[mock_alias])

        result = wrapper._generate_fish_integration()

        assert "Alix CLI Usage Tracking Integration for Fish" in result
        assert "function test_alias" in result
        assert "echo hello" in result
        assert "end" in result

    def test_install_tracking_integration(self):
        """Test install_tracking_integration method"""
        wrapper = ShellWrapper()

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".bashrc"

            # Mock storage to return some aliases
            mock_alias = Mock()
            mock_alias.name = "test_alias"
            mock_alias.command = "echo hello"
            wrapper.storage.list_all = Mock(return_value=[mock_alias])
            wrapper.storage.get = Mock(return_value=mock_alias)

            result = wrapper.install_tracking_integration(config_path, "bash")

            assert result is True
            assert config_path.exists()

            # Check that integration was added to config
            content = config_path.read_text()
            assert "Alix CLI Usage Tracking Integration" in content
            # The function name should be in the generated script
            assert "test_alias" in content

    @patch("alix.storage.Path.mkdir")
    def test_install_tracking_integration_failure(self, mock_mkdir):
        """Test install_tracking_integration method failure"""
        wrapper = ShellWrapper()

        # Use a path that will cause failure (non-existent directory)
        config_path = Path("/nonexistent/directory/.bashrc")

        result = wrapper.install_tracking_integration(config_path, "bash")

        assert result is False

    def test_generate_shell_integration_script_zsh(self):
        """Test generate_shell_integration_script with zsh shell (line 58)"""
        wrapper = ShellWrapper()

        result = wrapper.generate_shell_integration_script("zsh")

        assert "#!/bin/zsh" in result
        assert "Alix CLI Usage Tracking Integration for Zsh" in result

    def test_generate_shell_integration_script_fish(self):
        """Test generate_shell_integration_script with fish shell (line 60)"""
        wrapper = ShellWrapper()

        result = wrapper.generate_shell_integration_script("fish")

        assert "Alix CLI Usage Tracking Integration for Fish" in result
        # Since there are no aliases, no functions are generated
        assert 'echo "Alix usage tracking enabled for 0 aliases"' in result

    @patch("alix.shell_wrapper.os.chmod")
    def test_create_standalone_tracking_script_directory_creation(self, mock_chmod):
        """Test create_standalone_tracking_script directory creation"""
        wrapper = ShellWrapper()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a nested path that doesn't exist
            output_path = Path(temp_dir) / "subdir" / "nested" / "tracking.sh"

            # Mock storage to return some aliases
            mock_alias = Mock()
            mock_alias.name = "test_alias"
            mock_alias.command = "echo hello"
            wrapper.storage.list_all = Mock(return_value=[mock_alias])
            wrapper.storage.get = Mock(return_value=mock_alias)

            result = wrapper.create_standalone_tracking_script(output_path, "bash")

            assert result is True
            # Verify that chmod was called to make it executable
            mock_chmod.assert_called_once_with(output_path, 0o755)

    def test_create_standalone_tracking_script_exception_handling(self):
        """Test create_standalone_tracking_script exception handling"""
        wrapper = ShellWrapper()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "tracking.sh"

            # Mock storage to return some aliases
            mock_alias = Mock()
            mock_alias.name = "test_alias"
            mock_alias.command = "echo hello"
            wrapper.storage.list_all = Mock(return_value=[mock_alias])

            # Mock open to raise exception
            with patch("alix.shell_wrapper.open", side_effect=Exception("File write error")):
                result = wrapper.create_standalone_tracking_script(output_path, "bash")

            assert result is False
