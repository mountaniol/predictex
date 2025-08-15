#!/usr/bin/env python3
"""
Question Creator Backend Server (Port 3004)

This backend serves as a parser and transformer for the Question Creator UI.
It parses text input into JSON format and delegates AI evaluation to the existing backend (port 3001).

Endpoints:
- GET /api/providers - List available AI providers and models
- POST /api/parse - Parse text input into question JSON
- POST /api/evaluate - Evaluate question using AI (delegates to port 3001)
- GET /api/files - List available JSON files on server
- GET /api/file/<filename> - Load specific JSON file
- POST /api/save - Save JSON file with backup
"""

import os
import sys
import json
import re
import requests
import datetime
from typing import Dict, List, Any, Optional, Tuple
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Add parent directory to path to import from existing backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'backend'))

app = Flask(__name__)
CORS(app)

# Debug middleware to log all requests
@app.before_request
def log_requests():
    print(f"📡 [DEBUG] {request.method} {request.path} from {request.remote_addr}")
    if request.is_json:
        print(f"📡 [DEBUG] JSON body size: {len(request.get_data())} bytes")

# Configuration
QUESTIONS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'public', 'questions')
BACKUP_DIR = os.path.join(QUESTIONS_DIR, 'backups')
EXISTING_BACKEND_URL = 'http://localhost:3001'

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

