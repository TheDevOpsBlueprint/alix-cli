import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from alix.models import Alias

HISTORY_FILE = Path.home() / ".alix" / "history.json"
MAX_HISTORY = 20


class HistoryManager:
    """Safe history manager for undo/redo of alias operations."""

    def __init__(self, path: Path = HISTORY_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.undo: List[Dict[str, Any]] = []
        self.redo: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.undo = []
            self.redo = []
            return
        try:
            with open(self.path, "r") as fh:
                data = json.load(fh)
                self.undo = data.get("undo", []) or []
                self.redo = data.get("redo", []) or []
        except json.JSONDecodeError:
            # corrupted history file -> reset to empty stacks
            self.undo = []
            self.redo = []
        except OSError:
            self.undo = []
            self.redo = []

    def save(self) -> None:
        payload = {"undo": self.undo[-MAX_HISTORY:], "redo": self.redo[-MAX_HISTORY:]}
        try:
            with open(self.path, "w") as fh:
                json.dump(payload, fh, indent=2)
        except OSError:
            # Best effort: fail silently (higher-level code may log)
            pass

    def push(self, op: Dict[str, Any]) -> None:
        """Push new operation onto undo stack and clear redo."""
        if "type" not in op or "aliases" not in op:
            raise ValueError(f"Invalid operation: {op}")
        op = dict(op)
        op.setdefault("timestamp", datetime.now().isoformat())
        self.undo.append(op)
        # Trim undo to MAX_HISTORY
        if len(self.undo) > MAX_HISTORY:
            self.undo = self.undo[-MAX_HISTORY:]
        # Clear redo (new branch)
        self.redo = []
        self.save()

    def _format_message(self, action: str, op_type: str, count: int, total: int, skipped: int = 0) -> str:
        """Format user-friendly messages with emojis and proper grammar."""
        if skipped > 0:
            if action in ["Undid", "Redid"]:
                return f"{action} {op_type} ({count} of {total} aliases {'restored' if 'remove' in op_type else 'processed'}, {skipped} skipped)"
            else:
                return f"{action} {op_type} ({count} of {total} aliases {'restored' if 'remove' in op_type else 'processed'}, {skipped} skipped)"

        if count != total:
            return f"{action} {op_type} ({count} of {total} aliases {'restored' if 'remove' in op_type else 'processed'})"

        # Handle pluralization
        alias_word = "aliases" if count != 1 else "alias"
        if op_type == "remove_group":
            return f"{action} {op_type} ({count} {alias_word} restored)"
        elif op_type in ["add", "import"]:
            return f"{action} {op_type} ({count} {alias_word} {'added' if action == 'Redid' else 'removed'})"
        elif op_type == "edit":
            return f"{action} {op_type} ({count} {alias_word} {'updated' if action == 'Redid' else 'restored'})"
        elif op_type in ["group_add", "group_remove", "tag_add", "tag_remove", "tag_rename", "tag_delete", "group_delete", "group_import"]:
            return f"{action} {op_type} ({count} {alias_word} {'processed' if action == 'Redid' else 'processed'})"
        elif op_type == "rename":
            return f"{action} {op_type} ({count} {alias_word} {'renamed' if action == 'Redid' else 'renamed back'})"
        elif op_type == "group_delete":
            return f"{action} {op_type} ({count} {alias_word} {'reassigned' if action == 'Redid' else 'reassigned'})"
        else:
            return f"{action} {op_type} ({count} {alias_word} {'removed' if action == 'Redid' else 'restored'})"

    def _execute_undo_operation(self, storage, op: Dict[str, Any]) -> Tuple[str, int, int]:
        """Execute undo operation and return (message, performed_count, skipped_count)."""
        op_type = op.get("type")
        aliases = op.get("aliases", [])
        performed = 0
        skipped = 0

        if op_type == "add":
            # inverse: remove by name
            for a in aliases:
                name = a.get("name")
                if not name:
                    skipped += 1
                    continue
                try:
                    if storage.remove(name, record_history=False):
                        performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type in ("remove", "remove_group"):
            # inverse: re-add aliases
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                except Exception:
                    skipped += 1
                    continue
                try:
                    if storage.add(alias_obj, record_history=False):
                        performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type == "edit":
            # inverse: restore original aliases
            original_aliases = op.get("aliases", [])
            for a in original_aliases:
                try:
                    alias_obj = self._load_alias(a)
                except Exception:
                    skipped += 1
                    continue
                try:
                    # Remove current version and add original
                    storage.remove(alias_obj.name, record_history=False)
                    if storage.add(alias_obj, record_history=False):
                        performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type == "import":
            # inverse: remove all imported aliases
            for a in aliases:
                name = a.get("name")
                if not name:
                    skipped += 1
                    continue
                try:
                    if storage.remove(name, record_history=False):
                        performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type == "rename":
            # inverse: rename back to old name
            old_name = op.get("old_name")
            new_name = op.get("new_name")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    # Remove the alias with new name and add with old name
                    storage.remove(new_name, record_history=False)
                    alias_obj.name = old_name
                    storage.add(alias_obj, record_history=False)
                    performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type == "group_add":
            # inverse: remove alias from group
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    alias_obj.group = None  # Remove from group
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            storage.save()

        elif op_type == "group_remove":
            # inverse: add alias back to group
            group_name = op.get("group_name")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    alias_obj.group = group_name  # Restore to group
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            storage.save()

        elif op_type == "group_delete":
            # inverse: restore group assignments
            reassign_to = op.get("reassign_to")
            group_name = op.get("group_name")

            # If reassign_to is None, restore to the original group name
            # If reassign_to has a value, it means aliases were reassigned, so restore to that group
            restore_group = reassign_to if reassign_to is not None else group_name

            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    alias_obj.group = restore_group  # Restore to correct group
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            storage.save()

        elif op_type == "tag_add":
            # inverse: remove added tags
            added_tags = op.get("added_tags", [])
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    for tag in added_tags:
                        if tag in alias_obj.tags:
                            alias_obj.tags.remove(tag)
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        elif op_type == "tag_remove":
            # inverse: restore removed tags
            removed_tags = op.get("removed_tags", [])
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    for tag in removed_tags:
                        if tag not in alias_obj.tags:
                            alias_obj.tags.append(tag)
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        elif op_type == "tag_rename":
            # inverse: rename back to old tag
            old_tag = op.get("old_tag")
            new_tag = op.get("new_tag")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    if new_tag in alias_obj.tags:
                        alias_obj.tags = [old_tag if tag == new_tag else tag for tag in alias_obj.tags]
                        storage.aliases[alias_obj.name] = alias_obj
                        performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        elif op_type == "tag_delete":
            # inverse: restore deleted tag
            deleted_tag = op.get("deleted_tag")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    if deleted_tag not in alias_obj.tags:
                        alias_obj.tags.append(deleted_tag)
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        # group_add, group_remove, and group_delete undo are handled above

        elif op_type == "group_import":
            # inverse: remove imported aliases from group
            group_name = op.get("group_name")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    if alias_obj.group == group_name:
                        alias_obj.group = None  # Remove from imported group
                        storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        return self._format_message("Undid", op_type, performed, len(aliases), skipped), performed, skipped

    def _execute_redo_operation(self, storage, op: Dict[str, Any]) -> Tuple[str, int, int]:
        """Execute redo operation and return (message, performed_count, skipped_count)."""
        op_type = op.get("type")
        aliases = op.get("aliases", [])
        performed = 0
        skipped = 0

        if op_type == "add":
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                except Exception:
                    skipped += 1
                    continue
                try:
                    if storage.add(alias_obj, record_history=False):
                        performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type in ("remove", "remove_group"):
            for a in aliases:
                name = a.get("name")
                if not name:
                    skipped += 1
                    continue
                try:
                    if storage.remove(name, record_history=False):
                        performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type == "edit":
            # redo: apply the new aliases
            new_aliases = op.get("new_aliases", [])
            for a in new_aliases:
                try:
                    alias_obj = self._load_alias(a)
                except Exception:
                    skipped += 1
                    continue
                try:
                    # Remove current version and add new version
                    storage.remove(alias_obj.name, record_history=False)
                    if storage.add(alias_obj, record_history=False):
                        performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type == "import":
            # redo: re-import all aliases
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                except Exception:
                    skipped += 1
                    continue
                try:
                    if storage.add(alias_obj, record_history=False):
                        performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type == "rename":
            # redo: rename to new name again
            old_name = op.get("old_name")
            new_name = op.get("new_name")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    # Remove the alias with old name and add with new name
                    storage.remove(old_name, record_history=False)
                    alias_obj.name = new_name
                    storage.add(alias_obj, record_history=False)
                    performed += 1
                except Exception:
                    skipped += 1
                    continue

        elif op_type == "group_add":
            # redo: add alias back to group
            group_name = op.get("group_name")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    alias_obj.group = group_name  # Restore to group
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        elif op_type == "group_remove":
            # redo: remove alias from group again
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    alias_obj.group = None  # Remove from group
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        elif op_type == "group_delete":
            # redo: delete group again (restore original group assignments)
            reassign_to = op.get("reassign_to")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    alias_obj.group = reassign_to  # Restore to reassign target (None if no reassignment)
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        elif op_type == "tag_add":
            # redo: add tags back
            added_tags = op.get("added_tags", [])
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    for tag in added_tags:
                        if tag not in alias_obj.tags:
                            alias_obj.tags.append(tag)
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        elif op_type == "tag_remove":
            # redo: remove tags again
            removed_tags = op.get("removed_tags", [])
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    for tag in removed_tags:
                        if tag in alias_obj.tags:
                            alias_obj.tags.remove(tag)
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        elif op_type == "tag_rename":
            # redo: rename to new tag again
            old_tag = op.get("old_tag")
            new_tag = op.get("new_tag")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    if old_tag in alias_obj.tags:
                        alias_obj.tags = [new_tag if tag == old_tag else tag for tag in alias_obj.tags]
                        storage.aliases[alias_obj.name] = alias_obj
                        performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        elif op_type == "tag_delete":
            # redo: delete tag again
            deleted_tag = op.get("deleted_tag")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    if deleted_tag in alias_obj.tags:
                        alias_obj.tags.remove(deleted_tag)
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        # group_add, group_remove, and group_delete redo are handled above

        elif op_type == "group_import":
            # redo: restore aliases to imported group
            group_name = op.get("group_name")
            for a in aliases:
                try:
                    alias_obj = self._load_alias(a)
                    alias_obj.group = group_name  # Restore to imported group
                    storage.aliases[alias_obj.name] = alias_obj
                    performed += 1
                except Exception:
                    skipped += 1
                    continue
            # Ensure changes are saved to disk
            storage.save()

        return self._format_message("Redid", op_type, performed, len(aliases), skipped), performed, skipped

    def list_undo(self) -> List[Dict[str, Any]]:
        return list(self.undo)

    def list_redo(self) -> List[Dict[str, Any]]:
        return list(self.redo)

    def _load_alias(self, data: Dict[str, Any]) -> Alias:
        try:
            return Alias.from_dict(data)
        except Exception:
            # If invalid alias data, raise so caller can skip
            raise

    def perform_undo(self, storage) -> str:
        """Undo last op. storage must implement add(alias, record_history=False) and remove(name, record_history=False)."""
        if not self.undo:
            return "⚠️  Nothing to undo – history is empty."

        op = self.undo.pop()
        message, performed, skipped = self._execute_undo_operation(storage, op)

        # Add to redo stack and trim
        self.redo.append(op)
        if len(self.redo) > MAX_HISTORY:
            self.redo = self.redo[-MAX_HISTORY:]
        self.save()

        return f"✅ {message}"

    def perform_redo(self, storage) -> str:
        """Redo last undone op. storage must implement add(alias, record_history=False) and remove(name, record_history=False)."""
        if not self.redo:
            return "⚠️  Nothing to redo – already at the latest state."

        op = self.redo.pop()
        message, performed, skipped = self._execute_redo_operation(storage, op)

        # Add to undo stack and trim
        self.undo.append(op)
        if len(self.undo) > MAX_HISTORY:
            self.undo = self.undo[-MAX_HISTORY:]
        self.save()

        return f"🔁 {message}"

    def perform_undo_by_id(self, storage, operation_id: int) -> str:
        """Undo a specific operation by its index (1-based, most recent first)."""
        if operation_id < 1 or operation_id > len(self.undo):
            return f"❌ Invalid operation ID: {operation_id}. Valid range: 1-{len(self.undo)}"

        # Get the operation (undo list is in chronological order, most recent last)
        # So index 1 is the most recent (last item), index len(undo) is the oldest (first item)
        op_index = len(self.undo) - operation_id
        op = self.undo[op_index]

        # Remove the operation from undo stack
        del self.undo[op_index]

        # Execute the undo operation
        message, performed, skipped = self._execute_undo_operation(storage, op)

        # Add to redo stack and trim
        self.redo.append(op)
        if len(self.redo) > MAX_HISTORY:
            self.redo = self.redo[-MAX_HISTORY:]
        self.save()

        return f"✅ {message}"

    def perform_redo_by_id(self, storage, operation_id: int) -> str:
        """Redo a specific operation by its index (1-based, most recent first)."""
        if operation_id < 1 or operation_id > len(self.redo):
            return f"❌ Invalid operation ID: {operation_id}. Valid range: 1-{len(self.redo)}"

        # Get the operation (redo list is in chronological order, most recent last)
        op_index = len(self.redo) - operation_id
        op = self.redo[op_index]

        # Remove the operation from redo stack
        del self.redo[op_index]

        # Execute the redo operation
        message, performed, skipped = self._execute_redo_operation(storage, op)

        # Add to undo stack and trim
        self.undo.append(op)
        if len(self.undo) > MAX_HISTORY:
            self.undo = self.undo[-MAX_HISTORY:]
        self.save()

        return f"🔁 {message}"
