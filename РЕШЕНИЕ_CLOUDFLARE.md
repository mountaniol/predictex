# ✅ РЕШЕНИЕ: Настройка для creator.predictex.ai

## Проблема
При доступе через HTTPS (creator.predictex.ai) браузер блокирует HTTP запросы к backend (Mixed Content).

## Решение реализовано в 2 шага:

### ШАГ 1: Обновите конфигурацию Cloudflare Tunnel

Добавьте это правило **ПЕРВЫМ** в вашу конфигурацию:

```yaml
ingress:
  # ДОБАВЬТЕ ЭТО ПРАВИЛО ПЕРВЫМ!
  - hostname: creator.predictex.ai
    path: /api-creator
    service: http://192.168.1.50:3004
    originRequest:
      httpHostHeader: 192.168.1.50:3004

  # Ваше существующее правило для frontend
  - hostname: creator.predictex.ai
    service: http://192.168.1.50:3003
    originRequest:
      httpHostHeader: 192.168.1.50:3003
      
  # ... остальные правила
```

### ШАГ 2: Перезапустите приложение

**ВАЖНО:** Приложение должно быть перезапущено, чтобы подхватить новые настройки!

```bash
# 1. Остановите текущий frontend
# Найдите процесс на порту 3003
lsof -i :3003
# Остановите его (замените PID на реальный)
kill <PID>

# 2. Запустите заново
cd /media/AI/predictex/qna-evaluator/question-creator
npm start

# ИЛИ используйте production build:
npm run build
npx serve -s build -p 3003
```

### ШАГ 3: Перезапустите Cloudflare Tunnel

```bash
sudo systemctl restart cloudflared
# или
cloudflared tunnel run
```

## Проверка

1. **Backend работает?**
```bash
curl http://192.168.1.50:3004/api/providers
```

2. **Tunnel проксирует API?**
```bash
curl https://creator.predictex.ai/api-creator/api/providers
```

3. **В браузере откройте:**
https://creator.predictex.ai

В консоли браузера (F12) не должно быть ошибок Mixed Content.

## Что было сделано:

✅ Создан файл `.env` с настройкой `REACT_APP_API_BASE_URL=https://creator.predictex.ai/api-creator`
✅ Приложение пересобрано с новыми настройками
✅ Backend запущен на порту 3004

## Если все еще не работает:

1. **Убедитесь, что приложение перезапущено** после создания `.env` файла
2. **Проверьте, что правило для `/api-creator` добавлено ПЕРЕД основным правилом**
3. **Откройте test-api.html** в браузере для диагностики:
   ```
   https://creator.predictex.ai/test-api.html
   ```

## Текущий статус:
- ✅ Backend работает на порту 3004
- ✅ Конфигурация готова
- ⚠️ Требуется: добавить правило в Cloudflare и перезапустить frontend