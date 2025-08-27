#!/usr/bin/env python3
"""
Q4 JSON to TOML Converter for QnA Evaluator

This script converts the existing q4.json questionnaire configuration 
to the new TOML format with DSL follow-up rules and improved structure.

Usage:
    python tools/q4_json_to_toml_converter.py
    python tools/q4_json_to_toml_converter.py --input q4.json --output q4.toml
"""

import json
import toml
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from backend.follow_up_parser import FollowUpParser
except ImportError:
    print("Error: Could not import FollowUpParser. Make sure src/backend/follow_up_parser.py exists.")
    sys.exit(1)


class JsonToTomlConverter:
    """Converts QnA Evaluator JSON configuration to TOML format"""
    
    def __init__(self):
        """Initialize the converter"""
        self.parser = FollowUpParser()
        self.conversion_stats = {
            'questions_converted': 0,
            'follow_ups_converted': 0,
            'analysis_sections_converted': 0,
            'errors': []
        }
    
    def convert_file(self, input_path: str, output_path: str) -> bool:
        """
        Convert JSON file to TOML format
        
        Args:
            input_path: Path to input JSON file
            output_path: Path to output TOML file
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            print(f"Loading JSON from: {input_path}")
            with open(input_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            print("Converting to TOML structure...")
            toml_data = self.convert_structure(json_data)
            
            print(f"Writing TOML to: {output_path}")
            # Write TOML with header comments
            self.write_toml_with_formatting(toml_data, output_path)
            
            self.print_conversion_report()
            return True
            
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            return False
    
    def write_toml_with_formatting(self, data: Dict[str, Any], output_path: str):
        """Write TOML with proper formatting and comments"""
        
        header = f"""# QnA Evaluator Configuration - TOML Format
# Converted from q4.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 
# This file provides improved readability and maintainability over JSON:
# - Multi-line strings for long prompts and descriptions
# - Comments for documentation and organization
# - Simplified follow-up rules using DSL syntax
# - Flattened structure for better maintainability

