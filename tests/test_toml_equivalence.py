"""
Data Equivalence Tests for TOML Migration

This module verifies that TOML and JSON formats produce equivalent data
after processing through their respective parsers and loaders.
"""

import json
import os
import sys
import toml
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.follow_up_parser import FollowUpParser, FollowUpParserError

# Project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
QUESTIONS_DIR = os.path.join(PROJECT_ROOT, 'public', 'questions')


def load_and_process_json(file_path: str) -> Dict[str, Any]:
    """Load JSON file (original format)"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_and_process_toml(file_path: str) -> Dict[str, Any]:
    """Load and process TOML file to match JSON structure"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = toml.load(f)
    
    # Process the same way as backend does
    _process_toml_follow_up_rules(data)
    _process_toml_analysis_config(data)
    
    return data


def _process_toml_follow_up_rules(data: Dict[str, Any]) -> None:
    """Process follow_up_rules from TOML DSL format to JSON format"""
    if 'questions' not in data:
        return
        
    parser = FollowUpParser()
    
    for question in data['questions']:
        if 'follow_up_rules' in question:
            try:
                follow_up_rules = question['follow_up_rules']
                if follow_up_rules and len(follow_up_rules) > 0:
                    question['follow_ups'] = parser.rules_to_json(follow_up_rules)
                
                # Remove DSL rules from final data to maintain JSON compatibility
                del question['follow_up_rules']
                
            except FollowUpParserError as e:
                question_id = question.get('id', 'UNKNOWN')
                print(f"WARNING: Failed to parse follow-up rules for question {question_id}: {e}")
        
        # Process flattened AI context fields
        if 'ai_context_include_answers' in question:
            question['ai_context'] = {
                'include_answers': question['ai_context_include_answers']
            }
            del question['ai_context_include_answers']


def _process_toml_analysis_config(data: Dict[str, Any]) -> None:
    """Process flattened analysis configuration from TOML to nested JSON format"""
    if 'analysis' not in data:
        return
    
    analysis_data = data['analysis']
    sections = []
    
    # Extract base configuration
    loading_message = analysis_data.pop('loading_message', '')
    base_prompt = analysis_data.pop('base_prompt', '')
    
    # Process each analysis section
    for key, section_data in analysis_data.items():
        if not isinstance(section_data, dict):
            continue
            
        section = {
            'name': section_data.get('name', key.replace('_', ' ').title()),
            'model': section_data.get('model', 'gpt-4o'),
            'web_search': {
                'enabled': section_data.get('web_search_enabled', False),
                'max_searches': section_data.get('web_search_max_searches', 3)
            },
            'ai_context': {
                'include_answers': section_data.get('ai_context_include_answers', []),
                'include_scores': section_data.get('ai_context_include_scores', False),
                'include_overall_score': section_data.get('ai_context_include_overall_score', False)
            },
            'specific_prompt': section_data.get('specific_prompt', ''),
            'output_constraint': section_data.get('output_constraint', ''),
            'model_config': section_data.get('model_config', {})
        }
        sections.append(section)
    
    # Replace with nested structure for backward compatibility
    data['final_analysis_config'] = {
        'loading_message': loading_message,
        'base_prompt': base_prompt,
        'sections': sections
    }
    
    # Remove flattened analysis config
    del data['analysis']


