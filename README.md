# QnA Evaluator

Интеллектуальная система оценки бизнес-рисков на основе вопросов и ответов с использованием AI.

## 🚀 Быстрый старт

### Локальная разработка

1. **Клонируйте репозиторий:**
```bash
git clone <your-repo-url>
cd qna-evaluator
```

2. **Установите зависимости:**
```bash
npm install
```

3. **Настройте переменные окружения:**
```bash
# Создайте .env файл в корне проекта
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

4. **Запустите проект:**
```bash
# Запуск только фронтенда (для разработки)
npm start

# Или используйте скрипт для запуска фронтенда + бэкенда
./start-dev.sh
```

### Развертывание на Vercel

Для развертывания на [Vercel](https://vercel.com):

1. **Установите Vercel CLI:**
```bash
npm i -g vercel
```

2. **Разверните проект:**
```bash
vercel
```

3. **Настройте переменные окружения в Vercel Dashboard:**
   - `OPENAI_API_KEY` - ваш ключ OpenAI API

Подробные инструкции: [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md)

## 📁 Архитектура проекта

```
qna-evaluator/
├── src/                    # React компоненты
│   ├── App.js             # Главный компонент с AppContext
│   ├── QuestionSection.js # Отображение вопросов
│   ├── MetaQuestionsSection.js # Мета-вопросы
│   ├── AnswerInput.js     # Универсальный компонент ввода
│   ├── LanguageSelector.js # Выбор языка
│   ├── Header.js          # Заголовок
│   ├── Footer.js          # Подвал
│   └── useLoadQuestions.js # Хук загрузки данных
├── public/                # Статические файлы
│   ├── q3.json           # Новый формат вопросов
│   ├── questions2.json   # Legacy формат
│   └── ai-prompt.txt     # AI промпт
├── api/                  # Vercel serverless функции
│   └── evaluate.js       # API для оценки ответов
├── backend/              # Локальный Express сервер
│   ├── server.js         # Основной сервер
│   └── package.json      # Зависимости бэкенда
├── vercel.json          # Конфигурация Vercel
├── package.json         # Зависимости фронтенда
└── start-dev.sh         # Скрипт запуска
```

## 🎯 Функциональность

### Поддерживаемые типы вопросов:
- **choice-single** - одиночный выбор (радио/dropdown)
- **choice-multi** - множественный выбор с ограничениями
- **yes-no** - да/нет вопросы
- **text** - однострочный ввод
- **textarea** - многострочный ввод
- **number** - числовой ввод
- **internal** - скрытые вопросы

### Дополнительные возможности:
- ✅ **Follow-up вопросы** - появляются при выборе определенных опций
- ✅ **Hint и Info** - подсказки и дополнительная информация
- ✅ **"Other" опции** - с дополнительным текстовым полем
- ✅ **Максимальное количество выборов** для multi-select
- ✅ **Ранжированный выбор** для multi-select
- ✅ **Система зависимостей** между вопросами
- ✅ **Многоязычность** (английский, русский, немецкий)
- ✅ **AI оценка** ответов с контекстом

### Форматы данных:
- **q3.json** - новый формат с мета-вопросами и расширенной функциональностью
- **questions2.json** - legacy формат для обратной совместимости

## 🔧 Технологии

### Frontend:
- **React 18** - UI библиотека
- **React Context API** - управление состоянием
- **React Hooks** - функциональные компоненты
- **CSS-in-JS** - стилизация

### Backend:
- **Vercel Functions** - serverless API (продакшн)
- **Express.js** - локальный сервер (разработка)
- **OpenAI API** - AI оценка ответов
- **Axios** - HTTP клиент

### Инфраструктура:
- **Vercel** - хостинг и развертывание
- **GitHub** - версионный контроль
- **npm** - управление зависимостями

## 📊 API

### Endpoint: `/api/evaluate`

**Request:**
```json
{
  "system": "AI system prompt",
  "prompt_add": "Question-specific scoring rules",
  "meta": {
    "MET.LOC": "location",
    "MET.IND": "industry"
  },
  "question": {
    "id": "SG01",
    "text": "Question text"
  },
  "answer": {
    "value": "selected option or text",
    "extra": {
      "follow_up_id": "follow-up answer"
    },
    "other_text": "other option text"
  },
  "answers_ctx": {
    "SG01": "previous answer"
  }
}
```

**Response:**
```json
{
  "score": 85
}
```

## 🌐 Развертывание

### Vercel (рекомендуется)
- Автоматическое развертывание из Git
- Serverless функции
- CDN для статических файлов
- SSL сертификаты
- Мониторинг и логи

### Локальный сервер
- Express.js сервер
- Для разработки и тестирования
- Требует настройки CORS

## 🔒 Безопасность

- API ключи хранятся в переменных окружения
- CORS настроен для безопасности
- Валидация входных данных
- Обработка ошибок API

## 📝 Лицензия

MIT License

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch
3. Внесите изменения
4. Создайте Pull Request

## 📞 Поддержка

При возникновении проблем:
1. Проверьте [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md)
2. Убедитесь, что все зависимости установлены
3. Проверьте переменные окружения
4. Создайте Issue в репозитории


