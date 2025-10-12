"""Tests for usage tracking functionality"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from alix.models import Alias, UsageRecord
from alix.storage import AliasStorage
from alix.usage_tracker import UsageTracker, UsageAnalytics
from alix.shell_wrapper import ShellWrapper


class TestUsageRecord:
    """Test UsageRecord model"""
    
    def test_usage_record_creation(self):
        """Test creating a usage record"""
        timestamp = datetime.now()
        record = UsageRecord(timestamp=timestamp, context="test context")
        
        assert record.timestamp == timestamp
        assert record.context == "test context"
    
    def test_usage_record_to_dict(self):
        """Test converting usage record to dictionary"""
        timestamp = datetime.now()
        record = UsageRecord(timestamp=timestamp, context="test context")
        
        data = record.to_dict()
        
        assert data["timestamp"] == timestamp.isoformat()
        assert data["context"] == "test context"
    
    def test_usage_record_from_dict(self):
        """Test creating usage record from dictionary"""
        timestamp = datetime.now()
        data = {
            "timestamp": timestamp.isoformat(),
            "context": "test context"
        }
        
        record = UsageRecord.from_dict(data)
        
        assert record.timestamp == timestamp
        assert record.context == "test context"


class TestAliasUsageTracking:
    """Test alias usage tracking functionality"""
    
    def test_alias_record_usage(self):
        """Test recording usage for an alias"""
        alias = Alias(name="test", command="echo hello")
        initial_count = alias.used_count
        
        alias.record_usage("test context")
        
        assert alias.used_count == initial_count + 1
        assert alias.last_used is not None
        assert len(alias.usage_history) == 1
        assert alias.usage_history[0].context == "test context"
    
    def test_alias_usage_stats(self):
        """Test getting usage statistics for an alias"""
        alias = Alias(name="test", command="echo hello")
        
        # Test with no usage
        stats = alias.get_usage_stats()
        assert stats["total_uses"] == 0
        assert stats["first_used"] is None
        assert stats["last_used"] is None
        assert stats["usage_frequency"] == 0
        
        # Test with usage
        alias.record_usage()
        alias.record_usage()
        
        stats = alias.get_usage_stats()
        assert stats["total_uses"] == 2
        assert stats["first_used"] is not None
        assert stats["last_used"] is not None
        assert stats["usage_frequency"] > 0
    
    def test_alias_usage_history_limit(self):
        """Test that usage history is limited to prevent bloat"""
        alias = Alias(name="test", command="echo hello")
        
        # Record more than 100 uses
        for i in range(150):
            alias.record_usage()
        
        # Should only keep last 100 records
        assert len(alias.usage_history) == 100
        assert alias.used_count == 150


class TestUsageTracker:
    """Test UsageTracker functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def usage_tracker(self, temp_dir):
        """Create UsageTracker instance for testing"""
        return UsageTracker(temp_dir)
    
    def test_track_alias_usage(self, usage_tracker):
        """Test tracking alias usage"""
        usage_tracker.track_alias_usage("test_alias", "test context")
        
        assert "test_alias" in usage_tracker.tracking_data["alias_usage"]
        assert usage_tracker.tracking_data["alias_usage"]["test_alias"]["total_uses"] == 1
        assert usage_tracker.tracking_data["alias_usage"]["test_alias"]["last_used"] is not None
    
    def test_get_usage_analytics(self, usage_tracker):
        """Test getting usage analytics"""
        # Create test aliases
        aliases = [
            Alias(name="alias1", command="echo hello", used_count=5),
            Alias(name="alias2", command="echo world", used_count=0),
            Alias(name="alias3", command="echo test", used_count=10)
        ]
        
        analytics = usage_tracker.get_usage_analytics(aliases)
        
        assert analytics.total_aliases == 3
        assert analytics.total_uses == 15
        assert analytics.most_used_alias == "alias3"
        assert analytics.least_used_alias == "alias2"
        assert "alias2" in analytics.unused_aliases
        assert analytics.average_usage_per_alias == 5.0
    
    def test_get_alias_usage_history(self, usage_tracker):
        """Test getting usage history for a specific alias"""
        # Track some usage
        usage_tracker.track_alias_usage("test_alias")
        usage_tracker.track_alias_usage("test_alias")
        
        history = usage_tracker.get_alias_usage_history("test_alias", days=30)
        
        assert len(history) == 2
        assert all("date" in record for record in history)
    
    def test_cleanup_old_data(self, usage_tracker):
        """Test cleaning up old tracking data"""
        # Add some old data
        old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        usage_tracker.tracking_data["daily_usage"] = {old_date: 5}
        
        usage_tracker.cleanup_old_data(days_to_keep=30)
        
        assert old_date not in usage_tracker.tracking_data["daily_usage"]
    
    def test_export_analytics(self, usage_tracker, temp_dir):
        """Test exporting analytics data"""
        # Add some tracking data
        usage_tracker.track_alias_usage("test_alias")
        
        output_file = temp_dir / "analytics.json"
        usage_tracker.export_analytics(output_file)
        
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert "exported_at" in data
        assert "tracking_data" in data
        assert "summary" in data

    def test_initialization_without_storage_path(self, temp_dir):
        """Test initialization without providing storage_path"""
        # Mock the home directory to use temp_dir for this test
        with patch('pathlib.Path.home', return_value=temp_dir):
            # Create a UsageTracker without providing storage_path
            # This should use the default path and create the directory
            usage_tracker = UsageTracker()

            # Check that the tracking directory was created
            assert usage_tracker.tracking_dir.exists()
            assert usage_tracker.tracking_dir.is_dir()

            # Check that the tracking file path is set correctly
            expected_path = temp_dir / ".alix" / "usage_tracking.json"
            assert usage_tracker.tracking_file == expected_path

    def test_load_tracking_data_corrupted_file(self, usage_tracker):
        """Test loading corrupted tracking data file"""
        # Create a corrupted JSON file
        corrupted_content = "{ invalid json content }"
        usage_tracker.tracking_file.write_text(corrupted_content)

        # Loading should handle the error gracefully and return empty dict
        data = usage_tracker._load_tracking_data()
        assert data == {}

    def test_usage_date_cleanup(self, usage_tracker):
        """Test usage date cleanup when more than 30 dates"""
        alias_name = "test_alias"

        # Track usage more than 30 times to trigger cleanup
        for i in range(35):
            usage_tracker.track_alias_usage(alias_name)

        # Check that only last 30 usage dates are kept
        alias_data = usage_tracker.tracking_data["alias_usage"][alias_name]
        usage_dates = alias_data["usage_dates"]
        assert len(usage_dates) == 30

        # Verify total uses is still correct
        assert alias_data["total_uses"] == 35

    def test_get_usage_analytics_empty_aliases(self, usage_tracker):
        """Test getting usage analytics with empty aliases list"""
        # Test with empty aliases list
        analytics = usage_tracker.get_usage_analytics([])

        assert analytics.total_aliases == 0
        assert analytics.total_uses == 0
        assert analytics.most_used_alias is None
        assert analytics.least_used_alias is None
        assert analytics.unused_aliases == []
        assert analytics.recently_used == []
        assert analytics.usage_trends == {}
        assert analytics.average_usage_per_alias == 0.0
        assert analytics.most_productive_aliases == []

    def test_cleanup_old_data_daily_usage(self, usage_tracker):
        """Test cleaning up old daily usage data"""
        # Add old and new daily usage data
        old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        new_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

        usage_tracker.tracking_data["daily_usage"] = {
            old_date: 5,
            new_date: 3
        }

        # Clean up data older than 30 days
        usage_tracker.cleanup_old_data(days_to_keep=30)

        # Old data should be removed, new data should remain
        assert old_date not in usage_tracker.tracking_data["daily_usage"]
        assert new_date in usage_tracker.tracking_data["daily_usage"]
        assert usage_tracker.tracking_data["daily_usage"][new_date] == 3

    def test_cleanup_old_data_alias_usage(self, usage_tracker):
        """Test cleaning up old alias usage data"""
        # Add old and new usage dates for an alias
        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        new_date = (datetime.now() - timedelta(days=10)).isoformat()

        alias_name = "test_alias"
        usage_tracker.tracking_data["alias_usage"] = {
            alias_name: {
                "total_uses": 2,
                "last_used": new_date,
                "usage_dates": [old_date, new_date]
            }
        }

        # Clean up data older than 30 days
        usage_tracker.cleanup_old_data(days_to_keep=30)

        # Old usage date should be removed, new date should remain
        remaining_dates = usage_tracker.tracking_data["alias_usage"][alias_name]["usage_dates"]
        assert old_date not in remaining_dates
        assert new_date in remaining_dates
        assert len(remaining_dates) == 1


