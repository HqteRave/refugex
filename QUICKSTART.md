# 🚀 SC-CraftX API v2 — БЫСТРЫЙ СТАРТ

## 📦 Что нового

✅ **Асинхронная архитектура** — использует официальную библиотеку `stalcraft-api`  
✅ **Нет блокировок UI** — всё работает в фоне через QThread  
✅ **Автоматический retry** — при 429 (rate limit)  
✅ **Умное кэширование** — SQLite + TTL  
✅ **Pydantic типизация** — никаких ошибок типов  

---

## ⚡ Установка за 3 минуты

### 1. Установи зависимости

```bash
pip install -r requirements_v2.txt
```

Или вручную:
```bash
pip install stalcraft-api aiosqlite pydantic python-dotenv PyQt6
```

### 2. Настрой credentials

**Получи токены:**
1. Зайди на https://exbo.net/oauth/applications
2. Создай приложение
3. Скопируй **Client ID** и **Client Secret**

**Создай `.env` файл:**
```bash
cp .env.example .env
```

Отредактируй `.env`:
```env
STALCRAFT_CLIENT_ID=твой_client_id
STALCRAFT_CLIENT_SECRET=твой_client_secret
STALCRAFT_REGION=ru
```

### 3. Протестируй

```bash
python examples/simple_test.py
```

Должен увидеть: `✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!`

---

## 📁 Новая структура

```
SC-CraftX/
├── api_v2/              ← НОВОЕ! Асинхронный API
│   ├── models.py        - Pydantic модели
│   ├── database.py      - Асинхронный SQLite
│   ├── client.py        - Главный клиент (stalcraft-api)
│   ├── qt_bridge.py     - Интеграция с PyQt6
│   └── README.md        - Подробная документация
│
├── examples/            ← НОВОЕ! Примеры
│   ├── simple_test.py   - Простой тест
│   └── pyqt6_example.py - Полный GUI пример
│
├── api/                 ← СТАРОЕ (не удаляй пока)
├── ui/                  
├── settings_v2.py       ← НОВОЕ! Обновлённые настройки
├── requirements_v2.txt  ← НОВОЕ! Зависимости
└── .env.example         ← Обновлён
```

---

## 💡 Как использовать

### Вариант 1: Простой запрос

```python
import asyncio
from api_v2 import create_client

async def main():
    async with create_client() as client:
        stats = await client.get_price_stats("pistol-pm")
        print(f"Средняя цена: {stats.avg_price} ₽")

asyncio.run(main())
```

### Вариант 2: Интеграция с PyQt6

```python
from PyQt6.QtWidgets import QMainWindow
from api_v2 import AutoSyncManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Создаём менеджер
        self.sync_manager = AutoSyncManager(
            item_ids=["pistol-pm", "rifle-akm"],
            interval_seconds=60
        )
        
        # Подключаем сигнал
        self.sync_manager.price_updated.connect(self.on_price_update)
        
        # Запускаем автообновление
        self.sync_manager.start_auto_sync()
    
    def on_price_update(self, item_id: str, stats):
        print(f"{item_id}: {stats.avg_price} ₽")
    
    def closeEvent(self, event):
        self.sync_manager.cleanup()
        event.accept()
```

---

## 📚 Документация

- **`GETTING_STARTED.md`** — Подробная инструкция
- **`api_v2/README.md`** — Полная документация API
- **`CHANGELOG_V2.md`** — Что изменилось
- **`examples/`** — Рабочие примеры

---

## 🔧 Миграция со старого кода

### Было (api/)

```python
from api.client import ApiClient

client = ApiClient()
stats = client.get_price_stats("pistol-pm")  # БЛОКИРУЕТ UI!
print(stats.avg)
```

### Стало (api_v2/)

```python
from api_v2 import PriceSyncManager

# В __init__:
self.sync_manager = PriceSyncManager()
self.sync_manager.price_updated.connect(self.update_ui)

# Запрос:
self.sync_manager.fetch_price("pistol-pm")  # НЕ блокирует!

# Обработчик:
def update_ui(self, item_id, stats):
    print(f"{stats.avg_price} ₽")
```

---

## ❓ Частые вопросы

### "STALCRAFT_CLIENT_ID не установлен"
→ Создай `.env` файл и добавь свои токены

### "429 Too Many Requests"
→ Увеличь `MIN_REQUEST_INTERVAL` в `.env` (например, до 0.6)

### UI зависает
→ Используй `PriceSyncManager`, не прямые вызовы клиента

### Данные не обновляются
→ Принудительное обновление: `fetch_price(item_id, use_cache=False)`

---

## ✅ Готово!

Теперь у тебя **production-ready** система синхронизации!

**Что дальше:**
1. Запусти `python examples/pyqt6_example.py` для демо
2. Интегрируй `PriceSyncManager` в свой UI
3. Настрой автообновление через `AutoSyncManager`

**Нужна помощь?** Читай `GETTING_STARTED.md` 📖

---

**Версия:** 2.0.0  
**Статус:** ✅ Production Ready
