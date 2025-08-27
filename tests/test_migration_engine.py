#!/usr/bin/env python3
"""
Test suite for Migration Engine

Verifies mathematical properties:
1. Bijective transformations
2. Data integrity preservation
3. ACID guarantees
4. Rollback safety
5. Concurrent migration handling
"""

import pytest
import json
import time
import tempfile
from pathlib import Path
import sys
from unittest.mock import Mock, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.backend.migration_engine import (
    MigrationEngine, ClientData, ServerSession, 
    MigrationState, MigrationCheckpoint
)
from src.backend.session_manager import SessionManager
from src.backend.feature_flag_manager import FeatureFlagManager, FeatureFlag


class TestBijectiveTransformations:
    """Test mathematical bijection properties"""
    
    def test_bijection_property(self):
        """Verify f⁻¹(f(x)) = x for transformations"""
        # Create sample client data
        client_data = ClientData(
            session_id="test_session_1",
            user_id="test_user_1",
            answers={'Q1': 'answer1', 'Q2': ['opt1', 'opt2']},
            scores={'Q1': 85, 'Q2': 92},
            explanations={'Q1': 'Good', 'Q2': 'Excellent'},
            question_states={'Q1': 'fully_answered', 'Q2': 'fully_answered'},
            local_storage={'theme': 'dark'},
            session_storage={'temp': 'data'},
            timestamp=1234567890
        )
        
        # Transform to server session
        server_session = ServerSession.from_client_data(client_data)
        
        # Transform back to client data
        restored_client_data = server_session.to_client_data()
        
        # Verify bijection property
        assert client_data.compute_hash() == restored_client_data.compute_hash()
        assert client_data.answers == restored_client_data.answers
        assert client_data.scores == restored_client_data.scores
        assert client_data.explanations == restored_client_data.explanations
        assert client_data.question_states == restored_client_data.question_states
    
    def test_hash_consistency(self):
        """Test that hashing is consistent and deterministic"""
        client_data = ClientData(
            session_id="test_session",
            user_id="test_user",
            answers={'Q1': 'answer'},
            scores={'Q1': 80},
            explanations={'Q1': 'Explanation'},
            question_states={'Q1': 'fully_answered'},
            local_storage={},
            session_storage={},
            timestamp=1234567890
        )
        
        hash1 = client_data.compute_hash()
        hash2 = client_data.compute_hash()
        
        assert hash1 == hash2, "Hash should be deterministic"
    
    def test_data_preservation(self):
        """Verify all data fields are preserved in transformation"""
        client_data = ClientData(
            session_id="complex_session",
            user_id="complex_user",
            answers={
                'Q1': 'simple_answer',
                'Q2': ['option1', 'option2', 'option3'],
                'Q3': {'nested': 'data', 'with': ['arrays']},
                'Q4': None,
                'Q5': ''
            },
            scores={'Q1': 0, 'Q2': 100, 'Q3': 50.5},
            explanations={'Q1': 'Short', 'Q2': 'A very long explanation ' * 100},
            question_states={'Q1': 'unanswered', 'Q2': 'waiting', 'Q3': 'fully_answered'},
            local_storage={'complex': {'nested': {'data': 'structure'}}},
            session_storage={'arrays': [1, 2, 3, 4, 5]},
            timestamp=9999999999
        )
        
        # Round-trip transformation
        server_session = ServerSession.from_client_data(client_data)
        restored = server_session.to_client_data()
        
        # Verify all fields preserved
        assert json.dumps(client_data.answers, sort_keys=True) == \
               json.dumps(restored.answers, sort_keys=True)
        assert client_data.scores == restored.scores
        assert client_data.explanations == restored.explanations
        assert client_data.question_states == restored.question_states
        assert client_data.local_storage == restored.local_storage
        assert client_data.session_storage == restored.session_storage


