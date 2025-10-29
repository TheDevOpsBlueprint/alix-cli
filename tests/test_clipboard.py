import subprocess
from unittest.mock import patch, MagicMock
from alix.clipboard import (
    ClipboardManager,
    PyperclipBackend,
    MacOSBackend,
    WindowsBackend,
    LinuxBackend,
    FallbackBackend,
)


class TestPyperclipBackend:
    def test_copy_pyperclip_none(self):
        with patch('alix.clipboard.pyperclip', None):
            backend = PyperclipBackend()
            assert backend.copy("test") == False

    def test_copy_success(self):
        with patch('alix.clipboard.pyperclip') as mock_pyperclip:
            mock_pyperclip.copy = MagicMock()
            backend = PyperclipBackend()
            assert backend.copy("test") == True
            mock_pyperclip.copy.assert_called_once_with("test")

    def test_copy_exception(self):
        with patch('alix.clipboard.pyperclip') as mock_pyperclip:
            mock_pyperclip.copy = MagicMock(side_effect=Exception("test exception"))
            mock_pyperclip.PyperclipException = Exception
            backend = PyperclipBackend()
            assert backend.copy("test") == False


class TestMacOSBackend:
    def test_copy_wrong_platform(self):
        with patch('alix.clipboard.platform.system', return_value="Linux"):
            backend = MacOSBackend()
            assert backend.copy("test") == False

    def test_copy_success(self):
        with patch('alix.clipboard.platform.system', return_value="Darwin"), \
             patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            backend = MacOSBackend()
            assert backend.copy("test") == True
            mock_popen.assert_called_once_with(["pbcopy"], stdin=subprocess.PIPE)
            mock_process.communicate.assert_called_once_with(b"test")

    def test_copy_exception(self):
        with patch('alix.clipboard.platform.system', return_value="Darwin"), \
             patch('alix.clipboard.subprocess.Popen', side_effect=Exception):
            backend = MacOSBackend()
            assert backend.copy("test") == False


class TestWindowsBackend:
    def test_copy_wrong_platform(self):
        with patch('alix.clipboard.platform.system', return_value="Linux"):
            backend = WindowsBackend()
            assert backend.copy("test") == False

    def test_copy_success(self):
        with patch('alix.clipboard.platform.system', return_value="Windows"), \
             patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            backend = WindowsBackend()
            assert backend.copy("test") == True
            mock_popen.assert_called_once_with(["clip"], stdin=subprocess.PIPE, shell=True)
            mock_process.communicate.assert_called_once_with(b"test")

    def test_copy_exception(self):
        with patch('alix.clipboard.platform.system', return_value="Windows"), \
             patch('alix.clipboard.subprocess.Popen', side_effect=Exception):
            backend = WindowsBackend()
            assert backend.copy("test") == False


