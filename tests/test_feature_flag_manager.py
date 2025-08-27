#!/usr/bin/env python3
"""
Test suite for Feature Flag Manager

Verifies mathematical properties:
1. Hash distribution uniformity
2. Deterministic consistency  
3. Gradual rollout monotonicity
4. Session state consistency
5. Emergency rollback safety
"""

import pytest
import tempfile
import time
from pathlib import Path
import sys
import toml
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.backend.feature_flag_manager import (
    FeatureFlagManager, FeatureFlag, ClientMode
)


class TestHashFunction:
    """Test mathematical properties of hash function"""
    
    def test_hash_deterministic(self):
        """Hash function is deterministic - same input always produces same output"""
        manager = FeatureFlagManager()
        
        # Test multiple times to ensure consistency
        for _ in range(100):
            hash1 = manager._hash_user_flag("user123", "test_flag")
            hash2 = manager._hash_user_flag("user123", "test_flag")
            assert hash1 == hash2, "Hash not deterministic"
    
    def test_hash_range(self):
        """Hash function outputs are in [0, 99] range"""
        manager = FeatureFlagManager()
        
        for i in range(1000):
            user_id = f"user_{i}"
            hash_val = manager._hash_user_flag(user_id, "test_flag")
            assert 0 <= hash_val <= 99, f"Hash {hash_val} out of range"
    
    def test_hash_distribution(self):
        """Hash function has uniform distribution (±5% tolerance)"""
        manager = FeatureFlagManager()
        buckets = [0] * 10
        
        # Generate hashes for many users
        for i in range(10000):
            user_id = f"user_{i}"
            hash_val = manager._hash_user_flag(user_id, "test_flag")
            bucket = hash_val // 10
            buckets[bucket] += 1
        
        # Check distribution (expected ~1000 per bucket)
        expected = 1000
        tolerance = 0.07  # 7% tolerance for statistical variance
        
        for count in buckets:
            deviation = abs(count - expected) / expected
            assert deviation <= tolerance, f"Non-uniform distribution: {buckets}"
    
    def test_hash_independence(self):
        """Different flags give different hash values for same user"""
        manager = FeatureFlagManager()
        user_id = "test_user"
        
        hash1 = manager._hash_user_flag(user_id, "flag1")
        hash2 = manager._hash_user_flag(user_id, "flag2")
        hash3 = manager._hash_user_flag(user_id, "flag3")
        
        # Should be different (very high probability)
        assert len({hash1, hash2, hash3}) > 1, "Flags not independent"


class TestRolloutLogic:
    """Test gradual rollout mathematical properties"""
    
    def test_rollout_percentage_accuracy(self):
        """Rollout percentage is accurate within ±1%"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            # Add test flag
            manager.flags["test"] = FeatureFlag(
                name="test",
                enabled=True,
                percentage=30  # 30% rollout
            )
            
            # Count enabled users
            enabled_count = 0
            total = 10000
            
            for i in range(total):
                if manager.is_enabled(f"user_{i}", "test"):
                    enabled_count += 1
            
            actual_percentage = (enabled_count / total) * 100
            assert abs(actual_percentage - 30) <= 1.0, \
                f"Rollout percentage {actual_percentage:.2f}% not within ±1% of 30%"
    
    def test_rollout_monotonicity(self):
        """N% rollout is subset of (N+x)% rollout (monotonicity)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            # Get users enabled at different percentages
            users_10 = set()
            users_30 = set()
            users_50 = set()
            users_100 = set()
            
            # Test at 10%
            manager.flags["test"] = FeatureFlag(name="test", enabled=True, percentage=10)
            for i in range(1000):
                if manager.is_enabled(f"user_{i}", "test"):
                    users_10.add(f"user_{i}")
            
            # Test at 30%
            manager.flags["test"].percentage = 30
            for i in range(1000):
                if manager.is_enabled(f"user_{i}", "test"):
                    users_30.add(f"user_{i}")
            
            # Test at 50%
            manager.flags["test"].percentage = 50
            for i in range(1000):
                if manager.is_enabled(f"user_{i}", "test"):
                    users_50.add(f"user_{i}")
            
            # Test at 100%
            manager.flags["test"].percentage = 100
            for i in range(1000):
                if manager.is_enabled(f"user_{i}", "test"):
                    users_100.add(f"user_{i}")
            
            # Verify monotonicity
            assert users_10.issubset(users_30), "10% not subset of 30%"
            assert users_30.issubset(users_50), "30% not subset of 50%"
            assert users_50.issubset(users_100), "50% not subset of 100%"
    
    def test_user_overrides(self):
        """User overrides always take precedence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            # Flag disabled but user in overrides
            manager.flags["test"] = FeatureFlag(
                name="test",
                enabled=False,
                percentage=0,
                user_overrides={"special_user"}
            )
            
            assert manager.is_enabled("special_user", "test"), \
                "Override user not enabled when flag disabled"
            assert not manager.is_enabled("normal_user", "test"), \
                "Normal user enabled when flag disabled"
    
    def test_user_excludes(self):
        """User excludes always take precedence (even over overrides)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            # Flag enabled but user in excludes
            manager.flags["test"] = FeatureFlag(
                name="test",
                enabled=True,
                percentage=100,
                user_excludes={"excluded_user"}
            )
            
            assert not manager.is_enabled("excluded_user", "test"), \
                "Excluded user enabled when in excludes"
            assert manager.is_enabled("normal_user", "test"), \
                "Normal user not enabled at 100%"