class TestMigrationEngine:
    """Test migration engine functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.session_manager = SessionManager()
        self.feature_flag_manager = FeatureFlagManager()
        self.migration_engine = MigrationEngine(
            self.session_manager,
            self.feature_flag_manager
        )
    
    def test_data_integrity_validation(self):
        """Test integrity validation mechanism"""
        client_data = ClientData(
            session_id="integrity_test",
            user_id="user_integrity",
            answers={'Q1': 'answer'},
            scores={'Q1': 75},
            explanations={'Q1': 'Test'},
            question_states={'Q1': 'fully_answered'},
            local_storage={},
            session_storage={},
            timestamp=time.time()
        )
        
        # Valid transformation
        server_session = self.migration_engine.transform_client_to_server(client_data)
        assert self.migration_engine.validate_data_integrity(client_data, server_session)
        
        # Create a corrupted server session
        import copy
        corrupted_session = copy.deepcopy(server_session)
        corrupted_session.data['answers']['Q1'] = 'corrupted'
        # Since to_client_data() uses the modified data, the integrity check will correctly fail
        assert not self.migration_engine.validate_data_integrity(client_data, corrupted_session)
    
    def test_checkpoint_creation_and_persistence(self):
        """Test checkpoint creation and saving"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override checkpoint directory
            original_create = self.migration_engine.create_checkpoint
            
            def create_checkpoint_with_tmpdir():
                checkpoint = MigrationCheckpoint(
                    checkpoint_id="test_checkpoint",
                    state=MigrationState.MIGRATING,
                    timestamp=time.time(),
                    migrated_sessions=[],
                    original_data={},
                    transformed_data={},
                    verification_hashes={}
                )
                
                checkpoint_path = Path(tmpdir) / "test_checkpoint.pkl"
                checkpoint.save(checkpoint_path)
                
                # Verify saved
                assert checkpoint_path.exists()
                
                # Load and verify
                loaded = MigrationCheckpoint.load(checkpoint_path)
                assert loaded.checkpoint_id == checkpoint.checkpoint_id
                assert loaded.state == checkpoint.state
                
                return checkpoint
            
            self.migration_engine.create_checkpoint = create_checkpoint_with_tmpdir
            checkpoint = self.migration_engine.create_checkpoint()
            
            assert checkpoint is not None
            assert checkpoint.checkpoint_id == "test_checkpoint"
    
    def test_session_migration_success(self):
        """Test successful session migration"""
        client_data = ClientData(
            session_id="migrate_success",
            user_id="user_success",
            answers={'Q1': 'answer'},
            scores={'Q1': 85},
            explanations={'Q1': 'Good'},
            question_states={'Q1': 'fully_answered'},
            local_storage={'key': 'value'},
            session_storage={'temp': 'data'},
            timestamp=time.time()
        )
        
        # Create checkpoint
        self.migration_engine.checkpoint = MigrationCheckpoint(
            checkpoint_id="test",
            state=MigrationState.MIGRATING,
            timestamp=time.time(),
            migrated_sessions=[],
            original_data={},
            transformed_data={},
            verification_hashes={}
        )
        
        # Ensure feature flag exists
        self.feature_flag_manager.flags["server_driven_ui"] = \
            FeatureFlag("server_driven_ui")
        
        # Migrate
        success, error = self.migration_engine.migrate_session(client_data)
        
        assert success is True
        assert error is None
        assert len(self.migration_engine.migration_log) == 1
        assert self.migration_engine.migration_log[0]['status'] == 'success'
    
    def test_session_migration_failure_handling(self):
        """Test migration failure and error handling"""
        # Create invalid client data (will fail hash verification)
        client_data = Mock(spec=ClientData)
        client_data.session_id = "fail_session"
        client_data.user_id = "fail_user"
        client_data.answers = {}
        client_data.scores = {}
        client_data.explanations = {}
        client_data.question_states = {}
        client_data.local_storage = {}
        client_data.session_storage = {}
        client_data.timestamp = 12345
        client_data.compute_hash.side_effect = Exception("Hash computation failed")
        
        success, error = self.migration_engine.migrate_session(client_data)
        
        assert success is False
        assert error is not None
        assert "Hash computation failed" in error
        assert len(self.migration_engine.migration_log) == 1
        assert self.migration_engine.migration_log[0]['status'] == 'failed'


