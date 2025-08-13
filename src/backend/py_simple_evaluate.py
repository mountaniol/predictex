import os
import json
import time
import requests
from openai import RateLimitError
from src.backend.ai_providers_with_search import get_ai_provider_with_search

# Define the absolute path to the project root.
# We go up two levels from `src/backend/` to reach the root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# --- Globals for caching ---
_questions_data = {} # Cache for question file content
#: Stores the content of the main AI prompt file.
_ai_prompt = ''

def clear_cache():
    """Clear all cached data to force reload from files."""
    global _questions_data, _ai_prompt
    _questions_data = {}
    _ai_prompt = ''
    print("[DEBUG] Cache cleared - will reload from files")

def load_questions_data(question_file, prompt_file):
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

def get_readable_answer(question, answer_value, all_answers=None):
    """
    @brief Converts an answer's internal code or value into a human-readable string for the AI prompt.
    
    @details This function enhances the raw answer data before sending it to the AI. For answers
             that come from a predefined set of options (e.g., 'yes-no', 'choice-single'), it
             looks up the corresponding 'label' from the question's 'options' list. For other
             types (like free text), it returns the value as is.
             
             For questions with "other" option and follow-up text fields, it combines the
             "Other" label with the content of the associated text field.
    
    @param question (dict): The question object, which contains metadata like `question_type` and `options`.
    @param answer_value: The raw answer value stored in the application's state.
    @param all_answers (dict): Dictionary of all answers, used to look up "other" text fields.
    
    @returns {str}: The human-readable version of the answer, suitable for inclusion in a prompt.
    """
    if not question or answer_value is None or answer_value == '':
        return answer_value
        
    q_type = question.get('question_type')
    options = question.get('options')

    if q_type == 'yes-no':
        return 'Yes' if answer_value == 'yes' else 'No'
    
    if isinstance(answer_value, list) and options:
        labels = []
        for code in answer_value:
            # Handle "other" option in multi-select
            if code == 'other':
                other_text_id = question.get('other_text_id')
                if other_text_id and all_answers and all_answers.get(other_text_id):
                    labels.append(f"Other: {all_answers.get(other_text_id)}")
                else:
                    labels.append('Other')
            else:
                # Find the label for this code
                for opt in options:
                    if opt['code'] == code:
                        labels.append(opt['label'])
                        break
        return ', '.join(labels)

    if options:
        for option in options:
            if option['code'] == answer_value:
                # Handle "other" option in single-select
                if answer_value == 'other':
                    other_text_id = question.get('other_text_id')
                    if other_text_id and all_answers and all_answers.get(other_text_id):
                        return f"Other: {all_answers.get(other_text_id)}"
                    else:
                        return option['label']
                return option['label']
    
    return answer_value


async def perform_web_search_for_question(question, config):
    """
    Выполняет веб-поиск для получения дополнительного контекста по вопросу
    """
    try:
        from .ai_providers_with_search import search_web
        from .search_models import SearchQuery
        
        # Формируем поисковый запрос на английском языке
        search_query = generate_search_query_from_question(question)
        
        if not search_query:
            print(f"🔍 No search query generated for question: {question.get('text', '')[:50]}...")
            return ""
        
        print(f"🔍 Performing web search for question evaluation: '{search_query}'")
        
        # Выполняем поиск
        results = await search_web(search_query, config)
        
        if not results:
            print(f"🔍 No search results found for query: {search_query}")
            return ""
        
        print(f"🔍 Found {len(results)} search results for question evaluation")
        
        # Форматируем результаты для включения в контекст
        search_context = format_search_results_for_evaluation(results[:3])  # Используем только первые 3 результата
        
        return search_context
        
    except Exception as e:
        print(f"🔍 ❌ Web search error during question evaluation: {e}")
        return ""


