import os
import json
import time
import requests
from openai import RateLimitError, BadRequestError
from src.backend.ai_providers_with_search import get_ai_provider_with_search

# Define the absolute path to the project root.
# We go up two levels from `src/backend/` to reach the root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# --- Globals for caching ---
_question_set = {} # Cache for question set content

def load_question_set(set_id):
    """
    @brief Loads and caches a question set from a file.
    @description Reads the specified question set JSON file from the public/questions
    directory. It uses a global variable to cache the data, preventing
    repeated file reads. The path is constructed relative to the project
    root to ensure it works in both local and serverless environments.
    @param set_id The name of the question set JSON file (e.g., "q4.json").
    @return A dictionary containing the question set data.
    @related_to app.config.json: The filename is read from the app config.
    """
    global _question_set
    # Construct absolute path
    file_path = os.path.join(PROJECT_ROOT, 'public', 'questions', set_id)

    # Load file if not cached or if a different set_id is requested
    if not _question_set or _question_set.get('version') != set_id: # A simple check
        try:
            print(f"[Data] Loading question set from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                _question_set = json.load(f)
        except Exception as e:
            print(f"!!! CRITICAL: Could not load or parse question set {file_path}. Error: {e}")
            # Return empty data to prevent a hard crash
            _question_set = {"questions": []}

    return _question_set


def format_data_for_prompt(context_config, answers, scores):
    """
    @brief Formats answers and scores into a human-readable string for the AI prompt.

    @details Based on the `ai_context` configuration for a specific report section,
             this function gathers the required answers and scores. It then formats them
             into a clean, readable multi-line string suitable for injection into the
             main prompt sent to the OpenAI API.

    @param context_config (dict): The `ai_context` object from a section's configuration,
                                 specifying which data to include (e.g., `include_answers`,
                                 `include_scores`).
    @param answers (dict): All available user answers, keyed by question ID.
    @param scores (dict): All available AI-generated scores, keyed by question ID.

    @returns {str}: A formatted string containing the requested contextual data.
    """
    # NOTE: This is a simplified implementation. The original Node.js version has
    # more sophisticated logic for finding question text by ID and formatting.
    # This should be expanded to match that for full fidelity.
    
    formatted_string = "Context:\n"
    if context_config.get("include_answers", []) == ["all"]:
         for q_id, answer in answers.items():
              formatted_string += f"- {q_id}: {answer}\n"

    if context_config.get("include_scores"):
        for q_id, score in scores.items():
            formatted_string += f"- Score for {q_id}: {score}\n"
            
    return formatted_string


def final_analysis_logic(section_index, answers, scores, final_analysis_config, config):
    """
    @brief Generates a single section of the final analysis report using OpenAI.

    @details This is the core logic for the final report generation. It performs these steps:
             1. Selects the configuration for the specified `section_index` from the `final_analysis_config`.
             2. Formats all required contextual data (answers, scores) into a string.
             3. Constructs the final prompt by combining the `base_prompt`, the formatted context,
                and the `specific_prompt` for the section.
             4. Calls the OpenAI API using the model and parameters defined in the section's configuration.
             5. Implements a robust retry loop with exponential backoff to handle API rate limiting.

    @param section_index (int): The zero-based index of the report section to generate.
    @param answers (dict): All user answers.
    @param scores (dict): All AI-generated scores.
    @param final_analysis_config (dict): The complete configuration object for the final report
                                         from the question JSON file.
    @param config (dict): The global application configuration object from app.config.json.

    @returns {dict}: A dictionary containing the generated 'report' content as a string.

    @side_effects Makes one or more external API calls to OpenAI.

    @related_to py_local_api_server.py: This function is called by the `/api/final-analysis.mjs` endpoint.
    """
    section_config = final_analysis_config['sections'][section_index]
    base_prompt = final_analysis_config['base_prompt']
    specific_prompt = section_config['specific_prompt']
    
    # Format the context data (answers, scores) required for this section
    context_data_str = format_data_for_prompt(section_config['ai_context'], answers, scores)
    
    full_prompt = f"{base_prompt}\n\n{context_data_str}\n\n{specific_prompt}"

    # --- AI Provider API Call with Retry Logic ---
    provider = get_ai_provider_with_search(config)
    
    backend_config = config.get("Backend", {})
    ai_provider_type = backend_config.get("ai_provider", "openai")
    
    attempt = 0
    initial_delay = 1.0
    max_delay = 30.0

    while True:
        try:
            model_config_from_json = section_config.get('model_config', {})
            
            # Get provider-specific configuration
            if ai_provider_type == "ollama":
                provider_config = backend_config.get("ollama", {})
                model = model_config_from_json.get('model', provider_config.get('model'))
                if not model:
                    raise ValueError("Ollama model must be specified in configuration")
            else:
                provider_config = backend_config.get("openai", {})
                model = model_config_from_json.get('model', provider_config.get('model'))
                if not model:
                    raise ValueError("OpenAI model must be specified in configuration")

            temperature = model_config_from_json.get('temperature', provider_config.get('default_temperature', 0.3))
            max_tokens = model_config_from_json.get('max_output_tokens', provider_config.get('default_max_tokens', 1024))
            stream = model_config_from_json.get('stream', provider_config.get('stream', False))

            messages = [{"role": "user", "content": full_prompt}]

            print(f"\n--- DEBUG: {ai_provider_type.upper()} Request (Final Analysis) ---")
            print(json.dumps({
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": stream,
                "response_format": {"type": "json_object"}
            }, indent=2))
            print("----------------------------------------------\n")

            try:
                response_content = ""
                if stream:
                    # Handle streaming response by concatenating chunks
                    for chunk in provider.stream_chat_completion(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"}
                    ):
                        response_content += chunk
                else:
                    # Handle non-streaming response
                    response = provider.chat_completion(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"}
                    )
                    response_content = response['content']

                print(f"\n--- DEBUG: {ai_provider_type.upper()} Response (Final Analysis) ---")
                print(response_content)
                print("-----------------------------------------------\n")

                # Parse JSON response
                try:
                    result_json = json.loads(response_content)
                    return result_json
                except json.JSONDecodeError as je:
                    print(f"JSON parsing error: {je}")
                    print(f"Response content: {response_content}")
                    # Try to extract JSON from the response
                    import re
                    json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    else:
                        # Return error if JSON parsing fails
                        return {"error": f"Could not parse AI response. Raw response: {response_content[:200]}..."}

            except (BadRequestError, requests.exceptions.HTTPError) as e:
                print(f"!!! {ai_provider_type} BadRequestError: {e}")
                # This error often happens if the prompt is malformed or violates policy
                return {"error": f"{ai_provider_type} API request error: {e}"}
            except Exception as e:
                print(f"An unexpected error occurred during final analysis: {e}")
                return {"error": "An unexpected error occurred on the server."}

        except (RateLimitError, requests.exceptions.HTTPError) as e:
            attempt += 1
            
            # Handle rate limiting
            if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                retry_after_ms_str = e.response.headers.get('retry-after-ms')
                api_wait_time = float(retry_after_ms_str) / 1000.0 if retry_after_ms_str else 0
            else:
                api_wait_time = 0
            
            exponential_delay = initial_delay * (2 ** (attempt - 1))
            jitter = (0.5 - (int.from_bytes(os.urandom(1), 'big') / 255.0)) * 0.5 # Jitter [-0.25, 0.25]
            wait_time = min(exponential_delay + jitter, max_delay)
            
            final_wait = max(wait_time, api_wait_time)
            
            print(f"Rate limit exceeded on final analysis. Attempt {attempt}. Retrying in {final_wait:.2f} seconds...")
            time.sleep(final_wait)
        except Exception as e:
            print(f"An unexpected error occurred during final analysis: {e}")
            raise