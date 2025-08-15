# План исправления проблем WebSearch

## Обзор проблемы
WebSearch система имеет критические проблемы, которые блокируют её эффективную работу:
1. **Hardcoded фильтры** блокируют поиск для всех бизнес-вопросов
2. **Неэффективное формирование запросов** из текста вопросов вместо ответов
3. **Конфликт логики** между модулями
4. **Отсутствие контекста** при поиске

## Фаза 1: Устранение блокировок (Критично)

### Задача 1.1: Удалить hardcoded фильтры в py_simple_evaluate.py
**Файл:** `src/backend/py_simple_evaluate.py`
**Проблема:** Функции `generate_search_query_from_question()` и `perform_web_search_for_question()` блокируют поиск

**Действия:**
```python
# УДАЛИТЬ строки 193-198:
strategic_question_prefixes = ['SG', 'MET.', 'SGA']
for prefix in strategic_question_prefixes:
    if question_id.startswith(prefix):
        return ""

# УДАЛИТЬ строки 201-210:
business_evaluation_keywords = [...]
for keyword in business_evaluation_keywords:
    if keyword in question_text.lower():
        return ""
```

### Задача 1.2: Рефакторинг perform_web_search_for_question()
**Действия:**
```python
async def perform_web_search_for_question(question, answer, all_answers, config):
    """Выполняет веб-поиск с учетом ответа пользователя"""
    try:
        # Генерируем запрос на основе ОТВЕТА, не вопроса
        search_query = generate_search_query_from_answer(
            question, answer, all_answers
        )
        
        if not search_query:
            return ""
        
        print(f"🔍 WebSearch query: '{search_query}'")
        
        # Выполняем поиск
        results = await search_web(search_query, config)
        
        # Форматируем для контекста
        return format_search_results_for_evaluation(results[:3])
        
    except Exception as e:
        print(f"🔍 WebSearch error: {e}")
        return ""
```

## Фаза 2: Улучшение генерации запросов

### Задача 2.1: Новая функция generate_search_query_from_answer()
**Файл:** `src/backend/py_simple_evaluate.py`

```python
def generate_search_query_from_answer(question, answer, all_answers):
    """
    Генерирует поисковый запрос на основе ОТВЕТА пользователя
    """
    import re
    from typing import List
    
    def extract_keywords(text: str, max_words: int = 5) -> List[str]:
        """Извлекает ключевые слова из текста"""
        # Удаляем стоп-слова
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 
                     'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 
                     'was', 'were', 'been', 'have', 'has', 'had'}
        
        # Извлекаем слова длиннее 3 символов
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Фильтруем стоп-слова
        keywords = [w for w in words if w not in stop_words]
        
        # Возвращаем уникальные слова
        seen = set()
        result = []
        for word in keywords:
            if word not in seen:
                seen.add(word)
                result.append(word)
                if len(result) >= max_words:
                    break
        
        return result
    
    search_terms = []
    
    # 1. Обработка ответа в зависимости от типа
    if isinstance(answer, list):
        # Для множественного выбора - используем выбранные опции
        for option_code in answer:
            if option_code != 'other':
                # Получаем label опции
                for opt in question.get('options', []):
                    if opt['code'] == option_code:
                        search_terms.extend(extract_keywords(opt['label']))
                        break
            else:
                # Для "Other" используем текст из other_text_id
                other_text_id = question.get('other_text_id')
                if other_text_id and all_answers.get(other_text_id):
                    search_terms.extend(extract_keywords(all_answers[other_text_id]))
    
    elif isinstance(answer, str):
        # Для текстовых ответов
        if len(answer) > 20:  # Достаточно длинный ответ
            search_terms.extend(extract_keywords(answer))
        else:
            # Короткий ответ - используем полностью
            search_terms.append(answer.lower())
    
    # 2. Добавляем контекст из зависимых ответов
    context_terms = []
    
    # Локация компании (важный контекст)
    if 'MET.LOC' in all_answers and all_answers['MET.LOC']:
        location = all_answers['MET.LOC']
        # Извлекаем город/страну
        location_parts = location.split(',')
        if location_parts:
            context_terms.append(location_parts[0].strip())
    
    # Индустрия/сектор
    if 'MET.INDUSTRY' in all_answers and all_answers['MET.INDUSTRY']:
        context_terms.extend(extract_keywords(all_answers['MET.INDUSTRY'], 2))
    
    # Размер компании
    if 'MET.SIZE' in all_answers and all_answers['MET.SIZE']:
        size = all_answers['MET.SIZE']
        if 'small' in size.lower():
            context_terms.append('SME')
        elif 'large' in size.lower():
            context_terms.append('enterprise')
    
    # 3. Формируем финальный запрос
    if not search_terms and not context_terms:
        # Если нет ключевых слов, используем тип вопроса
        question_type = question.get('cluster_name', '')
        if question_type:
            search_terms.append(question_type.lower())
    
    # Объединяем термины
    all_terms = search_terms[:3]  # Максимум 3 основных термина
    if context_terms:
        all_terms.extend(context_terms[:2])  # Максимум 2 контекстных термина
    
    # Добавляем модификаторы для улучшения результатов
    query = ' '.join(all_terms)
    
    # Добавляем временной контекст если нужны актуальные данные
    if any(word in question.get('text', '').lower() 
           for word in ['current', 'latest', 'recent', 'текущий', 'последний']):
        query += ' 2024 2025 latest trends'
    else:
        query += ' best practices industry analysis'
    
    return query.strip()
```

