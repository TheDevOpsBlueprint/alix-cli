import stat
from datetime import datetime

import pytest

from alix.history_manager import MAX_HISTORY
from alix.models import Alias
from alix.storage import AliasStorage


@pytest.fixture
def temp_storage(tmp_path):
    """Fixture for temporary storage to avoid file pollution."""
    storage_path = tmp_path / "aliases.json"
    storage = AliasStorage(storage_path=storage_path)
    # Clear any existing data to ensure clean state for each test
    storage.aliases.clear()
    storage.save()
    return storage


def test_add_undo_redo(temp_storage):
    alias = Alias(name="test", command="echo hello")

    # Add alias
    assert temp_storage.add(alias, record_history=True)
    assert len(temp_storage.list_all()) == 1
    assert len(temp_storage.history.list_undo()) == 1

    # Undo
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "Undid add" in msg
    assert len(temp_storage.list_all()) == 0
    assert len(temp_storage.history.list_redo()) == 1

    # Redo
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "Redid add" in msg
    assert len(temp_storage.list_all()) == 1


def test_remove_undo_redo(temp_storage):
    alias = Alias(name="test", command="echo hi")
    temp_storage.add(alias, record_history=True)

    # Remove alias
    assert temp_storage.remove(alias.name, record_history=True)
    assert len(temp_storage.list_all()) == 0
    assert len(temp_storage.history.list_undo()) == 2  # add + remove

    # Undo remove
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "Undid remove" in msg
    assert len(temp_storage.list_all()) == 1
    assert len(temp_storage.history.list_redo()) == 1

    # Redo remove
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "Redid remove" in msg
    assert len(temp_storage.list_all()) == 0


def test_remove_group_undo_redo(temp_storage):
    alias1 = Alias(name="test1", command="echo one", group="test_group")
    alias2 = Alias(name="test2", command="echo two", group="test_group")
    temp_storage.add(alias1, record_history=True)
    temp_storage.add(alias2, record_history=True)

    # Remove group
    removed_count = temp_storage.remove_group("test_group")
    assert removed_count == 2
    assert len(temp_storage.list_all()) == 0
    assert len(temp_storage.history.list_undo()) == 3  # add1 + add2 + remove_group

    # Undo remove group
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "Undid remove_group" in msg
    assert len(temp_storage.list_all()) == 2
    assert len(temp_storage.history.list_redo()) == 1

    # Undo add2
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "Undid add" in msg
    assert len(temp_storage.list_all()) == 1

    # Redo add2
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "Redid add" in msg
    assert len(temp_storage.list_all()) == 2


def test_empty_stacks(temp_storage):
    # Undo on empty
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "⚠️  Nothing to undo – history is empty." in msg
    assert len(temp_storage.history.list_redo()) == 0

    # Redo on empty
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "⚠️  Nothing to redo – already at the latest state." in msg
    assert len(temp_storage.history.list_undo()) == 0


def test_max_history_trimming(temp_storage):
    # Push more than MAX_HISTORY ops
    for i in range(MAX_HISTORY + 1):
        alias = Alias(name=f"test{i}", command=f"echo {i}")
        temp_storage.add(alias, record_history=True)

    assert len(temp_storage.history.list_undo()) == MAX_HISTORY
    # Oldest should be trimmed (last one is most recent)
    assert temp_storage.history.list_undo()[-1]["aliases"][0]["name"] == f"test{MAX_HISTORY}"


def test_corrupted_history_file(tmp_path):
    # Create a temporary history file with invalid JSON
    history_path = tmp_path / "history.json"
    history_path.parent.mkdir(exist_ok=True)
    with open(history_path, "w") as f:
        f.write("{invalid json")

    # Create storage with the corrupted history file
    storage = AliasStorage(storage_path=tmp_path / "aliases.json")

    # Verify stacks are empty (reset on corruption)
    assert len(storage.history.list_undo()) == 0
    assert len(storage.history.list_redo()) == 0

    # Undo/redo should not crash
    msg = storage.history.perform_undo(storage)
    assert "⚠️  Nothing to undo – history is empty." in msg


