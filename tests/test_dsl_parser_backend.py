"""
Unit tests for the Follow-up DSL Parser (Python Backend)

This module tests the backend DSL parser that processes follow-up rules
in TOML format and converts them to JSON format for backward compatibility.
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.follow_up_parser import FollowUpParser, FollowUpParserError


class TestFollowUpParser:
    """Test cases for the FollowUpParser class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.parser = FollowUpParser()
    
    def test_parse_simple_rule(self):
        """Test parsing a simple DSL rule"""
        rule = "when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140"
        
        expected = {
            'when': {'in': ['down_20plus']},
            'ask': {
                'id': 'SG04_REASON',
                'question_type': 'text',
                'ui': 'text',
                'placeholder': 'Main reason for decline',
                'max_chars': 140
            }
        }
        
        result = self.parser.parse_rule(rule)
        assert result == expected
    
    def test_parse_textarea_rule(self):
        """Test parsing a DSL rule with textarea type"""
        rule = "when:yes -> ask:SG05_NOTE:textarea:Brief reason:120"
        
        expected = {
            'when': {'in': ['yes']},
            'ask': {
                'id': 'SG05_NOTE',
                'question_type': 'text',
                'ui': 'textarea',
                'placeholder': 'Brief reason',
                'max_chars': 120
            }
        }
        
        result = self.parser.parse_rule(rule)
        assert result == expected
    
    def test_parse_rule_without_placeholder(self):
        """Test parsing a DSL rule without placeholder"""
        rule = "when:cancelled -> ask:SG06_NOTES:textarea"
        
        expected = {
            'when': {'in': ['cancelled']},
            'ask': {
                'id': 'SG06_NOTES',
                'question_type': 'text',
                'ui': 'textarea'
            }
        }
        
        result = self.parser.parse_rule(rule)
        assert result == expected
    
    def test_parse_rule_with_multiple_conditions(self):
        """Test parsing a DSL rule with comma-separated conditions"""
        rule = "when:high,critical -> ask:RISK_NOTE:text:Risk details:200"
        
        expected = {
            'when': {'in': ['high', 'critical']},
            'ask': {
                'id': 'RISK_NOTE',
                'question_type': 'text',
                'ui': 'text',
                'placeholder': 'Risk details',
                'max_chars': 200
            }
        }
        
        result = self.parser.parse_rule(rule)
        assert result == expected
    
    def test_parse_rule_choice_types(self):
        """Test parsing DSL rules with choice question types"""
        rule = "when:maybe -> ask:CHOICE_Q:choice-single"
        
        expected = {
            'when': {'in': ['maybe']},
            'ask': {
                'id': 'CHOICE_Q',
                'question_type': 'choice-single',
                'ui': 'radio'
            }
        }
        
        result = self.parser.parse_rule(rule)
        assert result == expected
    
    def test_rules_to_json(self):
        """Test converting a list of DSL rules to JSON format"""
        rules = [
            "when:down_20plus -> ask:SG04_REASON:text:Main reason:140",
            "when:yes -> ask:SG05_NOTE:textarea:Brief reason:120"
        ]
        
        expected = [
            {
                'when': {'in': ['down_20plus']},
                'ask': {
                    'id': 'SG04_REASON',
                    'question_type': 'text',
                    'ui': 'text',
                    'placeholder': 'Main reason',
                    'max_chars': 140
                }
            },
            {
                'when': {'in': ['yes']},
                'ask': {
                    'id': 'SG05_NOTE',
                    'question_type': 'text',
                    'ui': 'textarea',
                    'placeholder': 'Brief reason',
                    'max_chars': 120
                }
            }
        ]
        
        result = self.parser.rules_to_json(rules)
        assert result == expected
    
    def test_json_to_rules_roundtrip(self):
        """Test roundtrip conversion: DSL -> JSON -> DSL"""
        original_rules = [
            "when:down_20plus -> ask:SG04_REASON:text:Main reason:140",
            "when:yes -> ask:SG05_NOTE:textarea:Brief reason:120"
        ]
        
        # Convert to JSON and back
        json_format = self.parser.rules_to_json(original_rules)
        converted_rules = self.parser.json_to_rules(json_format)
        
        # Should match original (allowing for formatting differences)
        assert len(converted_rules) == len(original_rules)
        
        # Convert back to JSON to compare semantics
        original_json = self.parser.rules_to_json(original_rules)
        converted_json = self.parser.rules_to_json(converted_rules)
        assert original_json == converted_json
    
    def test_invalid_rule_syntax(self):
        """Test error handling for invalid DSL syntax"""
        with pytest.raises(FollowUpParserError):
            self.parser.parse_rule("invalid rule")
        
        with pytest.raises(FollowUpParserError):
            self.parser.parse_rule("when:test")  # Missing arrow
        
        with pytest.raises(FollowUpParserError):
            self.parser.parse_rule("-> ask:TEST:text")  # Missing when
    
    def test_invalid_question_type(self):
        """Test error handling for invalid question types"""
        with pytest.raises(FollowUpParserError):
            self.parser.parse_rule("when:test -> ask:Q1:invalid_type")
    
    def test_invalid_max_chars(self):
        """Test error handling for invalid max_chars values"""
        with pytest.raises(FollowUpParserError):
            self.parser.parse_rule("when:test -> ask:Q1:text:placeholder:abc")
        
        with pytest.raises(FollowUpParserError):
            self.parser.parse_rule("when:test -> ask:Q1:text:placeholder:-5")
    
    def test_empty_rule(self):
        """Test error handling for empty rules"""
        with pytest.raises(FollowUpParserError):
            self.parser.parse_rule("")
        
        with pytest.raises(FollowUpParserError):
            self.parser.parse_rule("   ")
    
    def test_validate_rule_syntax(self):
        """Test rule syntax validation"""
        valid_rule = "when:test -> ask:Q1:text:placeholder:100"
        invalid_rule = "invalid rule syntax"
        
        assert self.parser.validate_rule_syntax(valid_rule) is True
        assert self.parser.validate_rule_syntax(invalid_rule) is False
    
    def test_get_supported_question_types(self):
        """Test getting supported question types"""
        types = self.parser.get_supported_question_types()
        
        expected_types = ['text', 'textarea', 'number', 'choice-single', 'choice-multi', 'yes-no']
        assert all(t in types for t in expected_types)
    
    def test_real_world_examples_from_q4_toml(self):
        """Test with actual examples from q4.toml file"""
        # These are actual rules from the q4.toml file
        real_world_rules = [
            "when:down_20plus -> ask:SG04_REASON:textarea:Main reason for decline:140",
            "when:yes -> ask:SG05_NOTE:textarea:Brief reason (seasonality/shock):120",
            "when:yes -> ask:SG12_REASON:textarea:Brief reason:120",
            "when:yes -> ask:SG25_REASON:textarea:Brief reason / fix:120"
        ]
        
        # Should parse all without errors
        for rule in real_world_rules:
            result = self.parser.parse_rule(rule)
            assert 'when' in result
            assert 'ask' in result
            assert 'in' in result['when']
            assert 'id' in result['ask']
            assert 'question_type' in result['ask']
        
        # Test batch processing
        json_results = self.parser.rules_to_json(real_world_rules)
        assert len(json_results) == len(real_world_rules)
        
        # Test roundtrip
        dsl_results = self.parser.json_to_rules(json_results)
        assert len(dsl_results) == len(real_world_rules)


# Utility function tests
def test_utility_functions():
    """Test module-level utility functions"""
    from backend.follow_up_parser import parse_follow_up_rules, convert_follow_ups_to_dsl
    
    rules = ["when:test -> ask:Q1:text:placeholder:100"]
    
    # Test utility function
    json_result = parse_follow_up_rules(rules)
    assert len(json_result) == 1
    assert json_result[0]['when']['in'] == ['test']
    
    # Test reverse utility function
    dsl_result = convert_follow_ups_to_dsl(json_result)
    assert len(dsl_result) == 1


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])