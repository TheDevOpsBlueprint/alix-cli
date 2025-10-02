"""Usage tracking functionality for aliases"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from alix.models import Alias, UsageRecord


@dataclass
class UsageAnalytics:
    """Analytics data for alias usage"""
    total_aliases: int
    total_uses: int
    most_used_alias: Optional[str]
    least_used_alias: Optional[str]
    unused_aliases: List[str]
    recently_used: List[str]
    usage_trends: Dict[str, int]  # Daily usage counts
    average_usage_per_alias: float
    most_productive_aliases: List[Tuple[str, int]]  # (name, chars_saved)


class UsageTracker:
    """Handles tracking and analytics of alias usage"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize usage tracker"""
        if storage_path:
            self.tracking_file = storage_path / "usage_tracking.json"
        else:
            self.tracking_dir = Path.home() / ".alix"
            self.tracking_file = self.tracking_dir / "usage_tracking.json"
            self.tracking_dir.mkdir(exist_ok=True)
        
        self.tracking_data = self._load_tracking_data()
    
    def _load_tracking_data(self) -> Dict:
        """Load tracking data from file"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                return {}
        return {}
    
    def _save_tracking_data(self) -> None:
        """Save tracking data to file"""
        with open(self.tracking_file, 'w') as f:
            json.dump(self.tracking_data, f, indent=2, default=str)
    
    def track_alias_usage(self, alias_name: str, context: Optional[str] = None) -> None:
        """Track usage of an alias"""
        now = datetime.now()
        date_key = now.strftime("%Y-%m-%d")
        
        # Initialize tracking data structure if needed
        if "daily_usage" not in self.tracking_data:
            self.tracking_data["daily_usage"] = {}
        if "alias_usage" not in self.tracking_data:
            self.tracking_data["alias_usage"] = {}
        if "last_updated" not in self.tracking_data:
            self.tracking_data["last_updated"] = now.isoformat()
        
        # Update daily usage
        if date_key not in self.tracking_data["daily_usage"]:
            self.tracking_data["daily_usage"][date_key] = 0
        self.tracking_data["daily_usage"][date_key] += 1
        
        # Update alias-specific usage
        if alias_name not in self.tracking_data["alias_usage"]:
            self.tracking_data["alias_usage"][alias_name] = {
                "total_uses": 0,
                "last_used": None,
                "usage_dates": []
            }
        
        self.tracking_data["alias_usage"][alias_name]["total_uses"] += 1
        self.tracking_data["alias_usage"][alias_name]["last_used"] = now.isoformat()
        
        # Add to usage dates (keep only last 30 days)
        usage_dates = self.tracking_data["alias_usage"][alias_name]["usage_dates"]
        usage_dates.append(now.isoformat())
        if len(usage_dates) > 30:
            usage_dates.pop(0)
        
        self.tracking_data["last_updated"] = now.isoformat()
        self._save_tracking_data()
    
    def get_usage_analytics(self, aliases: List[Alias]) -> UsageAnalytics:
        """Generate comprehensive usage analytics"""
        if not aliases:
            return UsageAnalytics(
                total_aliases=0,
                total_uses=0,
                most_used_alias=None,
                least_used_alias=None,
                unused_aliases=[],
                recently_used=[],
                usage_trends={},
                average_usage_per_alias=0.0,
                most_productive_aliases=[]
            )
        
        # Basic statistics
        total_uses = sum(alias.used_count for alias in aliases)
        most_used = max(aliases, key=lambda a: a.used_count) if aliases else None
        least_used = min(aliases, key=lambda a: a.used_count) if aliases else None
        
        # Unused aliases (never used)
        unused_aliases = [alias.name for alias in aliases if alias.used_count == 0]
        
        # Recently used (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recently_used = [
            alias.name for alias in aliases 
            if alias.last_used and alias.last_used >= week_ago
        ]
        
        # Usage trends (last 30 days)
        usage_trends = self.tracking_data.get("daily_usage", {})
        
        # Most productive aliases (by characters saved)
        most_productive = [
            (alias.name, len(alias.command) - len(alias.name))
            for alias in aliases
        ]
        most_productive.sort(key=lambda x: x[1], reverse=True)
        
        return UsageAnalytics(
            total_aliases=len(aliases),
            total_uses=total_uses,
            most_used_alias=most_used.name if most_used else None,
            least_used_alias=least_used.name if least_used else None,
            unused_aliases=unused_aliases,
            recently_used=recently_used,
            usage_trends=usage_trends,
            average_usage_per_alias=total_uses / len(aliases) if aliases else 0,
            most_productive_aliases=most_productive[:10]
        )
    
    def get_alias_usage_history(self, alias_name: str, days: int = 30) -> List[Dict]:
        """Get usage history for a specific alias"""
        alias_data = self.tracking_data.get("alias_usage", {}).get(alias_name, {})
        usage_dates = alias_data.get("usage_dates", [])
        
        # Filter to last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_usage = [
            date for date in usage_dates
            if datetime.fromisoformat(date) >= cutoff_date
        ]
        
        return [{"date": date, "count": 1} for date in recent_usage]
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> None:
        """Clean up old tracking data to prevent file bloat"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        # Clean daily usage data
        if "daily_usage" in self.tracking_data:
            self.tracking_data["daily_usage"] = {
                date: count for date, count in self.tracking_data["daily_usage"].items()
                if date >= cutoff_str
            }
        
        # Clean alias usage data
        if "alias_usage" in self.tracking_data:
            for alias_name in self.tracking_data["alias_usage"]:
                usage_dates = self.tracking_data["alias_usage"][alias_name].get("usage_dates", [])
                self.tracking_data["alias_usage"][alias_name]["usage_dates"] = [
                    date for date in usage_dates
                    if datetime.fromisoformat(date) >= cutoff_date
                ]
        
        self._save_tracking_data()
    
    def export_analytics(self, output_file: Path) -> None:
        """Export analytics data to a file"""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "tracking_data": self.tracking_data,
            "summary": {
                "total_days_tracked": len(self.tracking_data.get("daily_usage", {})),
                "total_aliases_tracked": len(self.tracking_data.get("alias_usage", {})),
                "last_updated": self.tracking_data.get("last_updated")
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