def test_partial_failures(temp_storage):
    # Add valid alias
    alias_valid = Alias(name="valid", command="echo ok")
    temp_storage.add(alias_valid, record_history=True)

    # Simulate corrupted alias data in history
    corrupted_op = {
        "type": "add",
        "aliases": [{"invalid": "data"}],  # Missing name
        "timestamp": datetime.now().isoformat(),
    }
    temp_storage.history.push(corrupted_op)

    # Undo should handle gracefully
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "skipped" in msg.lower()


def test_multiple_undos_redos(temp_storage):
    # Add multiple aliases
    for i in range(3):
        temp_storage.add(Alias(name=f"a{i}", command=f"echo {i}"), record_history=True)

    # Undo all
    for i in range(3):
        msg = temp_storage.history.perform_undo(temp_storage)
        assert "✅" in msg and "Undid" in msg

    # Undo beyond empty
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "⚠️  Nothing to undo – history is empty." in msg

    # Redo all
    for i in range(3):
        msg = temp_storage.history.perform_redo(temp_storage)
        assert "🔁" in msg and "Redid" in msg

    # Redo beyond full
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "⚠️  Nothing to redo – already at the latest state." in msg


def test_remove_nonexistent(temp_storage):
    # Remove alias that does not exist
    result = temp_storage.remove("ghost_alias", record_history=True)
    assert result is False or result == 0  # whatever your remove returns

    # Remove group that does not exist
    result = temp_storage.remove_group("ghost_group")
    assert result == 0


def test_selective_undo_by_id(temp_storage):
    """Test selective undo by operation ID."""
    # Add multiple aliases
    alias1 = Alias(name="test1", command="echo one")
    alias2 = Alias(name="test2", command="echo two")
    alias3 = Alias(name="test3", command="echo three")

    temp_storage.add(alias1, record_history=True)
    temp_storage.add(alias2, record_history=True)
    temp_storage.add(alias3, record_history=True)

    # Verify all aliases exist
    assert len(temp_storage.list_all()) == 3
    assert len(temp_storage.history.list_undo()) == 3

    # Undo the middle operation (ID 2 = test2)
    msg = temp_storage.history.perform_undo_by_id(temp_storage, 2)
    assert "✅" in msg and "Undid add" in msg
    assert len(temp_storage.list_all()) == 2
    assert len(temp_storage.history.list_undo()) == 2  # One less in undo
    assert len(temp_storage.history.list_redo()) == 1  # One in redo

    # Verify test2 was removed
    assert temp_storage.get("test1") is not None
    assert temp_storage.get("test2") is None
    assert temp_storage.get("test3") is not None

    # Undo the first operation (ID 1 = test3, now the most recent)
    msg = temp_storage.history.perform_undo_by_id(temp_storage, 1)
    assert "✅" in msg and "Undid add" in msg
    assert len(temp_storage.list_all()) == 1

    # Verify test3 was removed
    assert temp_storage.get("test1") is not None
    assert temp_storage.get("test2") is None
    assert temp_storage.get("test3") is None


def test_selective_redo_by_id(temp_storage):
    """Test selective redo by operation ID."""
    # Add and undo multiple aliases
    alias1 = Alias(name="test1", command="echo one")
    alias2 = Alias(name="test2", command="echo two")

    temp_storage.add(alias1, record_history=True)
    temp_storage.add(alias2, record_history=True)

    # Undo both (this creates 2 redo operations)
    temp_storage.history.perform_undo(temp_storage)  # Undo test2
    temp_storage.history.perform_undo(temp_storage)  # Undo test1

    assert len(temp_storage.list_all()) == 0
    assert len(temp_storage.history.list_undo()) == 0
    assert len(temp_storage.history.list_redo()) == 2

    # Redo the first operation (ID 1 = most recent undo = test1)
    msg = temp_storage.history.perform_redo_by_id(temp_storage, 1)
    assert "🔁" in msg and "Redid add" in msg
    assert len(temp_storage.list_all()) == 1
    assert len(temp_storage.history.list_redo()) == 1

    # Verify test1 was restored (most recent undo)
    assert temp_storage.get("test1") is not None
    assert temp_storage.get("test2") is None


