"""
UISchemaGenerator - Converts questions from TOML/JSON to standardized UI schemas.

This module provides comprehensive transformation of question configurations to UI schemas,
supporting all question types, conditional visibility, validation rules, and performance optimization.

Key Features:
- Support for all question types (text, choice-single, choice-multi, yes-no, etc.)
- Conditional visibility evaluation using DSL
- Validation rule extraction and enforcement  
- TOML/JSON format compatibility
- Schema caching for performance
- Follow-up question DSL parsing
- Comprehensive error handling

Author: System Architect
Date: 2025-01-27
Status: TDD Implementation - Green Phase
"""

import json
import re
import hashlib
from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass, field, asdict
from functools import lru_cache


@dataclass
class CustomTextInput:
    """Custom text input configuration."""
    id: str
    placeholder: str = ""


@dataclass
class Option:
    """Option configuration for choice questions."""
    code: str
    label: str


@dataclass
class ValidationRules:
    """Validation rules for questions."""
    required: Optional[bool] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    
    def __post_init__(self):
        """Convert string numbers to appropriate types."""
        if isinstance(self.min, str):
            try:
                self.min = float(self.min) if '.' in self.min else int(self.min)
            except ValueError:
                pass
        if isinstance(self.max, str):
            try:
                self.max = float(self.max) if '.' in self.max else int(self.max)
            except ValueError:
                pass


@dataclass
class ConditionalRule:
    """Conditional visibility rule."""
    show_when: str


@dataclass 
class UISchema:
    """Complete UI schema for a question."""
    question_id: str
    type: str
    label: str
    hint: Optional[str] = None
    info: Optional[str] = None
    cluster_name: Optional[str] = None
    position_in_cluster: Optional[int] = None
    ui_variant: Optional[str] = None
    options: List[Option] = field(default_factory=list)
    validation: Optional[ValidationRules] = None
    conditional: Optional[ConditionalRule] = None
    custom_text_input: Optional[CustomTextInput] = None
    max_selections: Optional[int] = None
    with_other: Optional[bool] = None
    other_text_id: Optional[str] = None
    follow_up_rules: Optional[str] = None
    schema_version: Optional[str] = None
    required: bool = False

    def to_json(self) -> str:
        """Serialize schema to JSON string."""
        return json.dumps(asdict(self), default=str, ensure_ascii=False)
    
    def __eq__(self, other):
        """Equality comparison for schemas."""
        if not isinstance(other, UISchema):
            return False
        return asdict(self) == asdict(other)