class TestAliasStorageIntegration:
    """Test integration of usage tracking with AliasStorage"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Create AliasStorage instance for testing"""
        return AliasStorage(temp_dir / "aliases.json")
    
    def test_track_usage_integration(self, storage):
        """Test tracking usage through storage"""
        # Add an alias
        alias = Alias(name="test", command="echo hello")
        storage.add(alias)
        
        # Track usage
        storage.track_usage("test", "test context")
        
        # Check that usage was recorded
        updated_alias = storage.get("test")
        assert updated_alias.used_count == 1
        assert updated_alias.last_used is not None
        assert len(updated_alias.usage_history) == 1
    
    def test_get_usage_analytics(self, storage):
        """Test getting usage analytics through storage"""
        # Add some aliases with different usage patterns
        aliases = [
            Alias(name="alias1", command="echo hello", used_count=5),
            Alias(name="alias2", command="echo world", used_count=0),
            Alias(name="alias3", command="echo test", used_count=10)
        ]
        
        for alias in aliases:
            storage.add(alias)
        
        analytics = storage.get_usage_analytics()
        
        assert analytics["total_aliases"] == 3
        assert analytics["total_uses"] == 15
        assert analytics["most_used_alias"] == "alias3"
        assert analytics["least_used_alias"] == "alias2"
        assert "alias2" in analytics["unused_aliases"]


