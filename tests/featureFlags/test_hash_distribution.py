#!/usr/bin/env python3
"""
Feature Flag Hash Distribution Tests

Tests mathematical properties of hash distribution algorithm:
- Uniform distribution verification
- Consistency across sessions
- Percentage rollout accuracy
- Hash function collision analysis

Mathematical properties verified:
- HashFunction(userId, flagName) produces uniform distribution [0, 99]
- Consistency: same input -> same output (deterministic)
- Distribution: ~1% users per percentage point within statistical bounds
"""

import unittest
import hashlib
import statistics
from collections import Counter, defaultdict

class HashDistributionTest(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment with mathematical constants."""
        self.prime_multiplier = 37  # From mathematical analysis
        self.modulo_base = 100
        self.salt = "feature_flags_v1"
        self.test_users = list(range(1, 10001))  # 10,000 test users
        self.test_flags = ["server_driven_ui", "new_feature", "beta_test"]
        
    def compute_user_hash(self, user_id, flag_name):
        """
        Implement hash function from mathematical model.
        HashFunction(userId, flagName) = ((userId * 37 + flagHash) % 100)
        """
        # Convert user_id to number if string (using hash for non-numeric strings)
        if isinstance(user_id, str):
            try:
                user_id_num = int(user_id)
            except ValueError:
                # Hash string user IDs to numeric values
                user_id_num = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 2147483647
        else:
            user_id_num = user_id
        
        # Compute flag hash with salt
        flag_with_salt = flag_name + self.salt
        flag_hash = int(hashlib.md5(flag_with_salt.encode()).hexdigest(), 16) % 2147483647
        
        # Core mathematical formula
        hash_value = ((user_id_num * self.prime_multiplier + flag_hash) % self.modulo_base)
        return abs(hash_value)  # Ensure positive
        
    def test_hash_consistency(self):
        """Test that hash function is deterministic (same input -> same output)."""
        for flag in self.test_flags:
            for user in [1, 100, 999, 5000, 9999]:
                # Multiple calls should return identical results
                hash1 = self.compute_user_hash(user, flag)
                hash2 = self.compute_user_hash(user, flag)
                hash3 = self.compute_user_hash(user, flag)
                
                self.assertEqual(hash1, hash2, 
                    f"Hash inconsistency for user {user}, flag {flag}")
                self.assertEqual(hash2, hash3, 
                    f"Hash inconsistency for user {user}, flag {flag}")
                    
    def test_hash_range(self):
        """Test that hash values fall within expected range [0, 99]."""
        for flag in self.test_flags:
            for user in self.test_users[::100]:  # Sample every 100th user
                hash_value = self.compute_user_hash(user, flag)
                self.assertGreaterEqual(hash_value, 0, 
                    f"Hash below range for user {user}, flag {flag}: {hash_value}")
                self.assertLessEqual(hash_value, 99, 
                    f"Hash above range for user {user}, flag {flag}: {hash_value}")
                    
    def test_uniform_distribution(self):
        """Test that hash function produces approximately uniform distribution."""
        for flag in self.test_flags:
            hash_values = [self.compute_user_hash(user, flag) for user in self.test_users]
            
            # Count values in each bucket (0-99)
            bucket_counts = Counter(hash_values)
            
            # Expected count per bucket (10,000 users / 100 buckets = 100 per bucket)
            expected_per_bucket = len(self.test_users) / self.modulo_base
            tolerance = expected_per_bucket * 0.15  # 15% tolerance for randomness
            
            # Verify each bucket is within tolerance
            for bucket in range(self.modulo_base):
                actual_count = bucket_counts.get(bucket, 0)
                self.assertAlmostEqual(actual_count, expected_per_bucket, delta=tolerance,
                    msg=f"Bucket {bucket} distribution outside tolerance for {flag}: "
                        f"{actual_count} vs expected {expected_per_bucket}")
                        
    def test_percentage_rollout_accuracy(self):
        """Test that percentage rollouts achieve target percentages within statistical bounds."""
        flag = "server_driven_ui"
        test_percentages = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        
        for target_percentage in test_percentages:
            # Count users who would be enabled at this percentage
            enabled_users = sum(1 for user in self.test_users 
                              if self.compute_user_hash(user, flag) < target_percentage)
            
            actual_percentage = (enabled_users / len(self.test_users)) * 100
            
            # Allow 1% tolerance for statistical variation
            tolerance = 1.0
            self.assertAlmostEqual(actual_percentage, target_percentage, delta=tolerance,
                msg=f"Rollout accuracy outside tolerance: "
                    f"{actual_percentage:.2f}% vs target {target_percentage}%")
                    
    def test_hash_collision_analysis(self):
        """Analyze hash collisions - informational test for hash quality."""
        hash_combinations = defaultdict(list)
        
        # Generate hashes for all user/flag combinations
        for user in self.test_users[::10]:  # Sample every 10th user for performance
            for flag in self.test_flags:
                hash_value = self.compute_user_hash(user, flag)
                hash_combinations[hash_value].append((user, flag))
                
        # Analyze collision statistics (informational)
        collision_counts = [len(users) for users in hash_combinations.values()]
        max_collisions = max(collision_counts)
        avg_collisions = statistics.mean(collision_counts)
        unique_hashes = len(hash_combinations)
        
        # Log collision statistics for analysis
        print(f"\nHash Collision Analysis:")
        print(f"  Unique hash values: {unique_hashes}/100")
        print(f"  Max collisions per hash: {max_collisions}")
        print(f"  Average collisions: {avg_collisions:.2f}")
        
        # Basic sanity checks only (adjusted for our test scenario)
        total_combinations = (len(self.test_users) // 10) * len(self.test_flags)
        expected_unique = min(total_combinations, 100)  # Can't have more than 100 unique values
        
        self.assertGreater(unique_hashes, 10, "Too few unique hash values generated")
        self.assertLessEqual(unique_hashes, 100, "More unique hashes than possible")
        
        # Verify that we're actually distributing across multiple hash values
        # (as opposed to all users getting the same hash)
        self.assertGreater(unique_hashes, len(self.test_flags), 
                          f"Hash distribution too poor: only {unique_hashes} unique values for {len(self.test_flags)} flags")
            
    def test_cross_flag_independence(self):
        """Test that hash values for different flags are independent."""
        user = 1234
        
        # Get hash values for all flags
        hash_values = {flag: self.compute_user_hash(user, flag) for flag in self.test_flags}
        
        # Hash values should be different across flags (very high probability)
        unique_hashes = set(hash_values.values())
        self.assertEqual(len(unique_hashes), len(self.test_flags),
            f"Hash values not independent across flags: {hash_values}")
            
    def test_gradual_rollout_stability(self):
        """Test that gradual rollout maintains user assignments."""
        flag = "server_driven_ui"
        user_sample = self.test_users[:1000]  # Use 1000 users for performance
        
        # Get users enabled at different percentages
        enabled_at_10 = {user for user in user_sample 
                        if self.compute_user_hash(user, flag) < 10}
        enabled_at_25 = {user for user in user_sample 
                        if self.compute_user_hash(user, flag) < 25}
        enabled_at_50 = {user for user in user_sample 
                        if self.compute_user_hash(user, flag) < 50}
        
        # Mathematical property: enabled_at_10 ⊆ enabled_at_25 ⊆ enabled_at_50
        self.assertTrue(enabled_at_10.issubset(enabled_at_25),
            "Users enabled at 10% should remain enabled at 25%")
        self.assertTrue(enabled_at_25.issubset(enabled_at_50),
            "Users enabled at 25% should remain enabled at 50%")
            
    def test_hash_string_user_ids(self):
        """Test hash function with string user IDs (common in web applications)."""
        string_users = ["user123", "admin", "test@example.com", "uuid-1234-5678"]
        flag = "server_driven_ui"
        
        for user in string_users:
            hash_value = self.compute_user_hash(user, flag)
            
            # Should produce valid hash in range
            self.assertGreaterEqual(hash_value, 0)
            self.assertLessEqual(hash_value, 99)
            
            # Should be consistent across calls
            hash_value2 = self.compute_user_hash(user, flag)
            self.assertEqual(hash_value, hash_value2)
            
    def test_mathematical_properties(self):
        """Test core mathematical properties of the hash function."""
        flag = "test_flag"
        
        # Property 1: Deterministic function
        test_inputs = [1, 100, 999, "user123", "test@example.com"]
        for input_val in test_inputs:
            result1 = self.compute_user_hash(input_val, flag)
            result2 = self.compute_user_hash(input_val, flag)
            self.assertEqual(result1, result2, f"Non-deterministic for input {input_val}")
        
        # Property 2: Different inputs should generally produce different outputs
        different_outputs = set()
        for i in range(1, 101):
            different_outputs.add(self.compute_user_hash(i, flag))
        
        # Should have high diversity (at least 80% unique values)
        diversity = len(different_outputs) / 100
        self.assertGreater(diversity, 0.8, f"Low hash diversity: {diversity:.2f}")
        
        # Property 3: Output range constraint
        for i in range(1, 1001):
            output = self.compute_user_hash(i, flag)
            self.assertIn(output, range(100), f"Output {output} outside range for input {i}")

if __name__ == '__main__':
    # Run tests with detailed output
    unittest.main(verbosity=2)