def generate_search_query_from_question(question):
    """
    Генерирует поисковый запрос на английском языке на основе вопроса
    """
    question_text = question.get('text', '')
    question_type = question.get('question_type', '')
    question_id = question.get('id', '')
    
    if not question_text:
        return ""
    
    # ВАЖНО: НЕ выполняем веб-поиск для стратегических/оценочных вопросов из q4.json
    # Эти вопросы требуют анализа предоставленных данных, а не внешней информации
    strategic_question_prefixes = ['SG', 'MET.', 'SGA']
    for prefix in strategic_question_prefixes:
        if question_id.startswith(prefix):
            print(f"🔍 Skipping web search for strategic/evaluation question: {question_id}")
            return ""
    
    # Также пропускаем вопросы, которые явно про оценку бизнеса
    business_evaluation_keywords = [
        'selling', 'buyers', 'revenue', 'margin', 'customer', 'contract', 'backlog',
        'debt', 'tax', 'lawsuit', 'owner', 'employee', 'equipment', 'lease',
        'insurance', 'license', 'permit', 'violation', 'investigation'
    ]
    
    for keyword in business_evaluation_keywords:
        if keyword in question_text.lower():
            print(f"🔍 Skipping web search for business evaluation question containing '{keyword}': {question_text[:50]}...")
            return ""
    
    # Базовые ключевые слова для извлечения темы
    import re
    
    # Удаляем общие фразы и фокусируемся на ключевых концепциях
    cleaned_text = question_text
    
    # Паттерны для извлечения ключевых концепций
    key_concepts = []
    
    # Извлекаем технические термины, бренды, концепции
    tech_patterns = [
        r'\b(AI|artificial intelligence|machine learning|ML|deep learning|neural networks?|python|javascript|react|vue|angular|nodejs?|database|sql|nosql|cloud|aws|azure|gcp|docker|kubernetes|blockchain|cryptocurrency|bitcoin|ethereum)\b',
        r'\b(digital transformation|cybersecurity|data science|big data|analytics|business intelligence|automation|robotics|IoT|internet of things)\b',
        r'\b(marketing|sales|strategy|management|leadership|project management|agile|scrum|devops|CI/CD)\b',
        r'\b(startup|enterprise|SME|B2B|B2C|SaaS|platform|API|integration|scalability|performance)\b'
    ]
    
    for pattern in tech_patterns:
        matches = re.findall(pattern, question_text, re.IGNORECASE)
        key_concepts.extend(matches)
    
    # Если нашли технические термины, используем их
    if key_concepts:
        search_query = f"latest trends {' '.join(key_concepts[:3])} industry best practices"
        return search_query
    
    # Иначе, создаем общий запрос на основе типа вопроса
    if 'technology' in question_text.lower() or 'tech' in question_text.lower():
        return "latest technology trends industry best practices"
    elif 'market' in question_text.lower() or 'industry' in question_text.lower():
        return "market analysis industry trends current developments"
    elif 'experience' in question_text.lower() or 'skill' in question_text.lower():
        return "professional development skills industry standards"
    else:
        # Для общих вопросов
        words = re.findall(r'\b[a-zA-Z]{4,}\b', question_text)
        if len(words) >= 2:
            return f"{' '.join(words[:3])} industry trends best practices"
    
    return ""


def format_search_results_for_evaluation(results):
    """
    Форматирует результаты поиска для включения в контекст оценки
    """
    if not results:
        return ""
    
    formatted = "📚 Additional Context from Web Search:\n\n"
    
    for i, result in enumerate(results, 1):
        formatted += f"{i}. **{result.title}**\n"
        formatted += f"   Source: {result.source}\n"
        if result.url:
            formatted += f"   URL: {result.url}\n"
        formatted += f"   Content: {result.content[:300]}{'...' if len(result.content) > 300 else ''}\n\n"
    
    formatted += "---\n\n"
    return formatted


