# 🚀 Getting Started — SC-CraftX API v2

**Полное руководство по началу работы с новой асинхронной архитектурой**

---

## 📋 Содержание

1. [Быстрый старт (5 минут)](#быстрый-старт-5-минут)
2. [Подробная настройка](#подробная-настройка)
3. [Первый запуск](#первый-запуск)
4. [Интеграция с твоим UI](#интеграция-с-твоим-ui)
5. [Troubleshooting](#troubleshooting)

---

## ⚡ Быстрый старт (5 минут)

### Шаг 1: Установка зависимостей

```bash
pip install -r requirements_v2.txt
```

Или вручную:
```bash
pip install stalcraft-api aiosqlite pydantic python-dotenv PyQt6
```

### Шаг 2: Настройка credentials

1. **Получи токены:**
   - Перейди на https://exbo.net/oauth/applications
   - Создай новое приложение
   - Скопируй `Client ID` и `Client Secret`

2. **Создай `.env` файл:**

```bash
cp .env.example .env
```

Отредактируй `.env`:
```env
STALCRAFT_CLIENT_ID=твой_client_id_здесь
STALCRAFT_CLIENT_SECRET=твой_client_secret_здесь
STALCRAFT_REGION=ru
SYNC_INTERVAL=45
```

### Шаг 3: Тестовый запуск

```bash
python examples/simple_test.py
```

Если всё настроено правильно, увидишь:
```
✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!
```

---

## 🔧 Подробная настройка

### 1. Получение API credentials

#### Что такое Client ID и Client Secret?

- **Client ID** — публичный идентификатор твоего приложения
- **Client Secret** — секретный ключ (НЕ показывай никому!)

Эти токены нужны для **App Token** (публичные данные: цены, лоты).

#### Пошаговая инструкция:

1. Зайди на https://exbo.net/oauth/applications
2. Войди через свой аккаунт Stalcraft
3. Нажми "Создать приложение"
4. Заполни форму:
   - **Название:** SC-CraftX (или своё)
   - **Redirect URI:** `http://localhost` (для desktop app)
   - **Scopes:** Оставь пустым (для App Token не нужны)
5. Нажми "Создать"
6. Скопируй:
   - **Client ID** (например: `abc123def456...`)
   - **Client Secret** (например: `xyz789...`) — СОХРАНИ СРАЗУ!

#### User Token (опционально)

Если нужен доступ к **личному инвентарю** пользователя:

1. В форме приложения укажи Scopes:
   - `inventory:read` — чтение инвентаря
   - `auction:read` — личные сделки
   
2. Реализуй OAuth flow (см. `api_v2/README.md`)

**Для начала достаточно только Client ID + Secret (App Token)!**

---

### 2. Настройка конфигурации

Создай файл `.env` в корне проекта:

```env
# ═══════════════════════════════════════════════════════════════════════
# Обязательные параметры
# ═══════════════════════════════════════════════════════════════════════

STALCRAFT_CLIENT_ID=твой_client_id
STALCRAFT_CLIENT_SECRET=твой_client_secret

# ═══════════════════════════════════════════════════════════════════════
# Опциональные параметры (можно не менять)
# ═══════════════════════════════════════════════════════════════════════

# Регион (ru / eu / na / sea)
STALCRAFT_REGION=ru

# API endpoint (не меняй без необходимости)
STALCRAFT_API_BASE=https://eapi.stalcraft.net

# Кэш цен (секунды) — сколько хранить в памяти
CACHE_TTL=180

# История цен (часы) — сколько хранить в БД
HISTORY_KEEP_HOURS=48

# Интервал автообновления (секунды) — для реал-тайм: 30-60
SYNC_INTERVAL=45

# Максимум одновременных запросов к API
MAX_CONCURRENT_REQUESTS=3

# Минимальная пауза между запросами (секунды)
MIN_REQUEST_INTERVAL=0.4

# База данных
DB_PATH=cache.db

# Логирование
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_PATH=logs/stalcraft.log
```

---

## 🏃 Первый запуск

### Вариант 1: Простой тест

```bash
python examples/simple_test.py
```

**Что делает:**
- Проверяет настройки
- Запрашивает цену `pistol-pm`
- Синхронизирует 5 предметов
- Показывает статистику БД

**Ожидаемый результат:**
```
════════════════════════════════════════════════════════════
SC-CraftX API v2 — Тестирование
════════════════════════════════════════════════════════════

Регион: ru
API Base: https://eapi.stalcraft.net
Cache TTL: 180s
Sync Interval: 45s

════════════════════════════════════════════════════════════
ТЕСТ 1: Получение цены одного предмета
════════════════════════════════════════════════════════════

Запрос цены для: pistol-pm

📊 Статистика для pistol-pm:
  Сделок: 48
  Мин. цена: 12,500 ₽
  Средняя: 15,320 ₽
  Макс. цена: 18,900 ₽
  Ликвидность: high
  Продаж в час: 8.0
  Временной диапазон: 6.2 ч

✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!
```

### Вариант 2: PyQt6 пример

```bash
python examples/pyqt6_example.py
```

**Что делает:**
- Открывает GUI окно
- Показывает кнопки синхронизации
- Демонстрирует прогресс
- Логирует все обновления

---

## 🔗 Интеграция с твоим UI

### Простой способ (для начала)

```python
from PyQt6.QtWidgets import QMainWindow, QLabel
from api_v2 import PriceSyncManager, PriceStats

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Создаём менеджер
        self.sync_manager = PriceSyncManager()
        
        # Подключаем сигнал
        self.sync_manager.price_updated.connect(self.on_price_update)
        
        # UI элемент
        self.price_label = QLabel("Цена: загрузка...")
        self.setCentralWidget(self.price_label)
        
        # Запрашиваем цену
        self.sync_manager.fetch_price("pistol-pm")
    
    def on_price_update(self, item_id: str, stats: PriceStats):
        # Обновляем UI (вызывается автоматически!)
        self.price_label.setText(f"Цена {item_id}: {stats.avg_price} ₽")
    
    def closeEvent(self, event):
        self.sync_manager.cleanup()
        event.accept()
```

### Продвинутый способ (авто-синхронизация)

```python
from api_v2 import AutoSyncManager

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Список предметов для отслеживания
        items = ["pistol-pm", "rifle-akm", "ammo-9x18-pm"]
        
        # Создаём авто-менеджер
        self.sync_manager = AutoSyncManager(
            item_ids=items,
            interval_seconds=60  # Обновлять каждую минуту
        )
        
        # Подключаем сигналы
        self.sync_manager.price_updated.connect(self.on_price_update)
        self.sync_manager.sync_progress.connect(self.on_progress)
        
        # Запускаем автообновление
        self.sync_manager.start_auto_sync(include_lots=True)
    
    def on_price_update(self, item_id: str, stats: PriceStats):
        print(f"{item_id}: {stats.avg_price} ₽")
    
    def on_progress(self, progress):
        print(f"Прогресс: {progress.progress_percent:.0f}%")
```

### Замена старого кода

**Было:**
```python
from api.client import ApiClient

# Где-то в твоём UI коде
def load_price(self, item_id):
    client = ApiClient()
    stats = client.get_price_stats(item_id)  # БЛОКИРУЕТ UI!
    self.label.setText(f"{stats.avg} ₽")
```

**Стало:**
```python
from api_v2 import PriceSyncManager

# В __init__:
self.sync_manager = PriceSyncManager()
self.sync_manager.price_updated.connect(self.on_price_update)

# Запрос:
def load_price(self, item_id):
    self.sync_manager.fetch_price(item_id)  # НЕ блокирует!

# Обработчик:
def on_price_update(self, item_id: str, stats):
    self.label.setText(f"{stats.avg_price} ₽")
```

---

## 🐛 Troubleshooting

### Ошибка: "STALCRAFT_CLIENT_ID не установлен"

**Причина:** Не создан `.env` файл или пустые значения.

**Решение:**
1. Скопируй `.env.example` в `.env`
2. Заполни `STALCRAFT_CLIENT_ID` и `STALCRAFT_CLIENT_SECRET`
3. Проверь что нет лишних пробелов

### Ошибка: "401 Unauthorized"

**Причина:** Неверные credentials.

**Решение:**
1. Проверь что `CLIENT_ID` и `CLIENT_SECRET` скопированы правильно
2. Убедись что токены активны на https://exbo.net/oauth/applications
3. Попробуй создать новое приложение

### Ошибка: "429 Too Many Requests"

**Причина:** Слишком много запросов к API.

**Решение:**
1. Увеличь `MIN_REQUEST_INTERVAL` (например, 0.6)
2. Уменьши `MAX_CONCURRENT_REQUESTS` (например, 2)
3. Увеличь `SYNC_INTERVAL` для авто-синхронизации

### UI зависает

**Причина:** Используешь старый API или блокирующие вызовы.

**Решение:**
- ✅ Используй `PriceSyncManager` (не прямой вызов клиента)
- ✅ Подключай через сигналы
- ❌ НЕ вызывай `asyncio.run()` из UI потока

### Данные не обновляются

**Причина:** Кэш устарел, но TTL не истёк.

**Решение:**
```python
# Принудительное обновление (игнорировать кэш)
self.sync_manager.fetch_price(item_id, use_cache=False)

# ИЛИ: инвалидировать кэш вручную
from api_v2 import get_database
db = await get_database()
await db.invalidate_cache(item_id)
```

### ModuleNotFoundError: stalcraft

**Причина:** Не установлена библиотека.

**Решение:**
```bash
pip install stalcraft-api --upgrade
```

---

## 📚 Дальнейшие шаги

### 1. Изучи примеры

- `examples/simple_test.py` — базовое использование
- `examples/pyqt6_example.py` — полный пример с GUI

### 2. Прочитай документацию

- `api_v2/README.md` — полная документация API
- `CHANGELOG_V2.md` — что изменилось

### 3. Адаптируй под свой проект

Основные точки интеграции:

1. **Замени старые импорты:**
   ```python
   # Было
   from api.client import ApiClient
   
   # Стало
   from api_v2 import PriceSyncManager
   ```

2. **Используй сигналы вместо прямых вызовов:**
   ```python
   # Было
   stats = client.get_price_stats(item_id)
   
   # Стало
   self.sync_manager.price_updated.connect(callback)
   self.sync_manager.fetch_price(item_id)
   ```

3. **Добавь auto-sync для фоновых обновлений:**
   ```python
   self.sync_manager = AutoSyncManager(items, interval_seconds=60)
   self.sync_manager.start_auto_sync()
   ```

---

## 💡 Советы

### Производительность

- Используй `use_cache=True` (default) для частых запросов
- Группируй запросы через `sync_prices()` вместо по одному
- Настрой `SYNC_INTERVAL` под свои нужды (30-300s)

### Надёжность

- Всегда вызывай `cleanup()` при закрытии окна
- Обрабатывай сигнал `error` для показа уведомлений
- Логи помогают — смотри `logs/stalcraft.log`

### Безопасность

- **НЕ** коммить `.env` в git (добавь в `.gitignore`)
- **НЕ** показывай `CLIENT_SECRET` в UI или логах
- Храни credentials только локально

---

## ✅ Чеклист готовности

- [ ] Установлены все зависимости
- [ ] Создан `.env` с credentials
- [ ] Тест `simple_test.py` проходит успешно
- [ ] Понимаю как использовать `PriceSyncManager`
- [ ] Интегрировал в свой UI через сигналы
- [ ] Настроил автообновление (опционально)

---

**Готов к работе! Удачи с SC-CraftX! 🎮**

Если возникнут вопросы — проверь `api_v2/README.md` или изучи примеры в `examples/`.
