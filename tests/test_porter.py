from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from alix.porter import AliasPorter
from alix.storage import AliasStorage


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
