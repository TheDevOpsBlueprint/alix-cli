"""Data models for aliases"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import json

# Test alias constants for safe testing
TEST_ALIAS_NAME = "alix-test-echo"
TEST_ALIAS_CMD = "echo 'alix test working!'"


@dataclass
class UsageRecord:
    """Represents a single usage event of an alias"""
    timestamp: datetime
    context: Optional[str] = None  # Additional context like working directory, shell session, etc.
    
    def to_dict(self) -> dict:
        """Convert usage record to dictionary for storage"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UsageRecord":
        """Create usage record from dictionary"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            context=data.get("context")
        )


@dataclass
class Alias:
    """Represents a shell alias with usage tracking"""
    name: str
    command: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    used_count: int = 0
    shell: Optional[str] = None  # bash, zsh, fish, etc.
    last_used: Optional[datetime] = None
    usage_history: List[UsageRecord] = field(default_factory=list)

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
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_history": [record.to_dict() for record in self.usage_history]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Alias":
        """Create alias from dictionary"""
        data = data.copy()
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "last_used" in data and data["last_used"] and isinstance(data["last_used"], str):
            data["last_used"] = datetime.fromisoformat(data["last_used"])
        if "usage_history" in data:
            data["usage_history"] = [UsageRecord.from_dict(record) for record in data["usage_history"]]
        return cls(**data)
    
    def record_usage(self, context: Optional[str] = None) -> None:
        """Record a usage event for this alias"""
        now = datetime.now()
        self.used_count += 1
        self.last_used = now
        self.usage_history.append(UsageRecord(timestamp=now, context=context))
        
        # Keep only last 100 usage records to prevent storage bloat
        if len(self.usage_history) > 100:
            self.usage_history = self.usage_history[-100:]
    
    def get_usage_stats(self) -> Dict[str, any]:
        """Get usage statistics for this alias"""
        if not self.usage_history:
            return {
                "total_uses": self.used_count,
                "first_used": None,
                "last_used": self.last_used,
                "usage_frequency": 0,
                "recent_usage": []
            }
        
        # Calculate usage frequency (uses per day since creation)
        days_since_creation = (datetime.now() - self.created_at).days
        usage_frequency = self.used_count / max(days_since_creation, 1)
        
        # Get recent usage (last 10 records)
        recent_usage = self.usage_history[-10:] if len(self.usage_history) > 10 else self.usage_history
        
        return {
            "total_uses": self.used_count,
            "first_used": self.usage_history[0].timestamp if self.usage_history else None,
            "last_used": self.last_used,
            "usage_frequency": usage_frequency,
            "recent_usage": [record.to_dict() for record in recent_usage]
        }

    def __str__(self) -> str:
        """String representation for display"""
        return f"{self.name}='{self.command}'"