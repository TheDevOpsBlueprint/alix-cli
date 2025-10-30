"""Tests for clipboard functionality"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
import sys
import importlib

from alix.clipboard import (
    ClipboardManager,
    FallbackBackend,
    LinuxBackend,
    MacOSBackend,
    PyperclipBackend,
    WindowsBackend,
)


def test_pyperclip_import_failure():
    """Test behavior when pyperclip import fails"""

    # Save original pyperclip
    original_pyperclip = sys.modules.get('pyperclip')

    # Remove pyperclip from sys.modules to simulate import failure
    if 'pyperclip' in sys.modules:
        del sys.modules['pyperclip']

    # Mock __import__ to raise ImportError for pyperclip
    original_import = __builtins__['__import__']

    def mock_import(name, *args, **kwargs):
        if name == 'pyperclip':
            raise ImportError("No module named 'pyperclip'")
        return original_import(name, *args, **kwargs)

    __builtins__['__import__'] = mock_import

    try:
        # Reload the clipboard module
        if 'alix.clipboard' in sys.modules:
            importlib.reload(sys.modules['alix.clipboard'])

        # Import after reload
        from alix import clipboard
        assert clipboard.pyperclip is None

        # Test that PyperclipBackend handles None correctly
        backend = clipboard.PyperclipBackend()
        result = backend.copy("test")
        assert result is False

    finally:
        # Restore original state
        __builtins__['__import__'] = original_import
        if original_pyperclip:
            sys.modules['pyperclip'] = original_pyperclip
        # Reload to restore normal state
        importlib.reload(sys.modules['alix.clipboard'])


class TestPyperclipBackend:
    """Test PyperclipBackend functionality"""

    def test_copy_pyperclip_none(self):
        """Test copy when pyperclip is None"""
        with patch("alix.clipboard.pyperclip", None):
            backend = PyperclipBackend()
            result = backend.copy("test text")
            assert result is False

    def test_copy_success(self):
        """Test successful copy with pyperclip"""
        mock_pyperclip = MagicMock()
        with patch("alix.clipboard.pyperclip", mock_pyperclip):
            backend = PyperclipBackend()
            result = backend.copy("test text")
            mock_pyperclip.copy.assert_called_once_with("test text")
            assert result is True

    def test_copy_pyperclip_exception(self):
        """Test copy when pyperclip raises PyperclipException"""
        class MockPyperclipException(Exception):
            pass

        mock_pyperclip = MagicMock()
        mock_pyperclip.copy.side_effect = MockPyperclipException("error")
        mock_pyperclip.PyperclipException = MockPyperclipException
        with patch("alix.clipboard.pyperclip", mock_pyperclip):
            backend = PyperclipBackend()
            result = backend.copy("test text")
            assert result is False


class TestMacOSBackend:
    """Test MacOSBackend functionality"""

    def test_copy_wrong_platform(self):
        """Test copy on non-Darwin platform"""
        with patch("alix.clipboard.platform.system", return_value="Linux"):
            backend = MacOSBackend()
            result = backend.copy("test text")
            assert result is False

    def test_copy_success(self):
        """Test successful copy on macOS"""
        mock_process = MagicMock()
        mock_process.returncode = 0
        with patch("alix.clipboard.platform.system", return_value="Darwin"), \
             patch("alix.clipboard.subprocess.Popen", return_value=mock_process):
            backend = MacOSBackend()
            result = backend.copy("test text")
            assert result is True
            mock_process.communicate.assert_called_once_with(b"test text")

    def test_copy_subprocess_exception(self):
        """Test copy when subprocess raises exception"""
        with patch("alix.clipboard.platform.system", return_value="Darwin"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=Exception("error")):
            backend = MacOSBackend()
            result = backend.copy("test text")
            assert result is False


class TestWindowsBackend:
    """Test WindowsBackend functionality"""

    def test_copy_wrong_platform(self):
        """Test copy on non-Windows platform"""
        with patch("alix.clipboard.platform.system", return_value="Linux"):
            backend = WindowsBackend()
            result = backend.copy("test text")
            assert result is False

    def test_copy_success(self):
        """Test successful copy on Windows"""
        mock_process = MagicMock()
        mock_process.returncode = 0
        with patch("alix.clipboard.platform.system", return_value="Windows"), \
             patch("alix.clipboard.subprocess.Popen", return_value=mock_process):
            backend = WindowsBackend()
            result = backend.copy("test text")
            assert result is True
            mock_process.communicate.assert_called_once_with(b"test text")

    def test_copy_subprocess_exception(self):
        """Test copy when subprocess raises exception"""
        with patch("alix.clipboard.platform.system", return_value="Windows"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=Exception("error")):
            backend = WindowsBackend()
            result = backend.copy("test text")
            assert result is False


class TestLinuxBackend:
    """Test LinuxBackend functionality"""

    def test_copy_wrong_platform(self):
        """Test copy on non-Linux platform"""
        with patch("alix.clipboard.platform.system", return_value="Darwin"):
            backend = LinuxBackend()
            result = backend.copy("test text")
            assert result is False

    def test_copy_success_first_command(self):
        """Test successful copy with first command (xclip)"""
        mock_process = MagicMock()
        mock_process.returncode = 0
        with patch("alix.clipboard.platform.system", return_value="Linux"), \
             patch("alix.clipboard.subprocess.Popen", return_value=mock_process) as mock_popen:
            backend = LinuxBackend()
            result = backend.copy("test text")
            assert result is True
            # Should call xclip first
            mock_popen.assert_called_with(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)

    def test_copy_success_second_command(self):
        """Test successful copy with second command (xsel) after first fails"""
        mock_process = MagicMock()
        mock_process.returncode = 0
        with patch("alix.clipboard.platform.system", return_value="Linux"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=[FileNotFoundError, mock_process]) as mock_popen:
            backend = LinuxBackend()
            result = backend.copy("test text")
            assert result is True
            # Should call xsel after xclip fails
            calls = mock_popen.call_args_list
            assert len(calls) == 2
            assert calls[1][0][0] == ["xsel", "--clipboard", "--input"]

    def test_copy_all_commands_fail(self):
        """Test copy when all commands fail with FileNotFoundError"""
        with patch("alix.clipboard.platform.system", return_value="Linux"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=FileNotFoundError):
            backend = LinuxBackend()
            result = backend.copy("test text")
            assert result is False

    def test_copy_outer_exception(self):
        """Test copy when outer exception occurs"""
        with patch("alix.clipboard.platform.system", return_value="Linux"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=Exception("outer error")):
            backend = LinuxBackend()
            result = backend.copy("test text")
            assert result is False

    def test_copy_success_after_first_fails_with_returncode(self):
        """Test successful copy with second command after first fails with nonzero returncode"""
        mock_process1 = MagicMock()
        mock_process1.returncode = 1
        mock_process2 = MagicMock()
        mock_process2.returncode = 0
        with patch("alix.clipboard.platform.system", return_value="Linux"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=[mock_process1, mock_process2]) as mock_popen:
            backend = LinuxBackend()
            result = backend.copy("test text")
            assert result is True
            # Verify calls
            calls = mock_popen.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == ["xclip", "-selection", "clipboard"]
            assert calls[1][0][0] == ["xsel", "--clipboard", "--input"]

class TestFallbackBackend:
    """Test FallbackBackend functionality"""

    def test_copy_always_false(self):
        """Test that copy always returns False"""
        backend = FallbackBackend()
        result = backend.copy("test text")
        assert result is False


class TestClipboardManager:
    """Test ClipboardManager functionality"""

    def test_init(self):
        """Test ClipboardManager initialization"""
        from alix.clipboard import ClipboardManager, PyperclipBackend, MacOSBackend, WindowsBackend, LinuxBackend, FallbackBackend
        manager = ClipboardManager()
        assert len(manager.backends) == 5
        assert isinstance(manager.backends[0], PyperclipBackend)
        assert isinstance(manager.backends[1], MacOSBackend)
        assert isinstance(manager.backends[2], WindowsBackend)
        assert isinstance(manager.backends[3], LinuxBackend)
        assert isinstance(manager.backends[4], FallbackBackend)

    def test_copy_success_first_backend(self):
        """Test copy when first backend succeeds"""
        manager = ClipboardManager()
        with patch.object(manager.backends[0], "copy", return_value=True):
            result = manager.copy("test text")
            assert result is True

    def test_copy_all_backends_fail(self):
        """Test copy when all backends fail"""
        manager = ClipboardManager()
        for backend in manager.backends:
            with patch.object(backend, "copy", return_value=False):
                pass
        # Patch all backends to return False
        with patch.object(manager.backends[0], "copy", return_value=False), \
             patch.object(manager.backends[1], "copy", return_value=False), \
             patch.object(manager.backends[2], "copy", return_value=False), \
             patch.object(manager.backends[3], "copy", return_value=False), \
             patch.object(manager.backends[4], "copy", return_value=False):
            result = manager.copy("test text")
            assert result is False


class TestInputValidation:
    """Test input validation edge cases"""

    def test_copy_none_input(self):
        """Test copy with None input"""
        manager = ClipboardManager()
        with patch("alix.clipboard.pyperclip", None), \
             patch("alix.clipboard.platform.system", return_value="Linux"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=Exception("mock")):
            # Since backends fail, but no exception raised for input type
            result = manager.copy(None)
            assert result is False  # Should not crash, just return False

    def test_copy_int_input(self):
        """Test copy with int input"""
        manager = ClipboardManager()
        with patch("alix.clipboard.pyperclip", None), \
             patch("alix.clipboard.platform.system", return_value="Linux"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=Exception("mock")):
            result = manager.copy(123)
            assert result is False

    def test_copy_list_input(self):
        """Test copy with list input"""
        manager = ClipboardManager()
        with patch("alix.clipboard.pyperclip", None), \
             patch("alix.clipboard.platform.system", return_value="Linux"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=Exception("mock")):
            result = manager.copy([1, 2, 3])
            assert result is False

    def test_copy_dict_input(self):
        """Test copy with dict input"""
        manager = ClipboardManager()
        with patch("alix.clipboard.pyperclip", None), \
             patch("alix.clipboard.platform.system", return_value="Linux"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=Exception("mock")):
            result = manager.copy({"key": "value"})
            assert result is False

    def test_copy_empty_string(self):
        """Test copy with empty string"""
        manager = ClipboardManager()
        with patch.object(manager.backends[0], "copy", return_value=True):
            result = manager.copy("")
            assert result is True

    def test_copy_very_large_string(self):
        """Test copy with very large string"""
        large_text = "a" * 1000000  # 1MB string
        manager = ClipboardManager()
        with patch.object(manager.backends[0], "copy", return_value=True):
            result = manager.copy(large_text)
            assert result is True

    def test_copy_string_with_null_bytes(self):
        """Test copy with string containing null bytes"""
        text_with_null = "test\x00string"
        manager = ClipboardManager()
        with patch.object(manager.backends[0], "copy", return_value=True):
            result = manager.copy(text_with_null)
            assert result is True


class TestEncoding:
    """Test encoding and Unicode edge cases"""

    def test_copy_emojis(self):
        """Test copy with emojis"""
        emoji_text = "Hello 🌍 😀"
        manager = ClipboardManager()
        with patch.object(manager.backends[0], "copy", return_value=True):
            result = manager.copy(emoji_text)
            assert result is True

    def test_copy_non_ascii_characters(self):
        """Test copy with non-ASCII characters"""
        non_ascii_text = "café résumé naïve"
        manager = ClipboardManager()
        with patch.object(manager.backends[0], "copy", return_value=True):
            result = manager.copy(non_ascii_text)
            assert result is True

    def test_copy_right_to_left_text(self):
        """Test copy with right-to-left text"""
        rtl_text = "مرحبا بالعالم"  # Arabic
        manager = ClipboardManager()
        with patch.object(manager.backends[0], "copy", return_value=True):
            result = manager.copy(rtl_text)
            assert result is True

    def test_copy_surrogate_pairs(self):
        """Test copy with surrogate pairs (e.g., emojis with combining)"""
        surrogate_text = "👨‍👩‍👧‍👦"  # Family emoji
        manager = ClipboardManager()
        with patch.object(manager.backends[0], "copy", return_value=True):
            result = manager.copy(surrogate_text)
            assert result is True


class TestSubprocessEdgeCases:
    """Test subprocess edge cases"""

    def test_copy_timeout_scenario(self):
        """Test copy with subprocess timeout"""
        # For backends that use subprocess, mock communicate to raise TimeoutExpired
        from subprocess import TimeoutExpired
        mock_process = MagicMock()
        mock_process.communicate.side_effect = TimeoutExpired("timeout", 5)
        with patch("alix.clipboard.platform.system", return_value="Darwin"), \
             patch("alix.clipboard.subprocess.Popen", return_value=mock_process):
            backend = MacOSBackend()
            result = backend.copy("test text")
            assert result is False

    def test_copy_signal_interruption(self):
        """Test copy with signal interruption (KeyboardInterrupt)"""
        with patch("alix.clipboard.platform.system", return_value="Darwin"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=KeyboardInterrupt):
            backend = MacOSBackend()
            with pytest.raises(KeyboardInterrupt):
                backend.copy("test text")

    def test_copy_large_input_handling(self):
        """Test copy with large input in subprocess"""
        large_text = "a" * 100000  # Large input
        mock_process = MagicMock()
        mock_process.returncode = 0
        with patch("alix.clipboard.platform.system", return_value="Darwin"), \
             patch("alix.clipboard.subprocess.Popen", return_value=mock_process):
            backend = MacOSBackend()
            result = backend.copy(large_text)
            assert result is True
            mock_process.communicate.assert_called_once_with(large_text.encode("utf-8"))


class TestPlatformDetection:
    """Test platform detection edge cases"""

    def test_unknown_platform(self):
        """Test with unknown platform"""
        with patch("alix.clipboard.platform.system", return_value="UnknownOS"):
            backend = MacOSBackend()
            result = backend.copy("test text")
            assert result is False

    def test_case_sensitivity_platform_names(self):
        """Test case sensitivity in platform names"""
        # Darwin vs darwin
        with patch("alix.clipboard.platform.system", return_value="darwin"):  # lowercase
            backend = MacOSBackend()
            result = backend.copy("test text")
            assert result is False  # Should be case sensitive, assuming platform.system returns "Darwin"

        with patch("alix.clipboard.platform.system", return_value="DARWIN"):  # uppercase
            backend = MacOSBackend()
            result = backend.copy("test text")
            assert result is False


class TestExceptionHandling:
    """Test specific exception handling"""

    def test_copy_oserror(self):
        """Test copy with OSError"""
        with patch("alix.clipboard.platform.system", return_value="Darwin"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=OSError("OS error")):
            backend = MacOSBackend()
            result = backend.copy("test text")
            assert result is False

    def test_copy_permission_error(self):
        """Test copy with PermissionError"""
        with patch("alix.clipboard.platform.system", return_value="Darwin"), \
             patch("alix.clipboard.subprocess.Popen", side_effect=PermissionError("Permission denied")):
            backend = MacOSBackend()
            result = backend.copy("test text")
            assert result is False

    def test_copy_encoding_error(self):
        """Test copy with encoding error"""
        with patch("alix.clipboard.platform.system", return_value="Darwin"):
            with patch("alix.clipboard.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.returncode = 0
                mock_popen.return_value = mock_process
                # Make communicate raise UnicodeEncodeError
                mock_process.communicate.side_effect = UnicodeEncodeError("utf-8", "test", 0, 1, "error")
                backend = MacOSBackend()
                result = backend.copy("test")
                assert result is False