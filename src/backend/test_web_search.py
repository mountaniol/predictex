#!/usr/bin/env python3
"""
Тестирование системы веб-поиска
"""
import asyncio
import json
import os
import sys
from typing import Dict, Any

# Добавляем корневую директорию в путь для импортов
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.backend.search_router import SearchRouter
from src.backend.query_classifier import QueryClassifier
from src.backend.ai_providers_with_search import get_ai_provider_with_search, search_web


def load_config() -> Dict[str, Any]:
    """Загрузить конфигурацию"""
    config_path = os.path.join(PROJECT_ROOT, 'public', 'app.config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def test_query_classifier():
    """Тест классификатора запросов"""
    print("=== Тестирование QueryClassifier ===")
    
    config = load_config()
    classifier = QueryClassifier(config.get('Backend', {}).get('web_search', {}).get('classification', {}))
    
    test_queries = [
        "Что такое нейронные сети?",  # factual
        "Последние новости в мире технологий",  # current
        "Найди информацию о Python",  # general
        "Какие события произошли сегодня?",  # current
        "Определение машинного обучения",  # factual
    ]
    
    for query_text in test_queries:
        from src.backend.search_models import SearchQuery
        query = SearchQuery(text=query_text)
        classification = classifier.classify(query)
        
        print(f"Запрос: '{query_text}'")
        print(f"  Тип: {classification['primary_type']}")
        print(f"  Уверенность: {classification['confidence']:.2f}")
        print(f"  Рекомендуемые провайдеры: {classification['suggested_providers']}")
        print(f"  Обоснование: {classification['reasoning']}")
        print()


async def test_search_providers():
    """Тест поисковых провайдеров"""
    print("=== Тестирование поисковых провайдеров ===")
    
    config = load_config()
    web_search_config = config.get('Backend', {}).get('web_search', {})
    
    if not web_search_config.get('enabled', False):
        print("⚠️  Веб-поиск отключен в конфигурации")
        return
    
    search_router = SearchRouter(web_search_config)
    
    # Проверяем статус провайдеров
    print("Статус провайдеров:")
    provider_status = await search_router.get_provider_status()
    for name, status in provider_status.items():
        available = "✅" if status['available'] else "❌"
        print(f"  {name}: {available}")
    
    # Тестируем поиск
    test_queries = [
        "Python programming",  # для DuckDuckGo
        "Искусственный интеллект",  # для Wikipedia
        "технологии",  # для RSS
    ]
    
    for query_text in test_queries:
        print(f"\nПоиск: '{query_text}'")
        try:
            from src.backend.search_models import SearchQuery
            query = SearchQuery(text=query_text, max_results=3)
            response = await search_router.search(query)
            print(f"  Найдено результатов: {len(response.results)}")
            print(f"  Время поиска: {response.search_time:.2f}s")
            print(f"  Использованы источники: {response.sources_used}")
            print(f"  Кэш: {'попадание' if response.cache_hit else 'промах'}")
            
            for i, result in enumerate(response.results[:2], 1):
                print(f"    {i}. {result.title[:50]}...")
                print(f"       Источник: {result.source} (оценка: {result.score:.2f})")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
        
        print()


async def test_ai_integration():
    """Тест интеграции с AI провайдерами"""
    print("=== Тестирование интеграции с AI ===")
    
    config = load_config()
    backend_config = config.get('Backend', {})
    
    try:
        # Получаем AI провайдер с поддержкой веб-поиска
        ai_provider = get_ai_provider_with_search(config)
        
        # Определяем модель из конфигурации
        ai_provider_type = backend_config.get("ai_provider", "openai")
        if ai_provider_type == "ollama":
            provider_config = backend_config.get("ollama", {})
            model = provider_config.get("model")
            if not model:
                print("  ⚠️ Модель Ollama не указана в конфигурации, тест пропускается")
                return
        else:
            provider_config = backend_config.get("openai", {})
            model = provider_config.get("model")
            if not model:
                model = provider_config.get("simple_evaluate_model")
            if not model:
                print("  ⚠️ Модель OpenAI не указана в конфигурации, тест пропускается")
                return
                
        print(f"  ℹ️ Используется модель: {model}")
        
        test_messages = [
            # Запрос, который должен вызвать поиск
            [
                {"role": "user", "content": "Найди последние новости о разработке ИИ"}
            ],
            # Фактический запрос
            [
                {"role": "user", "content": "Что такое большие языковые модели?"}
            ],
            # Обычный запрос без поиска
            [
                {"role": "user", "content": "Привет, как дела?"}
            ]
        ]
        
        for i, messages in enumerate(test_messages, 1):
            print(f"Тест {i}: {messages[0]['content']}")
            try:
                # Тест обычного completion с явным указанием модели
                response = ai_provider.chat_completion(
                    messages=messages,
                    model=model,
                    max_tokens=150,
                    temperature=0.3
                )
                print(f"  ✅ Ответ получен (длина: {len(response['content'])} символов)")
                
                # Показываем первые 100 символов ответа
                preview = response['content'][:100] + "..." if len(response['content']) > 100 else response['content']
                print(f"  Превью: {preview}")
                
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
            
            print()
            
    except Exception as e:
        print(f"❌ Ошибка инициализации AI провайдера: {e}")


async def test_web_search_utility():
    """Тест утилитарной функции веб-поиска"""
    print("=== Тестирование утилитарной функции веб-поиска ===")
    
    config = load_config()
    
    try:
        # Создаем новый event loop для этого теста
        results = await search_web("машинное обучение", config)
        print(f"Найдено результатов: {len(results)}")
        
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result.title}")
            print(f"     Источник: {result.source}")
            print(f"     URL: {result.url}")
            print()
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