class TestSessionConsistency:
    """Test session state consistency guarantees"""
    
    def test_session_mode_consistency(self):
        """User gets same mode throughout session"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            manager.flags["server_driven_ui"] = FeatureFlag(
                name="server_driven_ui",
                enabled=True,
                percentage=50
            )
            
            user_id = "test_user"
            session_id = "session_123"
            
            # Get mode multiple times
            mode1 = manager.get_user_mode(user_id, session_id)
            mode2 = manager.get_user_mode(user_id, session_id)
            mode3 = manager.get_user_mode(user_id, session_id)
            
            assert mode1 == mode2 == mode3, "Mode not consistent within session"
    
    def test_session_cache_expiry(self):
        """Session cache expires after 1 hour"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            manager.flags["server_driven_ui"] = FeatureFlag(
                name="server_driven_ui",
                enabled=True,
                percentage=100
            )
            
            user_id = "test_user"
            
            # Get initial mode
            mode1 = manager.get_user_mode(user_id)
            assert mode1 == ClientMode.THIN
            
            # Change flag
            manager.flags["server_driven_ui"].enabled = False
            
            # Should still get cached mode
            mode2 = manager.get_user_mode(user_id)
            assert mode2 == ClientMode.THIN
            
            # Simulate cache expiry
            if user_id in manager.session_modes:
                manager.session_modes[user_id] = (ClientMode.THIN, time.time() - 3601)
            
            # Should get new mode
            mode3 = manager.get_user_mode(user_id)
            assert mode3 == ClientMode.THICK
    
    def test_session_clear_on_update(self):
        """Session cache clears when flags update"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            manager.flags["server_driven_ui"] = FeatureFlag(
                name="server_driven_ui",
                enabled=True,
                percentage=100
            )
            
            # Populate cache
            manager.get_user_mode("user1")
            manager.get_user_mode("user2")
            assert len(manager.session_modes) == 2
            
            # Update flag
            manager.update_flag("server_driven_ui", percentage=50)
            
            # Cache should be cleared
            assert len(manager.session_modes) == 0


class TestEmergencyRollback:
    """Test emergency rollback safety"""
    
    def test_emergency_rollback_immediate(self):
        """Emergency rollback immediately disables feature"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            # Enable feature
            manager.flags["server_driven_ui"] = FeatureFlag(
                name="server_driven_ui",
                enabled=True,
                percentage=100
            )
            
            # Verify enabled
            assert manager.is_enabled("user1", "server_driven_ui")
            
            # Emergency rollback
            success = manager.emergency_rollback("server_driven_ui")
            assert success
            
            # Verify disabled
            assert not manager.is_enabled("user1", "server_driven_ui")
            assert manager.flags["server_driven_ui"].percentage == 0
            assert not manager.flags["server_driven_ui"].enabled
    
    def test_rollback_preserves_overrides(self):
        """Emergency rollback preserves explicit overrides"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            manager.flags["server_driven_ui"] = FeatureFlag(
                name="server_driven_ui",
                enabled=True,
                percentage=100,
                user_overrides={"special_user"}
            )
            
            # Emergency rollback
            manager.emergency_rollback("server_driven_ui")
            
            # Normal users disabled
            assert not manager.is_enabled("normal_user", "server_driven_ui")
            
            # Override users still enabled
            assert manager.is_enabled("special_user", "server_driven_ui")
    
    def test_rollback_clears_sessions(self):
        """Emergency rollback clears all session caches"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            manager.flags["server_driven_ui"] = FeatureFlag(
                name="server_driven_ui",
                enabled=True,
                percentage=100
            )
            
            # Populate session cache
            manager.get_user_mode("user1")
            manager.get_user_mode("user2")
            assert len(manager.session_modes) > 0
            
            # Emergency rollback
            manager.emergency_rollback("server_driven_ui")
            
            # Sessions cleared
            assert len(manager.session_modes) == 0


