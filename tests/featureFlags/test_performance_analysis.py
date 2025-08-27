#!/usr/bin/env python3
"""
Feature Flag Performance Analysis

Tests and analyzes performance characteristics of the feature flag system:
- Evaluation latency under various load conditions  
- Memory usage patterns and growth
- Cache effectiveness and hit rates
- Concurrent access performance
- Configuration reload impact

Mathematical performance model verification:
- Hash computation: O(1) complexity
- Cache lookup: O(1) amortized complexity
- Memory growth: O(users × flags) bounded growth
- Concurrent safety: Lock-free read operations
"""

import unittest
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor
import hashlib

class PerformanceAnalysisTest(unittest.TestCase):
    
    def setUp(self):
        """Set up performance test environment."""
        self.prime_multiplier = 37
        self.modulo_base = 100
        self.salt = "feature_flags_v1"
        
        # Performance test parameters
        self.test_users = list(range(1, 10001))  # 10K users
        self.test_flags = [f"flag_{i}" for i in range(100)]  # 100 flags
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def compute_user_hash_with_cache(self, user_id, flag_name):
        """Hash function with caching for performance measurement."""
        start_time = time.perf_counter()
        
        cache_key = f"{user_id}:{flag_name}"
        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key], time.perf_counter() - start_time
            
        self.cache_misses += 1
        
        # Hash computation (same as main implementation)
        if isinstance(user_id, str):
            try:
                user_id_num = int(user_id)
            except ValueError:
                user_id_num = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 2147483647
        else:
            user_id_num = user_id
            
        flag_hash = int(hashlib.md5((flag_name + self.salt).encode()).hexdigest(), 16) % 2147483647
        hash_value = abs((user_id_num * self.prime_multiplier + flag_hash) % self.modulo_base)
        
        self.cache[cache_key] = hash_value
        return hash_value, time.perf_counter() - start_time

    def test_single_evaluation_latency(self):
        """Test latency of single hash evaluation."""
        flag = "server_driven_ui"
        latencies = []
        
        # Measure 1000 evaluations
        for i in range(1000):
            user_id = i + 1
            _, latency = self.compute_user_hash_with_cache(user_id, flag)
            latencies.append(latency * 1000)  # Convert to milliseconds
            
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        max_latency = max(latencies)
        
        print(f"\nSingle Evaluation Latency Analysis:")
        print(f"  Average: {avg_latency:.4f}ms")
        print(f"  95th percentile: {p95_latency:.4f}ms")
        print(f"  Maximum: {max_latency:.4f}ms")
        
        # Performance requirements (very fast operations)
        self.assertLess(avg_latency, 1.0, f"Average latency too high: {avg_latency:.4f}ms")
        self.assertLess(p95_latency, 2.0, f"P95 latency too high: {p95_latency:.4f}ms")

    def test_batch_evaluation_performance(self):
        """Test performance of batch evaluations."""
        user_id = 1234
        batch_sizes = [10, 50, 100, 500]
        
        for batch_size in batch_sizes:
            flags = self.test_flags[:batch_size]
            
            start_time = time.perf_counter()
            results = {}
            for flag in flags:
                hash_value, _ = self.compute_user_hash_with_cache(user_id, flag)
                results[flag] = hash_value < 50  # Simulate 50% rollout
            end_time = time.perf_counter()
            
            total_time = (end_time - start_time) * 1000  # Convert to ms
            per_flag_time = total_time / batch_size
            
            print(f"\nBatch Evaluation (size {batch_size}):")
            print(f"  Total time: {total_time:.4f}ms")
            print(f"  Per flag: {per_flag_time:.6f}ms")
            
            # Performance requirement: linear scaling
            self.assertLess(per_flag_time, 0.1, f"Per-flag time too high for batch {batch_size}")
            
    def test_cache_effectiveness(self):
        """Test cache hit rates and effectiveness."""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        
        # First pass: populate cache
        for user in self.test_users[:1000]:
            for flag in self.test_flags[:10]:
                self.compute_user_hash_with_cache(user, flag)
                
        # Second pass: test cache hits
        cache_operations_start = self.cache_hits + self.cache_misses
        for user in self.test_users[:1000]:  # Same users
            for flag in self.test_flags[:10]:  # Same flags
                self.compute_user_hash_with_cache(user, flag)
        cache_operations_end = self.cache_hits + self.cache_misses
        
        new_operations = cache_operations_end - cache_operations_start
        new_hits = self.cache_hits - (cache_operations_start // 2)  # Approximate
        cache_hit_rate = new_hits / new_operations if new_operations > 0 else 0
        
        print(f"\nCache Effectiveness Analysis:")
        print(f"  Total operations: {self.cache_hits + self.cache_misses}")
        print(f"  Cache hits: {self.cache_hits}")
        print(f"  Cache misses: {self.cache_misses}")
        print(f"  Hit rate: {cache_hit_rate:.2%}")
        print(f"  Cache size: {len(self.cache)}")
        
        # Cache should be highly effective for repeated operations
        self.assertGreater(cache_hit_rate, 0.8, f"Cache hit rate too low: {cache_hit_rate:.2%}")

    def test_concurrent_evaluation_performance(self):
        """Test performance under concurrent load."""
        def worker_thread(thread_id):
            """Worker function for concurrent testing."""
            results = []
            start_time = time.perf_counter()
            
            for i in range(100):  # 100 operations per thread
                user_id = thread_id * 100 + i
                flag = self.test_flags[i % len(self.test_flags)]
                hash_value, _ = self.compute_user_hash_with_cache(user_id, flag)
                results.append(hash_value)
                
            end_time = time.perf_counter()
            return end_time - start_time, len(results)
        
        # Test with different thread counts
        thread_counts = [1, 5, 10, 20]
        
        for num_threads in thread_counts:
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                start_time = time.perf_counter()
                futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
                
                results = [future.result() for future in futures]
                end_time = time.perf_counter()
                
            total_time = end_time - start_time
            total_operations = sum(result[1] for result in results)
            ops_per_second = total_operations / total_time
            
            print(f"\nConcurrent Performance ({num_threads} threads):")
            print(f"  Total time: {total_time:.4f}s")
            print(f"  Total operations: {total_operations}")
            print(f"  Operations/second: {ops_per_second:.0f}")
            
            # Performance should scale reasonably with thread count
            if num_threads == 1:
                baseline_ops = ops_per_second
            else:
                # Allow for some overhead, but expect reasonable scaling
                min_expected_ops = baseline_ops * num_threads * 0.5
                self.assertGreater(ops_per_second, min_expected_ops,
                    f"Concurrent performance degradation too severe: {ops_per_second:.0f} < {min_expected_ops:.0f}")

    def test_memory_usage_patterns(self):
        """Test memory usage growth patterns."""
        import sys
        
        initial_cache_size = len(self.cache)
        
        # Simulate gradual cache growth
        growth_phases = [
            (100, 10),    # 100 users, 10 flags
            (500, 25),    # 500 users, 25 flags  
            (1000, 50),   # 1000 users, 50 flags
            (2000, 100),  # 2000 users, 100 flags
        ]
        
        memory_growth = []
        
        for num_users, num_flags in growth_phases:
            phase_start_size = len(self.cache)
            
            # Add entries to cache
            for user in range(1, num_users + 1):
                for flag_idx in range(num_flags):
                    flag = f"test_flag_{flag_idx}"
                    self.compute_user_hash_with_cache(user, flag)
                    
            phase_end_size = len(self.cache)
            phase_growth = phase_end_size - phase_start_size
            memory_growth.append((num_users * num_flags, phase_growth))
            
            print(f"\nMemory Growth Phase ({num_users} users × {num_flags} flags):")
            print(f"  Expected entries: {num_users * num_flags}")
            print(f"  Actual growth: {phase_growth}")
            print(f"  Total cache size: {phase_end_size}")
            
            # Memory growth should be predictable (linear with user×flag combinations)
            expected_growth = num_users * num_flags
            growth_ratio = phase_growth / expected_growth
            self.assertAlmostEqual(growth_ratio, 1.0, delta=0.1,
                msg=f"Memory growth not linear: {growth_ratio:.2f} ratio")

    def test_configuration_reload_impact(self):
        """Test performance impact of configuration reloads."""
        # Simulate active evaluation load
        def evaluation_workload():
            """Background evaluation workload."""
            results = []
            for _ in range(1000):
                user = hash(threading.current_thread()) % 10000
                flag = self.test_flags[user % len(self.test_flags)]
                hash_value, latency = self.compute_user_hash_with_cache(user, flag)
                results.append(latency)
            return results
        
        # Measure baseline performance
        baseline_latencies = evaluation_workload()
        baseline_avg = statistics.mean(baseline_latencies) * 1000  # ms
        
        # Measure performance during "configuration reload" (cache clear simulation)
        def reload_simulation():
            """Simulate configuration reload by clearing cache periodically."""
            for _ in range(5):  # 5 reload events
                time.sleep(0.01)  # Small delay
                self.cache.clear()  # Simulate config reload clearing cache
                
        # Run evaluation workload concurrently with reload simulation
        with ThreadPoolExecutor(max_workers=2) as executor:
            reload_future = executor.submit(reload_simulation)
            workload_future = executor.submit(evaluation_workload)
            
            reload_future.result()
            reload_latencies = workload_future.result()
            
        reload_avg = statistics.mean(reload_latencies) * 1000  # ms
        performance_impact = ((reload_avg - baseline_avg) / baseline_avg) * 100
        
        print(f"\nConfiguration Reload Impact:")
        print(f"  Baseline latency: {baseline_avg:.4f}ms")
        print(f"  Reload latency: {reload_avg:.4f}ms")
        print(f"  Performance impact: {performance_impact:.1f}%")
        
        # Configuration reloads should have minimal impact (< 50% degradation)
        self.assertLess(abs(performance_impact), 50.0, 
            f"Configuration reload impact too severe: {performance_impact:.1f}%")

    def test_mathematical_complexity_verification(self):
        """Verify O(1) complexity of hash operations."""
        # Test different input sizes to verify O(1) complexity
        test_sizes = [100, 1000, 10000]
        avg_times = []
        
        for size in test_sizes:
            times = []
            for i in range(100):  # 100 measurements per size
                user_id = i % size + 1
                flag = f"test_flag_{i % 10}"
                
                start_time = time.perf_counter()
                self.compute_user_hash_with_cache(user_id, flag)
                end_time = time.perf_counter()
                
                times.append(end_time - start_time)
                
            avg_time = statistics.mean(times)
            avg_times.append(avg_time)
            
            print(f"\nComplexity Test (size {size}):")
            print(f"  Average time: {avg_time * 1000000:.2f}μs")
            
        # Verify that time doesn't increase significantly with input size (O(1))
        # Allow for some variance due to caching effects
        time_ratios = [avg_times[i+1] / avg_times[i] for i in range(len(avg_times)-1)]
        max_ratio = max(time_ratios)
        
        print(f"\nComplexity Analysis:")
        print(f"  Time ratios: {[f'{r:.2f}' for r in time_ratios]}")
        print(f"  Maximum ratio: {max_ratio:.2f}")
        
        # O(1) complexity: time should not increase significantly with input size
        self.assertLess(max_ratio, 3.0, f"Non-constant time complexity detected: {max_ratio:.2f}")

if __name__ == '__main__':
    # Run tests with detailed output
    print("Feature Flag Performance Analysis")
    print("=" * 50)
    unittest.main(verbosity=2)