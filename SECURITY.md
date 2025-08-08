# Безопасность

## Настройка переменных окружения

⚠️ **ВАЖНО**: Никогда не коммитьте файл `.env` с реальными API ключами в репозиторий!

### Настройка для разработки

1. Скопируйте файл `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

2. Заполните `.env` файл своими реальными данными:
   - `BOT_TOKEN` - токен Telegram бота от @BotFather
   - `OPENAI_API_KEY` - API ключ от OpenAI
   - `OPENAI_ASSISTANT_ID` - ID созданного Assistant в OpenAI
   - `GETCOURSE_API_KEY` - ключ API GetCourse
   - `ADMIN_IDS` - ID администраторов через запятую

### Безопасность API ключей

- ✅ Файл `.env` уже добавлен в `.gitignore`
- ✅ API ключи загружаются из переменных окружения
- ✅ Добавлены проверки наличия ключей при запуске
- ✅ В коде нет hardcoded ключей

### Для продакшена

Установите переменные окружения на сервере через:
- Системные переменные окружения
- Docker secrets
- Kubernetes secrets
- Или другой безопасный способ управления секретами

**НЕ используйте файл .env в продакшене!**

## Устранение проблем совместимости

### Ошибка "unexpected keyword argument 'proxies'"

Если на Linux сервере возникает ошибка:
```
Client.__init__() got an unexpected keyword argument 'proxies'
```

**Решение:**
1. Проверьте версии зависимостей: `python check_dependencies.py`
2. Обновите до точных версий: `pip install -r requirements-lock.txt --upgrade`
3. Если проблема остается, переустановите openai: `pip uninstall openai && pip install openai==1.54.4`

### Проверка системы

Перед запуском бота выполните:
```bash
python check_dependencies.py
```

Это покажет все проблемы с зависимостями и совместимостью.