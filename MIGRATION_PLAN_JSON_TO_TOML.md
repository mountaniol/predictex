# План миграции конфигурации с JSON на TOML

## 📋 Анализ текущей ситуации

### Используемые JSON файлы конфигурации:
1. **app.config.json** - основной файл конфигурации приложения
   - Расположение: `/public/app.config.json`
   - Использование: Backend (Python) и Frontend (React)
   - Содержит: настройки AI провайдеров, веб-поиска, портов, ретрай логики

2. **Файлы вопросов (q*.json, questions*.json)**
   - Расположение: `/public/questions/`
   - Использование: динамическая загрузка вопросов
   - НЕ ТРЕБУЮТ миграции (это данные, не конфигурация)

3. **package.json, tsconfig.json**
   - Системные файлы Node.js/TypeScript
   - НЕ ТРЕБУЮТ миграции

### Места использования app.config.json в коде:

#### Python Backend:
- `src/backend/py_local_api_server.py` - функция `load_app_config()`
- `src/backend/py_simple_evaluate.py` - загрузка путей к файлам
- `src/backend/py_final_analysis.py` - загрузка конфигурации анализа
- `src/backend/ai_providers.py` - конфигурация AI провайдеров
- `src/backend/ai_providers_with_search.py` - настройки веб-поиска
- `src/backend/test_web_search.py` - тестовая загрузка конфигурации

#### Question Creator Backend:
- `question-creator/backend/server.py` - может использовать конфигурацию

#### Frontend (React):
- Не напрямую загружает app.config.json
- Получает конфигурацию через API endpoints

## 🎯 Цели миграции

1. **Улучшенная читаемость** - TOML более человекочитаем
2. **Типобезопасность** - TOML имеет строгую типизацию
3. **Комментарии** - TOML поддерживает комментарии в файле
4. **Стандартизация** - TOML становится стандартом для конфигураций

## 🔄 План миграции

### Фаза 1: Подготовка (1-2 часа)

1. **Установка зависимостей**
   ```bash
   pip install toml
   npm install --save @iarna/toml  # для Frontend если потребуется
   ```

2. **Создание TOML версии конфигурации**
   - Конвертировать `app.config.json` → `app.config.toml`
   - Сохранить структуру, но использовать TOML синтаксис
   - Добавить полезные комментарии

3. **Создание конвертера JSON → TOML**
   - Скрипт `tools/json_to_toml_converter.py`
   - Автоматическая конвертация с сохранением структуры

### Фаза 2: Реализация загрузчика TOML (2-3 часа)

1. **Создание универсального загрузчика конфигурации**
   ```python
   # src/backend/config_loader.py
   class ConfigLoader:
       def load_config(self, path):
           if path.endswith('.toml'):
               return self.load_toml(path)
           elif path.endswith('.json'):
               return self.load_json(path)
   ```

2. **Обратная совместимость**
   - Поддержка обоих форматов одновременно
   - Приоритет: TOML > JSON
   - Fallback на JSON если TOML не найден

### Фаза 3: Обновление кода (3-4 часа)

1. **Python Backend - обновить загрузку конфигурации:**
   - `py_local_api_server.py`:
     ```python
     def load_app_config():
         # Сначала пробуем TOML
         toml_path = os.path.join(PROJECT_ROOT, 'public', 'app.config.toml')
         json_path = os.path.join(PROJECT_ROOT, 'public', 'app.config.json')
         
         if os.path.exists(toml_path):
             return load_toml_config(toml_path)
         elif os.path.exists(json_path):
             return load_json_config(json_path)
     ```

2. **Обновить все места загрузки конфигурации:**
   - py_simple_evaluate.py
   - py_final_analysis.py
   - ai_providers.py
   - ai_providers_with_search.py
   - test_web_search.py

3. **Question Creator Backend:**
   - Обновить server.py для поддержки TOML

### Фаза 4: Тестирование (2-3 часа)

1. **Unit тесты:**
   ```python
   # tests/test_config_loader.py
   def test_load_toml_config():
       config = load_config('app.config.toml')
       assert config['Backend']['ai_provider'] == 'ollama'
   
   def test_json_fallback():
       # Удаляем TOML, должен загрузиться JSON
       config = load_config()
       assert config is not None
   
   def test_config_equivalence():
       json_config = load_json('app.config.json')
       toml_config = load_toml('app.config.toml')
       assert json_config == toml_config
   ```

2. **Integration тесты:**
   - Тест работы приложения с TOML конфигом
   - Тест fallback на JSON
   - Тест миграции конфигурации

3. **E2E тесты:**
   - Запуск полного цикла с TOML конфигурацией
   - Проверка всех endpoints
   - Проверка веб-поиска и AI интеграции

