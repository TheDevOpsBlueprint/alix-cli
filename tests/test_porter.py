from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from alix.porter import AliasPorter
from alix.storage import AliasStorage
from alix.models import Alias


def test_export_to_dict__from_list(alias_list, porter_data):
    porter = AliasPorter()
    export = porter.export_to_dict(alias_list)

    assert export == porter_data


@patch.object(AliasStorage, "list_all")
def test_export_to_dict__from_storage(mock_list_all, alias_list, porter_data):
    mock_list_all.return_value = alias_list

    porter = AliasPorter()
    export = porter.export_to_dict()

    assert export == porter_data


@patch.object(AliasPorter, "export_to_dict")
@patch("alix.porter.json")
def test_export_to_file__json(mock_json, mock_exporter, porter_data):
    mock_exporter.return_value = porter_data
    mocked_open = mock_open()

    porter = AliasPorter()

    with patch("alix.porter.open", mocked_open):
        result = porter.export_to_file((Path("/tmp/aliases.json")))

    assert result == (True, "Exported 2 aliases to aliases.json")
    mock_json.dump.assert_called_once_with(
        porter_data, mocked_open(), indent=2, default=str
    )


@patch.object(AliasPorter, "export_to_dict")
@patch("alix.porter.yaml")
def test_export_to_file__yaml(mock_yaml, mock_exporter, porter_data):
    mock_exporter.return_value = porter_data
    mocked_open = mock_open()

    porter = AliasPorter()

    with patch("alix.porter.open", mocked_open):
        result = porter.export_to_file((Path("/tmp/aliases.json")), format="yaml")

    assert result == (True, "Exported 2 aliases to aliases.json")
    mock_yaml.dump.assert_called_once_with(
        porter_data, mocked_open(), default_flow_style=False, sort_keys=False
    )


@patch.object(AliasPorter, "export_to_dict")
@patch("alix.porter.json")
def test_export_to_file__fail(mock_json, mock_exporter):
    mock_exporter.return_value = {}
    mocked_open = mock_open()

    porter = AliasPorter()

    mocked_open.side_effect = Exception("File write error")
    with patch("alix.porter.open", mocked_open):
        result = porter.export_to_file((Path("/tmp/aliases.json")))

    assert result == (False, "Export failed: File write error")
    mock_json.dump.assert_not_called()


@patch("alix.porter.json")
def test_import_from_file__json(mock_json, alias, porter_data):
    mock_storage = Mock(spec=AliasStorage)
    mock_storage.aliases = {}
    mocked_open = mock_open()
    porter_data["aliases"] = porter_data["aliases"][0:1]
    mock_json.load.return_value = porter_data

    porter = AliasPorter()
    porter.storage = mock_storage

    with patch("alix.porter.open", mocked_open), patch(
        "pathlib.Path.exists", autospec=True
    ) as mock_exists:
        mock_exists.return_value = True

        result = porter.import_from_file(Path("/tmp/alias.json"))

    assert result == (True, "Imported 1 aliases")
    assert len(mock_storage.aliases) == 1
    assert mock_storage.aliases["alix-test-echo"] == alias
    assert (
        str(mock_storage.aliases["alix-test-echo"])
        == "alix-test-echo='alix test working!'"
    )
    mock_storage.save.assert_called_once()


@patch("alix.porter.yaml")
def test_import_from_file__alias_exists_no_merge(mock_yaml, alias, porter_data):
    mock_storage = Mock(spec=AliasStorage)
    mock_storage.aliases = {"alix-test-echo": alias}
    mocked_open = mock_open()
    mock_yaml.safe_load.return_value = porter_data

    porter = AliasPorter()
    porter.storage = mock_storage

    with patch("alix.porter.open", mocked_open), patch(
        "pathlib.Path.exists", autospec=True
    ) as mock_exists:
        mock_exists.return_value = True

        result = porter.import_from_file(Path("/tmp/alias.yaml"))

    assert result == (True, "Imported 0 aliases (skipped 2 existing)")
    assert len(mock_storage.aliases) == 1
    assert "alix-test-echo" in mock_storage.aliases
    mock_storage.save.assert_called_once()


def test_import_from_file__not_found():
    mocked_open = mock_open()

    porter = AliasPorter()

    with patch("alix.porter.open", mocked_open), patch(
        "pathlib.Path.exists", autospec=True
    ) as mock_exists:
        mock_exists.return_value = False

        result = porter.import_from_file(Path("/tmp/alias.json"))

    assert result == (False, "File not found: /tmp/alias.json")
    mocked_open.assert_not_called()


@patch("alix.porter.json")
def test_import_from_file__no_aliases_in_file(mock_json):
    mock_storage = Mock(spec=AliasStorage)
    mock_storage.aliases = {}
    mocked_open = mock_open()
    mock_json.load.return_value = {}

    porter = AliasPorter()
    porter.storage = mock_storage

    with patch("alix.porter.open", mocked_open), patch(
        "pathlib.Path.exists", autospec=True
    ) as mock_exists:
        mock_exists.return_value = True

        result = porter.import_from_file(Path("/tmp/alias.json"))

    assert result == (False, "Invalid format: missing 'aliases' field")
    assert len(mock_storage.aliases) == 0
    mock_storage.save.assert_not_called()


