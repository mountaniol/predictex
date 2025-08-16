# Обновление конфигурации Cloudflare Tunnel

## Ваша текущая конфигурация:
```yaml
ingress:
  - hostname: creator.predictex.ai
    service: http://192.168.1.50:3003
    originRequest:
      httpHostHeader: 192.168.1.50:3003
```

## Нужно обновить на:
```yaml
ingress:
  # API для Question Creator - ДОЛЖНО БЫТЬ ПЕРВЫМ
  - hostname: creator.predictex.ai
    path: /api-creator
    service: http://192.168.1.50:3004
    originRequest:
      httpHostHeader: 192.168.1.50:3004
      noTLSVerify: true

  # Frontend для Question Creator
  - hostname: creator.predictex.ai
    service: http://192.168.1.50:3003
    originRequest:
      httpHostHeader: 192.168.1.50:3003

  # Остальные ваши правила...
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

## Важно:
- Правило для `/api-creator` ДОЛЖНО быть ПЕРЕД общим правилом для `creator.predictex.ai`
- Backend работает на порту 3004, а не 3003

## После обновления конфигурации:

1. Перезапустите Cloudflare Tunnel:
```bash
sudo systemctl restart cloudflared
# или
cloudflared tunnel run
```

2. Пересоберите приложение:
```bash
cd /media/AI/predictex/qna-evaluator/question-creator
npm run build
```

3. Запустите оба сервиса:
```bash
# Terminal 1 - Backend
cd /media/AI/predictex/qna-evaluator/question-creator/backend
python server.py

# Terminal 2 - Frontend
cd /media/AI/predictex/qna-evaluator/question-creator
npm start
# или
npx serve -s build -l 3003
```

## Проверка:

1. Backend напрямую:
```bash
curl http://192.168.1.50:3004/api/providers
```

2. Backend через туннель:
```bash
curl https://creator.predictex.ai/api-creator/api/providers
```

3. Frontend:
Откройте https://creator.predictex.ai и проверьте консоль браузера