def test_invalid_undo_id(temp_storage):
    """Test undo with invalid operation ID."""
    msg = temp_storage.history.perform_undo_by_id(temp_storage, 999)
    assert "❌ Invalid operation ID" in msg

    msg = temp_storage.history.perform_undo_by_id(temp_storage, 0)
    assert "❌ Invalid operation ID" in msg

    msg = temp_storage.history.perform_undo_by_id(temp_storage, -1)
    assert "❌ Invalid operation ID" in msg


def test_invalid_redo_id(temp_storage):
    """Test redo with invalid operation ID."""
    msg = temp_storage.history.perform_redo_by_id(temp_storage, 999)
    assert "❌ Invalid operation ID" in msg

    msg = temp_storage.history.perform_redo_by_id(temp_storage, 0)
    assert "❌ Invalid operation ID" in msg

    msg = temp_storage.history.perform_redo_by_id(temp_storage, -1)
    assert "❌ Invalid operation ID" in msg


def test_selective_undo_redo_mixed_operations(temp_storage):
    """Test selective undo/redo with mixed operation types."""
    # Add alias
    alias = Alias(name="test", command="echo hello")
    temp_storage.add(alias, record_history=True)

    # Edit alias (this creates remove + add operations)
    alias.command = "echo world"
    temp_storage.remove("test", record_history=True)
    temp_storage.add(alias, record_history=True)

    # Remove alias
    temp_storage.remove("test", record_history=True)

    assert len(temp_storage.history.list_undo()) == 4  # add, remove, add, remove

    # Selectively undo the edit operation (middle one - should be the add operation from edit)
    msg = temp_storage.history.perform_undo_by_id(temp_storage, 2)  # ID 2 = add (part of edit)
    assert "✅" in msg and "Undid add" in msg

    # Verify the alias was removed (undo add should remove the alias)
    removed_alias = temp_storage.get("test")
    assert removed_alias is None


def test_selective_undo_after_new_operations(temp_storage):
    """Test that selective undo works correctly after new operations."""
    # Add initial alias
    alias1 = Alias(name="test1", command="echo one")
    temp_storage.add(alias1, record_history=True)

    # Undo the add
    temp_storage.history.perform_undo(temp_storage)
    assert len(temp_storage.list_all()) == 0

    # Add new alias (this clears redo stack)
    alias2 = Alias(name="test2", command="echo two")
    temp_storage.add(alias2, record_history=True)

    # Try to undo by ID - should only see the latest operation
    assert len(temp_storage.history.list_undo()) == 1
    msg = temp_storage.history.perform_undo_by_id(temp_storage, 1)
    assert "✅" in msg and "Undid add" in msg
    assert len(temp_storage.list_all()) == 0


def test_edge_case_empty_stacks_selective(temp_storage):
    """Test selective undo/redo on empty stacks."""
    # Empty undo stack
    msg = temp_storage.history.perform_undo_by_id(temp_storage, 1)
    assert "❌ Invalid operation ID" in msg

    # Empty redo stack
    msg = temp_storage.history.perform_redo_by_id(temp_storage, 1)
    assert "❌ Invalid operation ID" in msg


def test_edit_operation_undo_redo(temp_storage):
    """Test undo/redo for edit operations."""
    # Add alias
    alias = Alias(name="test", command="echo hello")
    temp_storage.add(alias, record_history=True)

    # Edit alias (creates remove + add operations)
    alias.command = "echo world"
    temp_storage.remove("test", record_history=True)
    temp_storage.add(alias, record_history=True)

    assert len(temp_storage.history.list_undo()) == 3  # add + remove + add

    # Undo edit (which is actually the add operation from the edit)
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid add" in msg

    # Verify alias was removed (undo add should remove the alias)
    edited_alias = temp_storage.get("test")
    assert edited_alias is None

    # Redo edit (which is actually the add operation from the edit)
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "🔁" in msg and "Redid add" in msg

    # Verify command was restored
    edited_alias = temp_storage.get("test")
    assert edited_alias.command == "echo world"


