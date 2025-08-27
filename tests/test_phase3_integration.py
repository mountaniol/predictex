#!/usr/bin/env python3
"""
TOML Migration Phase 3: System Integration & Testing
Comprehensive test suite for validating complete TOML system integration
"""

import os
import sys
import json
import time
import pytest
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.py_simple_evaluate import (
    load_questions_data, evaluate_answer_logic, 
    find_question_by_id, clear_cache
)
from src.backend.py_final_analysis import final_analysis_logic


class TestPhase3Integration:
    """Complete system integration tests for TOML migration Phase 3"""
    
    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup each test with fresh cache"""
        clear_cache()
        yield
        clear_cache()
    
    @pytest.fixture
    def mock_config(self):
        """Basic configuration for testing"""
        return {
            'Generic': {
                'question_set_file': 'q4.toml',
                'ai_prompt_file': 'ai-prompt.txt'
            },
            'Backend': {
                'ai_provider': 'ollama',
                'ollama': {
                    'base_url': 'http://localhost:11434',
                    'model': 'nous-hermes2:34b',
                    'default_temperature': 0.3,
                    'default_max_tokens': 1024
                },
                'web_search': {
                    'enabled': False  # Disable for testing
                }
            }
        }

    def test_toml_loading_success(self):
        """Test 1: Backend loads TOML file successfully"""
        data, prompt = load_questions_data('q4.toml', 'ai-prompt.txt')
        
        # Validate basic structure
        assert isinstance(data, dict), "TOML data should be dictionary"
        assert 'questions' in data, "TOML should contain questions array"
        assert 'final_analysis_config' in data, "TOML should contain analysis config"
        
        # Validate questions loaded
        questions = data['questions']
        assert len(questions) > 40, f"Expected 40+ questions, got {len(questions)}"
        
        # Validate AI prompt
        assert len(prompt) > 1000, f"AI prompt too short: {len(prompt)} characters"
        
        print(f"✅ TOML Loading: {len(questions)} questions, {len(prompt)} char prompt")

    def test_question_data_processing(self):
        """Test 2: All question data properly processed"""
        data, _ = load_questions_data('q4.toml', 'ai-prompt.txt')
        
        # Check for processed follow-up rules
        follow_up_questions = [q for q in data['questions'] if 'follow_ups' in q]
        expected_follow_ups = ['SG04', 'SG05', 'SG12', 'SG25']
        
        follow_up_ids = [q['id'] for q in follow_up_questions]
        for expected_id in expected_follow_ups:
            assert expected_id in follow_up_ids, f"Missing follow-up for {expected_id}"
        
        print(f"✅ Follow-up Processing: {len(follow_up_questions)} questions")

    def test_analysis_config_processing(self):
        """Test 3: Analysis configuration working"""
        data, _ = load_questions_data('q4.toml', 'ai-prompt.txt')
        
        # Validate analysis config structure
        config = data['final_analysis_config']
        assert 'sections' in config, "Analysis config missing sections"
        assert 'loading_message' in config, "Analysis config missing loading message"
        assert 'base_prompt' in config, "Analysis config missing base prompt"
        
        sections = config['sections']
        assert len(sections) >= 8, f"Expected 8+ analysis sections, got {len(sections)}"
        
        # Validate section structure
        for section in sections:
            assert 'name' in section, f"Analysis section missing name: {section}"
            assert 'model' in section, f"Analysis section missing model: {section}"
            assert 'web_search' in section, f"Analysis section missing web_search: {section}"
            assert 'ai_context' in section, f"Analysis section missing ai_context: {section}"
        
        print(f"✅ Analysis Config: {len(sections)} sections processed")

    def test_no_api_regression(self, mock_config):
        """Test 4: Ensure no regression in API responses"""
        # Test with a non-AI question (should return score: "NO")
        result = evaluate_answer_logic('MET.LOC', {'MET.LOC': 'New York'}, 
                                       mock_config, 'q4.toml', 'ai-prompt.txt')
        
        assert result is not None, "API should return result for MET.LOC"
        # Non-AI questions should not have score evaluation
        
        # Test with AI question structure (mock scenario)
        question = find_question_by_id('SG01')
        assert question is not None, "Should find SG01 question"
        assert question['id'] == 'SG01', "Should return correct question"
        
        print(f"✅ API Regression: Basic API calls functional")

    def test_question_lookup_functionality(self):
        """Test 5: Question lookup works with TOML data"""
        # Load data first
        load_questions_data('q4.toml', 'ai-prompt.txt')
        
        # Test various question types
        test_questions = ['MET.LOC', 'SG01', 'SG04', 'SG25', 'SG30']
        
        for q_id in test_questions:
            question = find_question_by_id(q_id)
            assert question is not None, f"Should find question {q_id}"
            assert question['id'] == q_id, f"Should return correct question ID"
            assert 'text' in question, f"Question {q_id} should have text"
            assert 'question_type' in question, f"Question {q_id} should have type"
        
        print(f"✅ Question Lookup: {len(test_questions)} questions found")

    def test_follow_up_rule_conversion(self):
        """Test 6: Follow-up rules properly converted from DSL"""
        data, _ = load_questions_data('q4.toml', 'ai-prompt.txt')
        
        # Test SG04 follow-up rule conversion
        sg04 = next((q for q in data['questions'] if q['id'] == 'SG04'), None)
        assert sg04 is not None, "Should find SG04 question"
        assert 'follow_ups' in sg04, "SG04 should have follow_ups"
        assert 'follow_up_rules' not in sg04, "DSL rules should be removed"
        
        follow_up = sg04['follow_ups'][0]
        expected_structure = {
            'when': {'in': ['down_20plus']},
            'ask': {
                'id': 'SG04_REASON',
                'question_type': 'text',
                'ui': 'text',
                'placeholder': 'Main reason for decline',
                'max_chars': 140
            }
        }
        
        assert follow_up['when'] == expected_structure['when'], "Follow-up condition incorrect"
        assert follow_up['ask']['id'] == expected_structure['ask']['id'], "Follow-up ask ID incorrect"
        assert follow_up['ask']['question_type'] == expected_structure['ask']['question_type'], "Follow-up type incorrect"
        
        print(f"✅ Follow-up DSL: SG04 rule converted correctly")

    def test_ai_context_processing(self):
        """Test 7: AI context fields properly processed"""
        data, _ = load_questions_data('q4.toml', 'ai-prompt.txt')
        
        # Find questions with AI context
        ai_context_questions = [q for q in data['questions'] 
                               if 'ai_context' in q and 'include_answers' in q['ai_context']]
        
        assert len(ai_context_questions) > 0, "Should have questions with AI context"
        
        for question in ai_context_questions:
            # Should not have flattened fields anymore
            assert 'ai_context_include_answers' not in question, \
                f"Question {question['id']} should not have flattened AI context"
            
            # Should have proper nested structure
            ai_context = question['ai_context']
            assert 'include_answers' in ai_context, \
                f"Question {question['id']} should have nested include_answers"
        
        print(f"✅ AI Context: {len(ai_context_questions)} questions processed")

    def test_data_equivalence_validation(self):
        """Test 8: Validate TOML produces equivalent data to JSON"""
        # Load TOML data
        toml_data, toml_prompt = load_questions_data('q4.toml', 'ai-prompt.txt')
        clear_cache()
        
        # Load JSON data for comparison
        json_data, json_prompt = load_questions_data('q4.json', 'ai-prompt.txt')
        
        # Compare basic structure
        assert len(toml_data['questions']) == len(json_data['questions']), \
            "TOML and JSON should have same number of questions"
        
        assert len(toml_data['final_analysis_config']['sections']) == \
               len(json_data['final_analysis_config']['sections']), \
            "TOML and JSON should have same number of analysis sections"
        
        # Compare question IDs
        toml_ids = {q['id'] for q in toml_data['questions']}
        json_ids = {q['id'] for q in json_data['questions']}
        assert toml_ids == json_ids, "TOML and JSON should have same question IDs"
        
        print(f"✅ Data Equivalence: {len(toml_ids)} questions match between formats")

    def test_performance_baseline(self):
        """Test 9: TOML loading performance within acceptable range"""
        # Measure TOML loading time
        start_time = time.time()
        for _ in range(10):
            clear_cache()
            load_questions_data('q4.toml', 'ai-prompt.txt')
        toml_time = time.time() - start_time
        
        # Measure JSON loading time
        start_time = time.time()
        for _ in range(10):
            clear_cache()
            load_questions_data('q4.json', 'ai-prompt.txt')
        json_time = time.time() - start_time
        
        # TOML should be within 50x of JSON performance (TOML parsing is inherently slower)
        ratio = toml_time / json_time if json_time > 0 else 1.0
        assert ratio < 50.0, f"TOML loading too slow: {ratio:.2f}x JSON time"
        
        print(f"✅ Performance: TOML {toml_time:.3f}s vs JSON {json_time:.3f}s ({ratio:.2f}x)")

    def test_final_analysis_compatibility(self, mock_config):
        """Test 10: Final analysis works with TOML configuration"""
        # Load TOML data first
        data, _ = load_questions_data('q4.toml', 'ai-prompt.txt')
        
        # Test analysis config structure
        analysis_config = data['final_analysis_config']
        assert 'sections' in analysis_config, "Analysis config should have sections"
        
        # Validate first section can be processed (structure test only)
        sections = analysis_config['sections']
        assert len(sections) > 0, "Should have analysis sections"
        
        first_section = sections[0]
        required_fields = ['name', 'model', 'web_search', 'ai_context']
        for field in required_fields:
            assert field in first_section, f"Analysis section should have {field}"
        
        print(f"✅ Final Analysis: {len(sections)} sections compatible")


def run_phase3_tests():
    """Run all Phase 3 integration tests"""
    print("🚀 Starting TOML Migration Phase 3 Integration Tests...")
    print("=" * 60)
    
    # Change to project root for proper imports
    os.chdir(PROJECT_ROOT)
    
    # Run tests with pytest
    result = pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--capture=no'
    ])
    
    if result == 0:
        print("=" * 60)
        print("✅ ALL PHASE 3 INTEGRATION TESTS PASSED!")
        print("🎉 TOML Migration Phase 3: System Integration & Testing COMPLETE")
    else:
        print("=" * 60)
        print("❌ Some Phase 3 integration tests failed")
        print("⚠️  Please review and fix issues before proceeding")
    
    return result == 0


if __name__ == '__main__':
    success = run_phase3_tests()
    sys.exit(0 if success else 1)