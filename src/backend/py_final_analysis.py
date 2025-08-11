import os
import json
import time
from openai import OpenAI, RateLimitError, BadRequestError

# --- Globals ---

#: A simple in-memory cache for loaded question set JSON data.
#: The keys are the `set_id` (e.g., 'q4') and values are the parsed dicts.
_question_data_cache = {}

def load_question_set(set_id):
    """
    @brief Loads a specific question set from the filesystem into a cache.

    @details This function reads the specified JSON file that defines the questions and
             final analysis structure (e.g., 'q4.json') from the `public/questions`
             directory. It uses an in-memory dictionary `_question_data_cache` to
             prevent re-reading the same file multiple times during the application's
             lifecycle, improving performance.

    @param set_id (str): The identifier for the question set, corresponding to the
                        filename (e.g., 'q4.json').

    @globals_written _question_data_cache: Caches the parsed JSON data on first load for a given `set_id`.

    @returns {dict}: The parsed JSON data for the requested question set as a dictionary.
    
    @raises FileNotFoundError: If the JSON file corresponding to the `set_id` does not exist.
    """
    if set_id in _question_data_cache:
        return _question_data_cache[set_id]

    try:
        file_path = os.path.join(os.getcwd(), 'public', 'questions', set_id)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _question_data_cache[set_id] = data
            return data
    except FileNotFoundError:
        print(f"Error: Question set file not found for id: {set_id}")
        raise


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

    # --- OpenAI API Call with Retry Logic ---
    client = OpenAI(api_key=os.getenv("REACT_APP_GPT_KEY"), project=os.getenv("REACT_APP_PROJECT_ID"))
    
    attempt = 0
    initial_delay = 1.0
    max_delay = 30.0

    while True:
        try:
            model_config_from_json = section_config.get('model_config', {})
            openai_config_from_app = config.get("Backend", {}).get("openai", {})

            model = model_config_from_json.get('model', 'gpt-4o')
            temperature = model_config_from_json.get('temperature', openai_config_from_app.get('default_temperature', 0.3))
            max_tokens = model_config_from_json.get('max_output_tokens', openai_config_from_app.get('default_max_tokens', 1024))
            stream = model_config_from_json.get('stream', False)

            request_payload = {
                "model": model,
                "messages": [{"role": "user", "content": full_prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": stream,
                "response_format": {"type": "json_object"}
            }

            print("\n--- DEBUG: OpenAI Request Payload ---")
            print(json.dumps(request_payload, indent=2))
            print("-------------------------------------\n")

            try:
                completion = client.chat.completions.create(**request_payload)

                response_content = ""
                if stream:
                    # Handle streaming response by concatenating chunks
                    # The streaming response sends parts of the JSON object. We need to
                    # accumulate them all to form a complete, valid JSON string.
                    for chunk in completion:
                        content = chunk.choices[0].delta.content
                        if content:
                            response_content += content
                else:
                    # Handle non-streaming response (the whole object comes at once)
                    response_content = completion.choices[0].message.content

                print("\n--- DEBUG: OpenAI Response Content ---")
                print(response_content)
                print("--------------------------------------\n")

                # The rest of the logic expects a JSON object string
                result_json = json.loads(response_content)
                
                return result_json

            except BadRequestError as e:
                print(f"!!! OpenAI BadRequestError: {e}")
                # This error often happens if the prompt is malformed or violates policy
                return {"error": f"OpenAI API request error: {e}"}
            except Exception as e:
                print(f"An unexpected error occurred during final analysis: {e}")
                return {"error": "An unexpected error occurred on the server."}

        except RateLimitError as e:
            attempt += 1
            retry_after_ms_str = e.response.headers.get('retry-after-ms')
            api_wait_time = float(retry_after_ms_str) / 1000.0 if retry_after_ms_str else 0
            
            exponential_delay = initial_delay * (2 ** (attempt - 1))
            jitter = (0.5 - (int.from_bytes(os.urandom(1), 'big') / 255.0)) * 0.5 # Jitter [-0.25, 0.25]
            wait_time = min(exponential_delay + jitter, max_delay)
            
            final_wait = max(wait_time, api_wait_time)
            
            print(f"Rate limit exceeded on final analysis. Attempt {attempt}. Retrying in {final_wait:.2f} seconds...")
            time.sleep(final_wait)
        except Exception as e:
            print(f"An unexpected error occurred during final analysis: {e}")
            raise
