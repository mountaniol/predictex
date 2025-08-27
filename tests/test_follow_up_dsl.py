"""
Unit tests for Follow-up DSL Parser

Tests the DSL parser functionality for converting between JSON follow-up structures
and simplified DSL string rules.
"""

import unittest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.follow_up_parser import FollowUpParser, FollowUpParserError


class TestFollowUpDSLParser(unittest.TestCase):
    """Test cases for Follow-up DSL Parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = FollowUpParser()
    
    def test_simple_rule_parsing(self):
        """Test parsing of simple DSL rules"""
        rule = "when:yes -> ask:TEST:text:Explain:100"
        result = self.parser.parse_rule(rule)
        
        expected = {
            'when': {'in': ['yes']},
            'ask': {
                'id': 'TEST',
                'question_type': 'text',
                'ui': 'text',
                'placeholder': 'Explain',
                'max_chars': 100
            }
        }
        
        self.assertEqual(result, expected)
    
    def test_textarea_rule_parsing(self):
        """Test parsing of textarea DSL rules"""
        rule = "when:down_20plus -> ask:SG04_REASON:textarea:Main reason for decline:140"
        result = self.parser.parse_rule(rule)
        
        expected = {
            'when': {'in': ['down_20plus']},
            'ask': {
                'id': 'SG04_REASON',
                'question_type': 'text',
                'ui': 'textarea',
                'placeholder': 'Main reason for decline',
                'max_chars': 140
            }
        }
        
        self.assertEqual(result, expected)
    
    def test_multiple_conditions_parsing(self):
        """Test parsing rules with multiple conditions"""
        rule = "when:opt1,opt2,opt3 -> ask:TEST:textarea:Details"
        result = self.parser.parse_rule(rule)
        
        expected = {
            'when': {'in': ['opt1', 'opt2', 'opt3']},
            'ask': {
                'id': 'TEST',
                'question_type': 'text',
                'ui': 'textarea',
                'placeholder': 'Details'
            }
        }
        
        self.assertEqual(result, expected)
    
    def test_minimal_rule_parsing(self):
        """Test parsing minimal DSL rules without optional fields"""
        rule = "when:yes -> ask:TEST:text"
        result = self.parser.parse_rule(rule)
        
        expected = {
            'when': {'in': ['yes']},
            'ask': {
                'id': 'TEST',
                'question_type': 'text',
                'ui': 'text'
            }
        }
        
        self.assertEqual(result, expected)
        self.assertNotIn('placeholder', result['ask'])
        self.assertNotIn('max_chars', result['ask'])
    
    def test_number_question_type(self):
        """Test parsing number question type"""
        rule = "when:selected -> ask:NUM_TEST:number:Enter amount:10"
        result = self.parser.parse_rule(rule)
        
        expected = {
            'when': {'in': ['selected']},
            'ask': {
                'id': 'NUM_TEST',
                'question_type': 'number',
                'ui': 'number',
                'placeholder': 'Enter amount',
                'max_chars': 10
            }
        }
        
        self.assertEqual(result, expected)
    
    def test_choice_question_types(self):
        """Test parsing choice question types"""
        # Single choice
        rule1 = "when:other -> ask:CHOICE1:choice-single:Pick one"
        result1 = self.parser.parse_rule(rule1)
        
        self.assertEqual(result1['ask']['question_type'], 'choice-single')
        self.assertEqual(result1['ask']['ui'], 'radio')
        
        # Multi choice  
        rule2 = "when:multiple -> ask:CHOICE2:choice-multi:Pick many"
        result2 = self.parser.parse_rule(rule2)
        
        self.assertEqual(result2['ask']['question_type'], 'choice-multi')
        self.assertEqual(result2['ask']['ui'], 'multiselect')
    
    def test_case_insensitive_parsing(self):
        """Test case insensitive DSL parsing"""
        rule = "WHEN:yes -> ASK:TEST:TEXT:Explain"
        result = self.parser.parse_rule(rule)
        
        # Should parse successfully despite uppercase
        self.assertEqual(result['when']['in'], ['yes'])
        self.assertEqual(result['ask']['id'], 'TEST')
    
    def test_whitespace_tolerance(self):
        """Test tolerance for extra whitespace in DSL rules"""
        rule = "  when:yes   ->   ask:TEST:text:Explain   "
        result = self.parser.parse_rule(rule)
        
        expected = {
            'when': {'in': ['yes']},
            'ask': {
                'id': 'TEST',
                'question_type': 'text',
                'ui': 'text',
                'placeholder': 'Explain'
            }
        }
        
        self.assertEqual(result, expected)
    
    def test_invalid_syntax_errors(self):
        """Test error handling for invalid DSL syntax"""
        invalid_rules = [
            "",  # Empty rule
            "invalid rule",  # No arrow
            "when:yes",  # Missing ask part
            "-> ask:TEST:text",  # Missing when part
            "when: -> ask:TEST:text",  # Empty condition
            "when:yes -> ask::text",  # Empty question ID
            "when:yes -> ask:TEST:",  # Empty question type
            "when:yes -> ask:TEST:invalid_type"  # Invalid question type
        ]
        
        for rule in invalid_rules:
            with self.assertRaises(FollowUpParserError):
                self.parser.parse_rule(rule)
    
    def test_invalid_max_chars(self):
        """Test error handling for invalid max_chars values"""
        invalid_rules = [
            "when:yes -> ask:TEST:text:Explain:0",  # Zero max chars
            "when:yes -> ask:TEST:text:Explain:-5",  # Negative max chars
            "when:yes -> ask:TEST:text:Explain:abc"  # Non-numeric max chars
        ]
        
        for rule in invalid_rules:
            with self.assertRaises(FollowUpParserError):
                self.parser.parse_rule(rule)
    
    def test_rules_to_json(self):
        """Test converting multiple DSL rules to JSON"""
        rules = [
            "when:down_20plus -> ask:SG04_REASON:textarea:Main reason:140",
            "when:yes -> ask:SG05_NOTE:text:Brief explanation:120"
        ]
        
        result = self.parser.rules_to_json(rules)
        
        self.assertEqual(len(result), 2)
        
        # Check first rule
        self.assertEqual(result[0]['when']['in'], ['down_20plus'])
        self.assertEqual(result[0]['ask']['id'], 'SG04_REASON')
        self.assertEqual(result[0]['ask']['ui'], 'textarea')
        
        # Check second rule
        self.assertEqual(result[1]['when']['in'], ['yes'])
        self.assertEqual(result[1]['ask']['id'], 'SG05_NOTE')
        self.assertEqual(result[1]['ask']['ui'], 'text')
    
    def test_json_to_rules(self):
        """Test converting JSON follow-ups back to DSL"""
        follow_ups = [
            {
                'when': {'in': ['down_20plus']},
                'ask': {
                    'id': 'SG04_REASON',
                    'question_type': 'text',
                    'ui': 'textarea',
                    'placeholder': 'Main reason for decline',
                    'max_chars': 140
                }
            },
            {
                'when': {'in': ['yes']},
                'ask': {
                    'id': 'SG05_NOTE',
                    'question_type': 'text',
                    'ui': 'text',
                    'placeholder': 'Brief reason'
                }
            }
        ]
        
        result = self.parser.json_to_rules(follow_ups)
        
        expected_rules = [
            "when:down_20plus -> ask:SG04_REASON:textarea:Main reason for decline:140",
            "when:yes -> ask:SG05_NOTE:text:Brief reason"
        ]
        
        self.assertEqual(result, expected_rules)
    
    def test_roundtrip_conversion(self):
        """Test bidirectional conversion between DSL and JSON"""
        original_rules = [
            "when:down_20plus -> ask:SG04_REASON:textarea:Main reason:140",
            "when:yes,no -> ask:MULTI_COND:text:Explain choice",
            "when:other -> ask:MINIMAL:number"
        ]
        
        # DSL -> JSON -> DSL
        json_result = self.parser.rules_to_json(original_rules)
        dsl_result = self.parser.json_to_rules(json_result)
        
        self.assertEqual(original_rules, dsl_result)
    
    def test_real_world_examples_from_q4(self):
        """Test with actual examples from q4.json"""
        # SG04 example
        sg04_rule = "when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140"
        sg04_result = self.parser.parse_rule(sg04_rule)
        
        self.assertEqual(sg04_result['when']['in'], ['down_20plus'])
        self.assertEqual(sg04_result['ask']['id'], 'SG04_REASON')
        self.assertEqual(sg04_result['ask']['max_chars'], 140)
        
        # SG05 example  
        sg05_rule = "when:yes -> ask:SG05_NOTE:textarea:Brief reason:120"
        sg05_result = self.parser.parse_rule(sg05_rule)
        
        self.assertEqual(sg05_result['when']['in'], ['yes'])
        self.assertEqual(sg05_result['ask']['ui'], 'textarea')
        self.assertEqual(sg05_result['ask']['max_chars'], 120)
    
    def test_validate_rule_syntax(self):
        """Test rule syntax validation method"""
        valid_rules = [
            "when:yes -> ask:TEST:text",
            "when:a,b,c -> ask:TEST:textarea:Explain:100"
        ]
        
        invalid_rules = [
            "invalid",
            "when:yes",
            "-> ask:TEST:text"
        ]
        
        for rule in valid_rules:
            self.assertTrue(self.parser.validate_rule_syntax(rule))
        
        for rule in invalid_rules:
            self.assertFalse(self.parser.validate_rule_syntax(rule))
    
    def test_get_supported_question_types(self):
        """Test getting supported question types"""
        types = self.parser.get_supported_question_types()
        
        expected_types = ['text', 'textarea', 'number', 'choice-single', 'choice-multi', 'yes-no']
        
        self.assertEqual(set(types), set(expected_types))
    
    def test_error_messages(self):
        """Test that error messages are descriptive"""
        with self.assertRaises(FollowUpParserError) as cm:
            self.parser.parse_rule("when:yes -> ask:TEST:invalid_type")
        
        self.assertIn("Invalid question type", str(cm.exception))
        self.assertIn("invalid_type", str(cm.exception))


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions in the module"""
    
    def test_parse_follow_up_rules_utility(self):
        """Test module-level parse_follow_up_rules function"""
        from backend.follow_up_parser import parse_follow_up_rules
        
        rules = ["when:yes -> ask:TEST:text:Explain"]
        result = parse_follow_up_rules(rules)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['ask']['id'], 'TEST')
    
    def test_convert_follow_ups_to_dsl_utility(self):
        """Test module-level convert_follow_ups_to_dsl function"""
        from backend.follow_up_parser import convert_follow_ups_to_dsl
        
        follow_ups = [{
            'when': {'in': ['yes']},
            'ask': {
                'id': 'TEST',
                'question_type': 'text',
                'ui': 'text',
                'placeholder': 'Explain'
            }
        }]
        
        result = convert_follow_ups_to_dsl(follow_ups)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "when:yes -> ask:TEST:text:Explain")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)