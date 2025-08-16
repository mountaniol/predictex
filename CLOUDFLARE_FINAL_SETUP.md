# Финальная настройка для creator.predictex.ai

## ✅ Что уже сделано:

1. **Backend запущен** на порту 3004
2. **Frontend собран** с правильным API URL: `https://creator.predictex.ai/api-creator`
3. **Файл .env настроен** с `REACT_APP_API_BASE_URL=https://creator.predictex.ai/api-creator`

## 📝 Что нужно добавить в вашу конфигурацию Cloudflare:

Обновите файл конфигурации Cloudflare Tunnel (обычно `~/.cloudflared/config.yml`):

```yaml
ingress:
  # API для Question Creator - ДОБАВЬТЕ ЭТО ПРАВИЛО ПЕРВЫМ!
  - hostname: creator.predictex.ai
    path: /api-creator
    service: http://192.168.1.50:3004
    originRequest:
      httpHostHeader: 192.168.1.50:3004
      noTLSVerify: true

  # Frontend для Question Creator (ваше существующее правило)
  - hostname: creator.predictex.ai
    service: http://192.168.1.50:3003
    originRequest:
      httpHostHeader: 192.168.1.50:3003

  # Остальные ваши правила остаются без изменений
  - hostname: www.predictex.ai
    service: http://127.0.0.1:3000
    originRequest:
      httpHostHeader: 127.0.0.1:3000

  - hostname: predictex.ai
    service: http://127.0.0.1:3000
    originRequest:
      httpHostHeader: 127.0.0.1:3000

  - service: http_status:404
```

## 🚀 Как запустить:

### 1. Перезапустите Cloudflare Tunnel:
```bash
sudo systemctl restart cloudflared
# или если запускаете вручную:
cloudflared tunnel run
```

### 2. Запустите Frontend (если еще не запущен):
```bash
cd /media/AI/predictex/qna-evaluator/question-creator
npm start
# или для production:
npx serve -s build -l 3003
```

### 3. Backend уже запущен на порту 3004

## ✅ Проверка:

1. **Проверьте API через туннель:**
```bash
curl https://creator.predictex.ai/api-creator/api/providers
```

Должен вернуть JSON с провайдерами AI.

2. **Откройте сайт:**
https://creator.predictex.ai

3. **Проверьте консоль браузера:**
- Не должно быть ошибок Mixed Content
- API запросы должны идти на `https://creator.predictex.ai/api-creator/api/...`

## 🔧 Если что-то не работает:

### Проверьте логи Cloudflare:
```bash
sudo journalctl -u cloudflared -f
```

### Проверьте, что сервисы работают локально:
```bash
# Frontend
curl http://192.168.1.50:3003

# Backend API
curl http://192.168.1.50:3004/api/providers
```

### Проверьте сетевую доступность:
```bash
# С той же машины
curl http://localhost:3004/api/providers

# С другой машины в сети
curl http://192.168.1.50:3004/api/providers
```

## 📌 Важно:
- Правило для `/api-creator` ОБЯЗАТЕЛЬНО должно быть ПЕРЕД общим правилом для `creator.predictex.ai`
- Backend работает на порту **3004**, не 3003
- Frontend работает на порту **3003**

## 🎉 После настройки:
Ваш Question Creator будет доступен по адресу https://creator.predictex.ai без ошибок Mixed Content!