import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# --- Import business logic from other modules ---
from py_simple_evaluate import evaluate_answer_logic
from py_final_analysis import final_analysis_logic, load_question_set

# --- App Initialization ---

# Load environment variables from a .env file into the environment
load_dotenv()

#: Flask application instance
app = Flask(__name__)
#: Enables Cross-Origin Resource Sharing for the Flask app, allowing the frontend to make requests.
CORS(app)

_app_config = None

def load_app_config():
    """
    @brief Loads the application configuration from public/app.config.json.
    @details Caches the config in a global variable to avoid repeated file reads.
    """
    global _app_config
    if _app_config is None:
        try:
            config_path = os.path.join(os.getcwd(), 'public', 'app.config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                _app_config = json.load(f)
        except Exception as e:
            print(f"CRITICAL: Could not load app.config.json. Error: {e}")
            # Fallback to an empty dict to prevent crashes, though functionality will be degraded.
            _app_config = {}
    return _app_config


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

        result = evaluate_answer_logic(question_id, all_answers, config)
        return jsonify(result)

    except ValueError as e:
        return jsonify({"message": str(e)}), 404
    except Exception as e:
        print(f"[Flask Server] Error in /api/simple-evaluate: {e}")
        return jsonify({"message": "Internal Server Error"}), 500


@app.route('/api/final-analysis.mjs', methods=['POST'])
def handle_final_analysis():
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
        data = request.get_json()
        print("\n--- DEBUG: /api/final-analysis.mjs ---")
        print(f"Received request keys: {list(data.keys()) if data else 'No data received'}")
        print("---------------------------------------\n")

        if not data or 'section_index' not in data or 'answers' not in data or 'calculations' not in data:
            print("Validation failed: 'section_index', 'answers', or 'calculations' key is missing.")
            return jsonify({"message": "Missing required parameters for final analysis"}), 400

        config = load_app_config()
        # Use config to determine which question set to load, with a fallback
        question_set_file = config.get("Generic", {}).get("question_set_file", "q4.json")
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
