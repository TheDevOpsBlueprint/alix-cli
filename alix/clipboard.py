import subprocess
import platform
from abc import ABC, abstractmethod

try:
    import pyperclip
except ImportError:
    pyperclip = None


# Backend Interface
class ClipboardBackend(ABC):
    @abstractmethod
    def copy(self, text: str) -> bool:
        """Copy text to clipboard. Return True on success or False otherwise."""
        ...


# pyperclip backend
class PyperclipBackend(ClipboardBackend):
    def copy(self, text: str) -> bool:
        if pyperclip is None:
            return False
        try:
            pyperclip.copy(text)
            return True
        except pyperclip.PyperclipException:
            return False


# macos backend
class MacOSBackend(ClipboardBackend):
    def copy(self, text: str) -> bool:
        if platform.system() != "Darwin":
            return False
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return p.returncode == 0
        except Exception:
            return False


# windows backend
class WindowsBackend(ClipboardBackend):
    def copy(self, text: str) -> bool:
        if platform.system() != "Windows":
            return False
        try:
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
            p.communicate(text.encode("utf-8"))
            return p.returncode == 0
        except Exception:
            return False


# linux backend
class LinuxBackend(ClipboardBackend):
    def copy(self, text: str) -> bool:
        if platform.system() != "Linux":
            return False
        try:
            # Try xclip first, then xsel
            for cmd in [
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
            ]:
                try:
                    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                    p.communicate(text.encode("utf-8"))
                    if p.returncode == 0:
                        return True
                except FileNotFoundError:
                    continue
            return False
        except Exception:
            return False


# fallback
class FallbackBackend(ClipboardBackend):
    def copy(self, text: str) -> bool:
        return False


# Clipboard Manager
class ClipboardManager:
    def __init__(self):
        self.backends = [
            PyperclipBackend(),
            MacOSBackend(),
            WindowsBackend(),
            LinuxBackend(),
            FallbackBackend(),
        ]

    def copy(self, text: str) -> bool:
        for backend in self.backends:
            if backend.copy(text):
                return True
        return False