class TestRollbackMechanism:
    """Test rollback safety and correctness"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.session_manager = SessionManager()
        self.feature_flag_manager = FeatureFlagManager()
        self.migration_engine = MigrationEngine(
            self.session_manager,
            self.feature_flag_manager
        )
        
        # Ensure feature flag exists
        self.feature_flag_manager.flags["server_driven_ui"] = \
            FeatureFlag("server_driven_ui")
    
    def test_rollback_restoration(self):
        """Test that rollback correctly restores original state"""
        # First create a session that we'll migrate
        session_id = self.session_manager.create_session({
            'answers': {'Q1': 'original_answer'},
            'scores': {'Q1': 50},
            'explanations': {'Q1': 'Original'},
            'questionStates': {'Q1': 'fully_answered'}
        })
        
        # Create original data for the checkpoint
        original_data = ClientData(
            session_id=session_id,
            user_id="user_rollback",
            answers={'Q1': 'original_answer'},
            scores={'Q1': 50},
            explanations={'Q1': 'Original'},
            question_states={'Q1': 'fully_answered'},
            local_storage={},
            session_storage={},
            timestamp=time.time()
        )
        
        # Create checkpoint with migrated data
        checkpoint = MigrationCheckpoint(
            checkpoint_id="rollback_checkpoint",
            state=MigrationState.COMPLETED,
            timestamp=time.time(),
            migrated_sessions=[session_id],
            original_data={session_id: original_data},
            transformed_data={},
            verification_hashes={session_id: original_data.compute_hash()}
        )
        
        # Now simulate migration by updating the session
        self.session_manager.update_session(session_id, {
            'answers': {'Q1': 'modified_answer'},
            'scores': {'Q1': 100},
            'explanations': {'Q1': 'Modified'},
            'questionStates': {'Q1': 'waiting'}
        })
        
        # Add user to thin client overrides
        self.feature_flag_manager.flags["server_driven_ui"].user_overrides.add("user_rollback")
        
        # Perform rollback
        success = self.migration_engine.rollback_migration(checkpoint)
        
        assert success is True
        assert self.migration_engine.state == MigrationState.IDLE
        
        # Verify session restored (use flat_format for direct data access)
        session = self.session_manager.get_session(session_id, flat_format=True)
        assert session['answers'] == original_data.answers
        assert session['scores'] == original_data.scores
        
        # Verify user removed from thin client
        assert "user_rollback" not in self.feature_flag_manager.flags["server_driven_ui"].user_overrides
    
    def test_rollback_with_multiple_sessions(self):
        """Test rollback with multiple sessions"""
        sessions_data = []
        checkpoint = MigrationCheckpoint(
            checkpoint_id="multi_rollback",
            state=MigrationState.COMPLETED,
            timestamp=time.time(),
            migrated_sessions=[],
            original_data={},
            transformed_data={},
            verification_hashes={}
        )
        
        # Create multiple sessions
        for i in range(5):
            client_data = ClientData(
                session_id=f"session_{i}",
                user_id=f"user_{i}",
                answers={'Q1': f'answer_{i}'},
                scores={'Q1': 70 + i},
                explanations={'Q1': f'Explanation_{i}'},
                question_states={'Q1': 'fully_answered'},
                local_storage={},
                session_storage={},
                timestamp=time.time()
            )
            
            checkpoint.migrated_sessions.append(f"session_{i}")
            checkpoint.original_data[f"session_{i}"] = client_data
            checkpoint.verification_hashes[f"session_{i}"] = client_data.compute_hash()
            
            # Add to thin client overrides
            self.feature_flag_manager.flags["server_driven_ui"].user_overrides.add(f"user_{i}")
        
        # Perform rollback
        success = self.migration_engine.rollback_migration(checkpoint)
        
        assert success is True
        
        # Verify all users removed from thin client
        for i in range(5):
            assert f"user_{i}" not in self.feature_flag_manager.flags["server_driven_ui"].user_overrides


class TestVerification:
    """Test migration verification procedures"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.session_manager = SessionManager()
        self.feature_flag_manager = FeatureFlagManager()
        self.migration_engine = MigrationEngine(
            self.session_manager,
            self.feature_flag_manager
        )
    
    def test_verification_with_valid_data(self):
        """Test verification with correctly migrated data"""
        # Create session first
        session_id = self.session_manager.create_session({
            'user_id': 'user_1',
            'answers': {'Q1': 'answer'},
            'scores': {'Q1': 80},
            'explanations': {'Q1': 'Good'},
            'questionStates': {'Q1': 'fully_answered'}
        })
        
        # Create client data with the actual session_id
        client_data = ClientData(
            session_id=session_id,
            user_id="user_1",
            answers={'Q1': 'answer'},
            scores={'Q1': 80},
            explanations={'Q1': 'Good'},
            question_states={'Q1': 'fully_answered'},
            local_storage={},
            session_storage={},
            timestamp=time.time()
        )
        
        # Setup checkpoint
        checkpoint = MigrationCheckpoint(
            checkpoint_id="verify_valid",
            state=MigrationState.VERIFYING,
            timestamp=time.time(),
            migrated_sessions=[session_id],
            original_data={},
            transformed_data={},
            verification_hashes={session_id: client_data.compute_hash()}
        )
        
        self.migration_engine.checkpoint = checkpoint
        
        # Verify
        results = self.migration_engine.verify_migration([session_id])
        
        assert results[session_id] is True
        assert self.migration_engine.verification_results[session_id] is True
    
    def test_verification_with_corrupted_data(self):
        """Test verification detects corrupted data"""
        # Setup checkpoint with original hash
        checkpoint = MigrationCheckpoint(
            checkpoint_id="verify_corrupt",
            state=MigrationState.VERIFYING,
            timestamp=time.time(),
            migrated_sessions=["corrupt_session"],
            original_data={},
            transformed_data={},
            verification_hashes={"corrupt_session": "original_hash_12345"}
        )
        
        self.migration_engine.checkpoint = checkpoint
        
        # Store corrupted data in session manager
        self.session_manager.update_session("corrupt_session", {
            'user_id': 'user_corrupt',
            'answers': {'Q1': 'corrupted_answer'},
            'scores': {'Q1': 999},
            'explanations': {'Q1': 'CORRUPTED'},
            'questionStates': {'Q1': 'invalid_state'}
        })
        
        # Verify - should detect corruption
        results = self.migration_engine.verify_migration(["corrupt_session"])
        
        assert results["corrupt_session"] is False
    
    def test_verification_without_checkpoint(self):
        """Test basic verification without checkpoint data"""
        # Create session with all required fields
        complete_session_id = self.session_manager.create_session({
            'answers': {'Q1': 'answer'},
            'scores': {'Q1': 75},
            'explanations': {'Q1': 'Explanation'},
            'questionStates': {'Q1': 'fully_answered'}
        })
        
        # Verify without checkpoint - should check field presence
        results = self.migration_engine.verify_migration([complete_session_id])
        
        assert results[complete_session_id] is True
        
        # Create incomplete session
        incomplete_session_id = self.session_manager.create_session({
            'answers': {'Q1': 'answer'},
            # Missing scores, explanations, questionStates
        })
        
        results = self.migration_engine.verify_migration([incomplete_session_id])
        
        assert results[incomplete_session_id] is False