class TestLinuxBackend:
    def test_copy_wrong_platform(self):
        with patch('alix.clipboard.platform.system', return_value="Darwin"):
            backend = LinuxBackend()
            assert backend.copy("test") == False

    def test_copy_xclip_success(self):
        with patch('alix.clipboard.platform.system', return_value="Linux"), \
             patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            backend = LinuxBackend()
            assert backend.copy("test") == True
            mock_popen.assert_called_once_with(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            mock_process.communicate.assert_called_once_with(b"test")

    def test_copy_xclip_filenotfound_xsel_success(self):
        with patch('alix.clipboard.platform.system', return_value="Linux"), \
             patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 0
            # First call raises FileNotFoundError, second succeeds
            mock_popen.side_effect = [FileNotFoundError, mock_process]
            backend = LinuxBackend()
            assert backend.copy("test") == True
            assert mock_popen.call_count == 2
            mock_process.communicate.assert_called_once_with(b"test")

    def test_copy_both_filenotfound(self):
        with patch('alix.clipboard.platform.system', return_value="Linux"), \
              patch('alix.clipboard.subprocess.Popen', side_effect=FileNotFoundError):
            backend = LinuxBackend()
            assert backend.copy("test") == False

    def test_copy_xclip_nonzero_xsel_success(self):
        with patch('alix.clipboard.platform.system', return_value="Linux"), \
              patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process1 = MagicMock()
            mock_process1.returncode = 1
            mock_process2 = MagicMock()
            mock_process2.returncode = 0
            mock_popen.side_effect = [mock_process1, mock_process2]
            backend = LinuxBackend()
            assert backend.copy("test") == True
            assert mock_popen.call_count == 2
            mock_process1.communicate.assert_called_once_with(b"test")
            mock_process2.communicate.assert_called_once_with(b"test")

    def test_copy_other_exception(self):
        with patch('alix.clipboard.platform.system', return_value="Linux"), \
             patch('alix.clipboard.subprocess.Popen', side_effect=Exception):
            backend = LinuxBackend()
            assert backend.copy("test") == False


class TestFallbackBackend:
    def test_copy(self):
        backend = FallbackBackend()
        assert backend.copy("test") == False


class TestClipboardManager:
    def test_init(self):
        manager = ClipboardManager()
        assert len(manager.backends) == 5
        assert isinstance(manager.backends[0], PyperclipBackend)
        assert isinstance(manager.backends[1], MacOSBackend)
        assert isinstance(manager.backends[2], WindowsBackend)
        assert isinstance(manager.backends[3], LinuxBackend)
        assert isinstance(manager.backends[4], FallbackBackend)

    def test_copy_first_backend_success(self):
        manager = ClipboardManager()
        with patch.object(manager.backends[0], 'copy', return_value=True):
            assert manager.copy("test") == True

    def test_copy_multiple_fail_then_success(self):
        manager = ClipboardManager()
        with patch.object(manager.backends[0], 'copy', return_value=False), \
             patch.object(manager.backends[1], 'copy', return_value=False), \
             patch.object(manager.backends[2], 'copy', return_value=True):
            assert manager.copy("test") == True

    def test_copy_all_fail(self):
        manager = ClipboardManager()
        for backend in manager.backends:
            with patch.object(backend, 'copy', return_value=False):
                pass
        assert manager.copy("test") == False

    def test_copy_empty_string(self):
        manager = ClipboardManager()
        with patch.object(manager.backends[0], 'copy', return_value=True):
            assert manager.copy("") == True

    def test_copy_very_long_string(self):
        manager = ClipboardManager()
        long_text = "a" * (1024 * 1024 + 1)  # >1MB
        with patch.object(manager.backends[0], 'copy', return_value=True):
            assert manager.copy(long_text) == True

    def test_copy_string_with_null_bytes(self):
        manager = ClipboardManager()
        text_with_null = "test\x00test"
        with patch.object(manager.backends[0], 'copy', return_value=True):
            assert manager.copy(text_with_null) == True

    def test_copy_invalid_unicode_surrogates(self):
        manager = ClipboardManager()
        text_with_surrogate = "test\ud800test"
        with patch.object(manager.backends[0], 'copy', return_value=True):
            assert manager.copy(text_with_surrogate) == True

    def test_copy_non_string_none(self):
        manager = ClipboardManager()
        # Non-string inputs are accepted and return False
        assert manager.copy(None) == False

    def test_copy_non_string_int(self):
        manager = ClipboardManager()
        # Non-string inputs are accepted and return False
        assert manager.copy(123) == False

    def test_copy_special_characters(self):
        manager = ClipboardManager()
        text_with_special = "test\n\t\r"
        with patch.object(manager.backends[0], 'copy', return_value=True):
            assert manager.copy(text_with_special) == True

    def test_copy_unexpected_platform_case_variants(self):
        # Test MacOS with lowercase
        with patch('alix.clipboard.platform.system', return_value="darwin"), \
             patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            backend = MacOSBackend()
            assert backend.copy("test") == False  # Should fail because it's case sensitive

        # Test Windows with lowercase
        with patch('alix.clipboard.platform.system', return_value="windows"), \
             patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            backend = WindowsBackend()
            assert backend.copy("test") == False

        # Test Linux with lowercase
        with patch('alix.clipboard.platform.system', return_value="linux"), \
             patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            backend = LinuxBackend()
            assert backend.copy("test") == False

    def test_copy_subprocess_oserror_permission_denied(self):
        with patch('alix.clipboard.platform.system', return_value="Darwin"), \
             patch('alix.clipboard.subprocess.Popen', side_effect=OSError("Permission denied")):
            backend = MacOSBackend()
            assert backend.copy("test") == False

    def test_copy_communication_broken_pipe_error(self):
        with patch('alix.clipboard.platform.system', return_value="Darwin"), \
             patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.side_effect = BrokenPipeError("Broken pipe")
            mock_popen.return_value = mock_process
            backend = MacOSBackend()
            assert backend.copy("test") == False

    def test_copy_non_zero_return_code_with_potential_success(self):
        # For MacOS, non-zero return code should fail
        with patch('alix.clipboard.platform.system', return_value="Darwin"), \
             patch('alix.clipboard.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_popen.return_value = mock_process
            backend = MacOSBackend()
            assert backend.copy("test") == False

    def test_copy_pyperclip_specific_exception(self):
        with patch('alix.clipboard.pyperclip') as mock_pyperclip:
            mock_pyperclip.PyperclipException = Exception
            mock_pyperclip.copy = MagicMock(side_effect=mock_pyperclip.PyperclipException("specific error"))
            backend = PyperclipBackend()
            assert backend.copy("test") == False

    def test_copy_all_backends_failure(self):
        manager = ClipboardManager()
        # All backends fail
        with patch.object(manager.backends[0], 'copy', return_value=False), \
             patch.object(manager.backends[1], 'copy', return_value=False), \
             patch.object(manager.backends[2], 'copy', return_value=False), \
             patch.object(manager.backends[3], 'copy', return_value=False), \
             patch.object(manager.backends[4], 'copy', return_value=False):
            assert manager.copy("test") == False