from pathlib import Path
from unittest.mock import ANY, Mock, mock_open, patch

from freezegun import freeze_time

from alix.storage import AliasStorage


@patch.object(AliasStorage, "load")
@patch("os.mkdir")
def test_init__default_path(mock_mkdir, mock_load):
    AliasStorage()

    expected_storage_path = Path.home() / ".alix"
    expected_backup_path = expected_storage_path / "backups"

    mock_mkdir.assert_any_call(expected_storage_path, ANY)
    mock_mkdir.assert_any_call(expected_backup_path, ANY)
    mock_load.assert_called_once()


@patch.object(AliasStorage, "load")
@patch("os.mkdir")
def test_init__custom_path(mock_mkdir, mock_load):
    expected_storage_path = Path("/some/path/file.json")
    expected_backup_path = Path("/some/path/backups")

    AliasStorage(storage_path=expected_storage_path)

    mock_mkdir.assert_any_call(expected_backup_path, ANY)
    mock_load.assert_called_once()


@freeze_time("2025-10-24 21:01:01")
@patch("os.mkdir")
@patch("alix.storage.shutil")
def test_create_backup(mock_shutil, mock_mkdir):
    storage = AliasStorage()
    storage.aliases = {"alix-test-echo": "alix test working!"}

    with (
        patch("pathlib.Path.exists", autospec=True) as mock_exists,
        patch("pathlib.Path.glob", autospec=True) as mock_glob,
        patch("pathlib.Path.unlink", autospec=True) as mock_unlink,
    ):
        mock_exists.return_value = True
        mock_glob.return_value = [
            Path("alias_20251024_200000.json"),
            Path("alias_20251023_200000.json"),
            Path("alias_20251022_200000.json"),
            Path("alias_20251021_200000.json"),
            Path("alias_20251020_200000.json"),
            Path("alias_20251019_200000.json"),
            Path("alias_20251018_200000.json"),
            Path("alias_20251017_200000.json"),
            Path("alias_20251016_200000.json"),
            Path("alias_20251015_200000.json"),
            Path("alias_20251014_200000.json"),
        ]

        storage.create_backup()

    mock_shutil.copy2.assert_called_once_with(
        Path.home() / Path(".alix/aliases.json"),
        Path.home() / Path(".alix/backups/aliases_20251024_210101.json"),
    )
    mock_unlink.assert_called_once_with(Path("alias_20251014_200000.json"))


@patch("os.mkdir")
@patch("alix.storage.shutil")
def test_create_backup__no_aliases_file(mock_shutil, mock_mkdir):
    storage = AliasStorage(Path("/tmp/nothing/aliases.json"))
    storage.aliases = {"alix-test-echo": "alix test working!"}

    storage.create_backup()

    mock_shutil.copy2.assert_not_called()


@patch("os.mkdir")
def test_load(mock_mkdir, storage_file_raw_data, alias):
    storage = AliasStorage()

    mocked_open = mock_open(read_data=storage_file_raw_data)
    with patch("alix.storage.open", mocked_open), patch(
        "pathlib.Path.exists", autospec=True
    ) as mock_exists:
        mock_exists.return_value = True

        storage.load()

    assert len(storage.aliases) == 1

    assert storage.aliases["alix-test-echo"] == alias


@patch("os.mkdir")
def test_load__corrupted_file(mock_mkdir):
    expected_data = '{"alix-test-echo": zzzzzz}'
    mocked_open = mock_open(read_data=expected_data)

    storage = AliasStorage()

    with patch("alix.storage.open", mocked_open), patch(
        "pathlib.Path.exists", autospec=True
    ) as mock_exists, patch("pathlib.Path.rename", autospec=True) as mock_rename:
        mock_exists.return_value = True

        storage.load()

    assert len(storage.aliases) == 0
    mock_rename.assert_called_once_with(
        Path.home() / Path(".alix/aliases.json"),
        Path.home() / Path(".alix/aliases.corrupted"),
    )


