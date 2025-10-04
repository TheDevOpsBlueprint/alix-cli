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

    def export_to_dict(self, aliases: List[Alias] = None, tag_filter: str = None) -> Dict[str, Any]:
        """Export aliases to a dictionary format"""
        if aliases is None:
            aliases = self.storage.list_all()
        
        # Apply tag filter if specified
        if tag_filter:
            aliases = [alias for alias in aliases if tag_filter in alias.tags]

        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "count": len(aliases),
            "aliases": [alias.to_dict() for alias in aliases],
        }
        
        if tag_filter:
            export_data["tag_filter"] = tag_filter
            
        return export_data

    def export_to_file(self, filepath: Path, format: str = "json", tag_filter: str = None) -> tuple[bool, str]:
        """Export aliases to a file"""
        data = self.export_to_dict(tag_filter=tag_filter)

        try:
            if format == "yaml":
                with open(filepath, "w") as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            else:  # json
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=2, default=str)

            msg = f"Exported {data['count']} aliases to {filepath.name}"
            if tag_filter:
                msg += f" (filtered by tag: {tag_filter})"
            return True, msg
        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def import_from_file(self, filepath: Path, merge: bool = False, tag_filter: str = None) -> tuple[bool, str]:
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
            tag_filtered = 0

            for alias_data in data["aliases"]:
                alias = Alias.from_dict(alias_data)
                
                # Apply tag filter if specified
                if tag_filter and tag_filter not in alias.tags:
                    tag_filtered += 1
                    continue
                
                if merge or alias.name not in self.storage.aliases:
                    self.storage.aliases[alias.name] = alias
                    imported += 1
                else:
                    skipped += 1

            self.storage.save()

            msg = f"Imported {imported} aliases"
            if skipped > 0:
                msg += f" (skipped {skipped} existing)"
            if tag_filtered > 0:
                msg += f" (filtered out {tag_filtered} by tag)"

            return True, msg

        except Exception as e:
            return False, f"Import failed: {str(e)}"

    def export_by_tags(self, tags: List[str], filepath: Path, format: str = "json", match_all: bool = False) -> tuple[bool, str]:
        """Export aliases that match any (or all) of the specified tags"""
        aliases = self.storage.list_all()
        
        if match_all:
            # Match aliases that have ALL specified tags
            filtered_aliases = [alias for alias in aliases if all(tag in alias.tags for tag in tags)]
        else:
            # Match aliases that have ANY of the specified tags
            filtered_aliases = [alias for alias in aliases if any(tag in alias.tags for tag in tags)]
        
        if not filtered_aliases:
            return False, f"No aliases found matching tags: {', '.join(tags)}"
        
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "tags": tags,
            "match_all": match_all,
            "count": len(filtered_aliases),
            "aliases": [alias.to_dict() for alias in filtered_aliases]
        }
        
        try:
            if format == "yaml":
                with open(filepath, "w") as f:
                    yaml.dump(export_data, f, default_flow_style=False, sort_keys=False)
            else:  # json
                with open(filepath, "w") as f:
                    json.dump(export_data, f, indent=2, default=str)

            match_type = "all" if match_all else "any"
            msg = f"Exported {len(filtered_aliases)} aliases matching {match_type} of tags: {', '.join(tags)}"
            return True, msg
        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def get_tag_statistics(self) -> Dict[str, Any]:
        """Get comprehensive tag statistics"""
        aliases = self.storage.list_all()
        tag_counts = {}
        tag_combinations = {}
        
        for alias in aliases:
            # Count individual tags
            for tag in alias.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Count tag combinations (pairs)
            if len(alias.tags) >= 2:
                for i, tag1 in enumerate(alias.tags):
                    for tag2 in alias.tags[i+1:]:
                        combo = tuple(sorted([tag1, tag2]))
                        tag_combinations[combo] = tag_combinations.get(combo, 0) + 1
        
        return {
            "total_tags": len(tag_counts),
            "total_aliases": len(aliases),
            "tagged_aliases": len([a for a in aliases if a.tags]),
            "untagged_aliases": len([a for a in aliases if not a.tags]),
            "tag_counts": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)),
            "tag_combinations": dict(sorted(tag_combinations.items(), key=lambda x: x[1], reverse=True))
        }