async def test_health_check():
    """Проверка состояния системы"""
    print("=== Проверка состояния системы ===")
    
    config = load_config()
    web_search_config = config.get('Backend', {}).get('web_search', {})
    
    if not web_search_config.get('enabled', False):
        print("⚠️  Веб-поиск отключен в конфигурации")
        return
    
    search_router = SearchRouter(web_search_config)
    
    try:
        health = await search_router.health_check()
        print(f"Статус системы: {health['status']}")
        print(f"Стратегия: {health['strategy']}")
        print(f"Включено: {health['enabled']}")
        
        print("\nПровайдеры:")
        for name, info in health['providers'].items():
            status = "✅" if info['available'] else "❌"
            print(f"  {name}: {status}")
            
        print(f"\nКлассификатор:")
        classifier_info = health['classifier']
        print(f"  Порог уверенности: {classifier_info['confidence_threshold']}")
        print(f"  Поддерживаемые типы: {classifier_info['supported_types']}")
        
        cache_info = health['cache']
        if cache_info.get('enabled'):
            print(f"\nКэш:")
            if 'stats' in cache_info:
                stats = cache_info['stats']
                print(f"  Всего записей: {stats.get('total_entries', 0)}")
                print(f"  Активных записей: {stats.get('active_entries', 0)}")
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")


async def main():
    """Главная функция тестирования"""
    print("🔍 Тестирование системы веб-поиска\n")
    
    # Проверяем конфигурацию
    try:
        config = load_config()
        print("✅ Конфигурация загружена")
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return
    
    # Запускаем тесты
    tests = [
        ("Классификатор запросов", test_query_classifier),
        ("Поисковые провайдеры", test_search_providers),
        ("Интеграция с AI", test_ai_integration),
        ("Утилитарная функция", test_web_search_utility),
        ("Проверка состояния", test_health_check),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print('='*60)
        
        try:
            await test_func()
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("✅ Тестирование завершено!")
    
    # Закрываем все ресурсы
    for test_name, test_func in tests:
        if test_name == "Поисковые провайдеры" and 'search_router' in locals():
            try:
                await search_router.cleanup()
                print("✅ Ресурсы SearchRouter очищены")
            except Exception as e:
                print(f"❌ Ошибка при очистке ресурсов SearchRouter: {e}")
        
        if test_name == "Интеграция с AI" and 'ai_provider' in locals():
            if hasattr(ai_provider, 'cleanup') and callable(ai_provider.cleanup):
                try:
                    await ai_provider.cleanup()
                    print("✅ Ресурсы AI провайдера очищены")
                except Exception as e:
                    print(f"❌ Ошибка при очистке ресурсов AI провайдера: {e}")


if __name__ == "__main__":
    # Запускаем тесты
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Тестирование прервано пользователем")
        print("Выполняется очистка ресурсов...")
        # Здесь нельзя вызвать cleanup напрямую, так как мы вне асинхронного контекста
        # Но можно вывести сообщение о необходимости перезапуска для корректной очистки
        print("Для корректной очистки ресурсов перезапустите скрипт и дайте ему завершиться нормально")