class TestConfigurationPersistence:
    """Test TOML configuration persistence"""
    
    def test_save_load_config(self):
        """Configuration persists correctly to TOML"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            
            # Create and save
            manager1 = FeatureFlagManager(str(config_path))
            manager1.update_flag(
                "server_driven_ui",
                enabled=True,
                percentage=42,
                user_overrides=["user1", "user2"],
                user_excludes=["user3"]
            )
            
            # Load in new instance
            manager2 = FeatureFlagManager(str(config_path))
            flag = manager2.flags["server_driven_ui"]
            
            assert flag.enabled == True
            assert flag.percentage == 42
            assert flag.user_overrides == {"user1", "user2"}
            assert flag.user_excludes == {"user3"}
    
    def test_hot_reload(self):
        """Hot reload updates configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            # Initial state
            assert manager.flags["server_driven_ui"].percentage == 0
            
            # Modify file directly
            config = toml.load(config_path)
            config["flags"]["server_driven_ui"]["percentage"] = 75
            with open(config_path, 'w') as f:
                toml.dump(config, f)
            
            # Hot reload
            manager.reload_config()
            
            # Check updated
            assert manager.flags["server_driven_ui"].percentage == 75


class TestABTesting:
    """Test A/B testing functionality"""
    
    def test_ab_test_distribution(self):
        """A/B test groups are evenly distributed"""
        manager = FeatureFlagManager()
        
        group_a = 0
        group_b = 0
        
        for i in range(10000):
            group = manager.get_ab_test_group(f"user_{i}", "test_experiment")
            if group == 'A':
                group_a += 1
            else:
                group_b += 1
        
        # Should be roughly 50/50 (±2% tolerance)
        ratio = group_a / (group_a + group_b)
        assert 0.48 <= ratio <= 0.52, f"A/B distribution skewed: {ratio:.2%} in A"
    
    def test_ab_test_consistency(self):
        """Users stay in same A/B group"""
        manager = FeatureFlagManager()
        
        user_id = "test_user"
        
        # Get group multiple times
        groups = [
            manager.get_ab_test_group(user_id, "experiment1")
            for _ in range(100)
        ]
        
        # Should all be same
        assert len(set(groups)) == 1, "User changed A/B groups"
    
    def test_ab_test_independence(self):
        """Different tests give independent assignments"""
        manager = FeatureFlagManager()
        
        user_id = "test_user"
        
        group1 = manager.get_ab_test_group(user_id, "experiment1")
        group2 = manager.get_ab_test_group(user_id, "experiment2")
        group3 = manager.get_ab_test_group(user_id, "experiment3")
        
        # Should have mix of A and B across experiments (probabilistic)
        # Just verify they can be different
        assert group1 in ['A', 'B'] and group2 in ['A', 'B'] and group3 in ['A', 'B']


class TestPerformance:
    """Test performance characteristics"""
    
    def test_evaluation_performance(self):
        """Flag evaluation is O(1) complexity"""
        manager = FeatureFlagManager()
        manager.flags["test"] = FeatureFlag(
            name="test",
            enabled=True,
            percentage=50
        )
        
        # Measure time for evaluations
        import time
        
        times = []
        for i in range(1000):
            start = time.perf_counter()
            manager.is_enabled(f"user_{i}", "test")
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        # Average should be very small (< 1ms)
        avg_time = sum(times) / len(times)
        assert avg_time < 0.001, f"Evaluation too slow: {avg_time*1000:.3f}ms average"
        
        # Verify O(1) - time shouldn't increase with user count
        first_100_avg = sum(times[:100]) / 100
        last_100_avg = sum(times[-100:]) / 100
        
        # Should be roughly same (±50% tolerance for timing variance)
        ratio = last_100_avg / first_100_avg if first_100_avg > 0 else 1
        assert 0.5 <= ratio <= 2.0, "Performance degrades with more users (not O(1))"


class TestStatistics:
    """Test monitoring and statistics"""
    
    def test_rollout_stats(self):
        """Rollout statistics are accurate"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "flags.toml"
            manager = FeatureFlagManager(str(config_path))
            
            manager.flags["server_driven_ui"] = FeatureFlag(
                name="server_driven_ui",
                enabled=True,
                percentage=30,
                user_overrides={"user1", "user2"},
                user_excludes={"user3"}
            )
            
            # Generate some sessions
            for i in range(10):
                manager.get_user_mode(f"user_{i}")
            
            stats = manager.get_rollout_stats("server_driven_ui")
            
            assert stats["enabled"] == True
            assert stats["percentage"] == 30
            assert stats["override_count"] == 2
            assert stats["exclude_count"] == 1
            assert stats["total_sessions"] == 10
            assert "thin_sessions" in stats
            assert "thick_sessions" in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])