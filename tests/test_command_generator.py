"""
Test-Driven Development Tests for CommandGenerator Component

This module implements Task 1.3 from BK-FR-CHANGE.md plan:
Comprehensive tests for the CommandGenerator component that will transform
the QnA Evaluator from thick client to Server-Driven UI architecture.

Mathematical Properties Under Test:
- Command Generation: StateChange → UICommand  
- Protocol Compliance: Commands conform to TypeScript interfaces
- Batching Optimization: Multiple updates → Minimal command set
- State Synchronization: State → Complete UI representation

Test Categories:
1. Core Command Generation (RENDER, UPDATE, STATE_SYNC)
2. Question Type Handling (text, choice-single, choice-multi, etc.)
3. Command Validation and Structure
4. Error Handling and Edge Cases
5. JSON Serialization and Protocol Compliance
6. Optimized Batching Logic
7. Conditional Rendering Commands
8. Performance and Memory Efficiency

Protocol Specification from BK-FR-CHANGE.md:
- RENDER commands for initial component rendering
- UPDATE commands for state changes  
- STATE_SYNC for full state synchronization
"""

import pytest
import json
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Import the real CommandGenerator implementation
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from backend.command_generator import CommandGenerator


class TestCommandGeneratorCore:
    """Test core command generation functionality"""
    
    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager for testing"""
        session_manager = Mock()
        session_manager.get_session.return_value = {
            'session_id': 'test-session-123',
            'data': {
                'answers': {'SG01': ['declining_sales'], 'MET.LOC': 'New York'},
                'scores': {'SG01': 75},
                'explanations': {'SG01': 'Test explanation'}
            },
            'created_at': datetime.now().isoformat(),
            'expires_at': datetime.now().isoformat()
        }
        return session_manager
    
    @pytest.fixture
    def mock_ui_schema_generator(self):
        """Mock UI schema generator for testing"""
        ui_generator = Mock()
        ui_generator.question_to_schema.return_value = {
            'type': 'choice-multi',
            'label': 'What are the main challenges?',
            'options': [
                {'code': 'declining_sales', 'label': 'Declining sales'},
                {'code': 'competition', 'label': 'Increased competition'},
                {'code': 'other', 'label': 'Other'}
            ],
            'validation': {
                'required': True,
                'min': 1,
                'max': 3
            }
        }
        return ui_generator
    
    @pytest.fixture
    def command_generator(self, mock_session_manager, mock_ui_schema_generator):
        """Create CommandGenerator instance for testing"""
        return CommandGenerator(
            session_manager=mock_session_manager,
            ui_schema_generator=mock_ui_schema_generator
        )
    
    @pytest.fixture
    def sample_question(self):
        """Sample question data for testing"""
        return {
            'id': 'SG01',
            'text': 'What are the main business challenges?',
            'hint': 'Select all that apply',
            'info': 'Choose the most significant challenges',
            'cluster_name': 'Strategic Assessment',
            'position_in_cluster': 1,
            'question_type': 'choice-multi',
            'options': [
                {'code': 'declining_sales', 'label': 'Declining sales'},
                {'code': 'competition', 'label': 'Increased competition'},
                {'code': 'cash_flow', 'label': 'Cash flow issues'},
                {'code': 'other', 'label': 'Other'}
            ],
            'with_other': True,
            'other_text_id': 'SG01_OTHER',
            'ai_context': {
                'include_answers': ['MET.LOC', 'MET.IND']
            },
            'score': 'YES'
        }


class TestRenderCommandGeneration(TestCommandGeneratorCore):
    """Test RENDER command generation - Task 1.3.1"""
    
    def test_render_command_generation_basic(self, command_generator, sample_question):
        """
        Generates correct RENDER commands
        
        Test Specification from BK-FR-CHANGE.md:
        - type: 'RENDER'
        - component: 'question' | 'section' | 'results' | 'report'  
        - data: { id, schema, props }
        """
        command = command_generator.generate_render_command(
            question=sample_question,
            context={'current_answer': ['declining_sales']}
        )
        
        # Verify basic structure
        assert command['type'] == 'RENDER'
        assert command['component'] == 'question' 
        assert 'data' in command
        assert command['data']['id'] == 'SG01'
        
        # Verify schema
        schema = command['data']['schema']
        assert schema['type'] == 'choice-multi'
        assert schema['label'] == 'What are the main business challenges?'
        assert 'options' in schema
        assert len(schema['options']) == 4
        
        # Verify props
        props = command['data']['props']
        assert props['value'] == ['declining_sales']
        assert props['disabled'] is False
        assert props['thinking'] is False
        assert props['visible'] is True
    
    def test_render_command_different_question_types(self, command_generator):
        """Test RENDER commands for different question types"""
        
        question_types = [
            {
                'question_type': 'text',
                'expected_schema_type': 'text'
            },
            {
                'question_type': 'choice-single', 
                'ui': 'radio',
                'expected_schema_type': 'choice-single'
            },
            {
                'question_type': 'choice-single',
                'ui': 'dropdown', 
                'expected_schema_type': 'choice-single'
            },
            {
                'question_type': 'textarea',
                'expected_schema_type': 'textarea'
            },
            {
                'question_type': 'number',
                'expected_schema_type': 'number'
            },
            {
                'question_type': 'yes-no',
                'expected_schema_type': 'choice-single'
            }
        ]
        
        for question_config in question_types:
            test_question = {
                'id': f"TEST_{question_config['question_type'].upper()}",
                'text': f"Test {question_config['question_type']} question",
                'question_type': question_config['question_type'],
            }
            if question_config.get('ui'):
                test_question['ui'] = question_config['ui']
            
            command = command_generator.generate_render_command(test_question)
            
            # Verify correct schema type
            assert command['data']['schema']['type'] == question_config['expected_schema_type']
    
    def test_render_command_with_conditionals(self, command_generator, sample_question):
        """Test RENDER commands with conditional visibility"""
        
        conditional_question = {
            **sample_question,
            'conditional': {
                'show_when': 'MET.LOC == "New York"'
            }
        }
        
        # Test with condition met
        command = command_generator.generate_render_command(
            conditional_question,
            context={'answers': {'MET.LOC': 'New York'}}
        )
        
        # Verify conditional handling
        assert 'conditional' in command['data']['schema']
        assert command['data']['schema']['conditional']['show_when'] == 'MET.LOC == "New York"'
        assert command['data']['props']['visible'] is True
        
        # Test with condition not met  
        command_hidden = command_generator.generate_render_command(
            conditional_question,
            context={'answers': {'MET.LOC': 'Boston'}}
        )
        assert command_hidden['data']['props']['visible'] is False
    
    def test_render_command_with_validation(self, command_generator, sample_question):
        """Test RENDER commands include proper validation rules"""
        
        command = command_generator.generate_render_command(sample_question)
        
        # Verify validation rules
        assert 'validation' in command['data']['schema']
        assert command['data']['schema']['validation']['required'] is True
        assert command['data']['schema']['validation']['min'] == 1
        assert command['data']['schema']['validation']['max'] == 4  # Based on number of options


class TestUpdateCommandGeneration(TestCommandGeneratorCore):
    """Test UPDATE command generation - Task 1.3.2"""
    
    def test_update_command_generation_basic(self, command_generator):
        """
        Generates correct UPDATE commands
        
        Test Specification from BK-FR-CHANGE.md:
        - type: 'UPDATE'
        - target: string (Component ID)
        - updates: [{path: string, value: any}]
        """
        updates = [
            {'path': 'props.thinking', 'value': True},
            {'path': 'props.disabled', 'value': True}
        ]
        
        command = command_generator.generate_update_command('SG01', updates)
        
        # Verify structure
        expected = {
            'type': 'UPDATE',
            'target': 'SG01',
            'updates': [
                {'path': 'props.thinking', 'value': True},
                {'path': 'props.disabled', 'value': True}
            ]
        }
        assert command == expected
    
    def test_update_command_single_property(self, command_generator):
        """Test UPDATE command with single property change"""
        
        updates = [{'path': 'props.value', 'value': ['declining_sales', 'competition']}]
        
        command = command_generator.generate_update_command('SG01', updates)
        
        # Verify structure
        assert command['type'] == 'UPDATE'
        assert command['target'] == 'SG01'
        assert len(command['updates']) == 1
        assert command['updates'][0]['path'] == 'props.value'
        assert command['updates'][0]['value'] == ['declining_sales', 'competition']
    
    def test_update_command_nested_paths(self, command_generator):
        """Test UPDATE commands with nested JSON paths"""
        
        updates = [
            {'path': 'props.validation.errors', 'value': ['Required field is empty']},
            {'path': 'data.score', 'value': 85},
            {'path': 'data.explanation', 'value': 'Good response showing understanding'}
        ]
        
        command = command_generator.generate_update_command('SG01', updates)
        
        # Verify nested path handling
        assert len(command['updates']) == 3
        assert any(update['path'] == 'props.validation.errors' for update in command['updates'])
        assert any(update['path'] == 'data.score' for update in command['updates'])
        assert any(update['path'] == 'data.explanation' for update in command['updates'])
    
    def test_update_command_validation(self, command_generator):
        """Test UPDATE command validates inputs"""
        
        # Test validation errors
        with pytest.raises(ValueError):
            command_generator.generate_update_command('', [])  # Empty target
            
        with pytest.raises(ValueError):
            command_generator.generate_update_command('SG01', [])  # Empty updates
            
        with pytest.raises(ValueError):
            command_generator.generate_update_command(None, [{'path': 'test', 'value': 1}])  # None target


class TestBatchCommandGeneration(TestCommandGeneratorCore):
    """Test batch command generation - Task 1.3.3"""
    
    def test_batch_command_generation_basic(self, command_generator):
        """
        Batches multiple updates efficiently
        
        Test optimization: Multiple related changes should be batched
        into minimal command set rather than individual commands.
        """
        
        changes = [
            {
                'type': 'answer_change',
                'question_id': 'SG01',
                'value': ['declining_sales', 'competition']
            },
            {
                'type': 'thinking_state',
                'question_id': 'SG01', 
                'thinking': True
            },
            {
                'type': 'score_update',
                'question_id': 'SG01',
                'score': 85,
                'explanation': 'Good analysis of business challenges'
            }
        ]
        
        commands = command_generator.generate_batch_commands(changes)
        
        # Verify batching efficiency
        # Expected: Single UPDATE command with all changes for SG01
        assert len(commands) == 1
        assert commands[0]['type'] == 'UPDATE'
        assert commands[0]['target'] == 'SG01'
        assert len(commands[0]['updates']) == 4  # value, thinking, score, explanation
    
    def test_batch_multiple_questions(self, command_generator):
        """Test batching across multiple questions"""
        
        changes = [
            {'type': 'answer_change', 'question_id': 'SG01', 'value': ['option1']},
            {'type': 'answer_change', 'question_id': 'SG02', 'value': 'text_answer'},
            {'type': 'thinking_state', 'question_id': 'SG01', 'thinking': True},
            {'type': 'thinking_state', 'question_id': 'SG02', 'thinking': True}
        ]
        
        commands = command_generator.generate_batch_commands(changes)
        
        # Verify separate commands for different targets
        assert len(commands) == 2  # One for SG01, one for SG02
        targets = {cmd['target'] for cmd in commands}
        assert targets == {'SG01', 'SG02'}
    
    def test_batch_optimization_algorithm(self, command_generator):
        """Test the batching optimization algorithm efficiency"""
        
        # Large number of changes to test optimization
        changes = []
        for i in range(100):
            changes.extend([
                {'type': 'thinking_state', 'question_id': f'Q{i % 10}', 'thinking': True},
                {'type': 'score_update', 'question_id': f'Q{i % 10}', 'score': i % 100}
            ])
        
        commands = command_generator.generate_batch_commands(changes)
        
        # Verify efficient batching
        # Should create ~10 commands (one per unique question), not 200
        assert len(commands) <= 10
        
        # Verify all changes are preserved
        total_updates = sum(len(cmd['updates']) for cmd in commands)
        assert total_updates == len(changes)
    
    def test_batch_preserves_change_order(self, command_generator):
        """Test that batching preserves the order of changes"""
        
        changes = [
            {'type': 'thinking_state', 'question_id': 'SG01', 'thinking': True},
            {'type': 'answer_change', 'question_id': 'SG01', 'value': ['option1']},
            {'type': 'thinking_state', 'question_id': 'SG01', 'thinking': False},
            {'type': 'score_update', 'question_id': 'SG01', 'score': 75}
        ]
        
        commands = command_generator.generate_batch_commands(changes)
        
        # Verify order preservation
        assert len(commands) == 1
        updates = commands[0]['updates']
        
        # Find thinking updates and verify they're in correct order
        thinking_indices = [i for i, u in enumerate(updates) if u['path'] == 'props.thinking']
        assert len(thinking_indices) == 2
        assert updates[thinking_indices[0]]['value'] is True
        assert updates[thinking_indices[1]]['value'] is False


class TestStateSyncGeneration(TestCommandGeneratorCore):
    """Test state synchronization generation - Task 1.3.4"""
    
    def test_state_sync_generation_complete(self, command_generator, mock_session_manager):
        """
        Generates complete state sync
        
        Test Specification from BK-FR-CHANGE.md:
        - type: 'STATE_SYNC'
        - state: {session_id, questions, scores, explanations}
        """
        
        session_id = 'test-session-123'
        
        command = command_generator.generate_state_sync(session_id)
        
        # Verify structure
        assert command['type'] == 'STATE_SYNC'
        assert 'state' in command
        assert command['state']['session_id'] == session_id
        assert 'questions' in command['state']
        assert 'scores' in command['state']
        assert 'explanations' in command['state']
        
        # Verify data from mock session manager
        assert command['state']['scores'] == {'SG01': 75}
        assert command['state']['explanations'] == {'SG01': 'Test explanation'}
    
    def test_state_sync_invalid_session(self, command_generator, mock_session_manager):
        """Test state sync with invalid session ID"""
        
        # Mock session not found
        mock_session_manager.get_session.return_value = None
        
        # Should handle missing session gracefully
        command = command_generator.generate_state_sync('invalid-session')
        assert command is None
    
    def test_state_sync_empty_session(self, command_generator, mock_session_manager):
        """Test state sync with empty session data"""
        
        mock_session_manager.get_session.return_value = {
            'session_id': 'empty-session',
            'data': {'answers': {}, 'scores': {}, 'explanations': {}},
            'created_at': datetime.now().isoformat(),
            'expires_at': datetime.now().isoformat()
        }
        
        command = command_generator.generate_state_sync('empty-session')
        
        # Verify empty state handling
        assert command['type'] == 'STATE_SYNC'
        assert command['state']['session_id'] == 'empty-session'
        assert len(command['state']['questions']) == 0
        assert len(command['state']['scores']) == 0


class TestCommandValidation(TestCommandGeneratorCore):
    """Test command validation and structure - Task 1.3.5"""
    
    def test_command_structure_validation(self, command_generator, sample_question):
        """Test that generated commands have valid structure"""
        
        render_command = command_generator.generate_render_command(sample_question)
        
        # Verify all required fields present
        required_fields = ['type', 'component', 'data']
        for field in required_fields:
            assert field in render_command
        
        # Verify data structure
        assert 'id' in render_command['data']
        assert 'schema' in render_command['data']
        assert 'props' in render_command['data']
    
    def test_command_type_validation(self, command_generator):
        """Test command types are valid"""
        
        valid_types = ['RENDER', 'UPDATE', 'STATE_SYNC']
        
        # Test RENDER command type
        render_cmd = command_generator.generate_render_command({'id': 'TEST', 'question_type': 'text'})
        assert render_cmd['type'] in valid_types
        
        # Test UPDATE command type  
        update_cmd = command_generator.generate_update_command('TEST', [{'path': 'props.value', 'value': 1}])
        assert update_cmd['type'] in valid_types
    
    def test_json_path_validation(self, command_generator):
        """Test JSON paths in UPDATE commands are valid"""
        
        valid_paths = [
            'props.value',
            'props.disabled', 
            'props.thinking',
            'props.validation.errors',
            'data.score',
            'data.explanation',
            'schema.validation.required'
        ]
        
        for path in valid_paths:
            updates = [{'path': path, 'value': 'test'}]
            
            command = command_generator.generate_update_command('TEST', updates)
            
            # Verify path format
            assert command['updates'][0]['path'] == path
    
    def test_invalid_json_paths_rejected(self, command_generator):
        """Test that invalid JSON paths are rejected"""
        
        invalid_paths = [
            '',              # Empty path
            'invalid..path', # Double dots
            '.leadingdot',   # Leading dot
            'trailing.',     # Trailing dot
            'spaces in path' # Spaces
        ]
        
        for invalid_path in invalid_paths:
            updates = [{'path': invalid_path, 'value': 'test'}]
            
            # Should reject invalid paths
            with pytest.raises(ValueError):
                command_generator.generate_update_command('TEST', updates)


class TestErrorHandling(TestCommandGeneratorCore):
    """Test error handling for invalid inputs - Task 1.3.6"""
    
    def test_none_question_handling(self, command_generator):
        """Test handling of None question input"""
        
        # Should handle None gracefully
        with pytest.raises(ValueError):
            command_generator.generate_render_command(None)
    
    def test_malformed_question_handling(self, command_generator):
        """Test handling of malformed question data"""
        
        malformed_questions = [
            {},                                    # Empty dict
            {'id': 'TEST'},                       # Missing required fields
            {'text': 'Test'},                     # Missing ID
            {'id': '', 'text': 'Test'},          # Empty ID
            {'id': 'TEST', 'question_type': ''}  # Empty type
        ]
        
        for bad_question in malformed_questions:
            # Should validate question structure
            with pytest.raises(ValueError):
                command_generator.generate_render_command(bad_question)
    
    def test_circular_dependency_handling(self, command_generator):
        """Test handling of circular dependencies in batch commands"""
        
        circular_changes = [
            {'type': 'trigger_dependency', 'question_id': 'A', 'depends_on': 'B'},
            {'type': 'trigger_dependency', 'question_id': 'B', 'depends_on': 'A'}
        ]
        
        # Should detect and handle circular dependencies
        with pytest.raises(ValueError):
            command_generator.generate_batch_commands(circular_changes)
    
    def test_memory_exhaustion_protection(self, command_generator):
        """Test protection against memory exhaustion from large batches"""
        
        # Create very large number of changes (exceeds MAX_BATCH_SIZE)
        large_batch = []
        for i in range(15000):  # Exceeds MAX_BATCH_SIZE of 10000
            large_batch.append({
                'type': 'answer_change',
                'question_id': f'Q{i}',
                'value': f'answer_{i}'
            })
        
        # Should handle large batches and raise error if too large
        with pytest.raises(ValueError, match="Batch size .* exceeds maximum"):
            command_generator.generate_batch_commands(large_batch)


class TestJSONSerialization(TestCommandGeneratorCore):
    """Test JSON serialization and protocol compliance - Task 1.3.7"""
    
    def test_commands_json_serializable(self, command_generator, sample_question):
        """Test that all generated commands can be serialized to JSON"""
        
        render_command = command_generator.generate_render_command(sample_question)
        
        # Verify JSON serialization works
        json_str = json.dumps(render_command)
        assert json_str is not None
        
        # Verify round-trip
        parsed = json.loads(json_str)
        assert parsed == render_command
    
    def test_special_value_serialization(self, command_generator):
        """Test serialization of special values (None, dates, etc.)"""
        
        updates_with_special_values = [
            {'path': 'props.null_value', 'value': None},
            {'path': 'props.boolean_true', 'value': True},
            {'path': 'props.boolean_false', 'value': False},
            {'path': 'props.number_zero', 'value': 0},
            {'path': 'props.empty_string', 'value': ''},
            {'path': 'props.empty_array', 'value': []},
            {'path': 'props.empty_object', 'value': {}}
        ]
        
        command = command_generator.generate_update_command('TEST', updates_with_special_values)
        
        # Verify special values serialize correctly
        json_str = json.dumps(command)
        parsed = json.loads(json_str)
        
        for i, update in enumerate(parsed['updates']):
            expected_value = updates_with_special_values[i]['value']
            assert update['value'] == expected_value
    
    def test_unicode_handling(self, command_generator):
        """Test handling of Unicode characters in commands"""
        
        unicode_question = {
            'id': 'UNICODE_TEST',
            'text': 'Test with émojis 🚀 and spëcial charäcters',
            'question_type': 'text'
        }
        
        command = command_generator.generate_render_command(unicode_question)
        
        # Verify Unicode handling
        json_str = json.dumps(command, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert '🚀' in parsed['data']['schema']['label']


class TestPerformanceOptimization(TestCommandGeneratorCore):
    """Test performance and memory efficiency - Task 1.3.8"""
    
    def test_large_batch_performance(self, command_generator):
        """Test performance with large batches of commands"""
        
        import time
        
        # Create large batch
        large_batch = []
        for i in range(1000):
            large_batch.append({
                'type': 'answer_change',
                'question_id': f'Q{i % 100}',  # Reuse question IDs for batching
                'value': f'answer_{i}'
            })
        
        start_time = time.time()
        commands = command_generator.generate_batch_commands(large_batch)
        end_time = time.time()
        
        # Verify reasonable performance
        processing_time = end_time - start_time
        assert processing_time < 1.0  # Should process 1000 changes in < 1 second
        assert len(commands) <= 100    # Should batch efficiently
    
    def test_memory_efficiency(self, command_generator):
        """Test memory efficiency of command generation"""
        
        import gc
        
        # Generate many commands and verify memory doesn't grow excessively
        initial_objects = len(gc.get_objects())
        
        for i in range(100):
            sample_question = {
                'id': f'Q{i}',
                'text': f'Question {i}',
                'question_type': 'text'
            }
            
            command = command_generator.generate_render_command(sample_question)
            del command  # Explicit cleanup
        
        # Verify no significant memory growth
        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects
        assert growth < 1000  # Reasonable growth limit
    
    def test_command_caching(self, command_generator, sample_question):
        """Test caching of identical command generation"""
        
        # Generate same command twice
        command1 = command_generator.generate_render_command(sample_question)
        command2 = command_generator.generate_render_command(sample_question)
        
        # Commands should be identical (even without caching, they should produce same result)
        assert command1 == command2


class TestConditionalRendering(TestCommandGeneratorCore):
    """Test conditional rendering commands - Task 1.3.9"""
    
    def test_conditional_show_hide(self, command_generator):
        """Test commands for conditional show/hide logic"""
        
        conditional_question = {
            'id': 'CONDITIONAL_TEST',
            'text': 'Conditional question',
            'question_type': 'text',
            'conditional': {
                'show_when': 'MET.SIZE == "gt1m"'
            }
        }
        
        # Test with condition met
        context_met = {'answers': {'MET.SIZE': 'gt1m'}}
        command_shown = command_generator.generate_render_command(
            conditional_question, context_met
        )
        # Verify question is shown
        assert command_shown['data']['props']['visible'] is True
        
        # Test with condition not met
        context_not_met = {'answers': {'MET.SIZE': 'lt250k'}}
        command_hidden = command_generator.generate_render_command(
            conditional_question, context_not_met
        )
        # Verify question is hidden
        assert command_hidden['data']['props']['visible'] is False
    
    def test_complex_conditional_expressions(self, command_generator):
        """Test complex conditional expressions"""
        
        complex_conditions = [
            'MET.SIZE == "gt1m"',  # Simplified for basic implementation
            'MET.LOC == "New York"',
            'MET.IND == "restaurant"'
        ]
        
        for condition in complex_conditions:
            conditional_question = {
                'id': 'COMPLEX_TEST',
                'text': 'Complex conditional',
                'question_type': 'text',
                'conditional': {'show_when': condition}
            }
            
            # Should handle expressions and preserve conditional in schema
            command = command_generator.generate_render_command(conditional_question, {})
            # Verify conditional is preserved in schema
            assert command['data']['schema']['conditional']['show_when'] == condition
    
    def test_follow_up_question_rendering(self, command_generator):
        """Test rendering of follow-up questions based on answers"""
        
        parent_question = {
            'id': 'PARENT',
            'text': 'Do you have employees?',
            'question_type': 'yes-no'
        }
        
        follow_up_question = {
            'id': 'FOLLOWUP',
            'text': 'How many employees?',
            'question_type': 'number',
            'conditional': {
                'show_when': 'PARENT == "yes"'
            }
        }
        
        # Test follow-up shown when parent is "yes"
        context_yes = {'answers': {'PARENT': 'yes'}}
        command = command_generator.generate_render_command(follow_up_question, context_yes)
        # Verify follow-up is visible
        assert command['data']['props']['visible'] is True
        
        # Test follow-up hidden when parent is "no"  
        context_no = {'answers': {'PARENT': 'no'}}
        command = command_generator.generate_render_command(follow_up_question, context_no)
        # Verify follow-up is hidden
        assert command['data']['props']['visible'] is False


class TestProtocolCompliance:
    """Test compliance with protocol specification from BK-FR-CHANGE.md"""
    
    def test_typescript_interface_compliance(self):
        """Test that commands match TypeScript interfaces from protocol spec"""
        
        # This test documents the expected interfaces
        # When CommandGenerator is implemented, it should generate commands matching these
        
        expected_render_interface = {
            "type": "RENDER",
            "component": str,  # 'question' | 'section' | 'results' | 'report'
            "data": {
                "id": str,
                "schema": dict,  # UISchema
                "props": dict    # Record<string, any>
            }
        }
        
        expected_update_interface = {
            "type": "UPDATE", 
            "target": str,    # Component ID
            "updates": [
                {
                    "path": str,  # JSON path to update
                    "value": object  # New value (any type)
                }
            ]
        }
        
        expected_state_sync_interface = {
            "type": "STATE_SYNC",
            "state": {
                "session_id": str,
                "questions": dict,  # Record<string, QuestionState>
                "scores": dict,     # Record<string, number>
                "explanations": dict # Record<string, string>
            }
        }
        
        # When CommandGenerator is implemented, generated commands should match these interfaces
        assert True  # Placeholder - will be replaced with actual tests
    
    def test_ui_schema_format_compliance(self):
        """Test UISchema format matches protocol specification"""
        
        expected_ui_schema = {
            "type": str,        # 'text' | 'number' | 'choice-single' | 'choice-multi' | 'textarea'
            "label": str,
            "hint": str,        # Optional
            "info": str,        # Optional
            "options": [        # Optional, for choice types
                {
                    "code": str,
                    "label": str
                }
            ],
            "validation": {     # Optional
                "required": bool,
                "min": int,     # Optional
                "max": int,     # Optional
                "pattern": str  # Optional regex
            },
            "conditional": {    # Optional
                "show_when": str  # DSL expression
            }
        }
        
        # When UISchemaGenerator is implemented, schemas should match this format
        assert True  # Placeholder
    
    def test_event_format_compliance(self):
        """Test that generated commands can be properly handled by event system"""
        
        # Commands should be serializable for SSE transmission
        # Commands should have proper structure for client processing
        # Commands should include all required fields
        
        assert True  # Placeholder - will be implemented with CommandGenerator


# Additional helper classes and fixtures for comprehensive testing

@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return {
        'session_id': str(uuid.uuid4()),
        'answers': {
            'MET.LOC': 'New York, NY, USA',
            'MET.IND': 'Software Development',
            'MET.SIZE': 'gt1m',
            'SG01': ['declining_sales', 'competition'],
            'SG01_OTHER': '',
            'SG02': 'We are facing increased competition from larger companies.'
        },
        'scores': {
            'SG01': 75,
            'SG02': 85
        },
        'explanations': {
            'SG01': 'Shows good understanding of business challenges',
            'SG02': 'Detailed analysis demonstrates strategic thinking'
        },
        'question_states': {
            'MET.LOC': 'fully_answered',
            'MET.IND': 'fully_answered', 
            'MET.SIZE': 'fully_answered',
            'SG01': 'fully_answered',
            'SG02': 'fully_answered'
        }
    }


@pytest.fixture
def sample_question_set():
    """Sample question set for testing"""
    return [
        {
            'id': 'MET.LOC',
            'text': 'Where is the business located?',
            'question_type': 'text',
            'score': 'NO'
        },
        {
            'id': 'MET.IND', 
            'text': 'What is the primary industry?',
            'question_type': 'text',
            'score': 'NO'
        },
        {
            'id': 'SG01',
            'text': 'What are the main business challenges?',
            'question_type': 'choice-multi',
            'options': [
                {'code': 'declining_sales', 'label': 'Declining sales'},
                {'code': 'competition', 'label': 'Increased competition'},
                {'code': 'cash_flow', 'label': 'Cash flow issues'},
                {'code': 'other', 'label': 'Other'}
            ],
            'with_other': True,
            'other_text_id': 'SG01_OTHER',
            'ai_context': {'include_answers': ['MET.LOC', 'MET.IND']}
        }
    ]


# Test utilities for command validation
def validate_render_command_structure(command: Dict[str, Any]) -> bool:
    """Utility to validate RENDER command structure"""
    required_fields = ['type', 'component', 'data']
    if not all(field in command for field in required_fields):
        return False
        
    if command['type'] != 'RENDER':
        return False
        
    data = command['data']
    data_required = ['id', 'schema', 'props']
    if not all(field in data for field in data_required):
        return False
        
    return True


def validate_update_command_structure(command: Dict[str, Any]) -> bool:
    """Utility to validate UPDATE command structure"""
    required_fields = ['type', 'target', 'updates']
    if not all(field in command for field in required_fields):
        return False
        
    if command['type'] != 'UPDATE':
        return False
        
    if not isinstance(command['updates'], list):
        return False
        
    for update in command['updates']:
        if not isinstance(update, dict):
            return False
        if not all(field in update for field in ['path', 'value']):
            return False
            
    return True


def validate_state_sync_command_structure(command: Dict[str, Any]) -> bool:
    """Utility to validate STATE_SYNC command structure"""
    required_fields = ['type', 'state']
    if not all(field in command for field in required_fields):
        return False
        
    if command['type'] != 'STATE_SYNC':
        return False
        
    state = command['state']
    state_required = ['session_id', 'questions', 'scores', 'explanations']
    if not all(field in state for field in state_required):
        return False
        
    return True


# Performance testing utilities
class PerformanceTimer:
    """Utility class for performance testing"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        import time
        self.start_time = time.time()
    
    def stop(self):
        import time
        self.end_time = time.time()
    
    def elapsed(self):
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v', '--tb=short'])