"""Data models for aliases"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

# Test alias constants for safe testing
TEST_ALIAS_NAME = "alix-test-echo"
TEST_ALIAS_CMD = "echo 'alix test working!'"


@dataclass
class Alias:
    """Represents a shell alias"""
    name: str
    command: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    used_count: int = 0
    shell: Optional[str] = None  # bash, zsh, fish, etc.
    group: Optional[str] = None 

    def to_dict(self) -> dict:
        """Convert alias to dictionary for storage"""
        return {
            "name": self.name,
            "command": self.command,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "used_count": self.used_count,
            "shell": self.shell,
            "group": self.group
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Alias":
        """Create alias from dictionary"""
        data = data.copy()
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

    def __str__(self) -> str:
        """String representation for display"""
        return f"{self.name}='{self.command}'"