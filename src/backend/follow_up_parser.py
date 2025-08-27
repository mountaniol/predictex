"""
Follow-up DSL Parser for TOML Migration

This module provides parsing capabilities for the Domain Specific Language (DSL)
used to express follow-up question rules in a simplified, readable format.

The DSL transforms complex nested JSON structures like:
{
  "when": {"in": ["down_20plus"]},
  "ask": {
    "id": "SG04_REASON",
    "question_type": "text",
    "ui": "textarea",
    "placeholder": "Main reason for decline",
    "max_chars": 140
  }
}

Into simple string rules like:
"when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140"
"""

import re
from typing import Dict, List, Any, Optional


class FollowUpParserError(Exception):
    """Custom exception for DSL parsing errors"""
    pass


class FollowUpParser:
    """Parser for follow-up DSL rules"""
    
    # Regex pattern for parsing DSL rules
    DSL_PATTERN = re.compile(
        r'when:(?P<condition>[^-]+)\s*->\s*ask:(?P<question_spec>.+)',
        re.IGNORECASE
    )
    
    # Regex pattern for parsing question specifications
    QUESTION_SPEC_PATTERN = re.compile(
        r'(?P<id>[^:]+):(?P<type>[^:]+)(?::(?P<placeholder>[^:]+))?(?::(?P<max_chars>[^:]+))?'
    )
    
    # Valid question types and their UI mappings
    QUESTION_TYPE_MAPPING = {
        'text': 'text',
        'textarea': 'textarea', 
        'number': 'number',
        'choice-single': 'radio',
        'choice-multi': 'multiselect',
        'yes-no': 'radio'
    }
    
    def __init__(self):
        """Initialize the parser"""
        pass
    
    def parse_rule(self, rule_string: str) -> Dict[str, Any]:
        """
        Parse a single DSL rule string into follow-up object structure
        
        Args:
            rule_string: DSL rule like "when:down_20plus -> ask:SG04_REASON:text:Main reason:140"
            
        Returns:
            Dictionary with 'when' and 'ask' keys matching original JSON format
            
        Raises:
            FollowUpParserError: If rule syntax is invalid
        """
        if not isinstance(rule_string, str) or not rule_string.strip():
            raise FollowUpParserError("Rule string cannot be empty")
        
        # Parse main DSL structure
        match = self.DSL_PATTERN.match(rule_string.strip())
        if not match:
            raise FollowUpParserError(f"Invalid DSL rule syntax: {rule_string}")
        
        condition = match.group('condition').strip()
        question_spec = match.group('question_spec').strip()
        
        # Parse condition (simple values or comma-separated list)
        conditions = [c.strip() for c in condition.split(',') if c.strip()]
        if not conditions:
            raise FollowUpParserError(f"No conditions found in rule: {rule_string}")
        
        # Parse question specification
        spec_match = self.QUESTION_SPEC_PATTERN.match(question_spec)
        if not spec_match:
            raise FollowUpParserError(f"Invalid question specification: {question_spec}")
        
        question_id = spec_match.group('id').strip()
        question_type = spec_match.group('type').strip().lower()
        placeholder = spec_match.group('placeholder')
        max_chars = spec_match.group('max_chars')
        
        # Validate question type
        if question_type not in self.QUESTION_TYPE_MAPPING:
            valid_types = ', '.join(self.QUESTION_TYPE_MAPPING.keys())
            raise FollowUpParserError(
                f"Invalid question type '{question_type}'. Valid types: {valid_types}"
            )
        
        # Build ask configuration
        ask_config = {
            'id': question_id,
            'question_type': 'text' if question_type in ['text', 'textarea'] else question_type,
            'ui': self.QUESTION_TYPE_MAPPING[question_type]
        }
        
        # Add optional fields
        if placeholder:
            ask_config['placeholder'] = placeholder.strip()
        
        if max_chars:
            try:
                max_chars_int = int(max_chars)
                if max_chars_int <= 0:
                    raise FollowUpParserError(f"Max chars must be positive integer: {max_chars}")
                ask_config['max_chars'] = max_chars_int
            except ValueError:
                raise FollowUpParserError(f"Max chars must be integer: {max_chars}")
        
        return {
            'when': {'in': conditions},
            'ask': ask_config
        }
    
    def rules_to_json(self, rules: List[str]) -> List[Dict[str, Any]]:
        """
        Convert list of DSL rules to JSON follow-up format
        
        Args:
            rules: List of DSL rule strings
            
        Returns:
            List of follow-up objects in original JSON format
            
        Raises:
            FollowUpParserError: If any rule is invalid
        """
        if not isinstance(rules, list):
            raise FollowUpParserError("Rules must be a list")
        
        result = []
        for i, rule in enumerate(rules):
            try:
                parsed_rule = self.parse_rule(rule)
                result.append(parsed_rule)
            except FollowUpParserError as e:
                raise FollowUpParserError(f"Error in rule {i+1}: {e}")
        
        return result
    
    def json_to_rules(self, follow_ups: List[Dict[str, Any]]) -> List[str]:
        """
        Convert JSON follow-ups back to DSL format (for reverse conversion)
        
        Args:
            follow_ups: List of follow-up objects in JSON format
            
        Returns:
            List of DSL rule strings
            
        Raises:
            FollowUpParserError: If JSON structure is invalid
        """
        if not isinstance(follow_ups, list):
            raise FollowUpParserError("Follow-ups must be a list")
        
        rules = []
        for i, follow_up in enumerate(follow_ups):
            try:
                # Validate structure
                if not isinstance(follow_up, dict):
                    raise FollowUpParserError(f"Follow-up {i+1} must be an object")
                
                if 'when' not in follow_up or 'ask' not in follow_up:
                    raise FollowUpParserError(f"Follow-up {i+1} missing 'when' or 'ask'")
                
                when_clause = follow_up['when']
                ask_clause = follow_up['ask']
                
                # Parse when clause
                if not isinstance(when_clause, dict) or 'in' not in when_clause:
                    raise FollowUpParserError(f"Follow-up {i+1} 'when' must have 'in' array")
                
                conditions = when_clause['in']
                if not isinstance(conditions, list) or not conditions:
                    raise FollowUpParserError(f"Follow-up {i+1} 'when.in' must be non-empty array")
                
                condition_str = ','.join(str(c) for c in conditions)
                
                # Parse ask clause
                if not isinstance(ask_clause, dict):
                    raise FollowUpParserError(f"Follow-up {i+1} 'ask' must be an object")
                
                required_fields = ['id', 'question_type']
                for field in required_fields:
                    if field not in ask_clause:
                        raise FollowUpParserError(f"Follow-up {i+1} 'ask' missing '{field}'")
                
                question_id = ask_clause['id']
                question_type = ask_clause['question_type']
                
                # Map question type based on UI hint
                ui_type = ask_clause.get('ui', '')
                if question_type == 'text' and ui_type == 'textarea':
                    dsl_type = 'textarea'
                elif question_type == 'text':
                    dsl_type = 'text'
                else:
                    dsl_type = question_type
                
                # Build rule parts
                rule_parts = [f"when:{condition_str}", " -> ", f"ask:{question_id}:{dsl_type}"]
                
                # Add optional parts
                if 'placeholder' in ask_clause:
                    placeholder = str(ask_clause['placeholder'])
                    rule_parts.append(f":{placeholder}")
                    
                    if 'max_chars' in ask_clause:
                        max_chars = ask_clause['max_chars']
                        rule_parts.append(f":{max_chars}")
                
                rule_string = ''.join(rule_parts)
                rules.append(rule_string)
                
            except FollowUpParserError:
                raise
            except Exception as e:
                raise FollowUpParserError(f"Error converting follow-up {i+1}: {e}")
        
        return rules
    
    def validate_rule_syntax(self, rule_string: str) -> bool:
        """
        Validate DSL rule syntax without full parsing
        
        Args:
            rule_string: DSL rule to validate
            
        Returns:
            True if syntax is valid, False otherwise
        """
        try:
            self.parse_rule(rule_string)
            return True
        except FollowUpParserError:
            return False
    
    def get_supported_question_types(self) -> List[str]:
        """
        Get list of supported question types
        
        Returns:
            List of valid question type strings
        """
        return list(self.QUESTION_TYPE_MAPPING.keys())


