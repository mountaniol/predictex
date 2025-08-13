import os
import sys

# Add the project root to the Python path to allow absolute imports
PROJECT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT_PATH not in sys.path:
    sys.path.append(PROJECT_ROOT_PATH)

import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import time

# --- Import business logic from other modules ---
from src.backend.py_simple_evaluate import evaluate_answer_logic
from src.backend.py_final_analysis import final_analysis_logic, load_question_set

# Define the absolute path to the project root.
# We go up two levels from `src/backend/` to reach the root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# --- App Initialization ---

# Load environment variables from a .env file into the environment
load_dotenv()

#: Flask application instance
app = Flask(__name__)
#: Enables Cross-Origin Resource Sharing for the Flask app, allowing the frontend to make requests.
CORS(app)

_app_config = None
_config_mtime = 0 # To track file modification time for caching

def load_app_config():
    """
    @brief Loads the application configuration from public/app.config.json.
    @description This function reads the main JSON configuration file. It also
    implements a simple caching mechanism by checking the file's modification
    time, reloading it only if it has changed. This is useful for local
    development.
    @return A dictionary containing the application configuration.
    @related_to app.config.json
    """
    global _app_config, _config_mtime
    config_path = os.path.join(PROJECT_ROOT, 'public', 'app.config.json')

    try:
        # For serverless environments, caching based on modification time might not be effective,
        # but it doesn't hurt. We'll rely on it mostly for local dev.
        mtime = os.path.getmtime(config_path) if os.path.exists(config_path) else 0
        if mtime > _config_mtime or _app_config is None:
            print(f"[Config] Loading configuration from {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                _app_config = json.load(f)
            _config_mtime = mtime
        return _app_config
    except Exception as e:
        print(f"!!! CRITICAL: Could not load or parse app.config.json from {config_path}. Error: {e}")
        # Return a default/empty config to prevent a hard crash
        return {}


@app.route('/api/simple-evaluate.mjs', methods=['POST'])
def handle_simple_evaluate():
    """
    @brief Flask endpoint to handle single question evaluation requests.

    @details This endpoint acts as the web interface for the `evaluate_answer_logic` function.
             It receives a POST request with a JSON body, validates the presence of required
             keys (`questionId`, `allAnswers`), and then passes this data to the core logic
             function. It returns the result as JSON and handles potential errors gracefully
             by returning appropriate HTTP status codes and error messages.

    @http_method POST
    @endpoint /api/simple-evaluate.mjs

    @json_body {
        "questionId": "SG01",
        "allAnswers": { "MET.LOC": "...", "SG01": "..." }
    }

    @returns {Response} A JSON response containing the 'score' and 'explanation' on success,
                        or an error message object on failure with a 4xx or 5xx status code.
    
    @related_to py_simple_evaluate.py: This is the primary web entry point for its logic.
    """
    try:
        data = request.get_json()
        if not data or 'questionId' not in data or 'allAnswers' not in data:
            return jsonify({"message": "Missing questionId or allAnswers in request body"}), 400

        question_id = data['questionId']
        all_answers = data['allAnswers']
        config = load_app_config()

        question_file = config.get("Generic", {}).get("question_set_file")
        prompt_file = config.get("Generic", {}).get("ai_prompt_file")

        if not question_file or not prompt_file:
            print("!!! CRITICAL: 'question_set_file' or 'ai_prompt_file' not found in app.config.json")
            return jsonify({"message": "Server configuration error: file paths not specified."}), 500

        result = evaluate_answer_logic(question_id, all_answers, config, question_file, prompt_file)
        return jsonify(result)

    except ValueError as e:
        return jsonify({"message": str(e)}), 404
    except Exception as e:
        print(f"[Flask Server] Error in /api/simple-evaluate: {e}")
        return jsonify({"message": "Internal Server Error"}), 500


@app.route('/api/final-analysis.mjs', methods=['POST'])
def handle_final_analysis():
    print("\n--- Python Server: Received request at /api/final-analysis.mjs ---")
    """
    @brief Flask endpoint to handle final analysis report generation requests.

    @details This endpoint serves as the web interface for generating sections of the final report.
             It expects a POST request with a JSON body containing all the data needed by the
             `final_analysis_logic` function. It performs basic validation and then calls the
             core logic to generate and return a single report section.

    @http_method POST
    @endpoint /api/final-analysis.mjs

    @json_body {
        "section_index": 0,
        "answers": { ... },
        "scores": { ... },
        "final_analysis_config": { ... }
    }

    @returns {Response} A JSON response with the generated 'report' section content on success,
                        or an error message object on failure.
                        
    @related_to py_final_analysis.py: This is the primary web entry point for its logic.
    """
    try:
        print("[handle_final_analysis] Attempting to parse JSON body...")
        data = request.get_json()
        print(f"[handle_final_analysis] Successfully parsed JSON. Received keys: {list(data.keys()) if data else 'No data'}")
        
        print("\n--- DEBUG: /api/final-analysis.mjs ---")
        print(f"Received request keys: {list(data.keys()) if data else 'No data received'}")
        print("---------------------------------------\n")

        if not data or 'section_index' not in data or 'answers' not in data or 'calculations' not in data:
            print(f"Validation failed: 'section_index', 'answers', or 'calculations' key is missing.")
            return jsonify({"message": "Missing required parameters for final analysis"}), 400

        config = load_app_config()
        # Use config to determine which question set to load. No fallback.
        question_set_file = config.get("Generic", {}).get("question_set_file")
        if not question_set_file:
            print("!!! CRITICAL: 'question_set_file' not found in app.config.json")
            return jsonify({"message": "Server configuration error: question_set_file not specified."}), 500
        
        load_question_set(question_set_file)

        result = final_analysis_logic(
            section_index=data['section_index'],
            answers=data['answers'],
            scores=data['calculations'], # Use 'calculations' from frontend as 'scores'
            final_analysis_config=data['final_analysis_config'],
            config=config
        )
        return jsonify(result)

    except Exception as e:
        print(f"[Flask Server] Error in /api/final-analysis: {e}")
        return jsonify({"message": "Internal Server Error"}), 500


@app.route('/api/test-web-search', methods=['POST'])
def handle_test_web_search():
    """
    @brief Тестовый endpoint для проверки веб-поиска
    """
    print("\n🔍 === TEST WEB SEARCH ENDPOINT CALLED ===")
    try:
        data = request.get_json()
        print(f"🔍 Received data: {data}")
        
        if not data or 'query' not in data:
            return jsonify({"message": "Missing 'query' in request body"}), 400

        query = data['query']
        config = load_app_config()
        
        print(f"🔍 Testing search query: '{query}'")
        print(f"🔍 Web search config enabled: {config.get('Backend', {}).get('web_search', {}).get('enabled', False)}")
        
        # Import here to avoid circular imports
        from src.backend.ai_providers_with_search import get_ai_provider_with_search
        
        # Create test messages that should trigger search
        test_messages = [
            {"role": "user", "content": query}
        ]
        
        print(f"🔍 Getting AI provider with search...")
        provider = get_ai_provider_with_search(config)
        
        print(f"🔍 Calling chat_completion with test messages...")
        
        # Get AI provider type and model from config
        backend_config = config.get("Backend", {})
        ai_provider_type = backend_config.get("ai_provider", "openai")
        
        if ai_provider_type == "ollama":
            provider_config = backend_config.get("ollama", {})
            model = provider_config.get("model")
            if not model:
                return jsonify({"message": "Ollama model not configured in app.config.json"}), 500
        else:
            provider_config = backend_config.get("openai", {})
            model = provider_config.get("model")
            if not model:
                return jsonify({"message": "OpenAI model not configured in app.config.json"}), 500
        
        print(f"🔍 Using model: {model}")
        
        response = provider.chat_completion(
            messages=test_messages,
            model=model,
            max_tokens=150,
            temperature=0.3
        )
        
        print(f"🔍 Response received: {response.get('content', '')[:200]}...")
        
        return jsonify({
            "success": True,
            "query": query,
            "response": response.get('content', ''),
            "message": "Web search test completed"
        })

    except Exception as e:
        print(f"🔍 ❌ Error in test web search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": f"Test web search error: {str(e)}"}), 500


