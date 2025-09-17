"""Configuration management for alix"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Manage alix configuration and themes"""

    THEMES = {
        "default": {
            "border_color": "cyan",
            "header_color": "cyan",
            "selected_color": "yellow",
            "search_color": "magenta",
            "success_color": "green",
            "error_color": "red",
        },
        "ocean": {
            "border_color": "blue",
            "header_color": "dodgerblue",  # Changed from bright_blue
            "selected_color": "cyan",
            "search_color": "turquoise",  # Changed from bright_cyan
            "success_color": "green",
            "error_color": "crimson",  # Changed from bright_red
        },
        "forest": {
            "border_color": "green",
            "header_color": "chartreuse",  # Changed from bright_green
            "selected_color": "yellow",
            "search_color": "gold",  # Changed from bright_yellow
            "success_color": "lime",  # Changed from bright_green
            "error_color": "red",
        },
        "monochrome": {
            "border_color": "white",
            "header_color": "white",  # Changed from bright_white
            "selected_color": "white",
            "search_color": "white",  # Changed from bright_white
            "success_color": "white",
            "error_color": "white",  # Changed from bright_white
        }
    }

    DEFAULT_CONFIG = {
        "theme": "default",
        "auto_backup": True,
        "confirm_delete": True,
        "show_descriptions": True,
        "max_backups": 10,
    }

    def __init__(self):
        self.config_dir = Path.home() / ".alix"
        self.config_path = self.config_dir / "config.json"
        self.config = self.load()

    def load(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    return {**self.DEFAULT_CONFIG, **user_config}
            except Exception:
                pass
        return self.DEFAULT_CONFIG.copy()

    def save(self) -> None:
        """Save configuration to file"""
        self.config_dir.mkdir(exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.config[key] = value
        self.save()

    def get_theme(self) -> Dict[str, str]:
        """Get current theme colors"""
        theme_name = self.config.get("theme", "default")
        return self.THEMES.get(theme_name, self.THEMES["default"])