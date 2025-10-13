import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from alix.cli import main
from alix.template_manager import TemplateManager


class TestTemplatesCLI:
    """Test CLI commands for template management"""

    @pytest.fixture
    def runner(self):
        """CLI test runner"""
        return CliRunner()

    @pytest.fixture
    def mock_template_manager(self):
        """Mock TemplateManager for testing"""
        mock_manager = MagicMock(spec=TemplateManager)

        mock_template = MagicMock()
        mock_template.name = "git"
        mock_template.category = "git"
        mock_template.description = "Git version control aliases"
        mock_template.aliases = [
            MagicMock(name="gs", command="git status", description="Git status", tags=["git"]),
            MagicMock(name="ga", command="git add", description="Git add", tags=["git"])
        ]

        mock_manager.list_templates.return_value = [mock_template]
        mock_manager.get_template.return_value = mock_template
        mock_manager.get_categories.return_value = ["git", "docker", "k8s"]
        mock_manager.import_template.return_value = (True, "Imported 2 aliases from 'git'")
        mock_manager.import_by_category.return_value = (True, "Imported 8 aliases from category 'git'")

        return mock_manager

    @patch("alix.cli.TemplateManager")
    def test_templates_list_command(self, mock_template_manager_class, runner, mock_template_manager):
        """Test templates list command"""
        mock_template_manager_class.return_value = mock_template_manager

        result = runner.invoke(main, ["templates", "list"])

        assert result.exit_code == 0
        assert "Available Templates" in result.output
        assert "git" in result.output
        assert "Git version control aliases" in result.output

    @patch("alix.cli.TemplateManager")
    def test_templates_add_command_success(self, mock_template_manager_class, runner, mock_template_manager):
        """Test templates add command success"""
        mock_template_manager_class.return_value = mock_template_manager

        result = runner.invoke(main, ["templates", "add", "git"])

        assert result.exit_code == 0
        assert "Imported 2 aliases from 'git'" in result.output
        mock_template_manager.import_template.assert_called_once_with("git", None)

    @patch("alix.cli.TemplateManager")
    def test_templates_add_command_not_exists(self, mock_template_manager_class, runner, mock_template_manager):
        """Test templates add command with non-existent template"""
        mock_template_manager.get_template.return_value = None
        mock_template_manager.import_template.return_value = (False, "Template 'nonexistent' not found")
        mock_template_manager_class.return_value = mock_template_manager

        result = runner.invoke(main, ["templates", "add", "nonexistent"])

        assert result.exit_code == 0
        assert "Template 'nonexistent' not found" in result.output

    @patch("alix.cli.TemplateManager")
    def test_templates_add_command_dry_run(self, mock_template_manager_class, runner, mock_template_manager):
        """Test templates add command with dry-run"""
        from alix.models import Alias

        mock_template = MagicMock()
        mock_template.name = "git"
        mock_template.category = "git"
        mock_template.description = "Git version control aliases"
        mock_template.aliases = [
            Alias(name="gs", command="git status", description="Git status", tags=["git"]),
            Alias(name="ga", command="git add", description="Git add", tags=["git"])
        ]
        mock_template_manager.get_template.return_value = mock_template
        mock_template_manager_class.return_value = mock_template_manager

        result = runner.invoke(main, ["templates", "add", "git", "--dry-run"])

        assert result.exit_code == 0
        assert "Preview: Would import from 'git'" in result.output
        mock_template_manager.import_template.assert_not_called()

    @patch("alix.cli.TemplateManager")
    def test_templates_add_command_with_aliases(self, mock_template_manager_class, runner, mock_template_manager):
        """Test templates add command with alias filter"""
        mock_template_manager_class.return_value = mock_template_manager

        result = runner.invoke(main, ["templates", "add", "git", "--aliases", "gs,ga"])

        assert result.exit_code == 0
        mock_template_manager.import_template.assert_called_once_with("git", ["gs", "ga"])

    @patch("alix.cli.TemplateManager")
    def test_templates_add_category_command(self, mock_template_manager_class, runner, mock_template_manager):
        """Test templates add-category command"""
        mock_template_manager_class.return_value = mock_template_manager

        result = runner.invoke(main, ["templates", "add-category", "git"])

        assert result.exit_code == 0
        assert "Imported 8 aliases from category 'git'" in result.output
        mock_template_manager.import_by_category.assert_called_once_with("git", None)

    @patch("alix.cli.TemplateManager")
    def test_templates_add_category_not_exists(self, mock_template_manager_class, runner, mock_template_manager):
        """Test templates add-category command with non-existent category"""
        mock_template_manager.get_categories.return_value = ["git", "docker"]
        mock_template_manager.import_by_category.return_value = (False, "Category 'nonexistent' not found")
        mock_template_manager_class.return_value = mock_template_manager

        result = runner.invoke(main, ["templates", "add-category", "nonexistent"])

        assert result.exit_code == 0
        assert "Category 'nonexistent' not found" in result.output

    @patch("alix.cli.TemplateManager")
    def test_templates_add_category_dry_run(self, mock_template_manager_class, runner, mock_template_manager):
        """Test templates add-category command with dry-run"""
        mock_template_manager_class.return_value = mock_template_manager

        result = runner.invoke(main, ["templates", "add-category", "git", "--dry-run"])

        assert result.exit_code == 0
        assert "Preview: Would import from category 'git'" in result.output
        mock_template_manager.import_by_category.assert_not_called()

    @patch("alix.cli.TemplateManager")
    def test_templates_add_category_with_aliases(self, mock_template_manager_class, runner, mock_template_manager):
        """Test templates add-category command with alias filter"""
        mock_template_manager_class.return_value = mock_template_manager

        result = runner.invoke(main, ["templates", "add-category", "git", "--aliases", "gs,ga"])

        assert result.exit_code == 0
        mock_template_manager.import_by_category.assert_called_once_with("git", ["gs", "ga"])

    def test_templates_help(self, runner):
        """Test templates command help"""
        result = runner.invoke(main, ["templates", "--help"])

        assert result.exit_code == 0
        assert "Manage alias templates" in result.output
        assert "list" in result.output
        assert "add" in result.output
        assert "add-category" in result.output