# Utility functions for module-level usage
def parse_follow_up_rules(rules: List[str]) -> List[Dict[str, Any]]:
    """
    Utility function to parse follow-up rules
    
    Args:
        rules: List of DSL rule strings
        
    Returns:
        List of follow-up objects in JSON format
    """
    parser = FollowUpParser()
    return parser.rules_to_json(rules)


def convert_follow_ups_to_dsl(follow_ups: List[Dict[str, Any]]) -> List[str]:
    """
    Utility function to convert JSON follow-ups to DSL
    
    Args:
        follow_ups: List of follow-up objects in JSON format
        
    Returns:
        List of DSL rule strings
    """
    parser = FollowUpParser()
    return parser.json_to_rules(follow_ups)


# Example usage for testing
if __name__ == "__main__":
    # Test examples from q4.json
    parser = FollowUpParser()
    
    # Test SG04 revenue decline follow-up
    test_rules = [
        "when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140",
        "when:yes -> ask:SG05_NOTE:textarea:Brief reason:120"
    ]
    
    print("Testing DSL parsing:")
    for rule in test_rules:
        try:
            result = parser.parse_rule(rule)
            print(f"Rule: {rule}")
            print(f"Parsed: {result}")
            print()
        except FollowUpParserError as e:
            print(f"Error parsing '{rule}': {e}")
    
    # Test roundtrip conversion
    print("Testing roundtrip conversion:")
    json_result = parser.rules_to_json(test_rules)
    dsl_result = parser.json_to_rules(json_result)
    print(f"Original DSL: {test_rules}")
    print(f"Converted back: {dsl_result}")
    print(f"Roundtrip success: {test_rules == dsl_result}")