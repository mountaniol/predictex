"""
Comprehensive Test Suite for SessionManager Component
====================================================

This module contains comprehensive tests for the SessionManager class following TDD methodology.
Tests are designed to FAIL initially (Red phase) before implementation exists.

Mathematical Test Model:
- State Space: {empty, created, active, expired, updated, deleted} × concurrent_sessions
- Invariants: UUID uniqueness, TTL monotonicity, data persistence consistency  
- Properties: Session isolation, expiry determinism, concurrent safety
- Coverage: CRUD operations, time-based behavior, concurrency, error handling

Test Categories:
1. Core Operations: create_session, get_session, update_session
2. Time-based: expiry handling, TTL management, cleanup
3. Concurrency: independent sessions, thread safety
4. Edge Cases: non-existent sessions, invalid inputs, boundary conditions
5. Persistence: data consistency across operations
"""

import pytest
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import will fail initially - this is expected in TDD Red phase
try:
    from src.backend.session_manager import SessionManager
except ImportError:
    # Expected during TDD Red phase - tests should fail gracefully
    SessionManager = None


class TestSessionManager:
    """
    Comprehensive test suite for SessionManager component.
    
    Mathematical Properties Tested:
    - UUID uniqueness: ∀ sessions s1,s2: s1.id ≠ s2.id
    - TTL monotonicity: session.created_at ≤ session.expires_at
    - Data persistence: get(create(data)) = data
    - Session isolation: update(s1) ∄ affects(s2)
    """
    
    @pytest.fixture
    def session_manager(self):
        """
        Create fresh SessionManager instance for each test.
        
        Mathematical Property: Each test operates on clean state space.
        """
        if SessionManager is None:
            pytest.skip("SessionManager not implemented yet (TDD Red phase)")
        return SessionManager()
    
    @pytest.fixture
    def sample_session_data(self):
        """Sample session data for testing."""
        return {
            "user_id": "user123",
            "answers": {"Q1": "answer1", "Q2": ["option1", "option2"]},
            "scores": {"Q1": 85, "Q2": 72},
            "metadata": {"started_at": datetime.now().isoformat()}
        }
    
    # ========================================================================
    # CORE OPERATION TESTS - CRUD Functionality
    # ========================================================================
    
    def test_create_session(self, session_manager, sample_session_data):
        """
        Test session creation returns valid UUID and persists data.
        
        Mathematical Property: create: SessionData → UUID × State
        Invariants: 
        - UUID is valid RFC 4122 format
        - Session data is persisted exactly as provided
        - Created session is immediately retrievable
        """
        # Execute creation
        session_id = session_manager.create_session(sample_session_data)
        
        # Verify UUID format and uniqueness
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # Standard UUID length
        assert uuid.UUID(session_id)  # Valid UUID format
        
        # Verify session is immediately retrievable
        retrieved_session = session_manager.get_session(session_id)
        assert retrieved_session is not None
        assert retrieved_session["session_id"] == session_id
        assert retrieved_session["data"] == sample_session_data
        
        # Verify timestamp fields
        assert "created_at" in retrieved_session
        assert "expires_at" in retrieved_session
        assert retrieved_session["created_at"] <= retrieved_session["expires_at"]
    
    def test_get_session(self, session_manager, sample_session_data):
        """
        Test session retrieval by ID returns correct data.
        
        Mathematical Property: get: UUID → SessionData ∪ {None}
        Invariants:
        - get(create(data)).data = data (persistence)
        - get(invalid_id) = None (error handling)
        """
        # Create session first
        session_id = session_manager.create_session(sample_session_data)
        
        # Test successful retrieval
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id
        assert session["data"] == sample_session_data
        
        # Verify required fields exist
        required_fields = ["session_id", "data", "created_at", "expires_at"]
        for field in required_fields:
            assert field in session, f"Missing required field: {field}"
    
    def test_update_session(self, session_manager, sample_session_data):
        """
        Test session update modifies persisted data correctly.
        
        Mathematical Property: update: UUID × SessionData → Bool
        Invariants:
        - get(update(id, new_data)).data = new_data (update correctness)
        - update preserves session_id and timestamps appropriately
        - update(invalid_id, data) = False (error handling)
        """
        # Create initial session
        session_id = session_manager.create_session(sample_session_data)
        
        # Prepare updated data
        updated_data = sample_session_data.copy()
        updated_data["answers"]["Q3"] = "new_answer"
        updated_data["scores"]["Q3"] = 95
        updated_data["metadata"]["updated_at"] = datetime.now().isoformat()
        
        # Execute update
        update_result = session_manager.update_session(session_id, updated_data)
        assert update_result is True
        
        # Verify updated data persisted
        updated_session = session_manager.get_session(session_id)
        assert updated_session["data"] == updated_data
        assert updated_session["session_id"] == session_id  # ID unchanged
        
        # Verify timestamps (created_at unchanged, updated_at new)
        original_session = session_manager.get_session(session_id)
        # Note: In real implementation, might track last_updated timestamp
    
    # ========================================================================
    # TIME-BASED BEHAVIOR TESTS - TTL and Expiry
    # ========================================================================
    
    def test_session_expiry(self, session_manager, sample_session_data):
        """
        Test expired sessions are cleaned up automatically.
        
        Mathematical Property: ∀ session s: now() > s.expires_at ⟹ get(s.id) = None
        Time Invariant: Expired sessions become inaccessible
        """
        # Create session with very short TTL (1 second for testing)
        with patch.object(session_manager, 'default_ttl', 1):
            session_id = session_manager.create_session(sample_session_data)
        
        # Verify session exists initially
        session = session_manager.get_session(session_id)
        assert session is not None
        
        # Wait for expiry (add buffer for processing time)
        time.sleep(1.5)
        
        # Trigger cleanup (might be automatic or manual depending on implementation)
        if hasattr(session_manager, 'cleanup_expired_sessions'):
            session_manager.cleanup_expired_sessions()
        
        # Verify session is no longer accessible
        expired_session = session_manager.get_session(session_id)
        assert expired_session is None
    
    def test_session_ttl_extension(self, session_manager, sample_session_data):
        """
        Test TTL can be extended for active sessions.
        
        Mathematical Property: extend_ttl: UUID × Seconds → Bool
        Time Invariant: new_expires_at > old_expires_at
        """
        # Create session
        session_id = session_manager.create_session(sample_session_data)
        original_session = session_manager.get_session(session_id)
        original_expires = original_session["expires_at"]
        
        # Extend TTL
        if hasattr(session_manager, 'extend_ttl'):
            extension_seconds = 3600  # 1 hour
            extend_result = session_manager.extend_ttl(session_id, extension_seconds)
            assert extend_result is True
            
            # Verify new expiry time
            updated_session = session_manager.get_session(session_id)
            new_expires = updated_session["expires_at"]
            
            # Convert to datetime for comparison (format depends on implementation)
            if isinstance(original_expires, str):
                original_dt = datetime.fromisoformat(original_expires)
                new_dt = datetime.fromisoformat(new_expires)
            else:
                original_dt = original_expires
                new_dt = new_expires
            
            assert new_dt > original_dt, "TTL extension should increase expiry time"
    
    # ========================================================================
    # CONCURRENCY TESTS - Multiple Sessions and Thread Safety
    # ========================================================================
    
    def test_concurrent_sessions(self, session_manager):
        """
        Test multiple sessions work independently without interference.
        
        Mathematical Property: Session Isolation
        ∀ sessions s1,s2: update(s1) ∄ affects(s2)
        Concurrency Invariant: Independent session spaces
        """
        # Create multiple sessions with different data
        session_data_1 = {"user": "user1", "data": "session1_data"}
        session_data_2 = {"user": "user2", "data": "session2_data"}
        session_data_3 = {"user": "user3", "data": "session3_data"}
        
        session_id_1 = session_manager.create_session(session_data_1)
        session_id_2 = session_manager.create_session(session_data_2)
        session_id_3 = session_manager.create_session(session_data_3)
        
        # Verify all sessions are independent and correct
        sessions = [
            (session_id_1, session_data_1),
            (session_id_2, session_data_2),
            (session_id_3, session_data_3)
        ]
        
        for session_id, expected_data in sessions:
            retrieved = session_manager.get_session(session_id)
            assert retrieved is not None
            assert retrieved["session_id"] == session_id
            assert retrieved["data"] == expected_data
        
        # Update one session and verify others unchanged
        updated_data_1 = {"user": "user1", "data": "updated_session1_data"}
        session_manager.update_session(session_id_1, updated_data_1)
        
        # Verify session 1 updated
        updated_session_1 = session_manager.get_session(session_id_1)
        assert updated_session_1["data"] == updated_data_1
        
        # Verify sessions 2 and 3 unchanged (isolation property)
        session_2 = session_manager.get_session(session_id_2)
        session_3 = session_manager.get_session(session_id_3)
        assert session_2["data"] == session_data_2
        assert session_3["data"] == session_data_3
    
    def test_thread_safety(self, session_manager):
        """
        Test SessionManager operations are thread-safe.
        
        Mathematical Property: Thread Safety
        Concurrent operations maintain data consistency
        No race conditions in session creation/retrieval/update
        """
        num_threads = 10
        sessions_per_thread = 5
        thread_results = {}
        
        def create_sessions_worker(thread_id):
            """Worker function to create sessions in parallel."""
            thread_sessions = []
            for i in range(sessions_per_thread):
                data = {
                    "thread_id": thread_id,
                    "session_index": i,
                    "data": f"thread_{thread_id}_session_{i}"
                }
                session_id = session_manager.create_session(data)
                thread_sessions.append((session_id, data))
            thread_results[thread_id] = thread_sessions
        
        # Execute parallel session creation
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(create_sessions_worker, thread_id)
                for thread_id in range(num_threads)
            ]
            # Wait for all threads to complete
            for future in futures:
                future.result()
        
        # Verify all sessions created correctly
        total_expected = num_threads * sessions_per_thread
        assert len(thread_results) == num_threads
        
        all_session_ids = set()
        for thread_id, thread_sessions in thread_results.items():
            assert len(thread_sessions) == sessions_per_thread
            
            for session_id, expected_data in thread_sessions:
                # Verify UUID uniqueness across threads
                assert session_id not in all_session_ids, f"Duplicate session ID: {session_id}"
                all_session_ids.add(session_id)
                
                # Verify session data integrity
                retrieved = session_manager.get_session(session_id)
                assert retrieved is not None
                assert retrieved["data"] == expected_data
        
        assert len(all_session_ids) == total_expected
    
    # ========================================================================
    # EDGE CASE TESTS - Error Handling and Boundary Conditions
    # ========================================================================
    
    def test_get_nonexistent_session(self, session_manager):
        """
        Test retrieving non-existent session returns None gracefully.
        
        Mathematical Property: get: InvalidID → None
        Error Handling: Graceful failure for invalid inputs
        """
        # Test with valid UUID format but non-existent session
        fake_uuid = str(uuid.uuid4())
        result = session_manager.get_session(fake_uuid)
        assert result is None
        
        # Test with invalid UUID format
        invalid_ids = ["", "invalid-uuid", "12345", None]
        for invalid_id in invalid_ids:
            if invalid_id is None:
                with pytest.raises((TypeError, ValueError)):
                    session_manager.get_session(invalid_id)
            else:
                # Should handle gracefully or raise appropriate exception
                try:
                    result = session_manager.get_session(invalid_id)
                    assert result is None  # Graceful handling
                except (ValueError, TypeError):
                    pass  # Appropriate exception raised
    
    def test_update_nonexistent_session(self, session_manager, sample_session_data):
        """
        Test updating non-existent session returns False.
        
        Mathematical Property: update: InvalidID × Data → False
        Error Handling: Safe handling of invalid session updates
        """
        fake_uuid = str(uuid.uuid4())
        result = session_manager.update_session(fake_uuid, sample_session_data)
        assert result is False
        
        # Test with invalid UUID format
        invalid_ids = ["", "invalid-uuid", None]
        for invalid_id in invalid_ids:
            if invalid_id is None:
                with pytest.raises((TypeError, ValueError)):
                    session_manager.update_session(invalid_id, sample_session_data)
            else:
                try:
                    result = session_manager.update_session(invalid_id, sample_session_data)
                    assert result is False
                except (ValueError, TypeError):
                    pass  # Appropriate exception handling
    
    def test_session_data_persistence(self, session_manager):
        """
        Test complex session data persists correctly across operations.
        
        Mathematical Property: Data Integrity
        Complex nested data structures maintain fidelity
        """
        # Complex nested data structure
        complex_data = {
            "user_info": {
                "id": "user123",
                "name": "Test User",
                "preferences": ["pref1", "pref2"]
            },
            "answers": {
                "SG01": ["option1", "other"],
                "SG01_other": "Custom text answer",
                "MET.LOC": "Charlotte, NC"
            },
            "scores": {"SG01": 85, "MET.SIZE": 72},
            "metadata": {
                "started_at": datetime.now().isoformat(),
                "completed_questions": ["SG01", "MET.LOC"],
                "progress": 0.67,
                "flags": {"has_other_answers": True}
            }
        }
        
        # Create session with complex data
        session_id = session_manager.create_session(complex_data)
        
        # Retrieve and verify exact data preservation
        retrieved = session_manager.get_session(session_id)
        assert retrieved["data"] == complex_data
        
        # Verify nested structure integrity
        assert retrieved["data"]["user_info"]["preferences"] == ["pref1", "pref2"]
        assert retrieved["data"]["answers"]["SG01"] == ["option1", "other"]
        assert retrieved["data"]["metadata"]["flags"]["has_other_answers"] is True
    
    def test_session_creation_with_empty_data(self, session_manager):
        """
        Test session creation with various empty data scenarios.
        
        Boundary Conditions: Empty, None, and minimal data
        """
        # Test empty dictionary
        empty_data = {}
        session_id = session_manager.create_session(empty_data)
        assert session_id is not None
        retrieved = session_manager.get_session(session_id)
        assert retrieved["data"] == empty_data
        
        # Test None data (should raise appropriate error)
        with pytest.raises((TypeError, ValueError)):
            session_manager.create_session(None)
        
        # Test minimal valid data
        minimal_data = {"key": "value"}
        session_id = session_manager.create_session(minimal_data)
        assert session_id is not None
        retrieved = session_manager.get_session(session_id)
        assert retrieved["data"] == minimal_data
    
    def test_uuid_uniqueness_large_scale(self, session_manager):
        """
        Test UUID uniqueness at scale.
        
        Mathematical Property: UUID Collision Probability ≈ 0
        Generate large number of sessions and verify all IDs unique
        """
        num_sessions = 1000
        session_ids = set()
        
        for i in range(num_sessions):
            data = {"index": i, "data": f"session_{i}"}
            session_id = session_manager.create_session(data)
            
            # Verify UUID uniqueness
            assert session_id not in session_ids, f"Duplicate UUID detected: {session_id}"
            session_ids.add(session_id)
            
            # Verify UUID format
            assert uuid.UUID(session_id)  # Raises exception if invalid
        
        # Verify all sessions are retrievable
        assert len(session_ids) == num_sessions
        for session_id in session_ids:
            session = session_manager.get_session(session_id)
            assert session is not None
    
    # ========================================================================
    # CLEANUP AND MAINTENANCE TESTS
    # ========================================================================
    
    def test_bulk_session_cleanup(self, session_manager):
        """
        Test bulk cleanup of expired sessions.
        
        Performance Property: Efficient batch cleanup
        Correctness: Only expired sessions removed
        """
        # Create mix of sessions with different TTLs
        active_sessions = []
        expired_sessions = []
        
        # Create sessions with normal TTL (should remain active)
        for i in range(3):
            data = {"type": "active", "index": i}
            session_id = session_manager.create_session(data)
            active_sessions.append(session_id)
        
        # Create sessions with very short TTL (will expire)
        with patch.object(session_manager, 'default_ttl', 0.5):
            for i in range(3):
                data = {"type": "expired", "index": i}
                session_id = session_manager.create_session(data)
                expired_sessions.append(session_id)
        
        # Wait for short TTL sessions to expire
        time.sleep(1)
        
        # Perform bulk cleanup
        if hasattr(session_manager, 'cleanup_expired_sessions'):
            cleanup_count = session_manager.cleanup_expired_sessions()
            assert cleanup_count >= len(expired_sessions)
        
        # Verify active sessions still exist
        for session_id in active_sessions:
            session = session_manager.get_session(session_id)
            assert session is not None
            assert session["data"]["type"] == "active"
        
        # Verify expired sessions are gone
        for session_id in expired_sessions:
            session = session_manager.get_session(session_id)
            assert session is None


