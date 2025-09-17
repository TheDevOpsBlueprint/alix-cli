"""Shell detection and configuration file handling"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict
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
        """Detect the current shell from environment"""
        # Try SHELL environment variable
        shell_env = os.environ.get("SHELL", "").lower()

        if "zsh" in shell_env:
            return ShellType.ZSH
        elif "bash" in shell_env:
            return ShellType.BASH
        elif "fish" in shell_env:
            return ShellType.FISH
        elif "sh" in shell_env:
            return ShellType.SH

        # Try parent process (fallback for Windows)
        if sys.platform == "win32":
            return ShellType.UNKNOWN

        # Check parent process name on Unix
        try:
            import psutil
            parent = psutil.Process(os.getppid())
            parent_name = parent.name().lower()

            for shell_type in ShellType:
                if shell_type.value in parent_name:
                    return shell_type
        except (ImportError, Exception):
            pass

        return ShellType.UNKNOWN

    def find_config_files(self, shell_type: Optional[ShellType] = None) -> Dict[str, Path]:
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