def test_import_from_file__failed():
    mocked_open = mock_open()
    mocked_open.side_effect = Exception("File read error")

    porter = AliasPorter()

    with patch("alix.porter.open", mocked_open), patch(
        "pathlib.Path.exists", autospec=True
    ) as mock_exists:
        mock_exists.return_value = True

        result = porter.import_from_file(Path("/tmp/alias.json"))

    assert result == (False, "Import failed: File read error")


class TestPorterTagFiltering:
    """Test tag filtering and statistics functionality in AliasPorter"""

    def test_export_to_dict_with_tag_filter(self):
        """Test export_to_dict with tag_filter"""
        porter = AliasPorter()

        # Create test aliases with different tags
        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1", "tag2"])
        alias2 = Alias(name="alias2", command="echo 2", tags=["tag2"])
        alias3 = Alias(name="alias3", command="echo 3", tags=["tag3"])

        aliases = [alias1, alias2, alias3]

        # Export with tag filter
        export_data = porter.export_to_dict(aliases=aliases, tag_filter="tag2")

        # Should only include aliases with tag2
        assert export_data["count"] == 2
        assert export_data["tag_filter"] == "tag2"
        assert len(export_data["aliases"]) == 2

        # Verify the correct aliases are included
        alias_names = [alias["name"] for alias in export_data["aliases"]]
        assert "alias1" in alias_names  # has tag2
        assert "alias2" in alias_names  # has tag2
        assert "alias3" not in alias_names  # doesn't have tag2

    @patch("alix.porter.json")
    def test_export_to_file_with_tag_filter(self, mock_json):
        """Test export_to_file with tag_filter"""
        porter = AliasPorter()

        # Create test aliases with tags
        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1"])
        alias2 = Alias(name="alias2", command="echo 2", tags=["tag2"])

        # Mock storage to return our test aliases
        porter.storage.list_all = Mock(return_value=[alias1, alias2])

        mocked_open = mock_open()

        with patch("alix.porter.open", mocked_open):
            result = porter.export_to_file(Path("/tmp/test.json"), tag_filter="tag1")

        # Should succeed and include tag filter in message
        assert result[0] is True
        assert "filtered by tag: tag1" in result[1]
        assert "Exported 1 aliases" in result[1]

        # Verify the export data includes tag_filter
        call_args = mock_json.dump.call_args[0][0]
        assert call_args["tag_filter"] == "tag1"
        assert call_args["count"] == 1

    @patch("alix.porter.json")
    def test_import_from_file_with_tag_filter(self, mock_json):
        """Test import_from_file with tag_filter"""
        mock_storage = Mock(spec=AliasStorage)
        mock_storage.aliases = {}
        mocked_open = mock_open()

        # Create test data with aliases having different tags
        import_data = {
            "aliases": [
                {"name": "alias1", "command": "echo 1", "tags": ["tag1"]},
                {"name": "alias2", "command": "echo 2", "tags": ["tag2"]},
                {"name": "alias3", "command": "echo 3", "tags": ["tag1", "tag2"]}
            ]
        }
        mock_json.load.return_value = import_data

        porter = AliasPorter()
        porter.storage = mock_storage

        with patch("alix.porter.open", mocked_open), patch(
            "pathlib.Path.exists", autospec=True
        ) as mock_exists:
            mock_exists.return_value = True

            result = porter.import_from_file(Path("/tmp/test.json"), tag_filter="tag1")

        # Should import only aliases with tag1
        assert result[0] is True
        assert "Imported 2 aliases" in result[1]
        assert "filtered out 1 by tag" in result[1]

        # Verify the aliases were added to storage
        assert len(mock_storage.aliases) == 2
        assert "alias1" in mock_storage.aliases
        assert "alias3" in mock_storage.aliases
        assert "alias2" not in mock_storage.aliases

    @patch("alix.porter.json")
    def test_export_by_tags_match_any(self, mock_json):
        """Test export_by_tags with match_any=False"""
        porter = AliasPorter()

        # Create test aliases with different tags
        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1"])
        alias2 = Alias(name="alias2", command="echo 2", tags=["tag2"])
        alias3 = Alias(name="alias3", command="echo 3", tags=["tag1", "tag2"])

        # Mock storage to return our test aliases
        porter.storage.list_all = Mock(return_value=[alias1, alias2, alias3])

        mocked_open = mock_open()

        with patch("alix.porter.open", mocked_open):
            result = porter.export_by_tags(["tag1", "tag2"], Path("/tmp/test.json"))

        # Should export aliases with any of the tags
        assert result[0] is True
        assert "matching any of tags: tag1, tag2" in result[1]

        # Verify export data
        call_args = mock_json.dump.call_args[0][0]
        assert call_args["count"] == 3  # All aliases match
        assert call_args["tags"] == ["tag1", "tag2"]
        assert call_args["match_all"] is False

    @patch("alix.porter.json")
    def test_export_by_tags_match_all(self, mock_json):
        """Test export_by_tags with match_all=True"""
        porter = AliasPorter()

        # Create test aliases with different tags
        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1"])
        alias2 = Alias(name="alias2", command="echo 2", tags=["tag2"])
        alias3 = Alias(name="alias3", command="echo 3", tags=["tag1", "tag2"])

        # Mock storage to return our test aliases
        porter.storage.list_all = Mock(return_value=[alias1, alias2, alias3])

        mocked_open = mock_open()

        with patch("alix.porter.open", mocked_open):
            result = porter.export_by_tags(["tag1", "tag2"], Path("/tmp/test.json"), match_all=True)

        # Should export only aliases with ALL tags
        assert result[0] is True
        assert "matching all of tags: tag1, tag2" in result[1]

        # Verify export data
        call_args = mock_json.dump.call_args[0][0]
        assert call_args["count"] == 1  # Only alias3 has both tags
        assert call_args["tags"] == ["tag1", "tag2"]
        assert call_args["match_all"] is True

    @patch("alix.porter.json")
    def test_export_by_tags_no_matches(self, mock_json):
        """Test export_by_tags with no matching aliases"""
        porter = AliasPorter()

        # Create test aliases without matching tags
        alias1 = Alias(name="alias1", command="echo 1", tags=["other"])
        alias2 = Alias(name="alias2", command="echo 2", tags=["different"])

        # Mock storage to return our test aliases
        porter.storage.list_all = Mock(return_value=[alias1, alias2])

        result = porter.export_by_tags(["tag1", "tag2"], Path("/tmp/test.json"))

        # Should fail with no matches
        assert result[0] is False
        assert "No aliases found matching tags: tag1, tag2" in result[1]

        # Should not attempt to write file
        mock_json.dump.assert_not_called()

    @patch("alix.porter.json")
    def test_export_by_tags_file_write_error(self, mock_json):
        """Test export_by_tags with file write error"""
        porter = AliasPorter()

        # Create test aliases
        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1"])
        porter.storage.list_all = Mock(return_value=[alias1])

        # Mock the json.dump to raise exception
        mock_json.dump.side_effect = Exception("Disk write error")

        with patch("alix.porter.open", mock_open()):
            result = porter.export_by_tags(["tag1"], Path("/tmp/test.json"))

        # Should fail with file write error
        assert result[0] is False
        assert "Export failed: Disk write error" in result[1]

        # Should have attempted to write file
        mock_json.dump.assert_called_once()

    @patch("alix.porter.yaml")
    def test_export_by_tags_yaml_file_write_error(self, mock_yaml):
        """Test export_by_tags with YAML file write error"""
        porter = AliasPorter()

        # Create test aliases
        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1"])
        porter.storage.list_all = Mock(return_value=[alias1])

        # Mock the yaml.dump to raise exception
        mock_yaml.dump.side_effect = Exception("YAML write error")

        with patch("alix.porter.open", mock_open()):
            result = porter.export_by_tags(["tag1"], Path("/tmp/test.yaml"), format="yaml")

        # Should fail with YAML write error
        assert result[0] is False
        assert "Export failed: YAML write error" in result[1]

        # Should have attempted to write YAML file
        mock_yaml.dump.assert_called_once()

    def test_get_tag_statistics(self):
        """Test get_tag_statistics method"""
        porter = AliasPorter()

        # Create test aliases with various tags
        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1", "tag2"])
        alias2 = Alias(name="alias2", command="echo 2", tags=["tag2", "tag3"])
        alias3 = Alias(name="alias3", command="echo 3", tags=["tag1"])
        alias4 = Alias(name="alias4", command="echo 4", tags=[])  # No tags

        # Mock storage to return our test aliases
        porter.storage.list_all = Mock(return_value=[alias1, alias2, alias3, alias4])

        stats = porter.get_tag_statistics()

        # Verify statistics
        assert stats["total_tags"] == 3  # tag1, tag2, tag3
        assert stats["total_aliases"] == 4
        assert stats["tagged_aliases"] == 3  # alias1, alias2, alias3
        assert stats["untagged_aliases"] == 1  # alias4

        # Verify tag counts
        assert stats["tag_counts"]["tag1"] == 2  # alias1, alias3
        assert stats["tag_counts"]["tag2"] == 2  # alias1, alias2
        assert stats["tag_counts"]["tag3"] == 1  # alias2

        # Verify tag combinations (pairs)
        assert ("tag1", "tag2") in stats["tag_combinations"]
        assert ("tag2", "tag3") in stats["tag_combinations"]
        assert stats["tag_combinations"][("tag1", "tag2")] == 1  # Only alias1 has both
        assert stats["tag_combinations"][("tag2", "tag3")] == 1  # Only alias2 has both
