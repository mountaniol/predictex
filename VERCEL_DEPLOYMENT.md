# Развертывание на Vercel

## Предварительные требования

1. Установите [Vercel CLI](https://vercel.com/docs/cli):
```bash
npm i -g vercel
```

2. Убедитесь, что у вас есть аккаунт на [Vercel](https://vercel.com)

## Шаги развертывания

### 1. Подготовка проекта

Убедитесь, что все файлы готовы:
- ✅ `vercel.json` - конфигурация Vercel
- ✅ `api/evaluate.js` - serverless API функция
- ✅ `package.json` - обновлен для Vercel
- ✅ `.vercelignore` - исключения файлов

### 2. Настройка переменных окружения

В Vercel Dashboard или через CLI добавьте переменную окружения:

```bash
vercel env add OPENAI_API_KEY
```

Или в Vercel Dashboard:
1. Перейдите в Settings → Environment Variables
2. Добавьте `OPENAI_API_KEY` с вашим ключом OpenAI

### 3. Развертывание

#### Вариант A: Через Vercel CLI
```bash
# В директории qna-evaluator
vercel

# Следуйте инструкциям:
# - Выберите проект или создайте новый
# - Подтвердите настройки
# - Дождитесь завершения развертывания
```

#### Вариант B: Через GitHub
1. Загрузите код в GitHub репозиторий
2. Подключите репозиторий к Vercel
3. Настройте переменные окружения
4. Разверните проект

### 4. Проверка развертывания

После развертывания проверьте:

1. **Frontend**: `https://your-project.vercel.app`
2. **API**: `https://your-project.vercel.app/api/evaluate`

### 5. Тестирование API

```bash
curl -X POST https://your-project.vercel.app/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "system": "You are an expert business evaluator.",
    "question": {"id": "TEST", "text": "Test question"},
    "answer": {"value": "Test answer"}
  }'
```

## Структура проекта для Vercel

```
qna-evaluator/
├── api/
│   └── evaluate.js          # Serverless API функция
├── public/
│   ├── q3.json             # Данные вопросов
│   └── ai-prompt.txt       # AI промпт
├── src/                    # React компоненты
├── vercel.json            # Конфигурация Vercel
├── package.json           # Зависимости и скрипты
└── .vercelignore          # Исключения файлов
```

## Возможные проблемы

### 1. Ошибка "OpenAI API key not configured"
- Убедитесь, что переменная `OPENAI_API_KEY` установлена в Vercel
- Проверьте, что ключ действителен

### 2. Ошибка CORS
- API функция уже настроена для CORS
- Убедитесь, что запросы идут на правильный endpoint

### 3. Ошибка сборки
- Проверьте, что все зависимости установлены
- Убедитесь, что `package.json` корректен

### 4. Файлы не загружаются
- Проверьте, что файлы находятся в папке `public/`
- Убедитесь, что пути в коде корректны

## Обновление развертывания

Для обновления:
```bash
vercel --prod
```

Или при push в GitHub (если настроен auto-deploy).

## Мониторинг

В Vercel Dashboard вы можете:
- Просматривать логи функций
- Мониторить производительность
- Настраивать домены
- Управлять переменными окружения