### Задача 2.2: Обновить вызов в evaluate_answer_logic()
**Файл:** `src/backend/py_simple_evaluate.py`

```python
# Строка ~333, заменить вызов perform_web_search_for_question на:
web_search_context = ""
try:
    import asyncio
    
    # Передаем answer в функцию поиска
    answer_value = all_answers.get(question_id)
    
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run, 
                perform_web_search_for_question(
                    question, 
                    answer_value,  # Передаем ответ
                    all_answers,   # И все ответы для контекста
                    config
                )
            )
            web_search_context = future.result(timeout=30)
    except RuntimeError:
        web_search_context = asyncio.run(
            perform_web_search_for_question(
                question, 
                answer_value,
                all_answers,
                config
            )
        )
```

## Фаза 3: Унификация логики принятия решений

### Задача 3.1: Централизовать логику в ai_providers_with_search.py
**Проблема:** Логика принятия решения о поиске дублируется

**Действия:**
1. Оставить всю логику ТОЛЬКО в `ai_providers_with_search.py`
2. Удалить проверки из `py_simple_evaluate.py`
3. Использовать конфигурацию для управления

### Задача 3.2: Улучшить _should_perform_search()
**Файл:** `src/backend/ai_providers_with_search.py`

```python
def _should_perform_search(self, messages: list) -> bool:
    """Централизованное решение о выполнении поиска"""
    
    # 1. Проверка базовых условий
    if not self.enabled:
        return False
    
    if not messages:
        return False
    
    # 2. Force search переопределяет всё
    if self.force_search_all:
        print("🔍 FORCE_SEARCH_ALL enabled - searching")
        return True
    
    # 3. Извлекаем последнее сообщение
    last_message = self._get_last_user_message(messages)
    if not last_message:
        return False
    
    # 4. Применяем фильтры ТОЛЬКО если не отключены
    if not self.disable_business_filters:
        # Проверяем, является ли это оценкой бизнеса
        if self._is_business_evaluation(last_message):
            # НО! Проверяем override настройки
            if self.config.get('search_for_business_questions', False):
                print("🔍 Business question, but search_for_business_questions=true")
                return True
            else:
                print("🔍 Skipping search for business evaluation")
                return False
    
    # 5. Проверяем триггеры
    if self._has_search_triggers(last_message):
        return True
    
    # 6. Проверяем паттерны
    if self._has_search_patterns(last_message):
        return True
    
    return False
```

