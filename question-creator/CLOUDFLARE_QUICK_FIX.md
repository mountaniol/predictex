# Quick Fix для Cloudflare Tunnel

## Что нужно добавить в вашу конфигурацию Cloudflare Tunnel:

### В файл конфигурации cloudflared (обычно ~/.cloudflared/config.yml):

```yaml
ingress:
  # Добавьте это правило ПЕРЕД вашим основным правилом
  - hostname: ваш-домен.com
    path: /api-creator
    service: http://localhost:3004
  
  # Ваши существующие правила...
  - hostname: ваш-домен.com
    service: http://localhost:3003
    
  - service: http_status:404
```

## Что было сделано в приложении:

1. ✅ Создан файл `.env` с настройкой:
   ```
   REACT_APP_API_BASE_URL=/api-creator
   ```

2. ✅ Приложение пересобрано с этой настройкой

3. ✅ Теперь все API запросы идут на `/api-creator` вместо прямого HTTP

## Как проверить:

1. Запустите backend:
   ```bash
   cd /media/AI/predictex/qna-evaluator/question-creator/backend
   python server.py
   ```

2. Запустите frontend:
   ```bash
   cd /media/AI/predictex/qna-evaluator/question-creator
   npm start
   # или для production:
   npx serve -s build -l 3003
   ```

3. Перезапустите Cloudflare Tunnel:
   ```bash
   sudo systemctl restart cloudflared
   # или
   cloudflared tunnel run
   ```

4. Откройте сайт через ваш домен и проверьте консоль браузера - должны быть запросы к `/api-creator/api/...`

## Если все еще не работает:

Проверьте, что backend отвечает локально:
```bash
curl http://localhost:3004/api/providers
```

Проверьте через туннель:
```bash
curl https://ваш-домен.com/api-creator/api/providers
```

Если второй запрос не работает - проблема в конфигурации Cloudflare Tunnel.