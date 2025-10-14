import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from alix.models import Alias
from alix.storage import AliasStorage


@dataclass
class Template:
    """Represents a template with metadata and aliases"""
    name: str
    category: str
    description: str
    aliases: List[Alias]
    version: str


class TemplateManager:
    """Manage alias templates from YAML files"""

    def __init__(self):
        self.templates_dir = Path(__file__).parent / "templates"
        self.storage = AliasStorage()
        self._templates: Dict[str, Template] = {}
        self._load_templates()

    def _validate_template_data(self, data: dict, filename: str) -> bool:
        """Validate template YAML structure"""
        if not isinstance(data, dict):
            return False

        required_fields = ["version", "category", "description", "aliases"]
        for field in required_fields:
            if field not in data:
                return False

        if not isinstance(data.get("aliases", []), list):
            return False

        # Validate each alias has required fields
        for alias_data in data.get("aliases", []):
            if not isinstance(alias_data, dict):
                return False
            if "name" not in alias_data or "command" not in alias_data:
                return False

        return True

    def _load_templates(self) -> None:
        """Load all templates from YAML files"""
        if not self.templates_dir.exists():
            return

        for yaml_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)

                template_name = yaml_file.stem

                # Validate template structure
                if not self._validate_template_data(data, yaml_file.name):
                    continue  # Skip invalid templates

                aliases = []

                for alias_data in data.get("aliases", []):
                    # Convert to Alias object
                    alias = Alias(
                        name=alias_data["name"],
                        command=alias_data["command"],
                        description=alias_data.get("description", ""),
                        tags=alias_data.get("tags", [])
                    )
                    aliases.append(alias)

                template = Template(
                    name=template_name,
                    category=data.get("category", "general"),
                    description=data.get("description", ""),
                    aliases=aliases,
                    version=data.get("version", "1.0")
                )

                self._templates[template_name] = template

            except Exception as e:
                # Skip malformed templates
                continue

    def list_templates(self, category: Optional[str] = None) -> List[Template]:
        """List available templates, optionally filtered by category"""
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        return sorted(templates, key=lambda t: t.name)

    def get_template(self, name: str) -> Optional[Template]:
        """Get a specific template by name"""
        return self._templates.get(name)

    def get_categories(self) -> List[str]:
        """Get all available template categories"""
        categories = set()
        for template in self._templates.values():
            categories.add(template.category)
        return sorted(list(categories))

    def import_template(self, template_name: str, alias_names: Optional[List[str]] = None) -> tuple[bool, str]:
        """Import aliases from a template, optionally filtered by alias names"""
        template = self.get_template(template_name)
        if not template:
            return False, f"Template '{template_name}' not found"

        aliases_to_import = template.aliases
        if alias_names:
            aliases_to_import = [a for a in template.aliases if a.name in alias_names]
            if not aliases_to_import:
                return False, f"No matching aliases found in template '{template_name}'"

        imported_count = 0
        skipped_count = 0

        for alias in aliases_to_import:
            if self.storage.add(alias):
                imported_count += 1
            else:
                skipped_count += 1

        msg = f"Imported {imported_count} aliases from '{template_name}'"
        if skipped_count > 0:
            msg += f" (skipped {skipped_count} existing)"

        return True, msg

    def import_by_category(self, category: str, alias_filter: Optional[List[str]] = None) -> tuple[bool, str]:
        """Import all templates from a category, optionally filtered by alias names"""
        templates = self.list_templates(category)
        if not templates:
            return False, f"No templates found in category '{category}'"

        total_imported = 0
        total_skipped = 0

        for template in templates:
            aliases_to_import = template.aliases
            if alias_filter:
                aliases_to_import = [a for a in template.aliases if a.name in alias_filter]

            for alias in aliases_to_import:
                if self.storage.add(alias):
                    total_imported += 1
                else:
                    total_skipped += 1

        msg = f"Imported {total_imported} aliases from category '{category}'"
        if total_skipped > 0:
            msg += f" (skipped {total_skipped} existing)"

        return True, msg