## Фаза 4: Оптимизация классификации

### Задача 4.1: Улучшить QueryClassifier
**Файл:** `src/backend/query_classifier.py`

Добавить учет типа вопроса:
```python
def classify_with_context(self, query: SearchQuery, 
                         question_type: str = None,
                         answer_context: dict = None) -> Dict[str, Any]:
    """
    Классификация с учетом контекста вопроса и ответа
    """
    base_classification = self.classify(query)
    
    # Корректируем на основе типа вопроса
    if question_type:
        if question_type == 'MET.LOC':
            # Географические вопросы - фактические
            base_classification['primary_type'] = 'factual'
            base_classification['suggested_providers'] = ['wikipedia', 'duckduckgo']
        
        elif question_type in ['SG01', 'SG02', 'SG03']:
            # Стратегические вопросы - текущие тренды
            base_classification['primary_type'] = 'current'
            base_classification['suggested_providers'] = ['duckduckgo', 'rss']
    
    # Корректируем на основе контекста ответа
    if answer_context:
        if 'technology' in str(answer_context).lower():
            # Технологические вопросы
            base_classification['suggested_providers'].append('rss')
    
    return base_classification
```

## Фаза 5: Тестирование

### Задача 5.1: Создать тестовый скрипт
**Файл:** `test_websearch_fix.py`

```python
#!/usr/bin/env python3
"""
Тест исправлений WebSearch
"""
import requests
import json

def test_websearch(question_id, answer, all_answers=None):
    """Тестирует WebSearch для конкретного вопроса"""
    
    url = "http://localhost:3001/api/simple-evaluate.mjs"
    
    payload = {
        "questionId": question_id,
        "allAnswers": all_answers or {question_id: answer}
    }
    
    print(f"\n{'='*60}")
    print(f"Testing: {question_id}")
    print(f"Answer: {answer}")
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Score: {result.get('score')}")
        print(f"Explanation preview: {result.get('explanation', '')[:200]}...")
        
        # Проверяем, есть ли признаки WebSearch в объяснении
        explanation = result.get('explanation', '')
        if any(keyword in explanation.lower() 
               for keyword in ['according to', 'based on', 'источник', 'search', 'found']):
            print("🔍 WebSearch likely performed!")
        else:
            print("⚠️ WebSearch might not have been performed")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

# Тестовые случаи
if __name__ == "__main__":
    # Тест 1: Стратегический вопрос
    test_websearch(
        "SG01",
        ["declining_sales", "increased_competition"],
        {
            "MET.LOC": "San Francisco, CA",
            "SG01": ["declining_sales", "increased_competition"]
        }
    )
    
    # Тест 2: Вопрос с текстовым ответом
    test_websearch(
        "SG02",
        "We use AI and machine learning for predictive analytics",
        {
            "MET.LOC": "New York, NY",
            "MET.INDUSTRY": "FinTech",
            "SG02": "We use AI and machine learning for predictive analytics"
        }
    )
    
    # Тест 3: Вопрос с "Other" опцией
    test_websearch(
        "SG03",
        ["other"],
        {
            "SG03": ["other"],
            "SG03_OTHER": "Blockchain technology implementation"
        }
    )
    
    print("\n" + "="*60)
    print("Testing complete!")
```

### Задача 5.2: Проверить логи
Добавить расширенное логирование:

```python
# В py_simple_evaluate.py
print(f"🔍 [SEARCH] Question: {question_id}")
print(f"🔍 [SEARCH] Answer: {answer_value}")
print(f"🔍 [SEARCH] Generated query: {search_query}")
print(f"🔍 [SEARCH] Results count: {len(results)}")

# В ai_providers_with_search.py
print(f"🔍 [DECISION] force_search_all: {self.force_search_all}")
print(f"🔍 [DECISION] disable_business_filters: {self.disable_business_filters}")
print(f"🔍 [DECISION] Final decision: {should_search}")
```

## Фаза 6: Мониторинг и метрики