class QuestionParser:
    """Parse text input into JSON question format"""
    
    def __init__(self):
        self.required_fields = ['id', 'text', 'cluster', 'position', 'type']
        self.question_types = [
            'text', 'textarea', 'number', 'yes-no', 
            'choice-single', 'choice-multi', 'internal'
        ]
        self.ui_variants = ['radio', 'dropdown', 'multiselect', 'textarea']
    
    def parse(self, text: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Parse text input into question JSON format.
        Returns (parsed_question, errors)
        """
        errors = []
        question = {}
        options = []
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        try:
            for line in lines:
                if ':' not in line:
                    continue
                    
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                # Required fields
                if key == 'id':
                    if not re.match(r'^[A-Z]+[0-9]+[A-Z]?$', value):
                        errors.append(f"Invalid ID format: {value}. Use format like SG01, MET.LOC")
                    question['id'] = value
                
                elif key == 'text':
                    if not value:
                        errors.append("Question text cannot be empty")
                    question['text'] = value
                
                elif key in ['cluster', 'cluster_name']:
                    if not value:
                        errors.append("Cluster name cannot be empty")
                    question['cluster_name'] = value
                
                elif key == 'position':
                    try:
                        question['position_in_cluster'] = int(value)
                    except ValueError:
                        errors.append(f"Position must be a number: {value}")
                
                elif key == 'type':
                    if value not in self.question_types:
                        errors.append(f"Unknown question type: {value}. Valid types: {', '.join(self.question_types)}")
                    question['question_type'] = value
                
                # Optional fields
                elif key == 'hint':
                    question['hint'] = value
                
                elif key == 'info':
                    question['info'] = value
                
                elif key == 'ui':
                    if value not in self.ui_variants:
                        errors.append(f"Unknown UI variant: {value}. Valid variants: {', '.join(self.ui_variants)}")
                    question['ui'] = value
                
                elif key == 'option':
                    if '->' in value:
                        code, label = value.split('->', 1)
                        options.append({
                            'code': code.strip(),
                            'label': label.strip()
                        })
                    else:
                        errors.append(f"Invalid option format: {value}. Use 'code -> label'")
                
                elif key == 'with_other':
                    question['with_other'] = value.lower() in ['true', 'yes', '1']
                
                elif key == 'other_text_id':
                    question['other_text_id'] = value
                
                elif key == 'max_selections':
                    try:
                        question['max_selections'] = int(value)
                    except ValueError:
                        errors.append(f"max_selections must be a number: {value}")
                
                elif key == 'ranked':
                    question['ranked'] = value.lower() in ['true', 'yes', '1']
                
                elif key in ['include_answers', 'dependencies']:
                    if not question.get('ai_context'):
                        question['ai_context'] = {}
                    question['ai_context']['include_answers'] = [
                        dep.strip() for dep in value.split(',') if dep.strip()
                    ]
                
                elif key == 'include_meta':
                    if not question.get('ai_context'):
                        question['ai_context'] = {}
                    question['ai_context']['include_meta'] = [
                        meta.strip() for meta in value.split(',') if meta.strip()
                    ]
                
                elif key in ['prompt_add', 'prompt_additional']:
                    question['prompt_add'] = value
                
                elif key == 'score':
                    if value.upper() in ['NO', 'AUTO']:
                        question['score'] = value.upper()
                    else:
                        errors.append(f"Score must be 'NO' or 'AUTO': {value}")
            
            # Check required fields
            for field in self.required_fields:
                json_field = {
                    'id': 'id',
                    'text': 'text', 
                    'cluster': 'cluster_name',
                    'position': 'position_in_cluster',
                    'type': 'question_type'
                }[field]
                
                if json_field not in question:
                    errors.append(f"Missing required field: {field}")
            
            # Add options if any
            if options:
                question['options'] = options
                question['options_sort'] = 'as_is'
            
            # Set defaults
            if 'score' not in question:
                question['score'] = 'AUTO'
            
            # Validate option requirements for choice types
            if question.get('question_type', '').startswith('choice') and not options:
                errors.append("Choice questions require at least one option")
            
            if errors:
                return None, errors
            
            return question, []
            
        except Exception as e:
            errors.append(f"Parsing error: {str(e)}")
            return None, errors

# Initialize parser
parser = QuestionParser()

@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Get available AI providers and models"""
    print("🔌 [DEBUG] GET /api/providers - Getting AI providers and models")
    try:
        providers = []
        
        # Get OpenAI models (static list)
        print("🤖 [DEBUG] Adding OpenAI provider with 4 models")
        providers.append({
            'name': 'openai',
            'models': [
                'gpt-4-1106-preview',
                'gpt-4',
                'gpt-3.5-turbo',
                'gpt-3.5-turbo-16k'
            ]
        })
        
        # Get Ollama models (dynamic from API)
        try:
            print("🦙 [DEBUG] Checking Ollama at http://localhost:11434/api/tags")
            ollama_response = requests.get('http://localhost:11434/api/tags', timeout=5)
            if ollama_response.status_code == 200:
                ollama_data = ollama_response.json()
                ollama_models = [model['name'] for model in ollama_data.get('models', [])]
                print(f"🦙 [DEBUG] Found {len(ollama_models)} Ollama models")
                if ollama_models:
                    providers.append({
                        'name': 'ollama',
                        'models': ollama_models
                    })
            else:
                print(f"🦙 [DEBUG] Ollama API returned status {ollama_response.status_code}")
        except Exception as e:
            print(f"🦙 [DEBUG] Ollama not available: {str(e)}")
            # Ollama not available, add placeholder
            providers.append({
                'name': 'ollama',
                'models': ['llama2:7b', 'nous-hermes2:34b']  # Common models
            })
        
        print(f"✅ [DEBUG] Returning {len(providers)} providers")
        return jsonify(providers)
        
    except Exception as e:
        print(f"❌ [DEBUG] Error in get_providers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/parse', methods=['POST'])
def parse_text():
    """Parse text input into JSON question format"""
    print("📝 [DEBUG] POST /api/parse - Parsing text input")
    try:
        data = request.get_json()
        text = data.get('text', '')
        print(f"📝 [DEBUG] Input text length: {len(text)} chars")
        
        if not text:
            print("❌ [DEBUG] No text provided")
            return jsonify({'success': False, 'errors': ['No text provided']})
        
        print("🔍 [DEBUG] Starting text parsing...")
        question, errors = parser.parse(text)
        print(f"🔍 [DEBUG] Parse result - Errors: {len(errors)}, Question: {bool(question)}")
        
        if errors:
            print(f"❌ [DEBUG] Parse errors: {errors}")
            return jsonify({
                'success': False,
                'errors': errors
            })
        
        print(f"✅ [DEBUG] Parse successful - Question ID: {question.get('id', 'N/A')}")
        return jsonify({
            'success': True,
            'question': question
        })
        
    except Exception as e:
        print(f"💥 [DEBUG] Parse exception: {str(e)}")
        return jsonify({
            'success': False,
            'errors': [f'Server error: {str(e)}']
        }), 500

@app.route('/api/evaluate', methods=['POST'])
def evaluate_question():
    """Evaluate question using AI (delegates to existing backend)"""
    try:
        data = request.get_json()
        question = data.get('question')
        provider = data.get('provider', 'openai:gpt-4-1106-preview')
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'})
        
        # Create a mock answer for evaluation
        mock_answer = "Sample answer for evaluation"
        if question.get('question_type') == 'choice-single' and question.get('options'):
            mock_answer = question['options'][0]['code']
        elif question.get('question_type') == 'choice-multi' and question.get('options'):
            mock_answer = [question['options'][0]['code']]
        elif question.get('question_type') == 'yes-no':
            mock_answer = 'yes'
        
        # Prepare evaluation request for existing backend
        eval_request = {
            'questionId': question['id'],
            'allAnswers': {
                question['id']: mock_answer
            }
        }
        
        # Configure AI provider if specified
        if provider and ':' in provider:
            provider_name, model_name = provider.split(':', 1)
            eval_request['provider'] = provider_name
            eval_request['model'] = model_name
        
        # Send to existing backend
        response = requests.post(
            f'{EXISTING_BACKEND_URL}/api/simple-evaluate.mjs',
            json=eval_request,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'score': result.get('score', 0),
                'explanation': result.get('explanation', 'No explanation provided')
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Backend evaluation failed: {response.status_code}'
            })
            
    except requests.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'Failed to connect to evaluation backend: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/files', methods=['GET'])
