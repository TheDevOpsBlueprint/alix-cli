"""Shell detection and configuration file handling"""

import os
import sys
import subprocess
import pwd
from pathlib import Path
from typing import Optional, Dict
from enum import Enum


class ShellType(Enum):
    """Supported shell types"""

    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    SH = "sh"
    UNKNOWN = "unknown"


class ShellDetector:
    """Detect shell type and configuration files"""

    # Common config file patterns
    CONFIG_FILES = {
        ShellType.BASH: [".bashrc", ".bash_profile", ".bash_aliases", ".profile"],
        ShellType.ZSH: [".zshrc", ".zshenv", ".zprofile", ".zsh_aliases"],
        ShellType.FISH: [".config/fish/config.fish", ".config/fish/functions"],
        ShellType.SH: [".profile", ".shinit"],
    }

    def __init__(self, home_dir: Optional[Path] = None):
        """Initialize detector with home directory"""
        self.home_dir = home_dir or Path.home()

    def detect_current_shell(self) -> ShellType:
        """Detect the current shell from environment with improved macOS support"""
        # Method 1: Try SHELL environment variable (most reliable when set)
        shell_env = os.environ.get("SHELL", "").lower()
        if shell_env:
            if "zsh" in shell_env:
                return ShellType.ZSH
            elif "bash" in shell_env:
                return ShellType.BASH
            elif "fish" in shell_env:
                return ShellType.FISH
            elif (
                "sh" in shell_env and "bash" not in shell_env and "zsh" not in shell_env
            ):
                return ShellType.SH

        # Method 2: Check /etc/passwd for user's default shell (reliable fallback)
        try:
            user_shell = pwd.getpwuid(os.getuid()).pw_shell.lower()
            if "zsh" in user_shell:
                return ShellType.ZSH
            elif "bash" in user_shell:
                return ShellType.BASH
            elif "fish" in user_shell:
                return ShellType.FISH
            elif user_shell.endswith("/sh"):
                return ShellType.SH
        except (ImportError, KeyError, AttributeError, OSError, PermissionError, RuntimeError, ValueError):
            pass

        # Method 3: macOS-specific detection using dscl (Directory Service Command Line)
        if sys.platform == "darwin":
            try:
                result = subprocess.run(
                    [
                        "dscl",
                        ".",
                        "-read",
                        f"/Users/{os.getenv('USER', '')}",
                        "UserShell",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout:
                    for line in result.stdout.splitlines():
                        if line.startswith("UserShell:"):
                            parts = line.split(":", 1)
                            if len(parts) == 2:
                                shell_path = parts[1].strip().lower()
                                if not shell_path:
                                    return ShellType.UNKNOWN
                                if "zsh" in shell_path:
                                    return ShellType.ZSH
                                elif "bash" in shell_path:
                                    return ShellType.BASH
                                elif "fish" in shell_path:
                                    return ShellType.FISH
                                elif shell_path.endswith("sh"):
                                    return ShellType.SH
                            return ShellType.UNKNOWN
            except (
                subprocess.TimeoutExpired,
                subprocess.CalledProcessError,
                FileNotFoundError,
                OSError,
                PermissionError,
                RuntimeError,
                ValueError,
                Exception,
            ):
                pass

        # Method 4: Check for shell-specific environment variables
        if os.environ.get("ZSH_NAME") or os.environ.get("ZSH_VERSION"):
            return ShellType.ZSH
        elif os.environ.get("BASH_VERSION"):
            return ShellType.BASH

        # Method 5: Try parent process (fallback)
        if sys.platform == "win32":
            return ShellType.UNKNOWN

        try:
            import psutil

            parent = psutil.Process(os.getppid())
            parent_name = parent.name().lower()

            # More specific matching for shell processes
            if parent_name in ["zsh", "-zsh"]:
                return ShellType.ZSH
            elif parent_name in ["bash", "-bash"]:
                return ShellType.BASH
            elif parent_name in ["fish", "-fish"]:
                return ShellType.FISH
            elif parent_name in ["sh", "-sh"]:
                return ShellType.SH
        except (ImportError, Exception):
            pass

        # Method 6: Check for existence of shell-specific config files as a hint
        shell_hints = self._get_shell_hints_from_configs()
        if shell_hints:
            return shell_hints

        # Method 7: macOS default detection (Big Sur 11.0+ defaults to zsh)
        if sys.platform == "darwin":
            try:
                # Check macOS version
                result = subprocess.run(
                    ["sw_vers", "-productVersion"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    version_line = result.stdout.strip().splitlines()[0]
                    parts = version_line.split(".")

                    # Require at least 2 parts, all non-empty and numeric
                    if len(parts) < 2 or any(p == "" or not p.isdigit() for p in parts):
                        return ShellType.UNKNOWN

                    try:
                        major, minor = int(parts[0]), int(parts[1])
                    except (ValueError, IndexError):
                        return ShellType.UNKNOWN

                    if major >= 11 or (major == 10 and minor >= 15):
                        return ShellType.ZSH
            except (
                subprocess.TimeoutExpired,
                subprocess.CalledProcessError,
                ValueError,
                FileNotFoundError,
                OSError,
                PermissionError,
                RuntimeError,
                Exception,
            ):
                pass

        return ShellType.UNKNOWN

    def _get_shell_hints_from_configs(self) -> Optional[ShellType]:
        """Get shell type hints from existing configuration files"""
        zsh_configs = [".zshrc", ".zshenv", ".zprofile"]
        bash_configs = [".bashrc", ".bash_profile", ".bash_aliases"]
        fish_configs = [".config/fish/config.fish"]

        # Check for zsh configs
        for config in zsh_configs:
            if (self.home_dir / config).exists():
                return ShellType.ZSH

        # Check for bash configs
        for config in bash_configs:
            if (self.home_dir / config).exists():
                return ShellType.BASH

        # Check for fish configs
        for config in fish_configs:
            if (self.home_dir / config).exists():
                return ShellType.FISH

        return None

    def find_config_files(
        self, shell_type: Optional[ShellType] = None
    ) -> Dict[str, Path]:
        """Find existing configuration files for shell"""
        if shell_type is None:
            shell_type = self.detect_current_shell()

        config_files = {}
        patterns = self.CONFIG_FILES.get(shell_type, [])

        for pattern in patterns:
            config_path = self.home_dir / pattern
            if config_path.exists() and config_path.is_file():
                config_files[pattern] = config_path

        return config_files