"""
        
        # Write basic info
        content_parts = [header]
        
        # Version and settings
        if 'version' in data:
            content_parts.append(f'version = "{data["version"]}"')
            content_parts.append('')
        
        # Settings section
        if 'settings' in data:
            content_parts.append('[settings.labels]')
            labels = data['settings']['labels']
            for key, value in labels.items():
                content_parts.append(f'{key} = "{value}"')
            content_parts.append('')
        
        # Questions section with organization
        if 'questions' in data:
            current_cluster = None
            for question in data['questions']:
                cluster_name = question.get('cluster_name', 'Uncategorized')
                
                # Add cluster header comment
                if cluster_name != current_cluster:
                    current_cluster = cluster_name
                    content_parts.append('')
                    content_parts.append('# ' + '=' * 65)
                    content_parts.append(f'# {cluster_name.upper()} SECTION')
                    content_parts.append('# ' + '=' * 65)
                    content_parts.append('')
                
                # Add question
                content_parts.append('[[questions]]')
                content_parts.append(f'id = "{question["id"]}"')
                content_parts.append(f'text = "{question["text"]}"')
                
                # Add other fields
                for key, value in question.items():
                    if key in ['id', 'text']:
                        continue
                    elif key in ['hint', 'info', 'prompt_add', 'ai_validate_prompt'] and isinstance(value, str) and len(value) > 100:
                        # Use multi-line strings for long text
                        content_parts.append(f'{key} = """')
                        content_parts.append(value)
                        content_parts.append('"""')
                    elif key == 'options' and isinstance(value, list):
                        # Format options as inline tables
                        content_parts.append('options = [')
                        for option in value:
                            if isinstance(option, dict):
                                parts = []
                                for k, v in option.items():
                                    parts.append(f'{k} = "{v}"')
                                content_parts.append(f'  {{{", ".join(parts)}}},')
                        content_parts.append(']')
                    elif key == 'follow_up_rules' and isinstance(value, list):
                        # DSL rules with comments
                        content_parts.append('# Follow-up rules using simplified DSL syntax')
                        content_parts.append('follow_up_rules = [')
                        for rule in value:
                            content_parts.append(f'  "{rule}",')
                        content_parts.append(']')
                    elif isinstance(value, str):
                        content_parts.append(f'{key} = "{value}"')
                    elif isinstance(value, bool):
                        content_parts.append(f'{key} = {str(value).lower()}')
                    elif isinstance(value, (int, float)):
                        content_parts.append(f'{key} = {value}')
                    elif isinstance(value, list):
                        if all(isinstance(item, str) for item in value):
                            formatted_list = '[' + ', '.join(f'"{item}"' for item in value) + ']'
                            content_parts.append(f'{key} = {formatted_list}')
                        else:
                            content_parts.append(f'{key} = {toml.dumps({key: value})[key + " = "]}')
                
                content_parts.append('')
        
        # Analysis configuration
        if 'analysis' in data:
            content_parts.append('')
            content_parts.append('# ' + '=' * 65)
            content_parts.append('# ANALYSIS CONFIGURATION')
            content_parts.append('# ' + '=' * 65)
            content_parts.append('')
            
            analysis_data = data['analysis']
            
            # Base analysis settings
            content_parts.append('[analysis]')
            if 'loading_message' in analysis_data:
                content_parts.append(f'loading_message = "{analysis_data["loading_message"]}"')
            if 'base_prompt' in analysis_data:
                content_parts.append('base_prompt = """')
                content_parts.append(analysis_data['base_prompt'])
                content_parts.append('"""')
            content_parts.append('')
            
            # Individual analysis sections
            for key, section in analysis_data.items():
                if key in ['loading_message', 'base_prompt'] or not isinstance(section, dict):
                    continue
                
                content_parts.append(f'[analysis.{key}]')
                content_parts.append(f'# {section.get("name", key)} analysis section')
                
                for field, value in section.items():
                    if isinstance(value, str) and len(value) > 100:
                        content_parts.append(f'{field} = """')
                        content_parts.append(value)
                        content_parts.append('"""')
                    elif isinstance(value, str):
                        content_parts.append(f'{field} = "{value}"')
                    elif isinstance(value, bool):
                        content_parts.append(f'{field} = {str(value).lower()}')
                    elif isinstance(value, (int, float)):
                        content_parts.append(f'{field} = {value}')
                    elif isinstance(value, list):
                        if all(isinstance(item, str) for item in value):
                            formatted_list = '[' + ', '.join(f'"{item}"' for item in value) + ']'
                            content_parts.append(f'{field} = {formatted_list}')
                        else:
                            content_parts.append(f'{field} = {value}')
                    elif isinstance(value, dict):
                        # Inline table for model_config etc
                        def format_value(v):
                            if isinstance(v, bool):
                                return str(v).lower()
                            elif isinstance(v, (int, float)):
                                return str(v)
                            else:
                                return f'"{v}"'
                        
                        formatted_dict = '{' + ', '.join(f'{k} = {format_value(v)}' for k, v in value.items()) + '}'
                        content_parts.append(f'{field} = {formatted_dict}')
                
                content_parts.append('')
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_parts))
    
    def convert_structure(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert JSON data structure to TOML format
        
        Args:
            json_data: Original JSON data
            
        Returns:
            TOML-compatible data structure
        """
        toml_data = {
            'version': json_data.get('version', '1.2'),
            'settings': json_data.get('settings', {}),
            'questions': []
        }
        
        # Convert questions
        if 'questions' in json_data:
            for question in json_data['questions']:
                converted_question = self.convert_question(question)
                toml_data['questions'].append(converted_question)
                self.conversion_stats['questions_converted'] += 1
        
        # Convert optional questions if they exist
        if 'optional_questions' in json_data:
            toml_data['optional_questions'] = []
            for question in json_data['optional_questions']:
                converted_question = self.convert_question(question)
                toml_data['optional_questions'].append(converted_question)
        
        # Convert final analysis configuration
        if 'final_analysis_config' in json_data:
            analysis_config = self.convert_analysis_config(json_data['final_analysis_config'])
            toml_data.update(analysis_config)
        
        return toml_data
    
    def convert_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a single question from JSON to TOML format
        
        Args:
            question: Original question data
            
        Returns:
            TOML-compatible question data
        """
        converted = {}
        
        # Copy basic fields
        basic_fields = [
            'id', 'text', 'hint', 'info', 'cluster_name', 'position_in_cluster',
            'question_type', 'ui', 'score', 'options_sort', 'max_selections',
            'ranked', 'with_other', 'other_text_id'
        ]
        
        for field in basic_fields:
            if field in question:
                converted[field] = question[field]
        
        # Convert options array to inline tables
        if 'options' in question:
            converted['options'] = self.convert_options(question['options'])
        
        # Flatten custom_text_input
        if 'custom_text_input' in question:
            custom_input = question['custom_text_input']
            if 'id' in custom_input:
                converted['custom_text_input_id'] = custom_input['id']
            if 'placeholder' in custom_input:
                converted['custom_text_input_placeholder'] = custom_input['placeholder']
        
        # Convert follow-ups to DSL
        if 'follow_ups' in question:
            try:
                dsl_rules = self.parser.json_to_rules(question['follow_ups'])
                converted['follow_up_rules'] = dsl_rules
                self.conversion_stats['follow_ups_converted'] += len(dsl_rules)
            except Exception as e:
                error_msg = f"Failed to convert follow-ups for question {question.get('id', 'unknown')}: {e}"
                self.conversion_stats['errors'].append(error_msg)
                print(f"⚠️  {error_msg}")
                # Keep original follow_ups as fallback
                converted['follow_ups'] = question['follow_ups']
        
        # Flatten ai_context
        if 'ai_context' in question:
            ai_context = question['ai_context']
            if 'include_answers' in ai_context:
                converted['ai_context_include_answers'] = ai_context['include_answers']
            if 'include_meta' in ai_context:
                converted['ai_context_include_meta'] = ai_context['include_meta']
        
        # Copy AI prompt fields
        ai_fields = ['prompt_add', 'ai_validate_prompt']
        for field in ai_fields:
            if field in question:
                converted[field] = question[field]
        
        return converted
    
    def convert_options(self, options: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Convert options array to TOML inline table format
        
        Args:
            options: Original options array
            
        Returns:
            TOML-compatible inline tables
        """
        converted_options = []
        for option in options:
            # Keep as simple dict for TOML inline table syntax
            converted_option = {}
            if 'code' in option:
                converted_option['code'] = option['code']
            if 'label' in option:
                converted_option['label'] = option['label']
            converted_options.append(converted_option)
        
        return converted_options
    
    def convert_analysis_config(self, analysis_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert final analysis configuration to flattened TOML sections
        
        Args:
            analysis_config: Original analysis configuration
            
        Returns:
            TOML-compatible analysis configuration
        """
        result = {}
        
        # Add analysis section with base configuration
        analysis_section = {}
        if 'loading_message' in analysis_config:
            analysis_section['loading_message'] = analysis_config['loading_message']
        if 'base_prompt' in analysis_config:
            analysis_section['base_prompt'] = analysis_config['base_prompt']
        
        # Convert sections to named subsections
        if 'sections' in analysis_config:
            for i, section in enumerate(analysis_config['sections']):
                section_name = self.normalize_section_name(section.get('name', f'section_{i}'))
                
                converted_section = {
                    'name': section.get('name', f'Section {i+1}'),
                    'model': section.get('model', 'gpt-4o')
                }
                
                # Flatten web_search configuration
                if 'web_search' in section:
                    web_search = section['web_search']
                    converted_section['web_search_enabled'] = web_search.get('enabled', False)
                    if 'max_searches' in web_search:
                        converted_section['web_search_max_searches'] = web_search['max_searches']
                
                # Flatten ai_context configuration
                if 'ai_context' in section:
                    ai_context = section['ai_context']
                    if 'include_answers' in ai_context:
                        converted_section['ai_context_include_answers'] = ai_context['include_answers']
                    if 'include_scores' in ai_context:
                        converted_section['ai_context_include_scores'] = ai_context['include_scores']
                    if 'include_overall_score' in ai_context:
                        converted_section['ai_context_include_overall_score'] = ai_context['include_overall_score']
                
                # Copy other fields
                other_fields = ['specific_prompt', 'output_constraint', 'model_config']
                for field in other_fields:
                    if field in section:
                        converted_section[field] = section[field]
                
                analysis_section[section_name] = converted_section
                self.conversion_stats['analysis_sections_converted'] += 1
        
        result['analysis'] = analysis_section
        return result
    
    def normalize_section_name(self, name: str) -> str:
        """
        Normalize section name for TOML key
        
        Args:
            name: Original section name
            
        Returns:
            Normalized name suitable for TOML key
        """
        # Convert to lowercase and replace spaces/special chars with underscores
        normalized = name.lower()
        normalized = ''.join(c if c.isalnum() else '_' for c in normalized)
        # Remove multiple underscores
        while '__' in normalized:
            normalized = normalized.replace('__', '_')
        # Remove leading/trailing underscores
        return normalized.strip('_')
    
    def print_conversion_report(self):
        """Print conversion statistics and summary"""
        stats = self.conversion_stats
        print("\n" + "="*60)
        print("CONVERSION REPORT")
        print("="*60)
        print(f"✅ Questions converted: {stats['questions_converted']}")
        print(f"✅ Follow-ups converted: {stats['follow_ups_converted']}")
        print(f"✅ Analysis sections converted: {stats['analysis_sections_converted']}")
        
        if stats['errors']:
            print(f"\n⚠️  Errors encountered: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"   - {error}")
        else:
            print(f"\n🎉 Conversion completed successfully with no errors!")
        
        print("\n📋 What was converted:")
        print("   - JSON structure → TOML format")
        print("   - Nested follow_ups → DSL rules")
        print("   - Options arrays → Inline tables")  
        print("   - AI context → Flattened fields")
        print("   - Analysis config → Named sections")
        print("   - Long prompts → Multi-line strings")
        print("="*60)


def main():
    """Main function to run the converter"""
    parser = argparse.ArgumentParser(description='Convert QnA Evaluator JSON to TOML format')
    parser.add_argument(
        '--input', 
        default='public/questions/q4.json',
        help='Input JSON file path (default: public/questions/q4.json)'
    )
    parser.add_argument(
        '--output', 
        default='public/questions/q4.toml',
        help='Output TOML file path (default: public/questions/q4.toml)'
    )
    parser.add_argument(
        '--backup', 
        action='store_true',
        help='Create backup of original JSON file'
    )
    parser.add_argument(
        '--validate',
        action='store_true', 
        help='Validate TOML output by parsing it back'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        return 1
    
    # Create backup if requested
    if args.backup:
        backup_path = f"{args.input}.backup"
        print(f"Creating backup: {backup_path}")
        import shutil
        shutil.copy2(args.input, backup_path)
    
    # Run conversion
    converter = JsonToTomlConverter()
    success = converter.convert_file(args.input, args.output)
    
    if not success:
        return 1
    
    # Validate output if requested
    if args.validate:
        print("\nValidating TOML output...")
        try:
            with open(args.output, 'r', encoding='utf-8') as f:
                toml.load(f)
            print("✅ TOML validation successful!")
        except Exception as e:
            print(f"❌ TOML validation failed: {e}")
            return 1
    
    print(f"\n🎉 Conversion complete! TOML file created: {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())