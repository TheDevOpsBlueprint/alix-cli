import pytest
from datetime import datetime

from alix.models import Alias
from alix.storage import AliasStorage
from alix.history_manager import MAX_HISTORY


@pytest.fixture
def temp_storage(tmp_path):
    """Fixture for temporary storage to avoid file pollution."""
    storage_path = tmp_path / "aliases.json"
    storage = AliasStorage(storage_path=storage_path)
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
    assert "Nothing to undo." in msg
    assert len(temp_storage.history.list_redo()) == 0
    
    # Redo on empty
    msg = temp_storage.history.perform_redo(temp_storage)
    assert "Nothing to redo." in msg
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
    with open(history_path, 'w') as f:
        f.write("{invalid json")
    
    # Create storage with the corrupted history file
    storage = AliasStorage(storage_path=tmp_path / "aliases.json")
    
    # Verify stacks are empty (reset on corruption)
    assert len(storage.history.list_undo()) == 0
    assert len(storage.history.list_redo()) == 0
    
    # Undo/redo should not crash
    msg = storage.history.perform_undo(storage)
    assert "Nothing to undo." in msg


def test_partial_failures(temp_storage):
    # Add valid alias
    alias_valid = Alias(name="valid", command="echo ok")
    temp_storage.add(alias_valid, record_history=True)
    
    # Simulate corrupted alias data in history
    corrupted_op = {
        "type": "add",
        "aliases": [{"invalid": "data"}],  # Missing name
        "timestamp": datetime.now().isoformat()
    }
    temp_storage.history.push(corrupted_op)
    
    # Undo should handle gracefully
    msg = temp_storage.history.perform_undo(temp_storage)
    assert "skipped" in msg.lower()