### Задача 6.1: Добавить метрики поиска
**Файл:** `src/backend/search_metrics.py`

```python
import json
import time
from datetime import datetime
from typing import Dict, Any

class SearchMetrics:
    """Сбор метрик эффективности поиска"""
    
    def __init__(self, log_file="search_metrics.jsonl"):
        self.log_file = log_file
    
    def log_search(self, 
                   question_id: str,
                   query: str,
                   results_count: int,
                   search_time: float,
                   providers_used: list,
                   was_useful: bool = None):
        """Логирует метрики поиска"""
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "question_id": question_id,
            "query": query,
            "results_count": results_count,
            "search_time": search_time,
            "providers": providers_used,
            "useful": was_useful
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(metric) + '\n')
    
    def analyze_effectiveness(self):
        """Анализирует эффективность поиска"""
        metrics = []
        
        with open(self.log_file, 'r') as f:
            for line in f:
                metrics.append(json.loads(line))
        
        # Анализ
        total = len(metrics)
        avg_results = sum(m['results_count'] for m in metrics) / total
        avg_time = sum(m['search_time'] for m in metrics) / total
        
        # По провайдерам
        provider_stats = {}
        for m in metrics:
            for p in m['providers']:
                provider_stats[p] = provider_stats.get(p, 0) + 1
        
        print(f"Total searches: {total}")
        print(f"Average results: {avg_results:.1f}")
        print(f"Average time: {avg_time:.2f}s")
        print(f"Providers usage: {provider_stats}")
```

## Временная шкала реализации

### День 1: Критические исправления
- [ ] Задача 1.1: Удалить hardcoded фильтры (30 мин)
- [ ] Задача 1.2: Рефакторинг perform_web_search_for_question (1 час)
- [ ] Задача 5.1: Создать и запустить тесты (30 мин)

### День 2: Улучшение генерации запросов
- [ ] Задача 2.1: Новая функция generate_search_query_from_answer (2 часа)
- [ ] Задача 2.2: Обновить вызовы (30 мин)
- [ ] Тестирование (30 мин)

### День 3: Оптимизация
- [ ] Задача 3.1: Унификация логики (1 час)
- [ ] Задача 4.1: Улучшение классификации (1 час)
- [ ] Задача 6.1: Добавить метрики (1 час)

## Ожидаемые результаты

### После Фазы 1:
- ✅ WebSearch будет работать для ВСЕХ вопросов
- ✅ Устранена основная блокировка

### После Фазы 2:
- ✅ Поисковые запросы станут релевантными
- ✅ Учитывается контекст ответов

### После Фазы 3-4:
- ✅ Единая логика принятия решений
- ✅ Оптимальный выбор провайдеров

### После Фазы 5-6:
- ✅ Полное тестовое покрытие
- ✅ Метрики для дальнейшей оптимизации

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Увеличение нагрузки на API | Средняя | Rate limiting, кэширование |
| Нерелевантные результаты | Низкая | Улучшенная генерация запросов |
| Замедление ответов | Средняя | Параллельный поиск, таймауты |
| Конфликты в коде | Низкая | Поэтапное внедрение, тесты |

## Команда и ресурсы

**Необходимо:**
- 1 разработчик на 3 дня
- Доступ к тестовому окружению
- Мониторинг логов после деплоя

**Зависимости:**
- Работающий backend сервер
- Доступ к поисковым API
- Тестовые данные

## Критерии успеха

1. **WebSearch выполняется для >90% вопросов** (сейчас ~0%)
2. **Релевантность результатов >70%** (по оценке пользователей)
3. **Время ответа <5 секунд** (с учетом поиска)
4. **Отсутствие ошибок** в production логах

## Следующие шаги после исправления

1. **A/B тестирование** с/без WebSearch
2. **Оптимизация кэша** для частых запросов
3. **Добавление новых провайдеров** (Google, Bing)
4. **ML-модель** для улучшения классификации
5. **Персонализация** поиска на основе истории