from pathlib import Path
from unittest.mock import Mock, call, mock_open, patch

from freezegun import freeze_time

from alix.storage import AliasStorage
from alix.models import Alias


@patch.object(AliasStorage, "load")
@patch("alix.storage.Path.mkdir")
def test_init__default_path(mock_mkdir, mock_load):
    AliasStorage()

    mock_mkdir.assert_has_calls([call(exist_ok=True), call(exist_ok=True), call(parents=True, exist_ok=True)])
    mock_load.assert_called_once()


@patch.object(AliasStorage, "load")
@patch("alix.storage.Path.mkdir")
def test_init__custom_path(mock_mkdir, mock_load):
    expected_storage_path = Path("/some/path/file.json")

    AliasStorage(storage_path=expected_storage_path)

    mock_mkdir.assert_has_calls([call(exist_ok=True), call(parents=True, exist_ok=True)])
    mock_load.assert_called_once()


@freeze_time("2025-10-24 21:01:01")
@patch("alix.storage.shutil")
def test_create_backup(mock_shutil):
    storage = AliasStorage()
    storage.aliases = {"alix-test-echo": "alix test working!"}

    with patch("pathlib.Path.exists", autospec=True) as mock_exists:
        with patch("pathlib.Path.glob", autospec=True) as mock_glob:
            with patch("pathlib.Path.unlink", autospec=True) as mock_unlink:
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


@patch("alix.storage.shutil")
@patch("alix.storage.Path.mkdir")
def test_create_backup__no_aliases_file(mock_mkdir, mock_shutil):
    storage = AliasStorage(Path("/tmp/nothing/aliases.json"))
    storage.aliases = {"alix-test-echo": "alix test working!"}

    storage.create_backup()

    mock_shutil.copy2.assert_not_called()


def test_load(storage_file_raw_data, alias):
    storage = AliasStorage()

    mocked_open = mock_open(read_data=storage_file_raw_data)
    with patch("alix.storage.open", mocked_open), patch("pathlib.Path.exists", autospec=True) as mock_exists:
        mock_exists.return_value = True

        storage.load()

    assert len(storage.aliases) == 1

    assert storage.aliases["alix-test-echo"] == alias


def test_load__corrupted_file():
    expected_data = '{"alix-test-echo": zzzzzz}'
    mocked_open = mock_open(read_data=expected_data)

    storage = AliasStorage()

    with (
        patch("alix.storage.open", mocked_open),
        patch("pathlib.Path.exists", autospec=True) as mock_exists,
        patch("pathlib.Path.rename", autospec=True) as mock_rename,
    ):
        mock_exists.return_value = True

        storage.load()

    assert len(storage.aliases) == 0
    mock_rename.assert_called_once_with(
        Path.home() / Path(".alix/aliases.json"),
        Path.home() / Path(".alix/aliases.corrupted"),
    )


@patch("alix.storage.json")
def test_add(mock_json, alias, storage_file_data):
    mocked_open = mock_open()
    mock_backup = Mock()

    storage = AliasStorage()
    storage.create_backup = mock_backup

    with patch("alix.storage.open", mocked_open):
        result = storage.add(alias)

    assert result is True
    assert storage.aliases["alix-test-echo"] == alias
    mock_backup.assert_called_once()
    mock_json.dump.assert_called_once_with(storage_file_data, mocked_open(), indent=2, default=str)


@patch("alix.storage.json")
def test_add__alias_exists(mock_json, alias):
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
def test_remove(mock_json, alias):
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
def test_remove__alias_absent(mock_json, alias):
    mock_backup = Mock()

    storage = AliasStorage()
    storage.create_backup = mock_backup

    result = storage.remove(alias.name)

    assert result is False
    assert "alix-test-echo" not in storage.aliases
    mock_backup.assert_not_called()
    mock_json.dump.assert_not_called()


def test_get(alias):
    storage = AliasStorage()
    storage.aliases[alias.name] = alias

    assert storage.get(alias.name) == alias


def test_list_all(alias_list):
    storage = AliasStorage()
    storage.aliases.clear()  # Clear any loaded aliases for test isolation
    storage.aliases[alias_list[0].name] = alias_list[0]
    storage.aliases[alias_list[1].name + "-2"] = alias_list[1]

    list_all = storage.list_all()
    assert list_all[0] == alias_list[0]
    assert list_all[1] == alias_list[1]


@patch("alix.storage.shutil")
def test_restore_latest_backup(mock_shutil):
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


@patch("alix.storage.shutil")
def test_restore_latest_backup__no_backups(mock_shutil):
    with patch("pathlib.Path.glob", autospec=True) as mock_glob:
        mock_glob.return_value = []
        mock_load = Mock()

        storage = AliasStorage()
        storage.load = mock_load

        result = storage.restore_latest_backup()

    assert result is False
    mock_load.assert_not_called()
    mock_shutil.copy2.assert_not_called()