@patch("alix.storage.json")
@patch("os.mkdir")
def test_add(mock_mkdir, mock_json, alias, storage_file_data):
    mocked_open = mock_open()
    mock_backup = Mock()

    storage = AliasStorage()
    storage.create_backup = mock_backup

    with patch("alix.storage.open", mocked_open):
        result = storage.add(alias)

    assert result is True
    assert storage.aliases["alix-test-echo"] == alias
    mock_backup.assert_called_once()
    mock_json.dump.assert_called_once_with(
        storage_file_data, mocked_open(), indent=2, default=str
    )


@patch("alix.storage.json")
@patch("os.mkdir")
def test_add__alias_exists(mock_mkdir, mock_json, alias):
    mock_backup = Mock()

    storage = AliasStorage()
    storage.create_backup = mock_backup
    storage.aliases[alias.name] = alias

    result = storage.add(alias)

    assert result is False
    assert storage.aliases["alix-test-echo"] == alias
    mock_backup.assert_not_called()
    mock_json.dump.assert_not_called()


@patch("alix.storage.json")
@patch("os.mkdir")
def test_remove(mock_mkdir, mock_json, alias):
    mocked_open = mock_open()
    mock_backup = Mock()

    storage = AliasStorage()
    storage.create_backup = mock_backup
    storage.aliases[alias.name] = alias

    with patch("alix.storage.open", mocked_open):
        result = storage.remove(alias.name)

    assert result is True
    assert "alix-test-echo" not in storage.aliases
    mock_backup.assert_called_once()
    mock_json.dump.assert_called_once_with({}, mocked_open(), indent=2, default=str)


@patch("alix.storage.json")
@patch("os.mkdir")
def test_remove__alias_absent(mock_mkdir, mock_json, alias):
    mock_backup = Mock()

    storage = AliasStorage()
    storage.create_backup = mock_backup

    result = storage.remove(alias.name)

    assert result is False
    assert "alix-test-echo" not in storage.aliases
    mock_backup.assert_not_called()
    mock_json.dump.assert_not_called()


@patch("os.mkdir")
def test_get(mock_mkdir, alias):
    storage = AliasStorage()
    storage.aliases[alias.name] = alias

    assert storage.get(alias.name) == alias


@patch("os.mkdir")
def test_list_all(mock_mkdir, alias_list):
    storage = AliasStorage()
    storage.aliases[alias_list[0].name] = alias_list[0]
    storage.aliases[alias_list[1].name + "-2"] = alias_list[1]

    list_all = storage.list_all()
    assert list_all[0] == alias_list[0]
    assert list_all[1] == alias_list[1]


@patch("os.mkdir")
@patch("alix.storage.shutil")
def test_restore_latest_backup(mock_shutil, mock_mkdir):
    with patch("pathlib.Path.glob", autospec=True) as mock_glob:
        mock_glob.return_value = [
            Path("alias_20251024_200000.json"),
            Path("alias_20251023_200000.json"),
        ]
        mock_load = Mock()

        storage = AliasStorage()
        storage.load = mock_load

        result = storage.restore_latest_backup()

    assert result is True
    mock_load.assert_called_once()
    mock_shutil.copy2.assert_called_once_with(
        Path("alias_20251024_200000.json"),
        Path.home() / Path(".alix/aliases.json"),
    )


@patch("os.mkdir")
@patch("alix.storage.shutil")
def test_restore_latest_backup__no_backups(mock_shutil, mock_mkdir):
    with patch("pathlib.Path.glob", autospec=True) as mock_glob:
        mock_glob.return_value = []
        mock_load = Mock()

        storage = AliasStorage()
        storage.load = mock_load

        result = storage.restore_latest_backup()

    assert result is False
    mock_load.assert_not_called()
    mock_shutil.copy2.assert_not_called()