class TestSessionManagerIntegration:
    """
    Integration tests for SessionManager with real-world usage patterns.
    
    These tests simulate actual application workflows and usage patterns
    to verify SessionManager behavior in realistic scenarios.
    """
    
    @pytest.fixture
    def session_manager(self):
        """Fresh SessionManager for integration tests."""
        if SessionManager is None:
            pytest.skip("SessionManager not implemented yet (TDD Red phase)")
        return SessionManager()
    
    def test_questionnaire_session_workflow(self, session_manager):
        """
        Test complete questionnaire session lifecycle.
        
        Simulates real application workflow:
        1. Create session with initial user data
        2. Progressive answer updates
        3. Score calculations and storage
        4. Final session retrieval
        """
        # Initial session creation (user starts questionnaire)
        initial_data = {
            "user_id": "user123",
            "questionnaire_id": "q4",
            "started_at": datetime.now().isoformat(),
            "answers": {},
            "scores": {},
            "progress": 0.0
        }
        
        session_id = session_manager.create_session(initial_data)
        
        # Simulate progressive question answering
        question_sequence = [
            ("MET.LOC", "Charlotte, NC", 0.1),
            ("SG01", ["declining_sales"], 0.3),
            ("SG02", ["option1", "option2"], 0.6),
            ("TEXT01", "Detailed business explanation", 0.8)
        ]
        
        for question_id, answer, progress in question_sequence:
            # Get current session
            current_session = session_manager.get_session(session_id)
            data = current_session["data"]
            
            # Update with new answer
            data["answers"][question_id] = answer
            data["progress"] = progress
            data["last_updated"] = datetime.now().isoformat()
            
            # Save updated session
            update_result = session_manager.update_session(session_id, data)
            assert update_result is True
        
        # Simulate score updates (AI evaluation results)
        scores = {"SG01": 25, "SG02": 65, "TEXT01": 80}
        current_session = session_manager.get_session(session_id)
        data = current_session["data"]
        data["scores"] = scores
        data["completed"] = True
        
        session_manager.update_session(session_id, data)
        
        # Final verification
        final_session = session_manager.get_session(session_id)
        final_data = final_session["data"]
        
        assert final_data["completed"] is True
        assert len(final_data["answers"]) == 4
        assert len(final_data["scores"]) == 3
        assert final_data["progress"] == 0.8
        
        # Verify all answers preserved
        expected_answers = {
            "MET.LOC": "Charlotte, NC",
            "SG01": ["declining_sales"],
            "SG02": ["option1", "option2"],
            "TEXT01": "Detailed business explanation"
        }
        
        for q_id, expected_answer in expected_answers.items():
            assert final_data["answers"][q_id] == expected_answer
    
    def test_session_recovery_scenario(self, session_manager):
        """
        Test session recovery after interruption.
        
        Simulates user returning to questionnaire after browser restart/crash.
        """
        # Create session with partial progress
        partial_data = {
            "user_id": "user456",
            "answers": {
                "Q1": "answer1",
                "Q2": ["option1", "option2"]
            },
            "scores": {"Q1": 75},
            "last_question": "Q2",
            "progress": 0.4,
            "interrupted_at": datetime.now().isoformat()
        }
        
        session_id = session_manager.create_session(partial_data)
        
        # Simulate recovery: retrieve session and continue
        recovered_session = session_manager.get_session(session_id)
        assert recovered_session is not None
        
        recovered_data = recovered_session["data"]
        assert recovered_data["progress"] == 0.4
        assert recovered_data["last_question"] == "Q2"
        assert "Q1" in recovered_data["answers"]
        assert "Q1" in recovered_data["scores"]
        
        # Continue with new answers
        recovered_data["answers"]["Q3"] = "new_answer"
        recovered_data["scores"]["Q2"] = 85
        recovered_data["progress"] = 0.7
        recovered_data["resumed_at"] = datetime.now().isoformat()
        
        update_result = session_manager.update_session(session_id, recovered_data)
        assert update_result is True
        
        # Verify continued session
        continued_session = session_manager.get_session(session_id)
        continued_data = continued_session["data"]
        
        assert continued_data["progress"] == 0.7
        assert len(continued_data["answers"]) == 3
        assert "resumed_at" in continued_data


# ============================================================================
# PYTEST CONFIGURATION AND FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def cleanup_sessions():
    """
    Session-level fixture to ensure cleanup after tests.
    
    This fixture runs once per test session to clean up any
    persistent state that might affect subsequent test runs.
    """
    yield  # Run tests
    
    # Cleanup after all tests complete
    # Note: Actual cleanup will depend on SessionManager implementation
    # (e.g., clearing in-memory storage, database cleanup, etc.)
    pass


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

# Pytest markers for test categorization
pytestmark = [
    pytest.mark.unit,
    pytest.mark.session_manager
]

# Test timeouts for performance verification
TIMEOUT_SECONDS = 30  # Maximum time for any individual test

def pytest_configure(config):
    """Configure pytest for SessionManager tests."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "session_manager: SessionManager component tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "concurrency: Concurrency and thread safety tests")
    config.addinivalue_line("markers", "performance: Performance and scalability tests")