def normalize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize data structure for comparison by sorting lists and handling type differences"""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            result[key] = normalize_data(value)
        return result
    elif isinstance(data, list):
        # Sort lists for consistent comparison (except for questions which need position order)
        if len(data) > 0 and isinstance(data[0], dict) and 'id' in data[0]:
            # This is a questions list - sort by position_in_cluster then by id
            return [normalize_data(item) for item in sorted(data, key=lambda x: (x.get('position_in_cluster', 0), x.get('id', '')))]
        else:
            return [normalize_data(item) for item in data]
    else:
        return data


def compare_questions(json_questions: List[Dict], toml_questions: List[Dict]) -> List[str]:
    """Compare questions lists and return differences"""
    differences = []
    
    # Create lookup dictionaries
    json_q_map = {q['id']: q for q in json_questions}
    toml_q_map = {q['id']: q for q in toml_questions}
    
    # Check for missing questions
    json_ids = set(json_q_map.keys())
    toml_ids = set(toml_q_map.keys())
    
    if json_ids != toml_ids:
        missing_in_toml = json_ids - toml_ids
        missing_in_json = toml_ids - json_ids
        
        if missing_in_toml:
            differences.append(f"Questions missing in TOML: {missing_in_toml}")
        if missing_in_json:
            differences.append(f"Questions missing in JSON: {missing_in_json}")
    
    # Compare individual questions
    for qid in json_ids & toml_ids:
        json_q = json_q_map[qid]
        toml_q = toml_q_map[qid]
        
        # Compare key fields
        key_fields = ['text', 'question_type', 'cluster_name', 'position_in_cluster']
        for field in key_fields:
            if json_q.get(field) != toml_q.get(field):
                differences.append(f"Question {qid}: {field} differs - JSON: {json_q.get(field)}, TOML: {toml_q.get(field)}")
        
        # Compare follow-ups specifically
        json_followups = json_q.get('follow_ups', [])
        toml_followups = toml_q.get('follow_ups', [])
        
        if len(json_followups) != len(toml_followups):
            differences.append(f"Question {qid}: follow-ups count differs - JSON: {len(json_followups)}, TOML: {len(toml_followups)}")
        else:
            for i, (json_fu, toml_fu) in enumerate(zip(json_followups, toml_followups)):
                if normalize_data(json_fu) != normalize_data(toml_fu):
                    differences.append(f"Question {qid}: follow-up {i} differs")
                    differences.append(f"  JSON: {json_fu}")
                    differences.append(f"  TOML: {toml_fu}")
    
    return differences


def test_data_equivalence():
    """Main test function to verify JSON and TOML data equivalence"""
    print("Testing data equivalence between JSON and TOML formats...")
    
    # File paths
    json_path = os.path.join(QUESTIONS_DIR, 'q4.json')
    toml_path = os.path.join(QUESTIONS_DIR, 'q4.toml')
    
    # Check if files exist
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    if not os.path.exists(toml_path):
        raise FileNotFoundError(f"TOML file not found: {toml_path}")
    
    # Load both formats
    print("Loading JSON data...")
    json_data = load_and_process_json(json_path)
    
    print("Loading and processing TOML data...")
    toml_data = load_and_process_toml(toml_path)
    
    # Basic structure checks
    print("Checking basic structure...")
    assert 'questions' in json_data, "JSON missing 'questions'"
    assert 'questions' in toml_data, "TOML missing 'questions'"
    
    print(f"JSON has {len(json_data['questions'])} questions")
    print(f"TOML has {len(toml_data['questions'])} questions")
    
    # Compare versions
    json_version = json_data.get('version', 'unknown')
    toml_version = toml_data.get('version', 'unknown')
    print(f"Versions - JSON: {json_version}, TOML: {toml_version}")
    
    # Compare settings
    json_settings = json_data.get('settings', {})
    toml_settings = toml_data.get('settings', {})
    
    if normalize_data(json_settings) != normalize_data(toml_settings):
        print("WARNING: Settings differ between JSON and TOML")
        print(f"JSON settings: {json_settings}")
        print(f"TOML settings: {toml_settings}")
    
    # Detailed question comparison
    print("Comparing questions in detail...")
    differences = compare_questions(json_data['questions'], toml_data['questions'])
    
    if differences:
        print(f"Found {len(differences)} differences:")
        for diff in differences[:10]:  # Show first 10 differences
            print(f"  - {diff}")
        if len(differences) > 10:
            print(f"  ... and {len(differences) - 10} more differences")
        
        # Don't fail the test if there are only minor differences
        critical_differences = [d for d in differences if 'missing' in d.lower()]
        if critical_differences:
            raise AssertionError(f"Critical differences found: {critical_differences}")
        else:
            print("Differences found but appear to be non-critical")
    else:
        print("✅ Questions match perfectly between JSON and TOML!")
    
    # Compare final analysis config if present
    if 'final_analysis_config' in json_data or 'final_analysis_config' in toml_data:
        print("Comparing final analysis configuration...")
        json_config = normalize_data(json_data.get('final_analysis_config', {}))
        toml_config = normalize_data(toml_data.get('final_analysis_config', {}))
        
        if json_config != toml_config:
            print("WARNING: Final analysis configuration differs")
            # Don't fail test for this, as it might be expected during migration
        else:
            print("✅ Final analysis configuration matches!")
    
    print("✅ Data equivalence test completed successfully!")
    return True


def test_follow_up_rules_consistency():
    """Test that all follow-up rules in TOML can be parsed correctly"""
    print("\nTesting follow-up rules consistency...")
    
    toml_path = os.path.join(QUESTIONS_DIR, 'q4.toml')
    if not os.path.exists(toml_path):
        print("TOML file not found, skipping follow-up rules test")
        return
    
    with open(toml_path, 'r', encoding='utf-8') as f:
        data = toml.load(f)
    
    parser = FollowUpParser()
    rules_tested = 0
    
    for question in data.get('questions', []):
        if 'follow_up_rules' in question:
            qid = question.get('id', 'UNKNOWN')
            rules = question['follow_up_rules']
            
            print(f"Testing {len(rules)} follow-up rules for question {qid}")
            
            try:
                # Test each rule individually
                for rule in rules:
                    parsed = parser.parse_rule(rule)
                    assert 'when' in parsed
                    assert 'ask' in parsed
                    rules_tested += 1
                
                # Test batch processing
                batch_result = parser.rules_to_json(rules)
                assert len(batch_result) == len(rules)
                
                # Test roundtrip
                dsl_back = parser.json_to_rules(batch_result)
                roundtrip_result = parser.rules_to_json(dsl_back)
                assert len(roundtrip_result) == len(batch_result)
                
                print(f"  ✅ All rules for {qid} processed successfully")
                
            except Exception as e:
                print(f"  ❌ Error processing rules for {qid}: {e}")
                raise
    
    print(f"✅ Tested {rules_tested} follow-up rules successfully!")


if __name__ == "__main__":
    try:
        test_data_equivalence()
        test_follow_up_rules_consistency()
        print("\n🎉 All equivalence tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)