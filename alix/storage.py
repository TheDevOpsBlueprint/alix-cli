"""Storage layer for aliases using JSON"""

import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from alix.models import Alias, TEST_ALIAS_NAME


class AliasStorage:
    """Handle storage and retrieval of aliases"""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize storage with optional custom path"""
        if storage_path:
            self.storage_path = storage_path
        else:
            # Default to ~/.alix/aliases.json
            self.storage_dir = Path.home() / ".alix"
            self.storage_path = self.storage_dir / "aliases.json"
            self.storage_dir.mkdir(exist_ok=True)

        self.aliases: Dict[str, Alias] = {}
        self.load()

    def load(self) -> None:
        """Load aliases from JSON file"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.aliases = {
                        name: Alias.from_dict(alias_data)
                        for name, alias_data in data.items()
                    }
            except (json.JSONDecodeError, Exception) as e:
                # If file is corrupted, start fresh but backup old file
                backup_path = self.storage_path.with_suffix('.backup')
                if self.storage_path.exists():
                    self.storage_path.rename(backup_path)
                self.aliases = {}

    def save(self) -> None:
        """Save aliases to JSON file"""
        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            name: alias.to_dict()
            for name, alias in self.aliases.items()
        }

        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def add(self, alias: Alias) -> bool:
        """Add a new alias, return True if successful"""
        if alias.name in self.aliases:
            return False
        self.aliases[alias.name] = alias
        self.save()
        return True

    def remove(self, name: str) -> bool:
        """Remove an alias, return True if it existed"""
        if name in self.aliases:
            del self.aliases[name]
            self.save()
            return True
        return False

    def get(self, name: str) -> Optional[Alias]:
        """Get an alias by name"""
        return self.aliases.get(name)

    def list_all(self) -> List[Alias]:
        """Get all aliases as a list"""
        return list(self.aliases.values())

    def clear_test_alias(self) -> None:
        """Remove test alias if it exists (for safe testing)"""
        self.remove(TEST_ALIAS_NAME)