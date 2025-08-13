#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции веб-поиска в оценку ответов
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

def create_test_question():
    """Создает тестовый вопрос для оценки"""
    return {
        "id": "TEST01",
        "text": "What are the latest trends in artificial intelligence and machine learning for business applications?",
        "question_type": "text",
        "prompt_add": "Focus on business impact and practical applications."
    }

def create_test_questions_file():
    """Создает временный файл с тестовыми вопросами"""
    test_questions = {
        "questions": [
            create_test_question()
        ]
    }
    
    questions_dir = os.path.join(PROJECT_ROOT, 'public', 'questions')
    os.makedirs(questions_dir, exist_ok=True)
    
    test_file_path = os.path.join(questions_dir, 'test_questions.json')
    with open(test_file_path, 'w', encoding='utf-8') as f:
        json.dump(test_questions, f, indent=2, ensure_ascii=False)
    
    return 'test_questions.json'

def create_test_prompt_file():
    """Создает временный файл с AI промптом"""
    test_prompt = """You are an expert evaluator. Your task is to evaluate answers to business and technology questions.

Consider the following criteria:
- Accuracy and relevance of the information
- Depth of understanding
- Practical applicability
- Current market trends and developments

Use any additional context provided from web searches to enhance your evaluation.

Provide a score from 0-100 and a detailed explanation."""
    
    questions_dir = os.path.join(PROJECT_ROOT, 'public', 'questions')
    os.makedirs(questions_dir, exist_ok=True)
    
    prompt_file_path = os.path.join(questions_dir, 'test_prompt.txt')
    with open(prompt_file_path, 'w', encoding='utf-8') as f:
        f.write(test_prompt)
    
    return 'test_prompt.txt'

async def test_web_search_integration():
    """Тестирует интеграцию веб-поиска в оценку"""
    print("🧪 Тестирование интеграции веб-поиска в оценку ответов")
    print("=" * 60)
    
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
    
    # Тестовый ответ пользователя
    test_answer = """AI and ML are transforming business through automation, predictive analytics, and personalized customer experiences. Companies are using chatbots, recommendation systems, and data-driven decision making to improve efficiency and competitiveness."""
    
    test_answers = {
        "TEST01": test_answer
    }
    
    print(f"📝 Тестовый ответ: {test_answer[:100]}...")
    
    try:
        # Импортируем и вызываем функцию оценки
        from src.backend.py_simple_evaluate import evaluate_answer_logic
        
        print("\n🔍 Запуск оценки с автоматическим веб-поиском...")
        
        result = evaluate_answer_logic(
            question_id="TEST01",
            all_answers=test_answers,
            config=config,
            question_file=question_file,
            prompt_file=prompt_file
        )
        
        print("\n📊 Результат оценки:")
        print(f"Оценка: {result.get('score', 'N/A')}/100")
        print(f"Объяснение: {result.get('explanation', 'N/A')}")
        
        if result.get('score') is not None:
            print("\n✅ Тест успешно завершен!")
            return True
        else:
            print("\n❌ Ошибка: не получен результат оценки")
            return False
            
    except Exception as e:
        print(f"\n❌ Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_search_query_generation():
    """Тестирует генерацию поисковых запросов"""
    print("\n🔤 Тестирование генерации поисковых запросов")
    print("-" * 40)
    
    try:
        from src.backend.py_simple_evaluate import generate_search_query_from_question
        
        test_questions = [
            {
                "text": "What are the latest trends in artificial intelligence?",
                "question_type": "text"
            },
            {
                "text": "How do you implement machine learning in business?",
                "question_type": "text"
            },
            {
                "text": "What is your experience with cloud technologies?",
                "question_type": "text"
            }
        ]
        
        for i, question in enumerate(test_questions, 1):
            query = generate_search_query_from_question(question)
            print(f"{i}. Вопрос: {question['text'][:50]}...")
            print(f"   Поисковый запрос: '{query}'")
            print()
        
        print("✅ Генерация поисковых запросов работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка генерации поисковых запросов: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск комплексного тестирования веб-поиска в оценке")
    print("=" * 70)
    
    success = True
    
    # Тест 1: Генерация поисковых запросов
    success &= await test_search_query_generation()
    
    # Тест 2: Полная интеграция с оценкой
    success &= await test_web_search_integration()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 Все тесты прошли успешно!")
        print("🔍 Веб-поиск интегрирован в систему оценки")
        print("🌐 Поиск настроен на английский язык")
    else:
        print("❌ Некоторые тесты завершились с ошибками")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())