class UISchemaGenerator:
    """Converts questions from TOML/JSON to UI schemas with caching and validation."""
    
    # Supported question types mapping
    SUPPORTED_TYPES = {
        'text', 'textarea', 'number', 'yes-no', 
        'choice-single', 'choice-multi'
    }
    
    def __init__(self):
        """Initialize generator with cache."""
        self._schema_cache = {}
        self._dependency_graph = {}
    
    def question_to_schema(self, question: Dict[str, Any], return_dict: bool = False) -> Union[Dict[str, Any], UISchema]:
        """Convert single question to UI schema with caching."""
        # Generate cache key
        cache_key = self._generate_cache_key(question)
        
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]
        
        # Validate required fields
        self._validate_required_fields(question)
        
        # Extract basic fields
        question_id = question["id"]
        question_type = question["question_type"]
        label = question["text"]
        
        # Validate question type
        if question_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported question type: {question_type}")
        
        # Create base schema
        schema = UISchema(
            question_id=question_id,
            type=question_type,
            label=label,
            hint=question.get("hint"),
            info=question.get("info", ""),
            cluster_name=question.get("cluster_name"),
            position_in_cluster=question.get("position_in_cluster"),
            ui_variant=question.get("ui"),
            schema_version=question.get("schema_version")
        )
        
        # Set required flag based on score field
        schema.required = question.get("score") != "NO"
        
        # Process question type specific fields
        self._process_question_type_fields(question, schema)
        
        # Process validation rules
        self._process_validation_rules(question, schema)
        
        # Process conditional rules
        self._process_conditional_rules(question, schema)
        
        # Process follow-up rules
        self._process_follow_up_rules(question, schema)
        
        # Process custom text input
        self._process_custom_text_input(question, schema)
        
        # Return appropriate format
        if return_dict:
            # Convert to dictionary for integration compatibility
            schema_dict = asdict(schema)
            # Cache the dictionary (separate cache for dict format)
            dict_cache_key = f"{cache_key}_dict"
            self._schema_cache[dict_cache_key] = schema_dict
            return schema_dict
        else:
            # Return UISchema object (default for backward compatibility)
            # Cache the object
            self._schema_cache[cache_key] = schema
            return schema
    
    def question_to_ui_schema(self, question: Dict[str, Any]) -> UISchema:
        """
        Convert single question to UISchema object (for backward compatibility).
        
        This method maintains the original interface that unit tests expect.
        """
        return self.question_to_schema(question, return_dict=False)
    
    def questions_to_schemas(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert multiple questions to schemas efficiently."""
        if not questions:
            return []
        
        schemas = []
        for question in questions:
            try:
                schema = self.question_to_schema(question)
                schemas.append(schema)
            except Exception as e:
                # Log error but continue processing
                print(f"Error processing question {question.get('id', 'unknown')}: {e}")
                continue
        
        return schemas
    
    def should_show_question(self, schema: Union[UISchema, Dict[str, Any]], answers: Dict[str, Any]) -> bool:
        """Evaluate if question should be shown based on conditional rules."""
        # Handle both UISchema objects and dictionaries for backward compatibility
        if isinstance(schema, dict):
            conditional = schema.get('conditional')
            if not conditional:
                return True
            show_when = conditional.get('show_when') if isinstance(conditional, dict) else conditional
        else:
            if not schema.conditional:
                return True
            show_when = schema.conditional.show_when
        
        return self._evaluate_condition(show_when, answers)
    
    def validate_answer(self, schema: Union[UISchema, Dict[str, Any]], answer: Any) -> bool:
        """Validate answer against schema rules."""
        # Handle both UISchema objects and dictionaries for backward compatibility
        if isinstance(schema, dict):
            with_other = schema.get('with_other', False)
            other_text_id = schema.get('other_text_id')
        else:
            with_other = schema.with_other
            other_text_id = schema.other_text_id
        
        # Handle different answer types
        if isinstance(answer, dict):
            # For questions with "other" options - check if question has other text id
            if with_other and other_text_id:
                return self._validate_other_answer(schema, answer)
            else:
                # Regular dict validation (shouldn't happen normally)
                return True
        elif isinstance(answer, list):
            # For multi-choice questions
            return self._validate_multi_choice_answer(schema, answer)
        else:
            # For single value answers
            return self._validate_single_answer(schema, answer)
    
    def validate_schema(self, schema: Union[UISchema, Dict[str, Any]]) -> bool:
        """Validate that schema is complete and valid."""
        try:
            # Handle both UISchema objects and dictionaries for backward compatibility
            if isinstance(schema, dict):
                question_id = schema.get('question_id')
                schema_type = schema.get('type')
                label = schema.get('label')
                options = schema.get('options', [])
            else:
                question_id = schema.question_id
                schema_type = schema.type
                label = schema.label
                options = schema.options
            
            # Check required fields
            if not question_id or not schema_type or not label:
                return False
            
            # Check type validity
            if schema_type not in self.SUPPORTED_TYPES:
                return False
            
            # Check options for choice questions
            if schema_type in ['choice-single', 'choice-multi']:
                if not options:
                    return False
                for option in options:
                    if isinstance(option, dict):
                        if not option.get('code') or not option.get('label'):
                            return False
                    else:
                        if not option.code or not option.label:
                            return False
            
            # Check yes-no options
            if schema_type == 'yes-no':
                if len(options) != 2:
                    return False
                if isinstance(options[0], dict):
                    codes = [opt.get('code') for opt in options]
                else:
                    codes = [opt.code for opt in options]
                if 'yes' not in codes or 'no' not in codes:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_follow_up_questions(self, schema: UISchema, answers: Dict[str, Any]) -> List[str]:
        """Get follow-up question IDs based on current answers."""
        if not schema.follow_up_rules:
            return []
        
        return self._parse_follow_up_dsl(schema.follow_up_rules, answers)
    
    def validate_question_dependencies(self, questions: List[Dict[str, Any]]) -> None:
        """Validate question dependencies for circular references."""
        # Build dependency graph
        deps = {}
        for question in questions:
            qid = question.get("id")
            if not qid:
                continue
                
            question_deps = set()
            
            # Extract conditional dependencies
            conditional = question.get("conditional", {})
            if conditional.get("show_when"):
                question_deps.update(self._extract_variables_from_condition(conditional["show_when"]))
            
            # Extract follow-up dependencies
            if question.get("follow_up_rules"):
                question_deps.update(self._extract_variables_from_condition(question["follow_up_rules"]))
            
            deps[qid] = question_deps
        
        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in deps.get(node, []):
                if neighbor in deps and has_cycle(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in deps:
            if has_cycle(node):
                raise ValueError(f"Circular dependency detected involving question: {node}")
    
    def _generate_cache_key(self, question: Dict[str, Any]) -> str:
        """Generate cache key for question."""
        # Create deterministic hash of question data
        question_str = json.dumps(question, sort_keys=True, default=str)
        return hashlib.md5(question_str.encode()).hexdigest()
    
    def _validate_required_fields(self, question: Dict[str, Any]) -> None:
        """Validate that question has required fields."""
        required_fields = ["id", "question_type", "text"]
        
        for field in required_fields:
            if field not in question:
                raise ValueError(f"Missing required field: {field}")
    
    def _process_question_type_fields(self, question: Dict[str, Any], schema: UISchema) -> None:
        """Process question type specific fields."""
        if schema.type in ['choice-single', 'choice-multi']:
            self._process_choice_fields(question, schema)
        elif schema.type == 'yes-no':
            self._process_yes_no_fields(schema)
    
    def _process_choice_fields(self, question: Dict[str, Any], schema: UISchema) -> None:
        """Process fields for choice questions."""
        options_data = question.get("options", [])
        schema.options = []
        
        for option_data in options_data:
            if not isinstance(option_data, dict):
                raise ValueError(f"Invalid option structure: {option_data}")
            
            if "code" not in option_data or "label" not in option_data:
                raise ValueError(f"Invalid option structure: missing 'code' or 'label' in {option_data}")
            
            option = Option(
                code=option_data["code"],
                label=option_data["label"]
            )
            schema.options.append(option)
        
        # Process multi-choice specific fields
        if schema.type == 'choice-multi':
            schema.max_selections = question.get("max_selections")
            schema.with_other = question.get("with_other", False)
            schema.other_text_id = question.get("other_text_id")
    
    def _process_yes_no_fields(self, schema: UISchema) -> None:
        """Process fields for yes-no questions."""
        schema.options = [
            Option(code="yes", label="Yes"),
            Option(code="no", label="No")
        ]
    
    def _process_validation_rules(self, question: Dict[str, Any], schema: UISchema) -> None:
        """Process validation rules."""
        validation_data = question.get("validation")
        if not validation_data:
            return
        
        schema.validation = ValidationRules(
            required=validation_data.get("required"),
            min=validation_data.get("min"),
            max=validation_data.get("max"),
            min_length=validation_data.get("min_length"),
            max_length=validation_data.get("max_length"),
            pattern=validation_data.get("pattern")
        )
    
    def _process_conditional_rules(self, question: Dict[str, Any], schema: UISchema) -> None:
        """Process conditional visibility rules."""
        conditional_data = question.get("conditional")
        if conditional_data and conditional_data.get("show_when"):
            schema.conditional = ConditionalRule(
                show_when=conditional_data["show_when"]
            )
    
    def _process_follow_up_rules(self, question: Dict[str, Any], schema: UISchema) -> None:
        """Process follow-up rules."""
        follow_up_rules = question.get("follow_up_rules")
        if follow_up_rules:
            schema.follow_up_rules = follow_up_rules
    
    def _process_custom_text_input(self, question: Dict[str, Any], schema: UISchema) -> None:
        """Process custom text input configuration."""
        custom_id = question.get("custom_text_input_id")
        if custom_id:
            schema.custom_text_input = CustomTextInput(
                id=custom_id,
                placeholder=question.get("custom_text_input_placeholder", "")
            )
    
    def _evaluate_condition(self, condition: str, answers: Dict[str, Any]) -> bool:
        """Evaluate conditional expression."""
        try:
            # Simple condition evaluation - handles basic == comparisons
            if "==" in condition:
                parts = condition.split("==")
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    expected_value = parts[1].strip().strip("'\"")
                    
                    actual_value = answers.get(var_name)
                    return str(actual_value) == expected_value
            
            return False
        except Exception:
            return False
    
    def _validate_other_answer(self, schema: Union[UISchema, Dict[str, Any]], answer: Dict[str, Any]) -> bool:
        """Validate answer with 'other' option."""
        if isinstance(schema, dict):
            question_id = schema.get('question_id')
            other_text_id = schema.get('other_text_id')
        else:
            question_id = schema.question_id
            other_text_id = schema.other_text_id
            
        main_answer = answer.get(question_id, [])
        other_text = answer.get(other_text_id, "")
        
        if isinstance(main_answer, list) and "other" in main_answer:
            # If "other" is selected, must have text
            if not other_text or not str(other_text).strip():
                return False
        
        return True
    
    def _validate_multi_choice_answer(self, schema: Union[UISchema, Dict[str, Any]], answer: List[str]) -> bool:
        """Validate multi-choice answer."""
        if isinstance(schema, dict):
            required = schema.get('required', False)
            max_selections = schema.get('max_selections')
            options = schema.get('options', [])
        else:
            required = schema.required
            max_selections = schema.max_selections
            options = schema.options
            
        if not answer:  # Empty selection
            return not required
        
        # Check max selections
        if max_selections and len(answer) > max_selections:
            return False
        
        # Check if all selected options exist
        if isinstance(options[0] if options else {}, dict):
            valid_codes = [opt.get('code') for opt in options]
        else:
            valid_codes = [opt.code for opt in options]
            
        for selected in answer:
            if selected not in valid_codes:
                return False
        
        return True
    
    def _validate_single_answer(self, schema: Union[UISchema, Dict[str, Any]], answer: str) -> bool:
        """Validate single value answer."""
        if isinstance(schema, dict):
            required = schema.get('required', False)
            validation = schema.get('validation')
            schema_type = schema.get('type')
        else:
            required = schema.required
            validation = schema.validation
            schema_type = schema.type
            
        if not answer and required:
            return False
        
        if not validation:
            return True
        
        # Handle both dict and ValidationRules object
        if isinstance(validation, dict):
            pattern = validation.get('pattern')
            min_val = validation.get('min')
            max_val = validation.get('max')
            min_length = validation.get('min_length')
            max_length = validation.get('max_length')
        else:
            pattern = validation.pattern
            min_val = validation.min
            max_val = validation.max
            min_length = validation.min_length
            max_length = validation.max_length
        
        # Check pattern
        if pattern and answer:
            if not re.match(pattern, str(answer)):
                return False
        
        # Check numeric constraints
        if schema_type == 'number' and answer:
            try:
                num_value = float(answer)
                if min_val is not None and num_value < min_val:
                    return False
                if max_val is not None and num_value > max_val:
                    return False
            except ValueError:
                return False
        
        # Check string length constraints
        if isinstance(answer, str):
            if min_length is not None and len(answer) < min_length:
                return False
            if max_length is not None and len(answer) > max_length:
                return False
        
        return True
    
    def _parse_follow_up_dsl(self, dsl: str, answers: Dict[str, Any]) -> List[str]:
        """Parse follow-up DSL and return applicable question IDs."""
        follow_up_questions = []
        
        try:
            # Handle simple IF-THEN-SHOW pattern
            if_match = re.search(r'IF\s+(.+?)\s+THEN\s+SHOW\s+(.+)', dsl, re.IGNORECASE)
            if if_match:
                condition = if_match.group(1)
                targets = if_match.group(2)
                
                if self._evaluate_complex_condition(condition, answers):
                    # Extract question IDs from targets
                    if '[' in targets and ']' in targets:
                        # Array format: [Q1, Q2, Q3]
                        targets = targets.strip('[]')
                        question_ids = [q.strip() for q in targets.split(',')]
                    else:
                        # Single question
                        question_ids = [targets.strip()]
                    
                    follow_up_questions.extend(question_ids)
            
            return follow_up_questions
            
        except Exception:
            return []
    
    def _evaluate_complex_condition(self, condition: str, answers: Dict[str, Any]) -> bool:
        """Evaluate complex conditional expressions."""
        try:
            # Handle parentheses first
            while '(' in condition and ')' in condition:
                # Find the innermost parentheses
                paren_match = re.search(r'\(([^()]+)\)', condition)
                if paren_match:
                    inner_condition = paren_match.group(1)
                    inner_result = self._evaluate_complex_condition(inner_condition, answers)
                    
                    # Replace parenthetical with result
                    condition = condition.replace(paren_match.group(0), str(inner_result).lower())
                else:
                    break
            
            # Handle OR conditions
            if ' OR ' in condition:
                parts = condition.split(' OR ')
                return any(self._evaluate_simple_condition(part.strip(), answers) for part in parts)
            
            # Handle AND conditions
            if ' AND ' in condition:
                parts = condition.split(' AND ')
                return all(self._evaluate_simple_condition(part.strip(), answers) for part in parts)
            
            # Simple condition
            return self._evaluate_simple_condition(condition, answers)
            
        except Exception:
            return False
    
    def _evaluate_simple_condition(self, condition: str, answers: Dict[str, Any]) -> bool:
        """Evaluate simple conditional expressions."""
        try:
            condition = condition.strip()
            
            # Handle equality comparisons
            if '==' in condition:
                parts = condition.split('==')
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    expected_value = parts[1].strip().strip("'\"")
                    
                    actual_value = answers.get(var_name)
                    return str(actual_value) == expected_value
            
            # Handle numeric comparisons
            if '>' in condition:
                parts = condition.split('>')
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    threshold = float(parts[1].strip())
                    
                    actual_value = answers.get(var_name, 0)
                    return float(actual_value) > threshold
            
            # Handle boolean values
            if condition in ['True', 'true']:
                return True
            if condition in ['False', 'false']:
                return False
            
            return False
            
        except Exception:
            return False
    
    def _extract_variables_from_condition(self, condition: str) -> Set[str]:
        """Extract variable names from conditional expressions."""
        variables = set()
        
        # Simple regex to find variable names (letters, numbers, dots, underscores)
        var_pattern = r'\b([A-Za-z][A-Za-z0-9._]*)\b'
        matches = re.findall(var_pattern, condition)
        
        for match in matches:
            # Filter out keywords and operators
            if match not in ['IF', 'THEN', 'SHOW', 'AND', 'OR', 'true', 'false', 'True', 'False']:
                variables.add(match)
        
        return variables