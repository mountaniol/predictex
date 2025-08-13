# End-to-End Testing Framework

Автоматизированные тесты для проверки веб-интерфейса системы оценки бизнеса Predictex AI.

## 📋 Обзор

Данный тестовый фреймворк создан для воспроизведения и документирования критической ошибки в AI evaluation системе, где:

- **Вопрос**: "Why are you selling now?" (SG01)
- **Ответ пользователя**: "Declining sales" 
- **Ожидаемый результат**: Score 0-19 (Critical Risk)
- **Фактический результат**: Score 50 + объяснение про "restaurant in Charlotte, NC"

## 🧪 Тестовые файлы

### [`test_sg01_evaluation_bug.py`](test_sg01_evaluation_bug.py)
Основной автоматизированный тест, который:
- Запускает браузер и навигирует к http://192.168.1.50:3000
- Заполняет базовую информацию в опроснике
- Выбирает "Declining sales" в вопросе SG01
- Проверяет score и explanation от AI
- Документирует найденные баги

### [`run_sg01_test.py`](run_sg01_test.py)
Простой раннер для запуска тестов с проверками предварительных условий.

### [`web_interface_explorer.py`](web_interface_explorer.py)
Исследовательский инструмент для понимания структуры веб-интерфейса.

## 🚀 Запуск тестов

### Предварительные условия

1. **Установить Playwright**:
   ```bash
   pip install playwright
   playwright install
   ```

2. **Запустить приложение**:
   Убедитесь, что приложение доступно по адресу http://192.168.1.50:3000

### Запуск теста

```bash
# Из корневой папки проекта
python tests/run_sg01_test.py

# Или напрямую
python tests/test_sg01_evaluation_bug.py
```

## 📊 Результаты теста

Тест автоматически проанализирует результаты и выведет:

```
🔬 STARTING SG01 EVALUATION BUG TEST
============================================================
🚀 Launching browser...
🌐 Navigating to http://192.168.1.50:3000...
✅ Application loaded successfully
📝 Filling basic information...
⏳ Waiting for SG01 question...
✅ SG01 question is visible
🎯 Selecting 'Declining sales' option...
✅ 'Declining sales' option selected
⏳ Waiting for AI evaluation...
📊 Capturing evaluation results...

============================================================
📋 EVALUATION RESULTS ANALYSIS
============================================================
Score: 50
Risk Level: High Risk
Explanation: For a restaurant in Charlotte, NC, having a DSO of 30-45 days is standard and does not present a major risk. Therefore, the score is high.

============================================================
🎯 EXPECTED vs ACTUAL BEHAVIOR
============================================================
Expected Score: 0-19 (Critical Risk)
Actual Score: 50

🚨 3 BUG(S) DETECTED:
  ❌ SCORE BUG: Score should be 0-19 for declining sales (critical risk)
  ❌ EXPLANATION BUG: AI giving unrelated restaurant explanation
  ❌ CONTEXT BUG: AI confusing question context (DSO vs declining sales)

💡 DIAGNOSIS:
  - Web interface works correctly (sends proper data)
  - AI evaluation logic has context confusion
  - Possible prompt contamination or memory leak

============================================================
❌ TEST FAILED: Bugs detected in AI evaluation
============================================================
```

## 🐛 Документированные баги

### Bug #1: Неправильный score
- **Ожидается**: 0-19 (Critical Risk)
- **Получено**: 50 (High Risk)
- **Причина**: AI не следует scoring guidance для "declining sales"

### Bug #2: Неправильное объяснение
- **Ожидается**: Объяснение про declining sales как критический риск
- **Получено**: "For a restaurant in Charlotte, NC, having a DSO of 30-45 days..."
- **Причина**: AI дает ответ про совершенно другой сценарий

### Bug #3: Контекстная путаница
- **Проблема**: AI путает контексты разных вопросов
- **Эффект**: Дает ответы про DSO вместо declining sales
- **Причина**: Возможная контаминация промптов или утечка памяти

## 🔧 Техническая информация

### Конфигурация браузера
- **Браузер**: Chromium (via Playwright)
- **Viewport**: 1280x720
- **Режим**: Non-headless (для визуального контроля)

### Архитектура теста
1. **Browser Automation**: Playwright для взаимодействия с веб-интерфейсом
2. **DOM Navigation**: Автоматический поиск и заполнение полей
3. **Result Capture**: Извлечение score и explanation из UI
4. **Bug Detection**: Автоматический анализ результатов на соответствие ожиданиям

### Логика проверок
```python
# Проверка score
if isinstance(score, int) and score >= 20:
    bugs_found.append("SCORE BUG: Score should be 0-19 for declining sales")

# Проверка explanation
if 'restaurant' in explanation.lower() and 'charlotte' in explanation.lower():
    bugs_found.append("EXPLANATION BUG: AI giving unrelated restaurant explanation")

# Проверка контекста
if 'dso' in explanation.lower():
    bugs_found.append("CONTEXT BUG: AI confusing question context")
```

## 📝 Расширение тестов

Для добавления новых тестов:

1. Создайте новый класс, наследующий от базовой логики
2. Реализуйте методы для специфических сценариев
3. Добавьте проверки в `analyze_results()`
4. Обновите документацию

## 🔍 Отладка

При проблемах с тестами:

1. **Проверьте доступность сервера**: http://192.168.1.50:3000
2. **Убедитесь в установке Playwright**: `playwright --version`
3. **Запустите в debug режиме**: измените `headless=False` на `headless=True`
4. **Проверьте селекторы**: возможно изменилась структура DOM