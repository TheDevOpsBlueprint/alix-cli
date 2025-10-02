import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from alix.models import Alias, TEST_ALIAS_NAME
from alix.usage_tracker import UsageTracker


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

        self.backup_dir = self.storage_path.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        self.aliases: Dict[str, Alias] = {}
        self.usage_tracker = UsageTracker(self.storage_path.parent)
        self.load()

    def create_backup(self) -> Optional[Path]:
        """Create timestamped backup of current aliases"""
        if not self.storage_path.exists() or not self.aliases:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"aliases_{timestamp}.json"

        try:
            shutil.copy2(self.storage_path, backup_path)
            # Keep only last 10 backups
            self.cleanup_old_backups(keep=10)
            return backup_path
        except Exception:
            return None

    def cleanup_old_backups(self, keep: int = 10) -> None:
        """Remove old backups, keeping only the most recent ones"""
        backups = sorted(self.backup_dir.glob("aliases_*.json"))
        if len(backups) > keep:
            for backup in backups[:-keep]:
                backup.unlink()

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
            except (json.JSONDecodeError, Exception):
                # If file is corrupted, start fresh but backup old file
                backup_path = self.storage_path.with_suffix('.corrupted')
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
        self.create_backup()  # Backup before modification
        self.aliases[alias.name] = alias
        self.save()
        return True

    def remove(self, name: str) -> bool:
        """Remove an alias, return True if it existed"""
        if name in self.aliases:
            self.create_backup()  # Backup before modification
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

    def restore_latest_backup(self) -> bool:
        """Restore from the most recent backup"""
        backups = sorted(self.backup_dir.glob("aliases_*.json"))
        if backups:
            latest_backup = backups[-1]
            shutil.copy2(latest_backup, self.storage_path)
            self.load()
            return True
        return False
    
    def track_usage(self, alias_name: str, context: Optional[str] = None) -> None:
        """Track usage of an alias"""
        if alias_name in self.aliases:
            # Update the alias object
            self.aliases[alias_name].record_usage(context)
            self.save()
            
            # Update the usage tracker
            self.usage_tracker.track_alias_usage(alias_name, context)
    
    def get_usage_analytics(self) -> Dict:
        """Get comprehensive usage analytics"""
        aliases = list(self.aliases.values())
        analytics = self.usage_tracker.get_usage_analytics(aliases)
        
        return {
            "total_aliases": analytics.total_aliases,
            "total_uses": analytics.total_uses,
            "most_used_alias": analytics.most_used_alias,
            "least_used_alias": analytics.least_used_alias,
            "unused_aliases": analytics.unused_aliases,
            "recently_used": analytics.recently_used,
            "usage_trends": analytics.usage_trends,
            "average_usage_per_alias": analytics.average_usage_per_alias,
            "most_productive_aliases": analytics.most_productive_aliases
        }
      
    def get_by_group(self, group_name: str) -> List[Alias]:
        """Get all aliases in a specific group"""
        return [alias for alias in self.aliases.values() if alias.group == group_name]

    def get_groups(self) -> List[str]:
        """Get all unique group names"""
        groups = set()
        for alias in self.aliases.values():
            if alias.group:
                groups.add(alias.group)
        return sorted(list(groups))

    def remove_group(self, group_name: str) -> int:
        """Remove all aliases in a group, return count of removed aliases"""
        count = 0
        aliases_to_remove = [name for name, alias in self.aliases.items() if alias.group == group_name]
        for name in aliases_to_remove:
            if self.remove(name):
                count += 1
        return count