def list_files():
    """List available JSON files"""
    try:
        files = []
        for filename in os.listdir(QUESTIONS_DIR):
            if filename.endswith('.json') and not filename.startswith('.'):
                files.append(filename)
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/<filename>', methods=['GET'])
def get_file(filename):
    """Get specific JSON file"""
    try:
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = os.path.join(QUESTIONS_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save', methods=['POST'])
def save_file():
    """Save JSON file with backup"""
    try:
        data = request.get_json()
        filename = data.get('filename', 'untitled.json')
        file_data = data.get('data')
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = os.path.join(QUESTIONS_DIR, filename)
        
        # Create backup if file exists
        if os.path.exists(filepath):
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            backup_filename = f"{filename}.{timestamp}.backup"
            backup_filepath = os.path.join(BACKUP_DIR, backup_filename)
            
            # Copy existing file to backup
            import shutil
            shutil.copy2(filepath, backup_filepath)
        
        # Save new file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True, 'message': 'File saved successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    print("🩺 [DEBUG] GET /api/health - Health check requested")
    response = {
        'status': 'healthy',
        'service': 'Question Creator Backend',
        'port': 3004,
        'timestamp': datetime.datetime.now().isoformat()
    }
    print(f"🩺 [DEBUG] Health check response: {response['status']}")
    return jsonify(response)

if __name__ == '__main__':
    print("🚀 Starting Question Creator Backend on port 3004...")
    print(f"📁 Questions directory: {QUESTIONS_DIR}")
    print(f"💾 Backup directory: {BACKUP_DIR}")
    print(f"🔗 Existing backend URL: {EXISTING_BACKEND_URL}")
    print(f"🌐 Host: 0.0.0.0 (accessible from any IP)")
    print(f"🐍 Python version: {sys.version}")
    print(f"📦 Flask app name: {app.name}")
    
    # Create directories if they don't exist
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f"✅ Backup directory ensured: {BACKUP_DIR}")
    
    print("🎯 Starting Flask development server...")
    app.run(host='0.0.0.0', port=3004, debug=True)