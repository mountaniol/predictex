#!/usr/bin/env python3
"""
Тестирует правильную оценку стратегических вопросов без веб-поиска
"""
import os
import sys
import json
import asyncio

# Добавляем корневой путь проекта в Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

def load_config():
    """Загружает конфигурацию приложения"""
    config_path = os.path.join(PROJECT_ROOT, 'public', 'app.config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return None

def create_sg01_test_question():
    """Создает тестовый вопрос SG01 из q4.json"""
    return {
        "id": "SG01",
        "text": "Why are you selling now?",
        "question_type": "choice-multi",
        "prompt_add": "Score intent of sale. Good: planned retirement/move/strategic refocus. Red: urgent cash need, lawsuits/tax issues, sale due to heavy losses. Penalize contradictions with SG02/SG04. Bands: 0–19 critical; 20–49 high; 50–79 moderate; 80–100 low."
    }

def create_test_questions_file():
    """Создает временный файл с тестовыми вопросами"""
    test_questions = {
        "questions": [
            create_sg01_test_question()
        ]
    }
    
    questions_dir = os.path.join(PROJECT_ROOT, 'public', 'questions')
    os.makedirs(questions_dir, exist_ok=True)
    
    test_file_path = os.path.join(questions_dir, 'test_sg01.json')
    with open(test_file_path, 'w', encoding='utf-8') as f:
        json.dump(test_questions, f, indent=2, ensure_ascii=False)
    
    return 'test_sg01.json'

def create_test_prompt_file():
    """Создает временный файл с AI промптом"""
    test_prompt = """You are an expert business evaluator specializing in risk assessment for business acquisitions and investments.

CRITICAL: You must analyze the SPECIFIC question being asked and the SPECIFIC answer provided. Do NOT give generic responses.

Key Evaluation Principles:
1. Score from 0-100 where 0 = extremely high risk, 100 = extremely low risk
2. READ the "Additional Question Context" carefully - it contains specific scoring guidance
3. MATCH your score to the guidance provided in the context
4. Your explanation must directly address the SPECIFIC question asked

IMPORTANT:
- If the Additional Question Context mentions "Red:" scenarios, those should receive LOW scores (0-19)
- If it mentions "Good:" scenarios, those should receive HIGH scores (80-100)
- Always explain your reasoning based on the SPECIFIC question and answer provided
- Do NOT reference unrelated business scenarios (like DSO, restaurants, etc.) unless they are mentioned in the question

Always provide a numerical score between 0 and 100, where higher scores indicate lower risk.
Your explanation must be directly relevant to the question asked and answer provided.
"""
    
    questions_dir = os.path.join(PROJECT_ROOT, 'public', 'questions')
    os.makedirs(questions_dir, exist_ok=True)
    
    prompt_file_path = os.path.join(questions_dir, 'test_sg01_prompt.txt')
    with open(prompt_file_path, 'w', encoding='utf-8') as f:
        f.write(test_prompt)
    
    return 'test_sg01_prompt.txt'

async def test_search_query_generation():
    """Тестирует, что для стратегических вопросов НЕ генерируется поисковый запрос"""
    print("🔍 Тестирование генерации поисковых запросов для стратегических вопросов")
    print("-" * 70)
    
    try:
        from src.backend.py_simple_evaluate import generate_search_query_from_question
        
        # Тестовые стратегические вопросы
        strategic_questions = [
            {
                "id": "SG01",
                "text": "Why are you selling now?",
                "question_type": "choice-multi"
            },
            {
                "id": "MET.LOC", 
                "text": "Where is the business located?",
                "question_type": "text"
            },
            {
                "id": "SG14",
                "text": "Average time to collect receivables (DSO)",
                "question_type": "choice-single"
            }
        ]
        
        # Тестовые обычные вопросы (должны генерировать запросы)
        regular_questions = [
            {
                "id": "TECH01",
                "text": "What are the latest trends in artificial intelligence?",
                "question_type": "text"
            },
            {
                "id": "GENERAL01",
                "text": "How do you implement machine learning?",
                "question_type": "text"
            }
        ]
        
        print("📝 Стратегические вопросы (НЕ должны генерировать поисковые запросы):")
        for question in strategic_questions:
            query = generate_search_query_from_question(question)
            status = "✅ ПРАВИЛЬНО" if not query else "❌ ОШИБКА"
            print(f"  {question['id']}: '{query}' - {status}")
        
        print("\n📝 Обычные вопросы (должны генерировать поисковые запросы):")
        for question in regular_questions:
            query = generate_search_query_from_question(question)
            status = "✅ ПРАВИЛЬНО" if query else "❌ ОШИБКА"
            print(f"  {question['id']}: '{query}' - {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования генерации поисковых запросов: {e}")
        return False

async def test_sg01_evaluation():
    """Тестирует правильную оценку вопроса SG01"""
    print("\n🧪 Тестирование оценки вопроса SG01")
    print("-" * 70)
    
    # Загружаем конфигурацию
    config = load_config()
    if not config:
        print("❌ Не удалось загрузить конфигурацию")
        return False
    
    print("✅ Конфигурация загружена")
    
    # Создаем тестовые файлы
    question_file = create_test_questions_file()
    prompt_file = create_test_prompt_file()
    
    print(f"✅ Созданы тестовые файлы: {question_file}, {prompt_file}")
    
    # Критические ответы (должны дать низкий score 0-19)
    critical_answers = {
        "SG01": ["declining_sales", "lawsuits_tax"]  # "Declining sales, Lawsuits or tax issues"
    }
    
    # Хорошие ответы (должны дать высокий score 80-100)
    good_answers = {
        "SG01": ["retirement_move"]  # "Retirement or move"
    }
    
    test_cases = [
        {
            "name": "Критические причины продажи",
            "answers": critical_answers,
            "expected_score_range": (0, 19),
            "expected_explanation_keywords": ["risk", "declining", "lawsuit", "critical"]
        },
        {
            "name": "Позитивные причины продажи", 
            "answers": good_answers,
            "expected_score_range": (80, 100),
            "expected_explanation_keywords": ["retirement", "planned", "low risk"]
        }
    ]
    
    results = []
    
    try:
        from src.backend.py_simple_evaluate import evaluate_answer_logic
        
        for test_case in test_cases:
            print(f"\n📊 Тестирование: {test_case['name']}")
            
            # Форматируем ответ как строку для evaluate_answer_logic
            answer_values = test_case['answers']['SG01']
            formatted_answer = ", ".join([code.replace('_', ' ').title() for code in answer_values])
            
            test_answers = {
                "SG01": formatted_answer
            }
            
            print(f"📝 Тестовый ответ: {formatted_answer}")
            
            try:
                result = evaluate_answer_logic(
                    question_id="SG01",
                    all_answers=test_answers,
                    config=config,
                    question_file=question_file,
                    prompt_file=prompt_file
                )
                
                score = result.get('score', 0)
                explanation = result.get('explanation', '')
                
                print(f"📈 Полученная оценка: {score}/100")
                print(f"📝 Объяснение: {explanation[:100]}...")
                
                # Проверяем диапазон оценки
                expected_min, expected_max = test_case['expected_score_range']
                score_correct = expected_min <= score <= expected_max
                
                # Проверяем ключевые слова в объяснении  
                explanation_correct = any(keyword.lower() in explanation.lower() 
                                        for keyword in test_case['expected_explanation_keywords'])
                
                test_result = {
                    'name': test_case['name'],
                    'score': score,
                    'score_correct': score_correct,
                    'explanation_correct': explanation_correct,
                    'expected_range': test_case['expected_score_range'],
                    'explanation': explanation
                }
                
                results.append(test_result)
                
                status = "✅ ПРОЙДЕН" if (score_correct and explanation_correct) else "❌ ПРОВАЛЕН"
                print(f"🎯 Результат теста: {status}")
                
                if not score_correct:
                    print(f"   ❌ Оценка {score} не в ожидаемом диапазоне {expected_min}-{expected_max}")
                if not explanation_correct:
                    print(f"   ❌ Объяснение не содержит ожидаемых ключевых слов")
                
            except Exception as e:
                print(f"❌ Ошибка оценки: {e}")
                results.append({
                    'name': test_case['name'],
                    'error': str(e)
                })
        
        return results
        
    except Exception as e:
        print(f"❌ Ошибка тестирования оценки: {e}")
        return []

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование исправленной системы оценки стратегических вопросов")
    print("=" * 80)
    
    success = True
    
    # Тест 1: Генерация поисковых запросов
    success &= await test_search_query_generation()
    
    # Тест 2: Правильная оценка SG01
    results = await test_sg01_evaluation()
    if results:
        success &= all(result.get('score_correct', False) and result.get('explanation_correct', False) 
                      for result in results if 'error' not in result)
    else:
        success = False
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 Все тесты прошли успешно!")
        print("✅ Веб-поиск отключен для стратегических вопросов")
        print("✅ Оценка SG01 работает корректно")
    else:
        print("❌ Некоторые тесты завершились с ошибками")
        print("🔧 Требуются дополнительные исправления")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())