def evaluate_answer_logic(question_id, all_answers, config, question_file, prompt_file):
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
    # Clear cache to ensure fresh AI prompt is loaded
    clear_cache()
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
        'answer': get_readable_answer(question, all_answers.get(question_id), all_answers),
        'answers_ctx': {}
    }

    ai_context = question.get('ai_context', {})
    if ai_context.get('include_meta'):
        for meta_id in ai_context['include_meta']:
            meta_question = find_question_by_id(meta_id)
            if meta_question and all_answers.get(meta_id):
                payload['meta'][meta_question['text']] = get_readable_answer(meta_question, all_answers[meta_id], all_answers)

    if ai_context.get('include_answers'):
        for answer_id in ai_context['include_answers']:
            ctx_question = find_question_by_id(answer_id)
            if ctx_question and all_answers.get(answer_id):
                payload['answers_ctx'][ctx_question['text']] = get_readable_answer(ctx_question, all_answers[answer_id], all_answers)

    # Perform web search for additional context (автоматический поиск для улучшения оценки)
    web_search_context = ""
    try:
        import asyncio
        
        # Проверяем, есть ли уже запущенный event loop
        try:
            # Если event loop уже запущен, создаем новый поток
            loop = asyncio.get_running_loop()
            # Используем run_in_executor для запуска в отдельном потоке
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, perform_web_search_for_question(question, config))
                web_search_context = future.result(timeout=30)
        except RuntimeError:
            # Если event loop не запущен, используем обычный asyncio.run
            web_search_context = asyncio.run(perform_web_search_for_question(question, config))
            
    except Exception as e:
        print(f"🔍 ❌ Web search failed during evaluation: {e}")
        web_search_context = ""

    # Build a string representation for the final prompt
    meta_str = '\n'.join([f"- {k}: {v}" for k, v in payload['meta'].items()])
    ctx_str = '\n'.join([f"- {k}: {v}" for k, v in payload['answers_ctx'].items()])
    
    full_prompt = f"""
Based on the following context, please evaluate the provided answer.

System Instructions:
{payload['system']}

Additional Question Context:
{payload['additional_context']}

{web_search_context}

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

    # --- AI Provider API Call with Retry Logic ---
    provider = get_ai_provider_with_search(config)
    
    backend_config = config.get("Backend", {})
    ai_provider_type = backend_config.get("ai_provider", "openai")
    
    # Get provider-specific configuration
    if ai_provider_type == "ollama":
        provider_config = backend_config.get("ollama", {})
        model = provider_config.get("model")
        if not model:
            raise ValueError("Ollama model must be specified in configuration")
    else:
        provider_config = backend_config.get("openai", {})
        model = provider_config.get("simple_evaluate_model")
        if not model:
            raise ValueError("OpenAI simple_evaluate_model must be specified in configuration")
    
    temperature = provider_config.get("default_temperature", 0.3)
    max_tokens = provider_config.get("default_max_tokens", 1024)

    attempt = 0
    initial_delay = 1.0  # seconds
    max_delay = 30.0     # seconds

    while True:
        try:
            messages=[
                {"role": "system", "content": payload['system']},
                {"role": "user", "content": full_prompt}
            ]
            print(f"\n--- DEBUG: {ai_provider_type.upper()} Request (Simple Evaluate) ---")
            print(json.dumps({"model": model, "messages": messages}, indent=2))
            print("-----------------------------------------------")
            print(f"\n🔍 PROMPT_ADD DEBUG: Question prompt_add = '{question.get('prompt_add', 'NONE')}'")
            print(f"🔍 FULL PROMPT DEBUG: User message content:\n{messages[1]['content']}")
            print("-----------------------------------------------\n")

            response = provider.chat_completion(
                messages=messages,
                model=model,
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            response_content = response['content']
            print(f"\n--- DEBUG: {ai_provider_type.upper()} Response (Simple Evaluate) ---")
            print(response_content)
            print("------------------------------------------------\n")
            
            # Parse JSON response
            try:
                return json.loads(response_content)
            except json.JSONDecodeError as je:
                print(f"JSON parsing error: {je}")
                print(f"Response content: {response_content}")
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    # Return a default response if JSON parsing fails
                    return {
                        "score": 50,
                        "explanation": f"Could not parse AI response. Raw response: {response_content[:200]}..."
                    }

        except (RateLimitError, requests.exceptions.HTTPError) as e:
            attempt += 1
            
            # Handle rate limiting
            if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                retry_after_ms_str = e.response.headers.get('retry-after-ms')
                api_wait_time = float(retry_after_ms_str) / 1000.0 if retry_after_ms_str else 0
            else:
                api_wait_time = 0
            
            # Calculate exponential backoff with jitter to prevent thundering herd
            exponential_delay = initial_delay * (2 ** (attempt - 1))
            jitter = (0.5 - (int.from_bytes(os.urandom(1), 'big') / 255.0)) * 0.5 # Jitter [-0.25, 0.25]
            wait_time = min(exponential_delay + jitter, max_delay)
            
            # Use the longer of the two delays (API suggestion vs our backoff)
            final_wait = max(wait_time, api_wait_time)
            
            print(f"Rate limit exceeded. Attempt {attempt}. Retrying in {final_wait:.2f} seconds...")
            time.sleep(final_wait)
        except Exception as e:
            print(f"An unexpected error occurred with {ai_provider_type} API: {e}")
            raise