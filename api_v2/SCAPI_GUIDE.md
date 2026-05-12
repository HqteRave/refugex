# 📘 SC-CraftX API v2 — Интеграция с scapi

## Что такое scapi?

`scapi` — это **внутреннее имя модуля** библиотеки `stalcraft-api` v2.1.1.

```bash
pip install stalcraft-api   # Устанавливает пакет stalcraft-api
import scapi                 # Но импортируется как scapi!
```

---

## Почему scapi, а не stalcraft?

Когда ты устанавливаешь `stalcraft-api`, внутри создаётся модуль `scapi`:

```
site-packages/
├── stalcraft_api-2.1.1.dist-info/  ← Метаданные пакета
└── scapi/                           ← Сам код библиотеки
    ├── __init__.py
    ├── client/
    ├── enums.py
    └── exceptions.py
```

Поэтому правильный импорт:
```python
from scapi import AppClient  # ✅ Правильно
from stalcraft import ...    # ❌ Ошибка!
```

---

## Как работает наш клиент

### 1. scapi.AppClient — синхронный

`scapi.AppClient` работает **синхронно** (блокирует поток):

```python
from scapi import AppClient

client = AppClient(client_id='...', client_secret='...')
auction = client.auction('pistol-pm')
history = auction.price_history(limit=50)  # Блокирует!
```

### 2. Наша обёртка — асинхронная

Мы обернули `scapi` в асинхронный интерфейс через `asyncio.to_thread`:

```python
# api_v2/client.py

async def get_price_history(self, item_id: str):
    def _fetch():
        # Синхронный вызов scapi
        auction = self._client.auction(item_id)
        result = auction.price_history(limit=50)
        return result.items
    
    # Выполняем в отдельном потоке (не блокирует event loop)
    prices = await asyncio.to_thread(_fetch)
    return prices
```

---

## Основные компоненты scapi

### AppClient

```python
from scapi import AppClient

client = AppClient(
    client_id='твой_id',
    client_secret='твой_secret',
    region='ru',  # или Region.RU
    base_url='https://eapi.stalcraft.net'
)
```

**Методы:**
- `client.auction(item_id)` → `AuctionEndpoint`
- `client.clan(clan_id)` → `ClanEndpoint`
- `client.emission()` → `EmissionState`
- `client.profile(username)` → `CharacterProfile`
- `client.close()` — закрыть соединение

### AuctionEndpoint

```python
auction = client.auction('pistol-pm')

# История продаж
history = auction.price_history(limit=50)
# → Listing[AuctionPrice]

# Активные лоты
lots = auction.lots(limit=100)
# → Listing[AuctionLot]
```

### Модели данных

**AuctionPrice** (история):
```python
class AuctionPrice:
    amount: int          # Количество
    price: int           # Общая цена
    time: datetime       # Время сделки
```

**AuctionLot** (активный лот):
```python
class AuctionLot:
    item_id: str
    amount: int
    buyout_price: int
    start_time: datetime
    end_time: datetime
```

### Исключения

```python
from scapi.exceptions import (
    ScApiException,      # Базовое
    RateLimitError,      # 429
    UnauthorizedError,   # 401
    ClientError,         # 4xx
    ServerError          # 5xx
)
```

---

## Как мы адаптировали scapi

### 1. Асинхронность

```python
# scapi (sync)
history = auction.price_history(limit=50)

# Наша обёртка (async)
history = await client.get_price_history(item_id)
```

### 2. Rate Limiting

```python
async def _execute_with_retry(self, func, *args):
    for attempt in range(max_retries):
        try:
            result = await asyncio.to_thread(func, *args)
            return result
        except RateLimitError:
            wait = BACKOFF_BASE ** attempt
            await asyncio.sleep(wait)
```

### 3. Кэширование

```python
async def get_price_history(self, item_id: str):
    # 1. Проверяем SQLite кэш
    cached = await db.get_cached_price(item_id)
    if cached:
        return cached
    
    # 2. Запрос к scapi
    prices = await self._execute_with_retry(...)
    
    # 3. Сохраняем в кэш
    await db.set_cached_price(item_id, prices)
```

### 4. Конвертация моделей

```python
# scapi модель → наша модель
scapi_prices: list[AuctionPrice] = ...

entries = [
    AuctionPriceEntry(
        time=price.time.isoformat(),
        price=price.price,
        amount=price.amount
    )
    for price in scapi_prices
]
```

---

## Преимущества использования scapi

✅ **Официальная библиотека** — поддержка разработчиков  
✅ **Автоматическое управление OAuth** — не нужно вручную обновлять токены  
✅ **Типизированные модели** — Pydantic из коробки  
✅ **Обработка ошибок** — встроенные исключения  
✅ **Поддержка всех endpoint'ов** — не только auction  

---

## Пример использования

```python
import asyncio
from api_v2 import create_client

async def main():
    async with create_client() as client:
        # Получить статистику
        stats = await client.get_price_stats("pistol-pm")
        
        print(f"Средняя цена: {stats.avg_price} ₽")
        print(f"Сделок: {stats.count}")
        print(f"Ликвидность: {stats.liquidity}")

asyncio.run(main())
```

---

## Troubleshooting

### ModuleNotFoundError: No module named 'stalcraft'

**Проблема:** Пытаешься импортировать `stalcraft` вместо `scapi`

**Решение:**
```python
from scapi import AppClient  # ✅ Правильно
```

### CredentialsError: Missing required credentials

**Проблема:** Не указаны `client_id` и `client_secret`

**Решение:** Проверь `.env` файл:
```env
STALCRAFT_CLIENT_ID=твой_id
STALCRAFT_CLIENT_SECRET=твой_secret
```

### RateLimitError (429)

**Проблема:** Слишком много запросов

**Решение:** Наш клиент автоматически делает retry с exponential backoff. Если проблема сохраняется:
- Увеличь `MIN_REQUEST_INTERVAL` в `.env`
- Уменьши `MAX_CONCURRENT_REQUESTS`

---

## Ссылки

- **PyPI:** https://pypi.org/project/stalcraft-api/
- **Документация scapi:** (пока отсутствует на сайте)
- **Stalcraft API:** https://eapi.stalcraft.net/

---

**Версия:** API v2.0 + scapi 2.1.1  
**Дата:** 2025-05-10
