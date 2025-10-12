from unittest.mock import MagicMock, patch

import pytest
import yaml

from alix.template_manager import TemplateManager


class TestTemplateManager:
    """Test cases for TemplateManager class"""

    @pytest.fixture
    def temp_templates_dir(self, tmp_path):
        """Create a temporary templates directory"""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        valid_template = {
            "version": "1.0",
            "category": "test",
            "description": "Test template",
            "aliases": [
                {"name": "test1", "command": "echo test1", "description": "Test alias 1", "tags": ["test"]},
                {"name": "test2", "command": "echo test2", "description": "Test alias 2", "tags": ["test"]},
            ],
        }

        with open(templates_dir / "valid.yaml", "w") as f:
            yaml.dump(valid_template, f)

        with open(templates_dir / "malformed.yaml", "w") as f:
            f.write("invalid: yaml: content: [\n")

        empty_template = {"version": "1.0", "category": "empty", "description": "Empty template", "aliases": []}

        with open(templates_dir / "empty.yaml", "w") as f:
            yaml.dump(empty_template, f)

        return templates_dir

    def test_init_with_templates_dir(self, temp_templates_dir):
        """Test TemplateManager initialization"""
        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir

        assert hasattr(manager, "_templates")
        assert hasattr(manager, "templates_dir")
        assert hasattr(manager, "storage")

    def test_load_templates_success(self, temp_templates_dir):
        """Test successful template loading"""
        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir

        manager._load_templates()

        assert "valid" in manager._templates
        template = manager._templates["valid"]
        assert template.name == "valid"
        assert template.category == "test"
        assert template.description == "Test template"
        assert len(template.aliases) == 2
        assert template.aliases[0].name == "test1"
        assert template.aliases[1].name == "test2"

    def test_load_templates_malformed_yaml(self, temp_templates_dir):
        """Test loading with malformed YAML files"""
        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir

        manager._load_templates()

        assert "valid" in manager._templates
        assert "malformed" not in manager._templates

    def test_load_templates_missing_directory(self, tmp_path):
        """Test loading when templates directory doesn't exist"""
        manager = TemplateManager()
        manager.templates_dir = tmp_path / "nonexistent"

        manager._templates = {}

        manager._load_templates()

        assert len(manager._templates) == 0

    def test_list_templates_empty(self):
        """Test listing templates when none exist"""
        manager = TemplateManager()
        manager._templates = {}

        templates = manager.list_templates()
        assert templates == []

    def test_list_templates_by_category(self, temp_templates_dir):
        """Test filtering templates by category"""
        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        test_templates = manager.list_templates(category="test")
        assert len(test_templates) == 1
        assert test_templates[0].category == "test"

        empty_templates = manager.list_templates(category="nonexistent")
        assert empty_templates == []

    def test_get_template_exists(self, temp_templates_dir):
        """Test getting existing template"""
        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        template = manager.get_template("valid")
        assert template is not None
        assert template.name == "valid"

    def test_get_template_not_exists(self):
        """Test getting non-existent template"""
        manager = TemplateManager()
        manager._templates = {}

        template = manager.get_template("nonexistent")
        assert template is None

    def test_get_categories(self, temp_templates_dir):
        """Test getting all categories"""
        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        categories = manager.get_categories()
        assert "test" in categories
        assert "empty" in categories

    @patch("alix.template_manager.AliasStorage")
    def test_import_template_success(self, mock_storage_class, temp_templates_dir):
        """Test successful template import"""
        mock_storage = MagicMock()
        mock_storage.add.return_value = True
        mock_storage_class.return_value = mock_storage

        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        success, message = manager.import_template("valid")

        assert success is True
        assert "Imported 2 aliases" in message
        assert mock_storage.add.call_count == 2

    @patch("alix.template_manager.AliasStorage")
    def test_import_template_not_exists(self, mock_storage_class):
        """Test importing non-existent template"""
        mock_storage_class.return_value = MagicMock()

        manager = TemplateManager()
        manager._templates = {}

        success, message = manager.import_template("nonexistent")

        assert success is False
        assert "Template 'nonexistent' not found" in message

    @patch("alix.template_manager.AliasStorage")
    def test_import_template_with_filter(self, mock_storage_class, temp_templates_dir):
        """Test importing template with alias filter"""
        mock_storage = MagicMock()
        mock_storage.add.return_value = True
        mock_storage_class.return_value = mock_storage

        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        success, message = manager.import_template("valid", alias_names=["test1"])

        assert success is True
        assert "Imported 1 aliases" in message
        assert mock_storage.add.call_count == 1

    def test_load_templates_skip_invalid_template(self, tmp_path):
        """Test _load_templates skips invalid templates"""
        manager = TemplateManager()
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create an invalid template (missing required fields)
        invalid_template = {
            "version": "1.0",
            # Missing category, description, aliases
        }

        with open(templates_dir / "invalid.yaml", "w") as f:
            yaml.dump(invalid_template, f)

        manager.templates_dir = templates_dir
        manager._templates = {}

        # This should skip the invalid template
        manager._load_templates()

        # Should have no templates loaded due to validation failure
        assert len(manager._templates) == 0

    def test_validate_template_data_invalid_data_type(self):
        """Test _validate_template_data with invalid data type"""
        manager = TemplateManager()

        # Test with non-dict data
        assert not manager._validate_template_data("invalid", "test.yaml")
        assert not manager._validate_template_data([], "test.yaml")
        assert not manager._validate_template_data(None, "test.yaml")

    def test_validate_template_data_missing_required_fields(self):
        """Test _validate_template_data with missing required fields"""
        manager = TemplateManager()

        # Missing version
        data = {"category": "test", "description": "test", "aliases": []}
        assert not manager._validate_template_data(data, "test.yaml")

        # Missing category
        data = {"version": "1.0", "description": "test", "aliases": []}
        assert not manager._validate_template_data(data, "test.yaml")

        # Missing description
        data = {"version": "1.0", "category": "test", "aliases": []}
        assert not manager._validate_template_data(data, "test.yaml")

        # Missing aliases
        data = {"version": "1.0", "category": "test", "description": "test"}
        assert not manager._validate_template_data(data, "test.yaml")

    def test_validate_template_data_invalid_aliases_list(self):
        """Test _validate_template_data with invalid aliases list"""
        manager = TemplateManager()

        # Aliases is not a list
        data = {"version": "1.0", "category": "test", "description": "test", "aliases": "invalid"}
        assert not manager._validate_template_data(data, "test.yaml")

    def test_validate_template_data_invalid_alias_data(self):
        """Test _validate_template_data with invalid alias data"""
        manager = TemplateManager()

        # Alias is not a dict
        data = {"version": "1.0", "category": "test", "description": "test", "aliases": ["invalid"]}
        assert not manager._validate_template_data(data, "test.yaml")

    def test_validate_template_data_missing_alias_fields(self):
        """Test _validate_template_data with missing alias fields"""
        manager = TemplateManager()

        # Missing name
        data = {"version": "1.0", "category": "test", "description": "test", "aliases": [{"command": "echo test"}]}
        assert not manager._validate_template_data(data, "test.yaml")

        # Missing command
        data = {"version": "1.0", "category": "test", "description": "test", "aliases": [{"name": "test"}]}
        assert not manager._validate_template_data(data, "test.yaml")

    def test_load_templates_exception_handling(self, tmp_path):
        """Test _load_templates exception handling"""
        manager = TemplateManager()
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create a file that will cause yaml.safe_load to fail
        invalid_yaml_file = templates_dir / "invalid.yaml"
        with open(invalid_yaml_file, "w") as f:
            f.write("invalid: yaml: content: [\n")

        manager.templates_dir = templates_dir
        manager._templates = {}

        # This should not raise an exception and should skip the invalid file
        manager._load_templates()

        # Should have no templates loaded due to exception
        assert len(manager._templates) == 0

    @patch("alix.template_manager.AliasStorage")
    def test_import_template_with_skipped_aliases(self, mock_storage_class, temp_templates_dir):
        """Test import_template with some aliases being skipped"""
        mock_storage = MagicMock()
        # First call returns True (imported), second returns False (skipped)
        mock_storage.add.side_effect = [True, False]
        mock_storage_class.return_value = mock_storage

        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        success, message = manager.import_template("valid")

        assert success is True
        assert "Imported 1 aliases" in message
        assert "skipped 1 existing" in message
        assert mock_storage.add.call_count == 2

    @patch("alix.template_manager.AliasStorage")
    def test_import_by_category_with_skipped_aliases(self, mock_storage_class, temp_templates_dir):
        """Test import_by_category with some aliases being skipped"""
        mock_storage = MagicMock()
        # First call returns True (imported), second returns False (skipped)
        mock_storage.add.side_effect = [True, False]
        mock_storage_class.return_value = mock_storage

        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        success, message = manager.import_by_category("test")

        assert success is True
        assert "Imported 1 aliases" in message
        assert "skipped 1 existing" in message
        assert mock_storage.add.call_count == 2

    @patch("alix.template_manager.AliasStorage")
    def test_import_template_no_matching_aliases(self, mock_storage_class, temp_templates_dir):
        """Test importing template with no matching aliases"""
        mock_storage_class.return_value = MagicMock()

        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        success, message = manager.import_template("valid", alias_names=["nonexistent"])

        assert success is False
        assert "No matching aliases found" in message

    @patch("alix.template_manager.AliasStorage")
    def test_import_by_category_success(self, mock_storage_class, temp_templates_dir):
        """Test importing by category"""
        mock_storage = MagicMock()
        mock_storage.add.return_value = True
        mock_storage_class.return_value = mock_storage

        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        success, message = manager.import_by_category("test")

        assert success is True
        assert "Imported 2 aliases" in message
        assert mock_storage.add.call_count == 2

    @patch("alix.template_manager.AliasStorage")
    def test_import_by_category_not_exists(self, mock_storage_class):
        """Test importing non-existent category"""
        mock_storage_class.return_value = MagicMock()

        manager = TemplateManager()
        manager._templates = {}

        success, message = manager.import_by_category("nonexistent")

        assert success is False
        assert "No templates found in category 'nonexistent'" in message

    @patch("alix.template_manager.AliasStorage")
    def test_import_by_category_with_filter(self, mock_storage_class, temp_templates_dir):
        """Test importing category with alias filter"""
        mock_storage = MagicMock()
        mock_storage.add.return_value = True
        mock_storage_class.return_value = mock_storage

        manager = TemplateManager()
        manager.templates_dir = temp_templates_dir
        manager._load_templates()

        success, message = manager.import_by_category("test", alias_filter=["test1"])

        assert success is True
        assert "Imported 1 aliases" in message
        assert mock_storage.add.call_count == 1
