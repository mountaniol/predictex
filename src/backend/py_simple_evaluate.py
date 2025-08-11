import os
import json
import time
from openai import OpenAI, RateLimitError

# Define the absolute path to the project root. This is robust for both local and Vercel execution.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# --- Globals for caching ---
_questions_data = {} # Cache for question file content
#: Stores the content of the main AI prompt file.
_ai_prompt = ''

def load_questions_data(question_file="q4.json", prompt_file="ai-prompt.txt"):
    """
    @brief Loads and caches question and prompt data from files.
    @description Reads the specified question JSON and AI prompt text file. It uses
    global variables to cache the data, preventing repeated file reads.
    The paths are constructed relative to the project root to ensure they work
    in both local and serverless environments.
    @param question_file The name of the question set JSON file (e.g., "q4.json").
    @param prompt_file The name of the AI prompt file (e.g., "ai-prompt.txt").
    @return A tuple containing the loaded questions data (dict) and AI prompt (str).
    @related_to app.config.json: The filenames are read from the app config.
    """
    global _questions_data, _ai_prompt

    # Construct absolute paths
    questions_path = os.path.join(PROJECT_ROOT, 'public', 'questions', question_file)
    prompt_path = os.path.join(PROJECT_ROOT, 'public', 'questions', prompt_file)

    # Load questions file if not cached
    if not _questions_data:
        try:
            print(f"[Data] Loading questions from: {questions_path}")
            with open(questions_path, 'r', encoding='utf-8') as f:
                _questions_data = json.load(f)
        except Exception as e:
            print(f"!!! CRITICAL: Could not load or parse question file {questions_path}. Error: {e}")
            # Return empty data to prevent a hard crash
            _questions_data = {"questions": []}

    # Load AI prompt file if not cached
    if not _ai_prompt:
        try:
            print(f"[Data] Loading AI prompt from: {prompt_path}")
            with open(prompt_path, 'r', encoding='utf-8') as f:
                _ai_prompt = f.read()
        except Exception as e:
            print(f"!!! CRITICAL: Could not load AI prompt file {prompt_path}. Error: {e}")
            _ai_prompt = "No prompt loaded."

    return _questions_data, _ai_prompt

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
    if not _questions_data or 'questions' not in _questions_data:
        return None
    return next((q for q in _questions_data['questions'] if q['id'] == question_id), None)

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
        'system': _ai_prompt,
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
