"""
CommandGenerator - Server-Driven UI Command Generation

This module implements Task 1.3 from BK-FR-CHANGE.md plan:
Transform QnA Evaluator from thick client to Server-Driven UI architecture.

Mathematical Properties:
- Command Generation: StateChange → UICommand  
- Protocol Compliance: Commands conform to TypeScript interfaces
- Batching Optimization: Multiple updates → Minimal command set
- State Synchronization: State → Complete UI representation

Core Components:
1. CommandGenerator - Main class for generating protocol commands
2. Command Types: RENDER, UPDATE, STATE_SYNC, BATCH
3. UI Schema Generation for different question types
4. Efficient batching algorithm for performance optimization
5. JSON Path validation and manipulation
"""

import json
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime


class CommandGenerator:
    """
    Generates protocol commands for Server-Driven UI architecture.
    
    Transforms backend state changes into frontend-consumable commands
    that drive the entire user interface through declarative updates.
    """
    
    def __init__(self, session_manager=None, ui_schema_generator=None):
        """
        Initialize CommandGenerator with required dependencies.
        
        Args:
            session_manager: Session management for state retrieval
            ui_schema_generator: UI schema generation for components
        """
        self.session_manager = session_manager
        self.ui_schema_generator = ui_schema_generator
        
        # Valid command types per protocol specification
        self.VALID_COMMAND_TYPES = {'RENDER', 'UPDATE', 'STATE_SYNC', 'BATCH'}
        
        # Valid component types for RENDER commands
        self.VALID_COMPONENTS = {'question', 'section', 'results', 'report'}
        
        # Valid JSON path pattern for UPDATE commands
        self.JSON_PATH_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$')
        
        # Maximum batch size for memory efficiency
        self.MAX_BATCH_SIZE = 10000
    
    def generate_render_command(self, question: Dict[str, Any], schema: Dict[str, Any] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate RENDER command for initial component rendering.
        
        Args:
            question: Question configuration from JSON
            schema: Optional pre-generated UI schema
            context: Additional context (answers, state, etc.)
            
        Returns:
            RENDER command matching protocol specification:
            {
                type: 'RENDER',
                component: 'question' | 'section' | 'results' | 'report',
                data: { id, schema, props }
            }
        """
        if question is None:
            raise ValueError("Question cannot be None")
        
        if not isinstance(question, dict):
            raise ValueError("Question must be a dictionary")
        
        if not question.get('id'):
            raise ValueError("Question must have an 'id' field")
        
        if not question.get('question_type'):
            raise ValueError("Question must have a 'question_type' field")
        
        context = context or {}
        
        # Use provided schema or generate UI schema for the question
        if schema is None:
            schema = self._generate_ui_schema(question)
        
        # Generate component props
        props = self._generate_component_props(question, context)
        
        # Handle conditional rendering
        if question.get('conditional'):
            props['visible'] = self._evaluate_conditional(question['conditional'], context)
            schema['conditional'] = question['conditional']
        else:
            props['visible'] = True
        
        return {
            'type': 'RENDER',
            'component': 'question',
            'data': {
                'id': question['id'],
                'schema': schema,
                'props': props
            }
        }
    
    def generate_evaluation_command(self, question_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate EVALUATION command for AI processing.
        
        Args:
            question_id: ID of question to evaluate
            context: Evaluation context (answers, session_id, etc.)
            
        Returns:
            EVALUATION command for backend AI processing
        """
        context = context or {}
        
        return {
            'type': 'EVALUATION',
            'target': question_id,
            'context': context
        }
    
    def generate_update_command(self, target: str, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate UPDATE command for state changes.
        
        Args:
            target: Component ID to update
            updates: List of path-value update pairs
            
        Returns:
            UPDATE command matching protocol specification:
            {
                type: 'UPDATE',
                target: string,
                updates: [{path: string, value: any}]
            }
        """
        if not target:
            raise ValueError("Target cannot be empty")
        
        if target is None:
            raise ValueError("Target cannot be None")
        
        if not updates:
            raise ValueError("Updates cannot be empty")
        
        if not isinstance(updates, list):
            raise ValueError("Updates must be a list")
        
        # Validate and process updates
        validated_updates = []
        for update in updates:
            if not isinstance(update, dict):
                raise ValueError("Each update must be a dictionary")
            
            if 'path' not in update or 'value' not in update:
                raise ValueError("Each update must have 'path' and 'value' fields")
            
            path = update['path']
            if not self._validate_json_path(path):
                raise ValueError(f"Invalid JSON path: {path}")
            
            validated_updates.append({
                'path': path,
                'value': update['value']
            })
        
        return {
            'type': 'UPDATE',
            'target': target,
            'updates': validated_updates
        }
    
    def generate_batch_commands(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate batched commands for multiple changes efficiently.
        
        Args:
            changes: List of state changes to process
            
        Returns:
            List of optimized commands (batched by target)
        """
        if len(changes) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Batch size {len(changes)} exceeds maximum {self.MAX_BATCH_SIZE}")
        
        if not changes:
            return []
        
        # Check for circular dependencies
        self._detect_circular_dependencies(changes)
        
        # Group changes by target for efficient batching
        target_changes = {}
        
        for change in changes:
            change_type = change.get('type')
            question_id = change.get('question_id')
            
            if not question_id:
                continue
                
            if question_id not in target_changes:
                target_changes[question_id] = []
            
            # Convert different change types to update operations
            updates = self._convert_change_to_updates(change)
            target_changes[question_id].extend(updates)
        
        # Generate UPDATE commands for each target
        commands = []
        for target, updates in target_changes.items():
            if updates:  # Only create command if there are updates
                command = self.generate_update_command(target, updates)
                commands.append(command)
        
        return commands
    
    def generate_state_sync(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate complete state synchronization command.
        
        Args:
            session_id: Session ID to synchronize
            
        Returns:
            STATE_SYNC command or None if session not found:
            {
                type: 'STATE_SYNC',
                state: {session_id, questions, scores, explanations}
            }
        """
        if not self.session_manager:
            raise ValueError("Session manager not configured")
        
        session_data = self.session_manager.get_session(session_id)
        if not session_data:
            return None
        
        # Extract session data components
        data = session_data.get('data', {})
        answers = data.get('answers', {})
        scores = data.get('scores', {})
        explanations = data.get('explanations', {})
        question_states = data.get('question_states', {})
        
        return {
            'type': 'STATE_SYNC',
            'state': {
                'session_id': session_id,
                'questions': question_states,
                'scores': scores,
                'explanations': explanations
            }
        }
    
    def _generate_ui_schema(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Generate UI schema for a question based on its type and configuration."""
        question_type = question['question_type']
        
        # Base schema
        schema = {
            'type': self._map_question_type_to_ui_type(question_type, question.get('ui')),
            'label': question.get('text', ''),
            'hint': question.get('hint', ''),
            'info': question.get('info', '')
        }
        
        # Remove empty optional fields
        schema = {k: v for k, v in schema.items() if v}
        
        # Add options for choice types
        if question_type in ['choice-single', 'choice-multi', 'yes-no']:
            if question_type == 'yes-no':
                schema['options'] = [
                    {'code': 'yes', 'label': 'Yes'},
                    {'code': 'no', 'label': 'No'}
                ]
            else:
                schema['options'] = question.get('options', [])
        
        # Add validation rules
        validation = self._generate_validation_rules(question)
        if validation:
            schema['validation'] = validation
        
        return schema
    
    def _generate_component_props(self, question: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate component props based on question and context."""
        props = {
            'disabled': False,
            'thinking': False
        }
        
        # Set current value from context
        current_answer = context.get('current_answer')
        if current_answer is not None:
            props['value'] = current_answer
        else:
            # Set default value based on question type
            question_type = question['question_type']
            if question_type == 'choice-multi':
                props['value'] = []
            else:
                props['value'] = ''
        
        return props
    
    def _generate_validation_rules(self, question: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate validation rules for a question."""
        validation = {}
        
        # Basic required validation (assume most questions are required)
        if question.get('score') != 'NO':  # Questions with score="NO" are typically optional meta questions
            validation['required'] = True
        
        # Multi-choice specific validation
        if question['question_type'] == 'choice-multi':
            validation['min'] = 1
            max_selections = question.get('max_selections')
            if max_selections:
                validation['max'] = max_selections
            else:
                # Default reasonable maximum for multi-choice
                options_count = len(question.get('options', []))
                validation['max'] = max(3, options_count)
        
        return validation if validation else None
    
    def _map_question_type_to_ui_type(self, question_type: str, ui: Optional[str]) -> str:
        """Map question type to UI schema type."""
        if question_type == 'text':
            return 'text'
        elif question_type == 'textarea':
            return 'textarea'
        elif question_type == 'number':
            return 'number'
        elif question_type in ['choice-single', 'yes-no']:
            return 'choice-single'
        elif question_type == 'choice-multi':
            return 'choice-multi'
        else:
            return 'text'  # Default fallback
    
    def _evaluate_conditional(self, conditional: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate conditional visibility rules."""
        show_when = conditional.get('show_when', '')
        if not show_when:
            return True
        
        answers = context.get('answers', {})
        
        # Simple evaluation - in real implementation, this would be more sophisticated
        # For now, handle basic equality checks
        if '==' in show_when:
            parts = show_when.split('==')
            if len(parts) == 2:
                var_name = parts[0].strip()
                expected_value = parts[1].strip().strip('"\'')
                actual_value = answers.get(var_name, '')
                return actual_value == expected_value
        
        # Default to visible if we can't evaluate
        return True
    
    def _validate_json_path(self, path: str) -> bool:
        """Validate JSON path format."""
        if not path:
            return False
        
        if path.startswith('.') or path.endswith('.') or '..' in path or ' ' in path:
            return False
        
        return self.JSON_PATH_PATTERN.match(path) is not None
    
    def _convert_change_to_updates(self, change: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert different types of changes to update operations."""
        change_type = change.get('type')
        updates = []
        
        if change_type == 'answer_change':
            updates.append({
                'path': 'props.value',
                'value': change.get('value')
            })
        elif change_type == 'thinking_state':
            updates.append({
                'path': 'props.thinking',
                'value': change.get('thinking', False)
            })
        elif change_type == 'score_update':
            if 'score' in change:
                updates.append({
                    'path': 'data.score',
                    'value': change['score']
                })
            if 'explanation' in change:
                updates.append({
                    'path': 'data.explanation',
                    'value': change['explanation']
                })
        elif change_type == 'trigger_dependency':
            # This could be used for validation, but doesn't generate updates
            pass
        
        return updates
    
    def _detect_circular_dependencies(self, changes: List[Dict[str, Any]]) -> None:
        """Detect circular dependencies in batch changes."""
        # Simple circular dependency detection
        # In a real implementation, this would be more sophisticated
        dependencies = {}
        
        for change in changes:
            if change.get('type') == 'trigger_dependency':
                question_id = change.get('question_id')
                depends_on = change.get('depends_on')
                
                if question_id and depends_on:
                    if question_id not in dependencies:
                        dependencies[question_id] = set()
                    dependencies[question_id].add(depends_on)
        
        # Check for direct circular dependencies (A->B, B->A)
        for question_id, deps in dependencies.items():
            for dep in deps:
                if dep in dependencies and question_id in dependencies[dep]:
                    raise ValueError(f"Circular dependency detected: {question_id} <-> {dep}")