# Backend API Server

Backend сервер для обработки запросов к OpenAI API.

## Установка

1. Установите зависимости:
```bash
npm install
```

2. Создайте файл `.env` на основе `env.example`:
```bash
cp env.example .env
```

3. Добавьте ваш OpenAI API ключ в файл `.env`:
```
OPENAI_API_KEY=your_actual_api_key_here
```

## Запуск

### Разработка
```bash
npm run dev
```

### Продакшн
```bash
npm start
```

Сервер запустится на порту 5000 (или на порту, указанном в переменной окружения PORT).

## API Endpoints

### POST /api/evaluate
Оценивает ответ на вопрос с помощью OpenAI API.

**Request Body:**
```json
{
  "question": "Текст вопроса",
  "answer": "Ответ пользователя",
  "systemPrompt": "Системный промпт для AI",
  "questionType": "open-ended|yes-no|numeric"
}
```

**Response:**
```json
{
  "score": 85
}
```

### GET /api/health
Проверка состояния сервера.

**Response:**
```json
{
  "status": "OK",
  "timestamp": "2025-08-07T10:30:00.000Z"
}
```

## Безопасность

- API ключи хранятся в переменных окружения
- CORS настроен для работы с frontend
- Валидация входных данных
- Обработка ошибок OpenAI API 