### Фаза 5: Миграция и документация (1-2 часа)

1. **Скрипт миграции для пользователей:**
   ```python
   # tools/migrate_config.py
   # Автоматически конвертирует существующие JSON конфиги в TOML
   ```

2. **Обновление документации:**
   - README.md - добавить информацию о TOML
   - CLAUDE.md - обновить примеры конфигурации
   - Создать CONFIGURATION.md с полным описанием

3. **Обновление .gitignore:**
   ```
   # Конфигурационные файлы
   app.config.json
   app.config.toml
   !app.config.example.toml
   ```

## 📝 Пример структуры app.config.toml

```toml
# Главный конфигурационный файл QnA Evaluator
# Формат: TOML v1.0.0

[Generic]
question_set_file = "q4.json"
ai_prompt_file = "ai-prompt.txt"

[Frontend]
api_base_url = "/api"
final_report_initial_rows = 30
request_send_delay = 1000  # миллисекунды

[Backend]
local_api_port = 3001
ai_provider = "ollama"  # или "openai"

  [Backend.ollama]
  base_url = "http://localhost:11434"
  model = "nous-hermes2:34b"
  default_temperature = 0.3
  default_max_tokens = 1024
  stream = true

  [Backend.openai]
  model = "gpt-4-1106-preview"
  simple_evaluate_model = "gpt-4-1106-preview"
  default_temperature = 0.3
  default_max_tokens = 1024

  [Backend.retry_logic]
  max_attempts = 5
  initial_delay_seconds = 1
  max_delay_seconds = 30

  [Backend.web_search]
  enabled = true
  enable_mock_providers = true
  default_language = "en"
  max_results = 5
  timeout = 30
  strategy = "smart_routing"

    [Backend.web_search.classification]
    confidence_threshold = 0.7
    fallback_strategy = "all_providers"

    [Backend.web_search.providers.duckduckgo]
    enabled = true
    weight = 0.7
    base_url = "https://api.duckduckgo.com/"
    html_url = "https://html.duckduckgo.com/html/"
    safe_search = "moderate"
    region = "us-en"
    timeout = 20

    [Backend.web_search.providers.wikipedia]
    enabled = true
    weight = 0.9
    language = "ru"
    fallback_languages = ["en"]
    max_summary_length = 1000
    include_images = false
    timeout = 15

    [Backend.web_search.providers.rss]
    enabled = true
    weight = 0.8
    cache_duration = 3600
    timeout = 20

      [Backend.web_search.providers.rss.feeds]
      news = [
        "https://rss.rbc.ru/rbcnews/news.rss",
        "https://tass.ru/rss/v2.xml",
        "https://www.interfax.ru/rss.asp"
      ]
      tech = [
        "https://habr.com/ru/rss/hub/programming/all/",
        "https://www.cnews.ru/inc/rss/news.xml"
      ]

    [Backend.web_search.cache]
    enabled = true
    db_path = "data/search_cache.db"
    default_ttl = 3600
    max_entries = 10000
    cleanup_interval = 3600

    [Backend.web_search.rate_limiting]
    enabled = true
    requests_per_minute = 60
    requests_per_hour = 1000
    burst_size = 10

  [Backend.ai_web_search_integration]
  enabled = true
  force_search_all = true
  disable_business_filters = true
  ai_powered_queries = true
  auto_search_triggers = ["find", "search", "current information", "latest news", "what's happening", "how much", "what price", "current data", "recent", "today", "latest"]
  max_search_results_in_context = 5
  search_result_format = "markdown"
```

## ⚠️ Риски и митигация

### Риски:
1. **Обратная несовместимость** - старые установки перестанут работать
   - Митигация: Поддержка обоих форматов, автоматическая миграция

2. **Ошибки парсинга** - TOML строже JSON
   - Митигация: Валидация конфигурации при загрузке

3. **Производительность** - TOML парсится медленнее JSON
   - Митигация: Кеширование распарсенной конфигурации

4. **Frontend интеграция** - React может требовать дополнительные библиотеки
   - Митигация: Backend API возвращает конфигурацию в JSON формате

## ✅ Критерии успеха

1. Приложение работает с TOML конфигурацией
2. Сохранена обратная совместимость с JSON
3. Все тесты проходят успешно
4. Документация обновлена
5. Скрипт миграции работает корректно
6. Производительность не ухудшилась

## 📅 Оценка времени

- **Общее время**: 10-15 часов
- **Минимальная версия** (только backend): 6-8 часов
- **Полная версия** (с frontend и документацией): 12-15 часов

## 🚀 Следующие шаги

1. Утвердить план миграции
2. Создать ветку `feature/toml-config`
3. Начать с Фазы 1 - подготовка
4. Итеративно выполнять фазы с тестированием
5. Code review и merge в main