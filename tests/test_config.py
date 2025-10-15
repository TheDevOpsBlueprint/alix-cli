"""Tests for configuration management"""

import json

import pytest

from alix.config import Config


class TestConfig:
    """Test Config class functionality"""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary config directory"""
        config_dir = tmp_path / ".alix"
        config_dir.mkdir()
        return config_dir

    def test_init(self):
        """Test Config initialization"""
        config = Config()
        assert hasattr(config, 'config_dir')
        assert hasattr(config, 'config_path')
        assert hasattr(config, 'config')
        assert isinstance(config.config, dict)

    def test_load_no_config_file(self, temp_config_dir):
        """Test loading when config file doesn't exist"""
        config = Config()
        config.config_dir = temp_config_dir
        config.config_path = temp_config_dir / "config.json"

        loaded_config = config.load()
        assert loaded_config == Config.DEFAULT_CONFIG.copy()

    def test_load_with_valid_config_file(self, temp_config_dir):
        """Test loading with valid config file"""
        config = Config()
        config.config_dir = temp_config_dir
        config.config_path = temp_config_dir / "config.json"

        # Create a valid config file
        user_config = {"theme": "ocean", "auto_backup": False}
        with open(config.config_path, "w") as f:
            json.dump(user_config, f)

        loaded_config = config.load()

        # Should merge user config with defaults
        expected = {**Config.DEFAULT_CONFIG, **user_config}
        assert loaded_config == expected

    def test_load_with_corrupted_json_file(self, temp_config_dir):
        """Test loading with corrupted JSON file"""
        config = Config()
        config.config_dir = temp_config_dir
        config.config_path = temp_config_dir / "config.json"

        # Create a corrupted JSON file
        with open(config.config_path, "w") as f:
            f.write("{ invalid json content }")

        loaded_config = config.load()

        # Should fall back to default config
        assert loaded_config == Config.DEFAULT_CONFIG.copy()

    def test_load_with_exception_during_json_load(self, temp_config_dir):
        """Test loading with exception during JSON loading"""
        config = Config()
        config.config_dir = temp_config_dir
        config.config_path = temp_config_dir / "config.json"

        # Create a file that exists but will cause an exception
        with open(config.config_path, "w") as f:
            f.write("not json")

        loaded_config = config.load()

        # Should fall back to default config
        assert loaded_config == Config.DEFAULT_CONFIG.copy()

    def test_save_config(self, temp_config_dir):
        """Test saving configuration"""
        config = Config()
        config.config_dir = temp_config_dir
        config.config_path = temp_config_dir / "config.json"
        config.config = {"theme": "forest", "auto_backup": False}

        config.save()

        # Verify file was created and contains correct data
        assert config.config_path.exists()
        with open(config.config_path, "r") as f:
            saved_data = json.load(f)
        assert saved_data == config.config

    def test_get_existing_key(self):
        """Test getting existing configuration key"""
        config = Config()
        config.config = {"theme": "ocean"}

        value = config.get("theme")
        assert value == "ocean"

    def test_get_nonexistent_key_without_default(self):
        """Test getting non-existent key without default"""
        config = Config()
        config.config = {}

        value = config.get("nonexistent")
        assert value is None

    def test_get_nonexistent_key_with_default(self):
        """Test getting non-existent key with default value"""
        config = Config()
        config.config = {}

        value = config.get("nonexistent", "default_value")
        assert value == "default_value"

    def test_set_config_value(self, temp_config_dir):
        """Test setting configuration value"""
        config = Config()
        config.config_dir = temp_config_dir
        config.config_path = temp_config_dir / "config.json"
        config.config = {}

        config.set("theme", "forest")

        assert config.config["theme"] == "forest"
        # Verify it was saved
        assert config.config_path.exists()

    def test_get_theme_default(self):
        """Test getting default theme"""
        config = Config()
        config.config = {"theme": "default"}

        theme = config.get_theme()
        assert theme == Config.THEMES["default"]

    def test_get_theme_ocean(self):
        """Test getting ocean theme"""
        config = Config()
        config.config = {"theme": "ocean"}

        theme = config.get_theme()
        assert theme == Config.THEMES["ocean"]

    def test_get_theme_forest(self):
        """Test getting forest theme"""
        config = Config()
        config.config = {"theme": "forest"}

        theme = config.get_theme()
        assert theme == Config.THEMES["forest"]

    def test_get_theme_monochrome(self):
        """Test getting monochrome theme"""
        config = Config()
        config.config = {"theme": "monochrome"}

        theme = config.get_theme()
        assert theme == Config.THEMES["monochrome"]

    def test_get_theme_invalid_theme(self):
        """Test getting theme with invalid theme name"""
        config = Config()
        config.config = {"theme": "invalid_theme"}

        theme = config.get_theme()
        # Should fall back to default theme
        assert theme == Config.THEMES["default"]

    def test_get_theme_missing_theme_config(self):
        """Test getting theme when theme config is missing"""
        config = Config()
        config.config = {}  # No theme specified

        theme = config.get_theme()
        # Should fall back to default theme
        assert theme == Config.THEMES["default"]