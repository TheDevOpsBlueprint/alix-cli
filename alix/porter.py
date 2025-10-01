import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from alix.models import Alias
from alix.storage import AliasStorage


class AliasPorter:
    """Handle import and export of aliases"""

    def __init__(self):
        self.storage = AliasStorage()

    def export_to_dict(self, aliases: List[Alias] = None) -> Dict[str, Any]:
        """Export aliases to a dictionary format"""
        if aliases is None:
            aliases = self.storage.list_all()

        return {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "count": len(aliases),
            "aliases": [alias.to_dict() for alias in aliases],
        }

    def export_to_file(self, filepath: Path, format: str = "json") -> tuple[bool, str]:
        """Export aliases to a file"""
        data = self.export_to_dict()

        try:
            if format == "yaml":
                with open(filepath, "w") as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            else:  # json
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=2, default=str)

            return True, f"Exported {data['count']} aliases to {filepath.name}"
        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def import_from_file(self, filepath: Path, merge: bool = False) -> tuple[bool, str]:
        """Import aliases from a file"""
        if not filepath.exists():
            return False, f"File not found: {filepath}"

        try:
            with open(filepath, "r") as f:
                if filepath.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            if "aliases" not in data:
                return False, "Invalid format: missing 'aliases' field"

            imported = 0
            skipped = 0

            for alias_data in data["aliases"]:
                alias = Alias.from_dict(alias_data)
                if merge or alias.name not in self.storage.aliases:
                    self.storage.aliases[alias.name] = alias
                    imported += 1
                else:
                    skipped += 1

            self.storage.save()

            msg = f"Imported {imported} aliases"
            if skipped > 0:
                msg += f" (skipped {skipped} existing)"

            return True, msg

        except Exception as e:
            return False, f"Import failed: {str(e)}"
