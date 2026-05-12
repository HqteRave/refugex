# SC-CraftX API v2 🚀

**Современная асинхронная архитектура для работы с Stalcraft API**

## ✨ Основные преимущества

✅ **Официальная библиотека** — использует `stalcraft-api`, поддерживаемую разработчиками  
✅ **Асинхронность** — не блокирует UI, быстрая работа  
✅ **Умное кэширование** — SQLite + TTL, минимум запросов к API  
✅ **Rate Limit** — автоматический backoff и retry при 429  
✅ **Типизация** — Pydantic модели, никаких ошибок типов  
✅ **Интеграция с PyQt6** — сигналы, потоки, без фризов  
✅ **История цен** — хранение за 48 часов в БД  
✅ **Автообновление** — настраиваемый интервал синхронизации  

---

## 📦 Установка

```bash
pip install stalcraft-api aiosqlite pydantic python-dotenv PyQt6
```

---

## ⚙️ Настройка

### 1. Создай `.env` файл

Скопируй `.env.example` в `.env` и заполни свои данные:

```env
# Твои credentials (получить на https://exbo.net/oauth/applications)
STALCRAFT_CLIENT_ID=твой_client_id
STALCRAFT_CLIENT_SECRET=твой_client_secret

# Регион (ru, eu, na, sea)
STALCRAFT_REGION=ru

# Интервал автообновления (секунды)
SYNC_INTERVAL=45

# TTL кэша (секунды)
CACHE_TTL=180
```

### 2. Получение токенов

1. Перейди на https://exbo.net/oauth/applications
2. Создай новое приложение
3. Скопируй `Client ID` и `Client Secret`
4. Вставь их в `.env`

**Типы токенов:**
- **App Token** (автоматически) — для публичных данных (история, лоты)
- **User Token** (опционально) — для личного инвентаря пользователя

---

## 🚀 Быстрый старт

### Пример 1: Простой запрос цены

```python
import asyncio
from api_v2 import create_client

async def main():
    async with create_client() as client:
        # Получаем статистику цен
        stats = await client.get_price_stats("pistol-pm", include_lots=True)
        
        print(f"Средняя цена: {stats.avg_price} ₽")
        print(f"Сделок: {stats.count}")
        print(f"Ликвидность: {stats.liquidity}")
        print(f"Активных лотов: {stats.market_total_lots}")

asyncio.run(main())
```

### Пример 2: Массовая синхронизация

```python
import asyncio
from api_v2 import create_client

async def main():
    items = ["pistol-pm", "rifle-akm", "ammo-9x18-pm"]
    
    async with create_client() as client:
        results = await client.sync_prices(items, include_lots=True)
        
        for item_id, update in results.items():
            if update.success:
                print(f"{item_id}: {update.stats.avg_price} ₽")
            else:
                print(f"{item_id}: Ошибка - {update.error}")

asyncio.run(main())
```

### Пример 3: Интеграция с PyQt6

```python
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
from api_v2 import AutoSyncManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Создаём менеджер
        self.sync_manager = AutoSyncManager(
            item_ids=["pistol-pm", "rifle-akm"],
            interval_seconds=60
        )
        
        # Подключаем сигналы
        self.sync_manager.price_updated.connect(self.on_price_update)
        self.sync_manager.sync_progress.connect(self.on_progress)
        
        # Запускаем автообновление
        self.sync_manager.start_auto_sync(include_lots=True)
    
    def on_price_update(self, item_id: str, stats):
        print(f"{item_id}: {stats.avg_price} ₽")
    
    def on_progress(self, progress):
        print(f"Прогресс: {progress.progress_percent:.0f}%")
    
    def closeEvent(self, event):
        self.sync_manager.cleanup()
        event.accept()

app = QApplication([])
window = MainWindow()
window.show()
app.exec()
```

---

## 📚 Архитектура

### Структура модулей

```
api_v2/
├── __init__.py          # Публичный API
├── models.py            # Pydantic модели (типизация)
├── database.py          # Асинхронная работа с SQLite
├── client.py            # Основной клиент (stalcraft-api)
└── qt_bridge.py         # Интеграция с PyQt6
```

### Основные классы

#### `StalcraftClient`

Главный асинхронный клиент для работы с API.

**Методы:**
- `get_price_history(item_id)` — история продаж (50 последних)
- `get_active_lots(item_id)` — активные лоты на аукционе
- `get_price_stats(item_id)` — полная статистика цен
- `sync_prices(item_ids)` — массовая синхронизация

**Возможности:**
- Автоматический retry при 429 (rate limit)
- Exponential backoff
- Умное кэширование (SQLite)
- Обработка ошибок

#### `PriceStats`

Модель статистики цен (Pydantic).

**Поля:**
- `count` — количество сделок
- `min_price`, `avg_price`, `max_price` — цены
- `liquidity` — ликвидность ("low", "medium", "high")
- `sales_per_hour`, `sales_per_day` — скорость продаж
- `market_min_price`, `market_total_lots` — данные аукциона
- `history` — список всех сделок

#### `PriceSyncManager`

Менеджер для интеграции с PyQt6.

**Сигналы:**
- `price_updated(item_id, stats)` — обновление цены
- `sync_progress(progress)` — прогресс синхронизации
- `sync_started()` — начало
- `sync_finished()` — завершение
- `error(message)` — ошибки