class TestShellWrapper:
    """Test ShellWrapper functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        import tempfile
        import shutil
        import os
        # Use a unique name to avoid conflicts
        temp_dir = os.path.join(tempfile.gettempdir(), f"alix_test_{os.getpid()}_{id(self)}")
        try:
            os.makedirs(temp_dir, exist_ok=True)
            yield Path(temp_dir)
        finally:
            # Clean up manually to avoid the rmtree issue
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
    
    @pytest.fixture
    def wrapper(self, temp_dir):
        """Create ShellWrapper instance for testing"""
        # Use a specific file path within the temp directory
        storage_file = temp_dir / "aliases.json"
        return ShellWrapper(storage_file)
    
    def test_generate_tracking_function(self, wrapper, temp_dir):
        """Test generating tracking function for an alias"""
        # Add an alias to the wrapper's storage
        alias = Alias(name="test", command="echo hello")
        wrapper.storage.add(alias)
        
        function = wrapper.generate_tracking_function("test")
        
        assert "test()" in function
        assert "echo hello" in function
        assert "alix track" in function
    
    def test_generate_all_tracking_functions(self, wrapper, temp_dir):
        """Test generating tracking functions for all aliases"""
        # Add some aliases to the wrapper's storage
        aliases = [
            Alias(name="alias1", command="echo hello"),
            Alias(name="alias2", command="echo world")
        ]
        
        for alias in aliases:
            wrapper.storage.add(alias)
        
        functions = wrapper.generate_all_tracking_functions()
        
        assert "alias1()" in functions
        assert "alias2()" in functions
        assert "echo hello" in functions
        assert "echo world" in functions
    
    def test_generate_shell_integration_script(self, wrapper, temp_dir):
        """Test generating shell integration script"""
        # Add an alias to the wrapper's storage
        alias = Alias(name="test", command="echo hello")
        wrapper.storage.add(alias)
        
        script = wrapper.generate_shell_integration_script("bash")
        
        assert "#!/bin/bash" in script
        assert "track_alias_usage" in script
        assert "test()" in script
    
    def test_create_standalone_tracking_script(self, wrapper, temp_dir):
        """Test creating standalone tracking script"""
        # Add an alias to the wrapper's storage
        alias = Alias(name="test", command="echo hello")
        wrapper.storage.add(alias)
        
        output_path = temp_dir / "tracking.sh"
        success = wrapper.create_standalone_tracking_script(output_path, "bash")
        
        assert success
        assert output_path.exists()
        assert output_path.stat().st_mode & 0o755  # Check executable permissions


class TestUsageAnalytics:
    """Test UsageAnalytics data class"""
    
    def test_usage_analytics_creation(self):
        """Test creating UsageAnalytics instance"""
        analytics = UsageAnalytics(
            total_aliases=10,
            total_uses=50,
            most_used_alias="test",
            least_used_alias="unused",
            unused_aliases=["unused"],
            recently_used=["test"],
            usage_trends={"2023-01-01": 5},
            average_usage_per_alias=5.0,
            most_productive_aliases=[("test", 10)]
        )
        
        assert analytics.total_aliases == 10
        assert analytics.total_uses == 50
        assert analytics.most_used_alias == "test"
        assert analytics.least_used_alias == "unused"
        assert "unused" in analytics.unused_aliases
        assert "test" in analytics.recently_used
        assert analytics.usage_trends["2023-01-01"] == 5
        assert analytics.average_usage_per_alias == 5.0
        assert analytics.most_productive_aliases[0] == ("test", 10)


class TestIntegration:
    """Integration tests for the complete usage tracking system"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_complete_usage_tracking_workflow(self, temp_dir):
        """Test complete workflow from alias creation to analytics"""
        # Create storage
        storage = AliasStorage(temp_dir / "aliases.json")
        
        # Add aliases
        aliases = [
            Alias(name="alias1", command="echo hello"),
            Alias(name="alias2", command="echo world"),
            Alias(name="alias3", command="echo test")
        ]
        
        for alias in aliases:
            storage.add(alias)
        
        # Track usage
        storage.track_usage("alias1", "context1")
        storage.track_usage("alias1", "context2")
        storage.track_usage("alias3", "context3")
        
        # Get analytics
        analytics = storage.get_usage_analytics()
        
        # Verify results
        assert analytics["total_aliases"] == 3
        assert analytics["total_uses"] == 3
        assert analytics["most_used_alias"] == "alias1"
        assert analytics["least_used_alias"] == "alias2"
        assert "alias2" in analytics["unused_aliases"]
        assert "alias1" in analytics["recently_used"]
        assert "alias3" in analytics["recently_used"]
    
    def test_persistence_across_sessions(self, temp_dir):
        """Test that usage tracking persists across storage sessions"""
        # First session: create storage and track usage
        storage1 = AliasStorage(temp_dir / "aliases.json")
        alias = Alias(name="test", command="echo hello")
        storage1.add(alias)
        storage1.track_usage("test", "context1")
        
        # Second session: load storage and verify data
        storage2 = AliasStorage(temp_dir / "aliases.json")
        loaded_alias = storage2.get("test")
        
        assert loaded_alias.used_count == 1
        assert loaded_alias.last_used is not None
        assert len(loaded_alias.usage_history) == 1
        assert loaded_alias.usage_history[0].context == "context1"
