# SC-CraftX 🎮

**Desktop приложение для мониторинга и анализа цен в Stalcraft: X**

---

## 🌟 Основные возможности

- 📊 **Мониторинг цен** — отслеживание аукциона в реальном времени
- 📈 **Статистика и аналитика** — история цен, ликвидность, тренды
- 🔄 **Автообновление** — фоновая синхронизация без блокировки UI
- 💾 **Локальная база данных** — кэширование для быстрого доступа
- 🎨 **PyQt6 интерфейс** — современный и удобный UI

---

## 🚀 Быстрый старт

### 1. Установка

```bash
# Клонируй репозиторий
git clone <your-repo>
cd SC-CraftX

# Установи зависимости
pip install -r requirements_v2.txt
```

### 2. Настройка

Создай `.env` файл:
```bash
cp .env.example .env
```

Получи API credentials на https://exbo.net/oauth/applications и добавь в `.env`:
```env
STALCRAFT_CLIENT_ID=твой_client_id
STALCRAFT_CLIENT_SECRET=твой_client_secret
```

### 3. Запуск

```bash
# Тест API
python examples/simple_test.py

# Или запусти GUI пример
python examples/pyqt6_example.py

# Или запусти основное приложение
python main.py
```

Подробная инструкция: **[QUICKSTART.md](QUICKSTART.md)**

---

## 📁 Структура проекта

```
SC-CraftX/
├── api_v2/              # Новая асинхронная архитектура
│   ├── models.py        - Pydantic модели
│   ├── database.py      - Асинхронный SQLite
│   ├── client.py        - API клиент (stalcraft-api)
│   └── qt_bridge.py     - Интеграция с PyQt6
│
├── api/                 # Старая версия (deprecated)
├── ui/                  # GUI компоненты
├── examples/            # Примеры использования
├── tools/               # Утилиты
├── data/                # Данные
│
├── main.py              # Точка входа
├── settings_v2.py       # Конфигурация
└── .env.example         # Пример настроек
```

---

## 🔧 API v2 — Новая архитектура

### Что нового?

✅ **Официальная библиотека** `stalcraft-api` — поддержка разработчиков  
✅ **Асинхронность** — не блокирует UI, быстрая работа  
✅ **Автоматический retry** — exponential backoff при rate limit  
✅ **Умное кэширование** — SQLite + TTL  
✅ **Типизация** — Pydantic модели  
✅ **Простая интеграция** — готовые Qt сигналы  

### Пример использования

```python
from api_v2 import AutoSyncManager

# Создаём менеджер синхронизации
sync_manager = AutoSyncManager(
    item_ids=["pistol-pm", "rifle-akm"],
    interval_seconds=60
)

# Подключаем обработчик
sync_manager.price_updated.connect(on_price_update)

# Запускаем автообновление
sync_manager.start_auto_sync()
```

Полная документация: **[api_v2/README.md](api_v2/README.md)**

---

## 📚 Документация

- **[QUICKSTART.md](QUICKSTART.md)** — Быстрый старт за 3 минуты
- **[GETTING_STARTED.md](GETTING_STARTED.md)** — Подробная инструкция
- **[api_v2/README.md](api_v2/README.md)** — Документация API
- **[CHANGELOG_V2.md](CHANGELOG_V2.md)** — История изменений

---

## 🛠️ Технологии

- **Python 3.10+**
- **PyQt6** — GUI фреймворк
- **stalcraft-api** — официальная библиотека Stalcraft API
- **aiosqlite** — асинхронный SQLite
- **Pydantic** — валидация данных
- **asyncio** — асинхронное программирование

---

## 🔑 Требования

- Python 3.10 или выше
- Stalcraft API credentials (получить на https://exbo.net/oauth/applications)
- Windows / Linux / macOS

---

## 📋 TODO

- [ ] WebSocket для real-time обновлений
- [ ] Графики истории цен (matplotlib)
- [ ] Экспорт данных (CSV, Excel)
- [ ] Telegram/Discord интеграция
- [ ] Машинное обучение для предсказания цен

---

## 🤝 Вклад в проект

Приветствуются любые улучшения! Если нашёл баг или есть идея:

1. Создай issue
2. Сделай fork
3. Внеси изменения
4. Отправь pull request

---

## 📄 Лицензия

Этот проект создан для использования с игрой Stalcraft: X и её официальным API.

---

## 🎯 Поддержка

- **Вопросы?** Создай issue на GitHub
- **Баги?** Проверь логи в `logs/stalcraft.log`
- **API проблемы?** https://eapi.stalcraft.net/

---

**Версия:** 2.0.0  
**Статус:** ✅ Production Ready  
**Дата:** 2025

---

**Сделано с ❤️ для сообщества Stalcraft**