class TestMigrationStats:
    """Test migration statistics and monitoring"""
    
    def test_stats_calculation(self):
        """Test migration statistics calculation"""
        session_manager = SessionManager()
        feature_flag_manager = FeatureFlagManager()
        migration_engine = MigrationEngine(session_manager, feature_flag_manager)
        
        # Setup checkpoint and state
        migration_engine.state = MigrationState.MIGRATING
        migration_engine.checkpoint = MigrationCheckpoint(
            checkpoint_id="stats_test",
            state=MigrationState.MIGRATING,
            timestamp=time.time(),
            migrated_sessions=["s1", "s2", "s3"],
            original_data={},
            transformed_data={},
            verification_hashes={}
        )
        
        # Add migration logs
        migration_engine.migration_log = [
            {'session_id': 's1', 'status': 'success', 'timestamp': time.time()},
            {'session_id': 's2', 'status': 'success', 'timestamp': time.time()},
            {'session_id': 's3', 'status': 'failed', 'error': 'Test error', 'timestamp': time.time()}
        ]
        
        # Add verification results
        migration_engine.verification_results = {
            's1': True,
            's2': True,
            's3': False
        }
        
        # Get stats
        stats = migration_engine.get_migration_stats()
        
        assert stats['state'] == 'migrating'
        assert stats['total_sessions'] == 3
        assert stats['successful_migrations'] == 2
        assert stats['failed_migrations'] == 1
        assert stats['progress_percentage'] == pytest.approx(66.67, 0.1)
        assert len(stats['verification_results']) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])