**Методы:**
- `fetch_price(item_id)` — запросить один предмет
- `sync_prices(item_ids)` — синхронизация списка
- `stop_sync()` — остановить
- `cleanup()` — очистка ресурсов

#### `AutoSyncManager`

Расширение `PriceSyncManager` с автообновлением.

**Методы:**
- `start_auto_sync()` — запустить авто-режим
- `stop_auto_sync()` — остановить
- `set_interval(seconds)` — изменить интервал

---

## 🔧 Настройки (settings_v2.py)

Все параметры можно настроить через `.env` или изменить в `Settings`:

```python
class Settings:
    # API
    CLIENT_ID: str
    CLIENT_SECRET: str
    API_BASE: str = "https://eapi.stalcraft.net"
    REGION: str = "ru"
    
    # Кэш
    CACHE_TTL: int = 180  # секунды
    HISTORY_KEEP_HOURS: int = 48
    
    # Синхронизация
    SYNC_INTERVAL: int = 45  # секунды
    MAX_CONCURRENT_REQUESTS: int = 3
    MIN_REQUEST_INTERVAL: float = 0.4
    
    # Rate Limiting
    RATE_LIMIT_BACKOFF_BASE: float = 2.0
    RATE_LIMIT_MAX_RETRIES: int = 5
```

---

## 💾 База данных

API v2 использует SQLite для кэширования и истории:

### Таблицы

**`price_cache`** — кэш цен (TTL)
- `item_id` — ID предмета
- `data` — JSON история
- `cached_at` — время кэширования

**`price_history`** — история за 48 часов
- `item_id` — ID предмета
- `sale_time` — время сделки (ISO)
- `price`, `amount`, `per_unit` — данные сделки

### Управление БД

```python
from api_v2 import get_database

# Получить экземпляр БД
db = await get_database()

# Статистика
stats = await db.get_stats()
print(f"Кэшировано: {stats['cached_items']} предметов")
print(f"История: {stats['history_records']} записей")

# Очистка устаревших данных
await db.cleanup_stale_cache(ttl_seconds=3600)
await db.cleanup_old_history_all(keep_hours=48)
```

---

## 🐛 Решение проблем

### Ошибка: "STALCRAFT_CLIENT_ID не установлен"

**Решение:** Создай `.env` файл и добавь свои credentials.

### 429 Too Many Requests

API автоматически делает retry с exponential backoff. Если ошибка не исчезает:
1. Увеличь `MIN_REQUEST_INTERVAL` в `.env`
2. Уменьши `MAX_CONCURRENT_REQUESTS`
3. Увеличь `SYNC_INTERVAL`

### Данные не обновляются

1. Проверь TTL кэша (`CACHE_TTL`)
2. Используй `use_cache=False` для принудительного обновления
3. Проверь логи (уровень `DEBUG`)

### UI зависает

- Убедись что используешь `PriceSyncManager` (асинхронный)
- НЕ блокируй Qt event loop синхронными вызовами
- Используй сигналы для передачи данных

---

## 📊 Примеры

Все примеры находятся в папке `examples/`:

- `simple_test.py` — базовое тестирование API
- `pyqt6_example.py` — полноценное приложение на PyQt6

**Запуск:**

```bash
# Простой тест
python examples/simple_test.py

# PyQt6 пример
python examples/pyqt6_example.py
```

---

## 🔄 Миграция со старой версии

### Было (api/)

```python
from api.client import ApiClient

client = ApiClient()
stats = client.get_price_stats("pistol-pm")  # Блокирует!
print(stats.avg)
```

### Стало (api_v2/)

```python
from api_v2 import create_client

async with create_client() as client:
    stats = await client.get_price_stats("pistol-pm")  # Асинхронно!
    print(stats.avg_price)
```

### Интеграция с PyQt6

**Было:**
```python
# Блокировка UI при запросе
stats = client.get_price_stats(item_id)
self.update_ui(stats)
```

**Стало:**
```python
# Асинхронно через сигналы
self.sync_manager.price_updated.connect(self.update_ui)
self.sync_manager.fetch_price(item_id)
```

---

## 📈 Производительность

**Оптимизации:**
- Кэширование запросов (180s TTL)
- Пагинация активных лотов (auto)
- Throttling (0.4s между запросами)
- Semaphore (макс 3 одновременных)
- SQLite WAL mode + оптимизированные индексы

**Типичная скорость:**
- Запрос из кэша: <10ms
- Запрос к API: ~500-1000ms
- Синхронизация 10 предметов: ~8-12s

---

## 🤝 Поддержка

**Вопросы?** Открой issue или напиши в Discord!

**Баги?** Проверь логи (`logs/stalcraft.log`) и создай issue с описанием.

---

## 📝 Лицензия

Этот проект создан для использования с игрой Stalcraft: X и её официальным API.

---

## 🎯 Roadmap

- [ ] Поддержка WebSocket для real-time обновлений
- [ ] Интеграция с личным инвентарём пользователя
- [ ] Графики истории цен (matplotlib)
- [ ] Экспорт данных (CSV, JSON, Excel)
- [ ] Алерты на изменение цен
- [ ] Telegram bot интеграция

---

**Версия:** 2.0.0  
**Автор:** SC-CraftX Team  
**Дата:** 2025