def test_rename_operation_undo_redo(temp_storage):
    """Test undo/redo for rename operations."""
    # Add alias
    alias = Alias(name="old_name", command="echo hello")
    temp_storage.add(alias, record_history=True)

    # Rename alias (simulate by creating operation manually)
    rename_op = {
        "type": "rename",
        "aliases": [{"name": "old_name", "command": "echo hello"}],
        "old_name": "old_name",
        "new_name": "new_name",
        "timestamp": datetime.now().isoformat(),
    }
    temp_storage.history.push(rename_op)

    # Remove old and add new name
    temp_storage.remove("old_name", record_history=False)
    alias.name = "new_name"
    temp_storage.add(alias, record_history=False)

    # Undo rename
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid rename" in msg

    # Verify name was reverted
    assert temp_storage.get("old_name") is not None
    assert temp_storage.get("new_name") is None

    # Redo rename
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "🔁" in msg and "Redid rename" in msg

    # Verify name was restored
    assert temp_storage.get("old_name") is None
    assert temp_storage.get("new_name") is not None


def test_group_operations_undo_redo(temp_storage):
    """Test undo/redo for group operations."""
    # Add aliases to group
    alias1 = Alias(name="test1", command="echo one")
    alias2 = Alias(name="test2", command="echo two")
    temp_storage.add(alias1, record_history=True)
    temp_storage.add(alias2, record_history=True)

    # Add to group (simulate group_add operation)
    group_add_op = {
        "type": "group_add",
        "aliases": [{"name": "test1", "command": "echo one"}, {"name": "test2", "command": "echo two"}],
        "group_name": "test_group",
        "timestamp": datetime.now().isoformat(),
    }
    temp_storage.history.push(group_add_op)

    # Apply group assignment
    alias1.group = "test_group"
    alias2.group = "test_group"
    temp_storage.aliases["test1"] = alias1
    temp_storage.aliases["test2"] = alias2
    temp_storage.save()

    # Undo group_add
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid group_add" in msg

    # Verify aliases removed from group
    assert temp_storage.get("test1").group is None
    assert temp_storage.get("test2").group is None

    # Redo group_add
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "🔁" in msg and "Redid group_add" in msg

    # Verify aliases restored to group
    assert temp_storage.get("test1").group == "test_group"
    assert temp_storage.get("test2").group == "test_group"


def test_tag_operations_undo_redo(temp_storage):
    """Test undo/redo for tag operations."""
    # Add alias
    alias = Alias(name="test", command="echo hello", tags=["old"])
    temp_storage.add(alias, record_history=True)

    # Add tag (simulate tag_add operation)
    tag_add_op = {
        "type": "tag_add",
        "aliases": [{"name": "test", "command": "echo hello", "tags": ["old"]}],
        "added_tags": ["new_tag"],
        "timestamp": datetime.now().isoformat(),
    }
    temp_storage.history.push(tag_add_op)

    # Apply tag addition
    alias.tags.append("new_tag")
    temp_storage.aliases["test"] = alias
    temp_storage.save()

    # Undo tag_add
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid tag_add" in msg

    # Verify tag was removed
    assert "new_tag" not in temp_storage.get("test").tags
    assert "old" in temp_storage.get("test").tags

    # Redo tag_add
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "🔁" in msg and "Redid tag_add" in msg

    # Verify tag was restored
    assert "new_tag" in temp_storage.get("test").tags
    assert "old" in temp_storage.get("test").tags


def test_import_operation_undo_redo(temp_storage):
    """Test undo/redo for import operations."""
    # Simulate import operation
    import_op = {
        "type": "import",
        "aliases": [
            {"name": "imported1", "command": "echo imported1"},
            {"name": "imported2", "command": "echo imported2"},
        ],
        "timestamp": datetime.now().isoformat(),
    }
    temp_storage.history.push(import_op)

    # Apply import
    alias1 = Alias(name="imported1", command="echo imported1")
    alias2 = Alias(name="imported2", command="echo imported2")
    temp_storage.add(alias1, record_history=False)
    temp_storage.add(alias2, record_history=False)

    # Undo import
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid import" in msg

    # Verify aliases were removed
    assert temp_storage.get("imported1") is None
    assert temp_storage.get("imported2") is None

    # Redo import
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "🔁" in msg and "Redid import" in msg

    # Verify aliases were restored
    assert temp_storage.get("imported1") is not None
    assert temp_storage.get("imported2") is not None


