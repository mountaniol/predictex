"""
Comprehensive tests for UISchemaGenerator component.

This test suite follows Test-Driven Development principles and covers:
- Text question schema conversion
- Choice question schema with options
- Conditional visibility rules application 
- Validation rules extraction
- Different question types (text, textarea, number, yes-no, choice-single, choice-multi)
- with_other option handling
- custom_text_input support
- Complex validation rules (required, min, max, pattern)
- Conditional follow-up questions
- TOML DSL parsing for follow_up_rules
- Meta information preservation (hint, info, cluster_name)
- Edge cases and error handling

Author: QA Engineer
Date: 2025-01-27
Status: TDD - Tests written first, implementation follows
"""

import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch
import json
from pathlib import Path

# Import the component we're testing (will fail initially - TDD)
try:
    from src.backend.ui_schema_generator import UISchemaGenerator, UISchema, ValidationRules
except ImportError:
    # Expected during TDD - component doesn't exist yet
    UISchemaGenerator = None
    UISchema = None
    ValidationRules = None


class TestUISchemaGenerator:
    """Test suite for UISchemaGenerator component."""
    
    @pytest.fixture
    def generator(self):
        """Create UISchemaGenerator instance for testing."""
        if UISchemaGenerator is None:
            pytest.skip("UISchemaGenerator not implemented yet - TDD approach")
        return UISchemaGenerator()
    
    @pytest.fixture
    def sample_text_question(self):
        """Sample text question from q4.toml format."""
        return {
            "id": "MET.LOC",
            "text": "Where is the business located (country, state, city)?",
            "hint": "List main operating location(s).",
            "info": "Write the country, state or province if applicable, and the city where the business mainly operates.",
            "cluster_name": "Basic Information", 
            "position_in_cluster": 1,
            "question_type": "text",
            "score": "NO"
        }
    
    @pytest.fixture
    def sample_choice_single_question(self):
        """Sample choice-single question with dropdown UI."""
        return {
            "id": "MET.SIZE",
            "text": "Approximate annual revenue bracket",
            "hint": "Pick a rough yearly sales range.",
            "info": "Pick the rough yearly sales before expenses. If you do not know the exact number, choose the closest range.",
            "cluster_name": "Basic Information",
            "position_in_cluster": 3,
            "question_type": "choice-single", 
            "ui": "dropdown",
            "score": "NO",
            "options_sort": "as_is",
            "options": [
                {"code": "lt250k", "label": "< $250k"},
                {"code": "250k_1m", "label": "$250k to $1m"},
                {"code": "1m_5m", "label": "$1m to $5m"},
                {"code": "gt5m", "label": ">$5m"}
            ],
            "custom_text_input_id": "MET.SIZE_CUSTOM",
            "custom_text_input_placeholder": "Or enter exact annual revenue"
        }
    
    @pytest.fixture
    def sample_choice_multi_question(self):
        """Sample choice-multi question with other option."""
        return {
            "id": "SG01",
            "text": "What are the main challenges facing this business?",
            "hint": "Select all that apply",
            "cluster_name": "Strategic Assessment",
            "position_in_cluster": 1,
            "question_type": "choice-multi",
            "max_selections": 3,
            "with_other": True,
            "other_text_id": "SG01_OTHER",
            "options": [
                {"code": "declining_sales", "label": "Declining sales"},
                {"code": "competition", "label": "Increased competition"},
                {"code": "cash_flow", "label": "Cash flow issues"},
                {"code": "other", "label": "Other (specify)"}
            ]
        }
    
    @pytest.fixture
    def sample_conditional_question(self):
        """Sample question with conditional visibility."""
        return {
            "id": "FIN.DEBT_DETAILS",
            "text": "What types of debt does the business have?",
            "question_type": "choice-multi",
            "conditional": {
                "show_when": "FIN.DEBT == 'yes'"
            },
            "options": [
                {"code": "mortgage", "label": "Real estate mortgage"},
                {"code": "equipment", "label": "Equipment financing"},
                {"code": "credit_cards", "label": "Credit card debt"},
                {"code": "other", "label": "Other debt"}
            ]
        }
    
    @pytest.fixture
    def sample_validation_question(self):
        """Sample question with complex validation rules."""
        return {
            "id": "FIN.REVENUE",
            "text": "Annual revenue in USD",
            "question_type": "number",
            "validation": {
                "required": True,
                "min": 0,
                "max": 100000000,
                "pattern": r"^\d+(\.\d{1,2})?$"
            }
        }
    
    @pytest.fixture  
    def sample_follow_up_question(self):
        """Sample question with follow-up DSL rules."""
        return {
            "id": "BUS.TYPE", 
            "text": "What type of business structure?",
            "question_type": "choice-single",
            "options": [
                {"code": "sole_proprietorship", "label": "Sole Proprietorship"},
                {"code": "llc", "label": "LLC"},
                {"code": "corporation", "label": "Corporation"}
            ],
            "follow_up_rules": "IF BUS.TYPE == 'corporation' THEN SHOW TAX.CORP_TAX"
        }

    # ========================================================================
    # Test Cases from Plan (Required)
    # ========================================================================

    def test_text_question_schema(self, generator, sample_text_question):
        """Test conversion of text questions to UI schema."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        schema = generator.question_to_schema(sample_text_question)
        
        # Assert basic schema structure
        assert schema.type == "text"
        assert schema.label == "Where is the business located (country, state, city)?"
        assert schema.hint == "List main operating location(s)."
        assert schema.info == "Write the country, state or province if applicable, and the city where the business mainly operates."
        assert schema.required is False  # score="NO" implies not required for AI
        
        # Assert metadata preservation
        assert schema.cluster_name == "Basic Information"
        assert schema.position_in_cluster == 1
        assert schema.question_id == "MET.LOC"

    def test_choice_question_schema(self, generator, sample_choice_single_question):
        """Test conversion of choice questions with options."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        schema = generator.question_to_schema(sample_choice_single_question)
        
        # Assert choice-specific schema
        assert schema.type == "choice-single"
        assert schema.ui_variant == "dropdown"
        assert len(schema.options) == 4
        
        # Assert option structure
        option = schema.options[0]
        assert option.code == "lt250k"
        assert option.label == "< $250k"
        
        # Assert custom text input
        assert schema.custom_text_input is not None
        assert schema.custom_text_input.id == "MET.SIZE_CUSTOM"
        assert schema.custom_text_input.placeholder == "Or enter exact annual revenue"

    def test_conditional_schema(self, generator, sample_conditional_question):
        """Test application of conditional visibility rules.""" 
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        schema = generator.question_to_schema(sample_conditional_question)
        
        # Assert conditional visibility
        assert schema.conditional is not None
        assert schema.conditional.show_when == "FIN.DEBT == 'yes'"
        
        # Test with mock answers
        answers = {"FIN.DEBT": "yes"}
        visible = generator.should_show_question(schema, answers)
        assert visible is True
        
        answers = {"FIN.DEBT": "no"}
        visible = generator.should_show_question(schema, answers)
        assert visible is False

    def test_validation_rules(self, generator, sample_validation_question):
        """Test inclusion of validation rules in schema."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        schema = generator.question_to_schema(sample_validation_question)
        
        # Assert validation rules
        assert schema.validation is not None
        assert schema.validation.required is True
        assert schema.validation.min == 0
        assert schema.validation.max == 100000000
        assert schema.validation.pattern == r"^\d+(\.\d{1,2})?$"
        
        # Test validation logic
        assert generator.validate_answer(schema, "1000.50") is True
        assert generator.validate_answer(schema, "-100") is False  # Below min
        assert generator.validate_answer(schema, "abc") is False  # Invalid pattern

    # ========================================================================
    # Additional Comprehensive Test Cases
    # ========================================================================

    def test_textarea_question_schema(self, generator):
        """Test textarea question type conversion."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "NOTES",
            "text": "Additional comments",
            "question_type": "textarea",
            "validation": {"max_length": 1000}
        }
        
        schema = generator.question_to_schema(question)
        
        assert schema.type == "textarea"
        assert schema.validation.max_length == 1000

    def test_number_question_schema(self, generator):
        """Test number question type conversion."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "EMPLOYEES",
            "text": "Number of employees",
            "question_type": "number",
            "validation": {"min": 0, "max": 10000}
        }
        
        schema = generator.question_to_schema(question)
        
        assert schema.type == "number"
        assert schema.validation.min == 0
        assert schema.validation.max == 10000

    def test_yes_no_question_schema(self, generator):
        """Test yes-no question type conversion."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "PROFITABLE",
            "text": "Is the business profitable?",
            "question_type": "yes-no"
        }
        
        schema = generator.question_to_schema(question)
        
        assert schema.type == "yes-no"
        assert len(schema.options) == 2
        assert schema.options[0].code == "yes"
        assert schema.options[1].code == "no"

    def test_choice_multi_with_max_selections(self, generator, sample_choice_multi_question):
        """Test choice-multi question with selection limits."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        schema = generator.question_to_schema(sample_choice_multi_question)
        
        assert schema.type == "choice-multi"
        assert schema.max_selections == 3
        assert schema.with_other is True
        assert schema.other_text_id == "SG01_OTHER"

    def test_with_other_option_handling(self, generator, sample_choice_multi_question):
        """Test proper handling of 'other' options with text fields."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        schema = generator.question_to_schema(sample_choice_multi_question)
        
        # Find 'other' option
        other_option = next((opt for opt in schema.options if opt.code == "other"), None)
        assert other_option is not None
        assert other_option.label == "Other (specify)"
        
        # Test other field validation
        answers = {"SG01": ["other"], "SG01_OTHER": ""}
        is_valid = generator.validate_answer(schema, answers)
        assert is_valid is False  # Other selected but no text
        
        answers = {"SG01": ["other"], "SG01_OTHER": "Custom reason"}
        is_valid = generator.validate_answer(schema, answers)
        assert is_valid is True

    def test_custom_text_input_support(self, generator, sample_choice_single_question):
        """Test custom text input field support."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        schema = generator.question_to_schema(sample_choice_single_question)
        
        # Assert custom text input configuration
        assert schema.custom_text_input is not None
        assert schema.custom_text_input.id == "MET.SIZE_CUSTOM"
        assert schema.custom_text_input.placeholder == "Or enter exact annual revenue"

    def test_complex_validation_rules(self, generator):
        """Test extraction of complex validation rules."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "EMAIL",
            "text": "Business email",
            "question_type": "text",
            "validation": {
                "required": True,
                "pattern": r"^[^@]+@[^@]+\.[^@]+$",
                "min_length": 5,
                "max_length": 100
            }
        }
        
        schema = generator.question_to_schema(question)
        
        assert schema.validation.required is True
        assert schema.validation.pattern == r"^[^@]+@[^@]+\.[^@]+$"
        assert schema.validation.min_length == 5
        assert schema.validation.max_length == 100

    def test_conditional_follow_up_questions(self, generator, sample_follow_up_question):
        """Test conditional follow-up question DSL parsing."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        schema = generator.question_to_schema(sample_follow_up_question)
        
        # Assert follow-up rule parsing
        assert schema.follow_up_rules is not None
        assert "corporation" in schema.follow_up_rules
        assert "TAX.CORP_TAX" in schema.follow_up_rules
        
        # Test follow-up evaluation
        answers = {"BUS.TYPE": "corporation"}
        follow_ups = generator.get_follow_up_questions(schema, answers)
        assert "TAX.CORP_TAX" in follow_ups
        
        answers = {"BUS.TYPE": "llc"}
        follow_ups = generator.get_follow_up_questions(schema, answers)
        assert "TAX.CORP_TAX" not in follow_ups

    def test_toml_dsl_parsing_for_follow_up_rules(self, generator):
        """Test TOML DSL parsing for complex follow-up rules."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "COMPLEX_RULE",
            "text": "Complex conditional question",
            "question_type": "text", 
            "follow_up_rules": "IF (REV > 1000000 AND EMPLOYEES > 10) OR TYPE == 'corporation' THEN SHOW [TAX.ADVANCED, LEGAL.COMPLIANCE]"
        }
        
        schema = generator.question_to_schema(question)
        
        # Test complex DSL parsing
        answers = {"REV": 1500000, "EMPLOYEES": 15, "TYPE": "llc"}
        follow_ups = generator.get_follow_up_questions(schema, answers)
        assert "TAX.ADVANCED" in follow_ups
        assert "LEGAL.COMPLIANCE" in follow_ups

    def test_meta_information_preservation(self, generator, sample_text_question):
        """Test preservation of metadata (hint, info, cluster_name)."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        schema = generator.question_to_schema(sample_text_question)
        
        # Assert all metadata is preserved
        assert schema.hint == sample_text_question["hint"]
        assert schema.info == sample_text_question["info"]
        assert schema.cluster_name == sample_text_question["cluster_name"]
        assert schema.position_in_cluster == sample_text_question["position_in_cluster"]

    # ========================================================================
    # Edge Cases and Error Handling
    # ========================================================================

    def test_missing_required_fields(self, generator):
        """Test handling of questions with missing required fields.""" 
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        invalid_question = {
            # Missing 'id' and 'question_type'
            "text": "Invalid question"
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            generator.question_to_schema(invalid_question)

    def test_invalid_question_type(self, generator):
        """Test handling of unsupported question types."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        invalid_question = {
            "id": "INVALID",
            "text": "Question with unsupported type",
            "question_type": "unsupported_type"
        }
        
        with pytest.raises(ValueError, match="Unsupported question type"):
            generator.question_to_schema(invalid_question)

    def test_malformed_options(self, generator):
        """Test handling of malformed option arrays."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        invalid_question = {
            "id": "MALFORMED",
            "text": "Question with malformed options",
            "question_type": "choice-single",
            "options": [
                {"code": "valid", "label": "Valid option"},
                {"invalid": "structure"}  # Missing 'code' and 'label'
            ]
        }
        
        with pytest.raises(ValueError, match="Invalid option structure"):
            generator.question_to_schema(invalid_question)

    def test_circular_conditional_dependencies(self, generator):
        """Test detection of circular conditional dependencies."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        questions = [
            {
                "id": "A",
                "text": "Question A",
                "question_type": "text",
                "conditional": {"show_when": "B == 'yes'"}
            },
            {
                "id": "B", 
                "text": "Question B",
                "question_type": "text",
                "conditional": {"show_when": "A == 'yes'"}
            }
        ]
        
        with pytest.raises(ValueError, match="Circular dependency detected"):
            generator.validate_question_dependencies(questions)

    def test_empty_question_list(self, generator):
        """Test handling of empty question lists."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        result = generator.questions_to_schemas([])
        assert result == []

    def test_null_and_none_values(self, generator):
        """Test handling of null and None values in questions."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "NULL_TEST",
            "text": "Question with null values",
            "question_type": "text",
            "hint": None,
            "info": "",
            "validation": None
        }
        
        schema = generator.question_to_schema(question)
        
        # None values should be handled gracefully
        assert schema.hint is None
        assert schema.info == ""
        assert schema.validation is None

    def test_unicode_and_special_characters(self, generator):
        """Test handling of Unicode and special characters."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "UNICODE_TEST",
            "text": "Question with émojis 🚀 and spéciål chàractërs",
            "question_type": "text",
            "options": [
                {"code": "café", "label": "Café ☕"},
                {"code": "naïve", "label": "Naïve approach"}
            ]
        }
        
        schema = generator.question_to_schema(question)
        
        # Unicode should be preserved
        assert "émojis 🚀" in schema.label
        assert "spéciål chàractërs" in schema.label

    def test_very_long_strings(self, generator):
        """Test handling of very long strings."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        long_text = "A" * 10000  # 10K character string
        question = {
            "id": "LONG_TEST",
            "text": long_text,
            "question_type": "textarea"
        }
        
        schema = generator.question_to_schema(question)
        assert len(schema.label) == 10000

    # ========================================================================
    # Performance and Integration Tests
    # ========================================================================

    def test_batch_question_processing(self, generator):
        """Test efficient batch processing of multiple questions."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        questions = []
        for i in range(100):
            questions.append({
                "id": f"Q{i:03d}",
                "text": f"Question {i}",
                "question_type": "text"
            })
        
        schemas = generator.questions_to_schemas(questions)
        
        assert len(schemas) == 100
        assert all(schema.question_id.startswith("Q") for schema in schemas)

    def test_schema_caching(self, generator):
        """Test schema generation caching for performance."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "CACHE_TEST",
            "text": "Cacheable question",
            "question_type": "text"
        }
        
        # First call
        schema1 = generator.question_to_schema(question)
        
        # Second call should use cache
        schema2 = generator.question_to_schema(question)
        
        # Should be the same object if cached
        assert schema1 is schema2 or schema1 == schema2

    def test_toml_integration(self, generator):
        """Test integration with actual TOML question files."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        # Load sample from actual q4.toml file
        toml_path = Path(__file__).parent.parent / "public" / "questions" / "q4.toml"
        if toml_path.exists():
            import toml
            data = toml.load(toml_path)
            questions = data.get("questions", [])
            
            if questions:
                schemas = generator.questions_to_schemas(questions[:5])  # Test first 5
                assert len(schemas) <= 5
                assert all(hasattr(schema, 'question_id') for schema in schemas)

    def test_json_compatibility(self, generator):
        """Test compatibility with legacy JSON question format."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        # Load legacy JSON format 
        json_path = Path(__file__).parent.parent / "public" / "questions" / "q4.json"
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
            
            questions = data.get("questions", [])
            if questions:
                schema = generator.question_to_schema(questions[0])
                assert schema is not None

    # ========================================================================
    # Schema Validation Tests  
    # ========================================================================

    def test_schema_validation_completeness(self, generator):
        """Test that generated schemas are complete and valid."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "COMPLETE_TEST",
            "text": "Complete question",
            "question_type": "choice-single",
            "options": [{"code": "opt1", "label": "Option 1"}]
        }
        
        schema = generator.question_to_schema(question)
        
        # Validate schema completeness
        assert generator.validate_schema(schema) is True

    def test_schema_serialization(self, generator):
        """Test that schemas can be serialized to JSON."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "SERIALIZE_TEST",
            "text": "Serializable question",
            "question_type": "text"
        }
        
        schema = generator.question_to_schema(question)
        
        # Should be serializable to JSON
        schema_json = schema.to_json()
        assert isinstance(schema_json, str)
        
        # Should be deserializable
        schema_dict = json.loads(schema_json)
        assert schema_dict["question_id"] == "SERIALIZE_TEST"

    def test_schema_versioning(self, generator):
        """Test schema version compatibility."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        question = {
            "id": "VERSION_TEST",
            "text": "Versioned question", 
            "question_type": "text",
            "schema_version": "1.2"
        }
        
        schema = generator.question_to_schema(question)
        assert hasattr(schema, 'schema_version')
        assert schema.schema_version == "1.2"


# ========================================================================
# Test Helper Classes and Fixtures
# ========================================================================

class MockUISchemaGenerator:
    """Mock implementation for early testing."""
    
    def question_to_schema(self, question):
        """Mock schema generation."""
        return {
            "question_id": question.get("id"),
            "type": question.get("question_type"),
            "label": question.get("text")
        }
    
    def validate_schema(self, schema):
        """Mock validation."""
        return True


@pytest.fixture
def mock_generator():
    """Provide mock generator for testing."""
    return MockUISchemaGenerator()


# ========================================================================
# Integration Test Scenarios
# ========================================================================

class TestUISchemaIntegration:
    """Integration tests with other system components."""
    
    @pytest.fixture
    def generator(self):
        """Generator fixture for integration tests."""
        if UISchemaGenerator is None:
            pytest.skip("UISchemaGenerator not implemented yet - TDD approach")
        return UISchemaGenerator()
    
    def test_command_generator_integration(self, generator):
        """Test integration with CommandGenerator."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        # This would test integration with CommandGenerator
        # when that component is implemented
        pass
    
    def test_session_manager_integration(self, generator):
        """Test integration with SessionManager.""" 
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        # This would test session-aware schema generation
        pass
    
    def test_dependency_engine_integration(self, generator):
        """Test integration with DependencyEngine."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        # This would test dependency-aware schema generation
        pass


# ========================================================================
# Performance Benchmarks
# ========================================================================

@pytest.mark.performance
class TestUISchemaPerformance:
    """Performance tests for UISchemaGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Generator fixture for performance tests."""
        if UISchemaGenerator is None:
            pytest.skip("UISchemaGenerator not implemented yet - TDD approach")
        return UISchemaGenerator()
    
    def test_single_question_performance(self, generator):
        """Benchmark single question conversion time.""" 
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        import time
        
        question = {
            "id": "PERF_TEST",
            "text": "Performance test question",
            "question_type": "text"
        }
        
        start_time = time.time()
        schema = generator.question_to_schema(question)
        end_time = time.time()
        
        # Should complete within 10ms
        assert (end_time - start_time) < 0.01
    
    def test_batch_processing_performance(self, generator):
        """Benchmark batch question processing."""
        if generator is None:
            pytest.skip("UISchemaGenerator not implemented yet")
            
        import time
        
        questions = [
            {
                "id": f"BATCH_Q{i}",
                "text": f"Batch question {i}",
                "question_type": "text"
            } 
            for i in range(1000)
        ]
        
        start_time = time.time()
        schemas = generator.questions_to_schemas(questions)
        end_time = time.time()
        
        # Should process 1000 questions within 1 second
        assert (end_time - start_time) < 1.0
        assert len(schemas) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])