class TestStorageGroupAndTagMethods:
    """Test storage methods for groups and tags"""

    def test_clear_test_alias(self,):
        """Test clear_test_alias method"""
        storage = AliasStorage()
        test_alias = Alias(name="alix-test-echo", command="echo test")
        storage.aliases["alix-test-echo"] = test_alias

        storage.clear_test_alias()

        assert "alix-test-echo" not in storage.aliases

    def test_track_usage_nonexistent_alias(self):
        """Test track_usage with non-existent alias"""
        storage = AliasStorage()

        storage.track_usage("nonexistent_alias", "test context")

    def test_get_by_group(self):
        """Test get_by_group method"""
        storage = AliasStorage()

        alias1 = Alias(name="alias1", command="echo 1", group="group1")
        alias2 = Alias(name="alias2", command="echo 2", group="group1")
        alias3 = Alias(name="alias3", command="echo 3", group="group2")

        storage.aliases = {
            "alias1": alias1,
            "alias2": alias2,
            "alias3": alias3
        }

        group1_aliases = storage.get_by_group("group1")
        group2_aliases = storage.get_by_group("group2")
        empty_group = storage.get_by_group("nonexistent")

        assert len(group1_aliases) == 2
        assert len(group2_aliases) == 1
        assert len(empty_group) == 0
        assert alias1 in group1_aliases
        assert alias2 in group1_aliases
        assert alias3 in group2_aliases

    def test_get_groups(self):
        """Test get_groups method"""
        storage = AliasStorage()

        alias1 = Alias(name="alias1", command="echo 1", group="group1")
        alias2 = Alias(name="alias2", command="echo 2", group="group2")
        alias3 = Alias(name="alias3", command="echo 3", group="group1")
        alias4 = Alias(name="alias4", command="echo 4")

        storage.aliases = {
            "alias1": alias1,
            "alias2": alias2,
            "alias3": alias3,
            "alias4": alias4
        }

        groups = storage.get_groups()

        assert groups == ["group1", "group2"]

    def test_remove_group_empty(self):
        """Test remove_group with no aliases in group"""
        storage = AliasStorage()

        alias1 = Alias(name="alias1", command="echo 1", group="group1")
        storage.aliases = {"alias1": alias1}

        count = storage.remove_group("nonexistent")

        assert count == 0
        assert len(storage.aliases) == 1
        assert "alias1" in storage.aliases

    def test_remove_group_with_aliases(self):
        """Test remove_group with aliases to remove"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            storage = AliasStorage(temp_path / "aliases.json")

            alias1 = Alias(name="alias1", command="echo 1", group="group1")
            alias2 = Alias(name="alias2", command="echo 2", group="group1")
            alias3 = Alias(name="alias3", command="echo 3", group="group2")

            storage.aliases = {
                "alias1": alias1,
                "alias2": alias2,
                "alias3": alias3
            }

            storage.save()

            def mock_remove(name, record_history=False):
                if name in storage.aliases:
                    del storage.aliases[name]
                    return True
                return False

            original_remove = storage.remove
            storage.remove = mock_remove

            try:
                count = storage.remove_group("group1")

                assert count == 2
                assert "alias1" not in storage.aliases
                assert "alias2" not in storage.aliases
                assert "alias3" in storage.aliases
            finally:
                storage.remove = original_remove

    def test_get_by_tag(self):
        """Test get_by_tag method"""
        storage = AliasStorage()

        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1", "tag2"])
        alias2 = Alias(name="alias2", command="echo 2", tags=["tag2"])
        alias3 = Alias(name="alias3", command="echo 3", tags=["tag3"])

        storage.aliases = {
            "alias1": alias1,
            "alias2": alias2,
            "alias3": alias3
        }

        tag1_aliases = storage.get_by_tag("tag1")
        tag2_aliases = storage.get_by_tag("tag2")
        tag3_aliases = storage.get_by_tag("nonexistent")

        assert len(tag1_aliases) == 1
        assert len(tag2_aliases) == 2
        assert len(tag3_aliases) == 0
        assert alias1 in tag1_aliases
        assert alias1 in tag2_aliases
        assert alias2 in tag2_aliases
        assert alias3 not in tag2_aliases

    def test_get_tags(self):
        """Test get_tags method"""
        storage = AliasStorage()

        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1", "tag2"])
        alias2 = Alias(name="alias2", command="echo 2", tags=["tag2", "tag3"])
        alias3 = Alias(name="alias3", command="echo 3", tags=[])

        storage.aliases = {
            "alias1": alias1,
            "alias2": alias2,
            "alias3": alias3
        }

        tags = storage.get_tags()

        assert tags == ["tag1", "tag2", "tag3"]

    def test_get_tag_counts(self):
        """Test get_tag_counts method"""
        storage = AliasStorage()

        alias1 = Alias(name="alias1", command="echo 1", tags=["tag1", "tag2"])
        alias2 = Alias(name="alias2", command="echo 2", tags=["tag2"])
        alias3 = Alias(name="alias3", command="echo 3", tags=["tag1"])

        storage.aliases = {
            "alias1": alias1,
            "alias2": alias2,
            "alias3": alias3
        }

        tag_counts = storage.get_tag_counts()

        assert tag_counts["tag1"] == 2
        assert tag_counts["tag2"] == 2

    def test_remove_group_with_remove_failure(self):
        """Test remove_group when remove method fails"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            storage = AliasStorage(temp_path / "aliases.json")

            alias1 = Alias(name="alias1", command="echo 1", group="group1")
            alias2 = Alias(name="alias2", command="echo 2", group="group1")

            storage.aliases = {
                "alias1": alias1,
                "alias2": alias2
            }

            def mock_remove(name, record_history=False):
                return False

            mock_push = Mock()
            storage.history.push = mock_push

            original_remove = storage.remove
            storage.remove = mock_remove

            try:
                count = storage.remove_group("group1")

                assert count == 0
                assert "alias1" in storage.aliases
                assert "alias2" in storage.aliases
                mock_push.assert_not_called()
            finally:
                storage.remove = original_remove
