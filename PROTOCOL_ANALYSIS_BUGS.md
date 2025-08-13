# Анализ протокола: Логические несостыковки и потенциальные баги

## Обнаруженные проблемы

### 🔴 КРИТИЧЕСКАЯ ПРОБЛЕМА: Различная логика циклов в runStartupCheck

**Местоположение:** `QuestionSection.js` строки 506-532 vs 244-266

**Проблема:**
В коде есть ДВА разных цикла для каскадной переоценки:
1. `runStartupCheck` (строка 506) - **БЕЗ** ограничения на количество проходов
2. `handleSubmitAndResolveDependencies` (строка 244) - **С** ограничением `passes < 10`

```javascript
// runStartupCheck - ОПАСНО!
while (reevaluatedInPass) {  // ← Никаких ограничений!
  reevaluatedInPass = false;
  // ... логика переоценки
}

// handleSubmitAndResolveDependencies - БЕЗОПАСНО
while (reevaluatedInPass && passes < 10) {  // ← Есть лимит
  passes++;
  // ... аналогичная логика
}
```

**Последствия:**
- При зацикливании в `runStartupCheck` приложение может полностью зависнуть
- Нет механизма аварийного выхода из бесконечного цикла
- Страница становится неотзывчивой

### 🟡 ПРОБЛЕМА: Нарушение принципа предотвращения циклов

**Местоположение:** Документация vs реальная реализация

**Заявлено в документации:**
> "Questions are evaluated in document order"
> "Each question can only depend on previously defined questions"

**Реальность:**
- Никакой проверки порядка зависимостей в коде нет
- `ai_context.include_answers` может содержать ID вопросов, определенных ПОСЛЕ текущего
- Возможны взаимные зависимости: SG01 → SG02 → SG01

### 🟡 ПРОБЛЕМА: Несогласованность состояний в computeAllStates

**Местоположение:** `QuestionSection.js` строка 144

```javascript
newStates[q.id] = getQuestionState(q, answers, currentScores, newStates);
```

**Проблема:**
- `getQuestionState` получает `newStates` как параметр для проверки зависимостей
- Но `newStates` заполняется в том же цикле
- Порядок обработки вопросов может влиять на результат
- Состояние зависимостей может быть устаревшим

### 🟠 ПРОБЛЕМА: Race condition в evaluationInProgress

**Местоположение:** `QuestionSection.js` строки 413, 258-260

```javascript
evaluationInProgress.current[question.id] = true;  // Установлено
// ... async AI call ...
evaluationInProgress.current[question.id] = false; // Очищено в другом месте
```

**Проблема:**
- Флаг `evaluationInProgress` устанавливается в `handleAnswerBlur`
- Но очищается в `handleSubmitAndResolveDependencies`
- При прямом вызове `evaluateAnswer` флаг может остаться установленным навсегда

### 🟠 ПРОБЛЕМА: Несогласованность в валидации "Other"

**Местоположение:** Различные функции имеют разную логику

**В handleAnswerChange:**
```javascript
if (selectedOptions.length === 1 && hasOther && (!otherText || otherText.trim() === '')) {
    hasOnlyOtherWithoutText = true;
    hasStandardAnswer = false;
}
```

**В handleAnswerBlur:**
```javascript
if (answer.length === 1 && hasOther && (!otherText || otherText.trim() === '')) {
    hasOnlyOtherWithoutText = true;
    hasValidAnswer = false;
}
```

**В getQuestionState:**
```javascript
if (selectedOptions.length === 1 && hasOther && (!otherText || otherText.trim() === '')) {
    hasOnlyOtherWithoutText = true;
    hasStandardAnswer = false;
}
```

**Проблема:** Дублирование логики в 3+ местах без общей функции

### 🟠 ПРОБЛЕМА: Потенциальная утечка памяти в lastEvaluatedAnswers

**Местоположение:** `QuestionSection.js` строка 63

```javascript
const lastEvaluatedAnswers = useRef({});  // Никогда не очищается!
```

**Проблема:**
- Ref накапливает данные о всех когда-либо оцененных вопросах
- При изменении структуры вопросов старые записи остаются
- Нет механизма очистки устаревших записей

### 🟡 ПРОБЛЕМА: Неопределенное поведение при изменении зависимостей

**Сценарий:**
1. Вопрос A зависит от B: `"include_answers": ["B"]`
2. Пользователь отвечает на B → A получает score
3. Пользователь изменяет ответ на B → A должен пересчитаться
4. Но A остается `fully_answered` пока не будет явно переоценен

**Проблема:** Нет автоматической инвалидации зависимых вопросов

### 🟠 ПРОБЛЕМА: Асинхронность и batching состояний

**Местоположение:** `QuestionSection.js` строки 276-283

```javascript
setScores(prev => ({...prev, ...currentScores}));
setExplanations(prev => ({...prev, ...currentExplanations}));
setQuestionStates(prev => ({...prev, ...currentStates}));
```

**Проблема:**
- Три отдельных setState вызова
- Может привести к промежуточным рендерам с несогласованным состоянием
- React может не батчить их в одном событии

## Потенциальные сценарии циклов

### Сценарий 1: Взаимные зависимости
```json
{
  "id": "A",
  "ai_context": {"include_answers": ["B"]}
},
{
  "id": "B", 
  "ai_context": {"include_answers": ["A"]}
}
```

### Сценарий 2: Цикл через промежуточные вопросы
```json
A depends on B → B depends on C → C depends on A
```

### Сценарий 3: Self-dependency через calculations
```javascript
// Если calculations содержит:
"A = B + C"
// А вопрос A зависит от самого себя через ai_context
```

### Сценарий 4: Состояние "partially_answered" никогда не стабилизируется
- Вопрос имеет ответ но зависимости не полностью удовлетворены
- Каждый цикл переоценки снова находит этот вопрос как кандидата
- Бесконечное повторение в `findNextQuestionToReevaluate`

## Рекомендации по исправлению

### 1. Унифицировать логику циклов
Добавить ограничение в `runStartupCheck`:
```javascript
let passes = 0;
while (reevaluatedInPass && passes < 10) {
  passes++;
  // ...
}
```

### 2. Добавить валидацию зависимостей
При загрузке вопросов проверять:
- Отсутствие циклических зависимостей
- Зависимости только на предыдущие вопросы
- Граф зависимостей является DAG (направленный ациклический граф)

### 3. Создать общую функцию валидации "Other"
```javascript
const validateOtherField = (selectedOptions, otherText, hasOther) => {
  // Единая логика для всех мест
}
```

### 4. Добавить механизм очистки refs
```javascript
const clearEvaluationTracking = useCallback(() => {
  evaluationInProgress.current = {};
  lastEvaluatedAnswers.current = {};
}, []);
```

### 5. Batch state updates
```javascript
// Использовать один setState с объектом
setStateAll({
  scores: newScores,
  explanations: newExplanations, 
  questionStates: newStates
});
```

### 6. Добавить инвалидацию зависимых вопросов
При изменении ответа найти все зависимые вопросы и сбросить их scores.