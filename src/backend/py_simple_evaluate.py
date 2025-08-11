import os
import json
import time
from openai import OpenAI, RateLimitError

# --- Globals ---

#: Caches the loaded question data to prevent redundant file I/O.
questions_data = None
#: Stores the content of the main AI prompt file.
ai_prompt = ''

def load_questions_data(question_file, prompt_file):
    """
    @brief Loads question data and AI prompt from the filesystem into global variables.
    
    @details This function is designed to be idempotent. It checks if the global `questions_data`
             variable is already populated. If so, it returns immediately to prevent redundant
             file I/O. It constructs absolute paths to `public/questions/q4.json` and
             `public/questions/ai-prompt.txt` relative to the project's root directory,
             reads their contents, and populates the corresponding global variables.
    
    @param question_file (str): The filename of the question set to load (e.g., 'q4.json').
    @param prompt_file (str): The filename of the AI prompt file to load (e.g., 'ai-prompt.txt').

    @globals_written questions_data: Populated with the parsed JSON from `q4.json`.
    @globals_written ai_prompt: Populated with the string content from `ai-prompt.txt`.
    
    @side_effects Reads from the filesystem. Modifies global variables `questions_data` and `ai_prompt`.
    
    @raises FileNotFoundError: If `q4.json` or `ai-prompt.txt` is not found at the expected paths.
    @raises json.JSONDecodeError: If the content of `q4.json` is not valid JSON.
    
    @related find_question_by_id: This function must be called before `find_question_by_id` can operate.
    """
    global questions_data, ai_prompt
    if questions_data:
        return

    try:
        # Construct path relative to the project root
        json_path = os.path.join(os.getcwd(), 'public', 'questions', question_file)
        with open(json_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)

        prompt_path = os.path.join(os.getcwd(), 'public', 'questions', prompt_file)
        with open(prompt_path, 'r', encoding='utf-8') as f:
            ai_prompt = f.read()

    except FileNotFoundError as e:
        print(f"Error: Required file not found - {e}")
        # In a production environment, you might want to handle this more gracefully
        # or ensure the server fails to start.
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from q4.json - {e}")
        raise

def find_question_by_id(question_id):
    """
    @brief Finds a question by its unique ID from the globally loaded question data.
    
    @details It searches through the `questions` list within the global `questions_data` dictionary.
             This function assumes that all questions, including those prefixed with "MET.", are
             located in this single flat list.
    
    @param question_id (str): The unique identifier for the question (e.g., "SG01", "MET.LOC").
    
    @globals_read questions_data: Requires this global to be populated by `load_questions_data`.
    
    @returns {dict|None}: The question object (as a dictionary) if found, otherwise `None`.
    
    @related load_questions_data: Depends on `load_questions_data` to have been called successfully.
    """
    if not questions_data or 'questions' not in questions_data:
        return None
    return next((q for q in questions_data['questions'] if q['id'] == question_id), None)

def get_readable_answer(question, answer_value):
    """
    @brief Converts an answer's internal code or value into a human-readable string for the AI prompt.
    
    @details This function enhances the raw answer data before sending it to the AI. For answers
             that come from a predefined set of options (e.g., 'yes-no', 'choice-single'), it
             looks up the corresponding 'label' from the question's 'options' list. For other
             types (like free text), it returns the value as is.
    
    @param question (dict): The question object, which contains metadata like `question_type` and `options`.
    @param answer_value: The raw answer value stored in the application's state.
    
    @returns {str}: The human-readable version of the answer, suitable for inclusion in a prompt.
    """
    if not question or answer_value is None or answer_value == '':
        return answer_value
        
    q_type = question.get('question_type')
    options = question.get('options')

    if q_type == 'yes-no':
        return 'Yes' if answer_value == 'yes' else 'No'
    
    if isinstance(answer_value, list) and options:
        labels = [opt['label'] for opt in options if opt['code'] in answer_value]
        return ', '.join(labels)

    if options:
        for option in options:
            if option['code'] == answer_value:
                return option['label']
    
    return answer_value


