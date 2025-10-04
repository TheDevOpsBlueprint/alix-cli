import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

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
            return "Nothing to undo."
        op = self.undo.pop()
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
            self.redo.append(op)
            # trim redo
            if len(self.redo) > MAX_HISTORY:
                self.redo = self.redo[-MAX_HISTORY:]
            self.save()
            msg = f"Undid add ({performed}/{len(aliases)} removed)"
            if skipped > 0:
                msg += f", {skipped} skipped"
            return msg

        if op_type in ("remove", "remove_group"):
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
            self.redo.append(op)
            if len(self.redo) > MAX_HISTORY:
                self.redo = self.redo[-MAX_HISTORY:]
            self.save()
            msg = f"Undid {op_type} ({performed}/{len(aliases)} restored)"
            if skipped > 0:
                msg += f", {skipped} skipped"
            return msg

        return f"Unknown operation type: {op_type}"

    def perform_redo(self, storage) -> str:
        """Redo last undone op. storage must implement add(alias, record_history=False) and remove(name, record_history=False)."""
        if not self.redo:
            return "Nothing to redo."
        op = self.redo.pop()
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
            self.undo.append(op)
            if len(self.undo) > MAX_HISTORY:
                self.undo = self.undo[-MAX_HISTORY:]
            self.save()
            msg = f"Redid add ({performed}/{len(aliases)} added)"
            if skipped > 0:
                msg += f", {skipped} skipped"
            return msg

        if op_type in ("remove", "remove_group"):
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
            self.undo.append(op)
            if len(self.undo) > MAX_HISTORY:
                self.undo = self.undo[-MAX_HISTORY:]
            self.save()
            msg = f"Redid {op_type} ({performed}/{len(aliases)} removed)"
            if skipped > 0:
                msg += f", {skipped} skipped"
            return msg

        return f"Unknown operation type: {op_type}"
