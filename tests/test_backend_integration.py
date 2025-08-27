#!/usr/bin/env python3
"""
Backend Integration Tests for Server-Driven UI Architecture

Tests the integration between all backend components:
- SessionManager
- DependencyEngine  
- CommandGenerator
- UISchemaGenerator
- EventHandler

This validates that the complete backend system works together correctly.
"""

import pytest
import json
import time
from unittest.mock import Mock, MagicMock

from src.backend.session_manager import SessionManager
from src.backend.dependency_engine import DependencyEngine
from src.backend.command_generator import CommandGenerator
from src.backend.ui_schema_generator import UISchemaGenerator
from src.backend.event_handler import EventHandler, UserEvent


class TestBackendIntegration:
    """Integration tests for all backend components working together"""
    
    @pytest.fixture
    def sample_questions(self):
        """Sample questions for testing"""
        return [
            {
                "id": "SG01",
                "text": "What is your main business challenge?",
                "question_type": "choice-single",
                "options": [
                    {"code": "revenue", "label": "Revenue decline"},
                    {"code": "cost", "label": "High costs"},
                    {"code": "other", "label": "Other"}
                ],
                "with_other": True,
                "other_text_id": "SG01_OTHER",
                "ai_context": {"include_answers": []},
                "cluster_name": "Strategic"
            },
            {
                "id": "SG02",
                "text": "How severe is this challenge?",
                "question_type": "choice-single",
                "options": [
                    {"code": "minor", "label": "Minor impact"},
                    {"code": "major", "label": "Major impact"}
                ],
                "ai_context": {"include_answers": ["SG01"]},
                "cluster_name": "Strategic"
            }
        ]
    
    @pytest.fixture
    def integrated_backend(self, sample_questions):
        """Create integrated backend system"""
        # Initialize components
        session_manager = SessionManager()
        dependency_engine = DependencyEngine()
        ui_schema_generator = UISchemaGenerator()
        command_generator = CommandGenerator()
        
        # Build dependency graph
        dependency_engine.build_dependency_graph(sample_questions)
        
        # Create event handler with all dependencies
        event_handler = EventHandler(
            session_manager=session_manager,
            dependency_engine=dependency_engine,
            command_generator=command_generator,
            ui_schema_generator=ui_schema_generator
        )
        
        return {
            'session_manager': session_manager,
            'dependency_engine': dependency_engine,
            'ui_schema_generator': ui_schema_generator,
            'command_generator': command_generator,
            'event_handler': event_handler,
            'questions': sample_questions
        }
    
    def test_complete_question_answering_workflow(self, integrated_backend):
        """Test complete workflow: session creation -> question answering -> cascades"""
        backend = integrated_backend
        
        # 1. Create session
        session_id = backend['session_manager'].create_session({'user_id': 'test_user'})
        assert session_id is not None
        
        # 2. Generate UI schema for first question
        schema = backend['ui_schema_generator'].question_to_schema(backend['questions'][0], return_dict=True)
        assert schema is not None
        assert schema['type'] == 'choice-single'
        
        # 3. Generate render command
        render_cmd = backend['command_generator'].generate_render_command(
            backend['questions'][0], schema, {})
        assert render_cmd['type'] == 'RENDER'
        assert render_cmd['data']['id'] == 'SG01'
        
        # 4. Simulate user answering first question
        event = UserEvent(
            event='answer_change',
            data={
                'session_id': session_id,
                'questionId': 'SG01',
                'value': ['revenue']
            }
        )
        
        result = backend['event_handler'].process_event(event)
        assert result.success is True
        assert len(result.commands) > 0
        
        # 5. Check session was updated
        session = backend['session_manager'].get_session(session_id)
        assert session is not None
        session_data = session.get('data', session)  # Handle both flat and nested formats
        assert 'SG01' in session_data.get('answers', {})
        
        # 6. Check cascade dependencies identified
        cascades = backend['dependency_engine'].get_cascade_dependencies('SG01')
        assert 'SG02' in cascades
    
    def test_error_handling_across_components(self, integrated_backend):
        """Test error propagation and handling across components"""
        backend = integrated_backend
        
        # Create session
        session_id = backend['session_manager'].create_session({})
        
        # Try to process invalid event
        invalid_event = UserEvent(
            event='invalid_event_type',
            data={
                'session_id': session_id,
                'questionId': 'NONEXISTENT',
                'value': None
            }
        )
        
        result = backend['event_handler'].process_event(invalid_event)
        assert result.success is False
        assert len(result.errors) > 0
        assert 'invalid_event_type' in str(result.errors[0])
        
        # Session should remain unchanged
        session = backend['session_manager'].get_session(session_id)
        session_data = session.get('data', session)  # Handle both flat and nested formats
        assert session_data.get('answers', {}) == {}
    
    def test_dependency_cascade_processing(self, integrated_backend):
        """Test that dependency cascades are properly processed"""
        backend = integrated_backend
        session_id = backend['session_manager'].create_session({})
        
        # Answer first question which should trigger cascade to second question
        event = UserEvent(
            event='answer_change',
            data={
                'session_id': session_id,
                'questionId': 'SG01',
                'value': ['revenue']
            }
        )
        
        result = backend['event_handler'].process_event(event)
        assert result.success is True
        
        # Should generate commands for both original and cascaded question
        command_types = [cmd.get('type') for cmd in result.commands]
        assert 'UPDATE' in command_types or 'RENDER' in command_types
        
        # Check that cascade was processed
        cascades = backend['dependency_engine'].get_cascade_dependencies('SG01')
        assert 'SG02' in cascades
    
    def test_concurrent_event_processing(self, integrated_backend):
        """Test concurrent event processing doesn't break state consistency"""
        backend = integrated_backend
        session_id = backend['session_manager'].create_session({})
        
        # Create multiple events
        events = [
            UserEvent(
                event='answer_change',
                data={
                    'session_id': session_id,
                    'questionId': 'SG01',
                    'value': ['revenue']
                }
            ),
            UserEvent(
                event='answer_blur',
                data={
                    'session_id': session_id,
                    'questionId': 'SG01',
                    'value': ['cost']
                }
            )
        ]
        
        # Process events
        results = []
        for event in events:
            result = backend['event_handler'].process_event(event)
            results.append(result)
        
        # All events should be processed successfully
        assert all(r.success for r in results)
        
        # Final session state should be consistent
        session = backend['session_manager'].get_session(session_id)
        session_data = session.get('data', session)  # Handle both flat and nested formats
        assert 'SG01' in session_data.get('answers', {})
        
        # Should have final answer (cost, from blur event)
        assert session_data.get('answers', {}).get('SG01') == ['cost']
    
    def test_performance_under_realistic_load(self, integrated_backend):
        """Test system performance with realistic question load"""
        backend = integrated_backend
        
        start_time = time.time()
        
        # Create multiple sessions and process events
        session_ids = []
        for i in range(10):
            session_id = backend['session_manager'].create_session({'user_id': f'user_{i}'})
            session_ids.append(session_id)
            
            # Process answer for each session
            event = UserEvent(
                event='answer_change',
                data={
                    'session_id': session_id,
                    'questionId': 'SG01',
                    'value': ['revenue']
                }
            )
            
            result = backend['event_handler'].process_event(event)
            assert result.success is True
        
        end_time = time.time()
        
        # Should process 10 sessions in under 1 second
        assert end_time - start_time < 1.0
        
        # All sessions should be properly maintained
        assert len(session_ids) == 10
        for session_id in session_ids:
            session = backend['session_manager'].get_session(session_id)
            assert session is not None
            session_data = session.get('data', session)  # Handle both flat and nested formats
            assert 'SG01' in session_data.get('answers', {})