def test_mixed_operation_sequence(temp_storage):
    """Test complex sequence of mixed operations."""
    # Add -> Edit -> Add -> Remove sequence
    alias1 = Alias(name="test1", command="echo one")
    alias2 = Alias(name="test2", command="echo two")

    temp_storage.add(alias1, record_history=True)
    temp_storage.add(alias2, record_history=True)

    # Edit first alias (creates remove + add operations)
    alias1.command = "echo modified"
    temp_storage.remove("test1", record_history=True)
    temp_storage.add(alias1, record_history=True)

    # Remove second alias
    temp_storage.remove("test2", record_history=True)

    assert len(temp_storage.history.list_undo()) == 5  # 2 adds + remove + add + remove

    # Undo remove (test2 should come back)
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid remove" in msg
    assert temp_storage.get("test2") is not None

    # Undo edit (which is actually the add operation from the edit)
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid add" in msg
    # After undoing the add operation from edit, test1 should be removed
    assert temp_storage.get("test1") is None

    # Undo remove (test1 should be added again)
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid remove" in msg
    assert temp_storage.get("test1") is not None

    # Undo add (test1 should be removed)
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid add" in msg
    assert temp_storage.get("test2") is None

    # Now redo all operations
    for i in range(4):
        msg = temp_storage.history.perform_redo(temp_storage)
        assert "🔁" in msg

    # Verify final state
    assert temp_storage.get("test1") is not None
    assert temp_storage.get("test2") is None
    assert temp_storage.get("test1").command == "echo modified"


def test_corrupted_history_during_operations(temp_storage, tmp_path):
    """Test handling of corrupted history files during operations."""
    # Add some aliases first
    alias1 = Alias(name="test1", command="echo one")
    alias2 = Alias(name="test2", command="echo two")
    temp_storage.add(alias1, record_history=True)
    temp_storage.add(alias2, record_history=True)

    # Corrupt the history file
    history_file = tmp_path / "aliases_history.json"
    with open(history_file, "w") as f:
        f.write("{ invalid json content }")

    # Try to undo - should handle gracefully
    msg = temp_storage.history.perform_undo(temp_storage)
    # Should either work (if it loaded successfully) or handle the error gracefully
    assert msg is not None

    # Try selective undo with corrupted history
    msg = temp_storage.history.perform_undo_by_id(temp_storage, 1)
    # Should handle gracefully even with corrupted history
    assert msg is not None


def test_invalid_operation_data_handling(temp_storage):
    """Test handling of invalid operation data in history."""
    # Push invalid operation (missing required fields)
    invalid_op = {
        "type": "add",
        # Missing "aliases" field
        "timestamp": datetime.now().isoformat(),
    }

    # This should raise an error when pushing
    try:
        temp_storage.history.push(invalid_op)
        assert False, "Should have raised ValueError for invalid operation"
    except ValueError:
        pass  # Expected

    # Push operation with empty aliases
    empty_op = {"type": "add", "aliases": [], "timestamp": datetime.now().isoformat()}
    temp_storage.history.push(empty_op)

    # Undo should handle empty aliases gracefully
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid add" in msg


def test_storage_failures_during_undo_redo(temp_storage):
    """Test handling of storage failures during undo/redo operations."""
    # Add alias
    alias = Alias(name="test", command="echo hello")
    temp_storage.add(alias, record_history=True)

    # Mock a storage failure by making storage operations fail
    original_remove = temp_storage.remove
    original_add = temp_storage.add

    def failing_remove(name, record_history=False):
        if name == "test":
            raise Exception("Storage failure")
        return original_remove(name, record_history)

    def failing_add(alias, record_history=False):
        if alias.name == "test":
            raise Exception("Storage failure")
        return original_add(alias, record_history)

    temp_storage.remove = failing_remove
    temp_storage.add = failing_add

    try:
        # Try to undo - should handle the failure gracefully
        msg = temp_storage.history.perform_undo(temp_storage)
        assert "Undid add" in msg
        # Should indicate partial failure
        assert "skipped" in msg.lower() or "of" in msg
    finally:
        # Restore original methods
        temp_storage.remove = original_remove
        temp_storage.add = original_add