@app.route('/api/direct-web-search', methods=['POST'])
def handle_direct_web_search():
    """
    @brief Прямой endpoint для тестирования веб-поиска без AI
    """
    print("\n🔍 === DIRECT WEB SEARCH ENDPOINT CALLED ===")
    try:
        data = request.get_json()
        print(f"🔍 Received data: {data}")
        
        if not data or 'query' not in data:
            return jsonify({"message": "Missing 'query' in request body"}), 400

        query = data['query']
        config = load_app_config()
        
        print(f"🔍 Direct search query: '{query}'")
        
        # Import here to avoid circular imports
        import asyncio
        from src.backend.ai_providers_with_search import search_web
        
        print(f"🔍 Starting direct web search...")
        
        # Run the async search function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(search_web(query, config))
            print(f"🔍 Direct search completed. Found {len(results)} results")
            
            # Convert results to JSON
            results_json = [result.to_dict() for result in results]
            
            return jsonify({
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": results_json[:5],  # Limit to first 5 for display
                "message": "Direct web search completed"
            })
        finally:
            loop.close()

    except Exception as e:
        print(f"🔍 ❌ Error in direct web search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": f"Direct web search error: {str(e)}"}), 500


if __name__ == '__main__':
    """
    @brief Main entry point for running the Flask development server.

    @details This block is executed only when the script is run directly from the command line
             (e.g., `python py_local_api_server.py`). It first prints the status of critical
             environment variables and then starts the Flask application on port 3001 with
             debug mode enabled. Debug mode provides useful features during development, such
             as automatic reloading when code changes are detected.
    """
    config = load_app_config()
    port = config.get("Backend", {}).get("local_api_port", 3001)

    print('===== Local Python API Server Environment =====')
    print('REACT_APP_GPT_KEY exists:', bool(os.getenv("REACT_APP_GPT_KEY")))
    print('REACT_APP_PROJECT_ID exists:', bool(os.getenv("REACT_APP_PROJECT_ID")))
    print(f'Attempting to start on port: {port}')
    print('===========================================')
    app.run(port=port, debug=True)