class TestComponentInterfaces:
    """Test that component interfaces are compatible"""
    
    def test_session_manager_interface_compatibility(self):
        """Test SessionManager interface matches expected format"""
        sm = SessionManager()
        session_id = sm.create_session({'test': 'data'})
        
        # Should return string session ID
        assert isinstance(session_id, str)
        
        # Should be able to retrieve session
        session = sm.get_session(session_id)
        assert isinstance(session, dict)
        
        # Should be able to update session
        sm.update_session(session_id, {'new_data': 'value'})
        updated = sm.get_session(session_id, flat_format=True)
        assert 'new_data' in updated
    
    def test_command_generator_interface_compatibility(self):
        """Test CommandGenerator generates valid protocol commands"""
        cg = CommandGenerator()
        
        # Test render command
        question = {
            'id': 'TEST',
            'text': 'Test question',
            'question_type': 'text'
        }
        schema = {'type': 'text', 'label': 'Test question'}
        
        render_cmd = cg.generate_render_command(question, schema, {})
        
        # Should match protocol format
        assert render_cmd['type'] == 'RENDER'
        assert 'data' in render_cmd
        assert render_cmd['data']['id'] == 'TEST'
    
    def test_ui_schema_generator_interface_compatibility(self):
        """Test UISchemaGenerator output format"""
        usg = UISchemaGenerator()
        
        question = {
            'id': 'TEST',
            'text': 'Test question',
            'question_type': 'text'
        }
        
        schema = usg.question_to_schema(question, return_dict=True)
        
        # Should have required fields
        assert 'type' in schema
        assert 'label' in schema
        assert schema['type'] == 'text'
        assert schema['label'] == 'Test question'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])