def evaluate_answer_logic(question_id, all_answers, config):
    """
    @brief Handles the core logic for evaluating a single answer using the OpenAI API.
    
    @details This is the main business logic function for this module. It orchestrates several steps:
             1. Ensures question data is loaded.
             2. Finds the specific question to be evaluated.
             3. Constructs a detailed, context-rich prompt by combining the base AI instructions,
                the specific question's context, and any dependent answers as specified in the
                question's `ai_context`.
             4. Sends this prompt to the OpenAI Chat Completions API.
             5. Implements a robust retry mechanism with exponential backoff to handle API rate limits
                gracefully, ensuring the request eventually succeeds without failing immediately.
    
    @param question_id (str): The ID of the question being evaluated.
    @param all_answers (dict): A dictionary of all user-provided answers, used to fetch context.
    @param config (dict): The application configuration object.
    
    @returns {dict}: A dictionary containing the 'score' and 'explanation' from the AI's JSON response.
    
    @raises ValueError: If the question with the given ID is not found in the loaded data.
    @raises Exception: For non-rate-limit related API errors after exhausting retries.
    
    @side_effects Makes one or more external API calls to OpenAI.
    
    @related_to py_local_api_server.py: This is the primary web entry point for its logic.
    """
    question_file = config.get("Generic", {}).get("question_set_file", "q4.json")
    prompt_file = config.get("Generic", {}).get("ai_prompt_file", "ai-prompt.txt")
    load_questions_data(question_file, prompt_file)
    question = find_question_by_id(question_id)

    if not question:
        raise ValueError(f"Question with ID {question_id} not found.")

    # --- Prompt Construction ---
    payload = {
        'system': ai_prompt,
        'additional_context': question.get('prompt_add', ''),
        'meta': {},
        'question': {'id': question['id'], 'text': question['text']},
        'answer': get_readable_answer(question, all_answers.get(question_id)),
        'answers_ctx': {}
    }

    ai_context = question.get('ai_context', {})
    if ai_context.get('include_meta'):
        for meta_id in ai_context['include_meta']:
            meta_question = find_question_by_id(meta_id)
            if meta_question and all_answers.get(meta_id):
                payload['meta'][meta_question['text']] = get_readable_answer(meta_question, all_answers[meta_id])

    if ai_context.get('include_answers'):
        for answer_id in ai_context['include_answers']:
            ctx_question = find_question_by_id(answer_id)
            if ctx_question and all_answers.get(answer_id):
                payload['answers_ctx'][ctx_question['text']] = get_readable_answer(ctx_question, all_answers[answer_id])

    # Build a string representation for the final prompt
    meta_str = '\n'.join([f"- {k}: {v}" for k, v in payload['meta'].items()])
    ctx_str = '\n'.join([f"- {k}: {v}" for k, v in payload['answers_ctx'].items()])
    
    full_prompt = f"""
Based on the following context, please evaluate the provided answer.

System Instructions:
{payload['system']}

Additional Question Context:
{payload['additional_context']}

Business Meta-Information:
{meta_str}

Dependent Answers Context:
{ctx_str}

Question:
{payload['question']['text']}

User's Answer:
{payload['answer']}

Return ONLY a single JSON object with 'score' (0-100) and 'explanation' (string) keys.
"""

    # --- OpenAI API Call with Retry Logic ---
    client = OpenAI(api_key=os.getenv("REACT_APP_GPT_KEY"), project=os.getenv("REACT_APP_PROJECT_ID"))
    
    openai_config = config.get("Backend", {}).get("openai", {})
    model = openai_config.get("simple_evaluate_model", "gpt-4-1106-preview")
    temperature = openai_config.get("default_temperature", 0.3)
    max_tokens = openai_config.get("default_max_tokens", 1024)

    attempt = 0
    initial_delay = 1.0  # seconds
    max_delay = 30.0     # seconds

    while True:
        try:
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": payload['system']},
                    {"role": "user", "content": full_prompt}
                ],
                model=model,
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )
            response_content = completion.choices[0].message.content
            return json.loads(response_content)

        except RateLimitError as e:
            attempt += 1
            
            # Extract retry-after-ms header if available
            retry_after_ms_str = e.response.headers.get('retry-after-ms')
            api_wait_time = float(retry_after_ms_str) / 1000.0 if retry_after_ms_str else 0
            
            # Calculate exponential backoff with jitter to prevent thundering herd
            exponential_delay = initial_delay * (2 ** (attempt - 1))
            jitter = (0.5 - (int.from_bytes(os.urandom(1), 'big') / 255.0)) * 0.5 # Jitter [-0.25, 0.25]
            wait_time = min(exponential_delay + jitter, max_delay)
            
            # Use the longer of the two delays (API suggestion vs our backoff)
            final_wait = max(wait_time, api_wait_time)
            
            print(f"Rate limit exceeded. Attempt {attempt}. Retrying in {final_wait:.2f} seconds...")
            time.sleep(final_wait)
        except Exception as e:
            print(f"An unexpected error occurred with OpenAI API: {e}")
            raise