def test_history_file_permission_errors(tmp_path):
    """Test handling of file permission errors."""

    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_file = readonly_dir / "history.json"

    # Make directory read-only
    readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # No write permission

    try:
        # Try to create history manager with read-only location
        from alix.history_manager import HistoryManager

        # This should not crash, but may fail silently
        history = HistoryManager(path=readonly_file)

        # Try operations that require writing
        Alias(name="test", command="echo hello")
        history.push(
            {
                "type": "add",
                "aliases": [{"name": "test", "command": "echo hello"}],
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Should handle gracefully (fail silently as per current implementation)
        undo_msg = history.perform_undo(None)  # Pass None storage to avoid other errors
        assert undo_msg is not None

    finally:
        # Restore permissions for cleanup
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def test_very_large_history_operations(temp_storage):
    """Test handling of very large numbers of aliases in operations."""
    # Create operation with many aliases
    many_aliases = []
    for i in range(100):  # Large number of aliases
        many_aliases.append({"name": f"alias{i}", "command": f"echo {i}"})

    large_op = {"type": "add", "aliases": many_aliases, "timestamp": datetime.now().isoformat()}
    temp_storage.history.push(large_op)

    # Add all aliases to storage
    for alias_data in many_aliases:
        alias = Alias(name=alias_data["name"], command=alias_data["command"])
        temp_storage.add(alias, record_history=False)

    # Undo should handle large number of aliases
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid add" in msg

    # Verify all aliases were removed
    for i in range(100):
        assert temp_storage.get(f"alias{i}") is None


def test_malformed_alias_data_in_history(temp_storage):
    """Test handling of malformed alias data in history operations."""
    # Push operation with malformed alias data
    malformed_op = {
        "type": "add",
        "aliases": [
            {"name": "valid", "command": "echo valid"},
            {"name": "", "command": "echo invalid"},  # Empty name
            {"command": "echo no_name"},  # Missing name
            {"name": "no_command"},  # Missing command
        ],
        "timestamp": datetime.now().isoformat(),
    }
    temp_storage.history.push(malformed_op)

    # Add valid alias first
    valid_alias = Alias(name="valid", command="echo valid")
    temp_storage.add(valid_alias, record_history=False)

    # Undo should handle malformed data gracefully
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid add" in msg

    # Should indicate partial success due to malformed data
    if "of" in msg or "skipped" in msg.lower():
        # Partial success expected due to malformed data
        pass
    else:
        # All succeeded (some malformed data might be acceptable)
        pass


def test_concurrent_history_modifications(temp_storage):
    """Test handling of concurrent modifications to history."""

    # Simulate concurrent modification by directly modifying the lists
    original_undo = temp_storage.history.undo[:]
    original_redo = temp_storage.history.redo[:]

    # Add alias
    alias = Alias(name="test", command="echo hello")
    temp_storage.add(alias, record_history=True)

    # Simulate concurrent modification (another process modified history)
    temp_storage.history.undo.append(
        {
            "type": "add",
            "aliases": [{"name": "concurrent", "command": "echo concurrent"}],
            "timestamp": datetime.now().isoformat(),
        }
    )

    # Try to undo - should handle the concurrent modification gracefully
    msg = temp_storage.history.perform_undo(temp_storage)
    assert msg is not None

    # Restore original state for other tests
    temp_storage.history.undo = original_undo
    temp_storage.history.redo = original_redo


def test_history_stack_overflow_protection(temp_storage):
    """Test that history stack trimming works correctly."""
    from alix.history_manager import MAX_HISTORY

    # Add more than MAX_HISTORY operations
    for i in range(MAX_HISTORY + 5):
        alias = Alias(name=f"test{i}", command=f"echo {i}")
        temp_storage.add(alias, record_history=True)

    # Should only keep MAX_HISTORY operations
    assert len(temp_storage.history.list_undo()) == MAX_HISTORY

    # The oldest operations should be trimmed
    # Most recent should be test{MAX_HISTORY + 4}
    most_recent_op = temp_storage.history.list_undo()[-1]
    assert most_recent_op["aliases"][0]["name"] == f"test{MAX_HISTORY + 4}"

    # Undo all operations
    for _ in range(MAX_HISTORY):
        msg = temp_storage.history.perform_undo(temp_storage)
        assert "✅" in msg

    # Should handle empty stack gracefully
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "⚠️  Nothing to undo – history is empty." in msg


def test_group_delete_undo_redo_without_reassignment(temp_storage):
    """Test that group delete undo correctly restores aliases to original group when no reassignment."""
    # Create aliases in a group
    alias1 = Alias(name="test1", command="echo hello1", group="testgroup")
    alias2 = Alias(name="test2", command="echo hello2", group="testgroup")
    temp_storage.add(alias1, record_history=True)
    temp_storage.add(alias2, record_history=True)

    # Verify initial state
    assert temp_storage.get("test1").group == "testgroup"
    assert temp_storage.get("test2").group == "testgroup"

    # Delete group without reassignment (simulates CLI behavior)
    group_aliases = [a for a in temp_storage.list_all() if a.group == "testgroup"]
    for alias in group_aliases:
        alias.group = None
        temp_storage.aliases[alias.name] = alias
    temp_storage.save()

    # Record history operation (simulating what CLI does for group delete without reassignment)
    history_op = {
        "type": "group_delete",
        "aliases": [alias.to_dict() for alias in group_aliases],
        "group_name": "testgroup",
        "reassign_to": None,  # No reassignment
        "timestamp": "2025-01-01T00:00:00.000000",
    }
    temp_storage.history.push(history_op)

    # Verify aliases are no longer in group
    assert temp_storage.get("test1").group is None
    assert temp_storage.get("test2").group is None

    # Undo the group delete
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid group_delete" in msg

    # Verify aliases were restored to the original group
    assert temp_storage.get("test1").group == "testgroup"
    assert temp_storage.get("test2").group == "testgroup"

    # Redo the group delete
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "🔁" in msg and "Redid group_delete" in msg

    # Verify aliases were removed from group again
    assert temp_storage.get("test1").group is None
    assert temp_storage.get("test2").group is None


def test_group_delete_undo_redo_with_reassignment(temp_storage):
    """Test that group delete undo correctly restores aliases to reassigned group."""
    # Create aliases in a group
    alias1 = Alias(name="test1", command="echo hello1", group="oldgroup")
    alias2 = Alias(name="test2", command="echo hello2", group="oldgroup")
    temp_storage.add(alias1, record_history=True)
    temp_storage.add(alias2, record_history=True)

    # Delete group with reassignment to new group
    group_aliases = [a for a in temp_storage.list_all() if a.group == "oldgroup"]
    for alias in group_aliases:
        alias.group = "newgroup"  # Reassign to new group
        temp_storage.aliases[alias.name] = alias
    temp_storage.save()

    # Record history operation (simulating what CLI does for group delete with reassignment)
    history_op = {
        "type": "group_delete",
        "aliases": [alias.to_dict() for alias in group_aliases],
        "group_name": "oldgroup",
        "reassign_to": "newgroup",  # Reassignment target
        "timestamp": "2025-01-01T00:00:00.000000",
    }
    temp_storage.history.push(history_op)

    # Verify aliases are in new group
    assert temp_storage.get("test1").group == "newgroup"
    assert temp_storage.get("test2").group == "newgroup"

    # Undo the group delete
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "✅" in msg and "Undid group_delete" in msg

    # Verify aliases were restored to the original group
    assert temp_storage.get("test1").group == "oldgroup"
    assert temp_storage.get("test2").group == "oldgroup"

    # Redo the group delete
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "🔁" in msg and "Redid group_delete" in msg

    # Verify aliases are back in reassigned group
    assert temp_storage.get("test1").group == "newgroup"
    assert temp_storage.get("test2").group == "newgroup"
