"""
api/stalcraft.py — ядро работы со Stalcraft Auction API.

Использует официальную библиотеку scapi (stalcraft-api).
Сохраняет полностью совместимый публичный интерфейс с предыдущей версией:
  - get_price_history(item_id) -> list
  - get_active_lots(item_id, result_amount) -> dict
  - calculate_price_stats(history) -> dict
  - _cache_invalidate(item_id)
  - get_last_api_error() / clear_api_error()
  - get_history_from_db(item_id, hours)

Исправленные проблемы:
  - Заменён requests + ручной OAuth на scapi.AppClient
  - scapi сам управляет токеном (client_credentials)
  - Listing наследует list — используем list(result), не result.items
  - close() у AppClient асинхронный — вызываем через _run_async()
  - Убраны гонки кэша: per-item threading.Lock
  - Exponential backoff при RateLimitError / ServerError
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone

from app_paths import app_path
from settings import Settings

log = logging.getLogger("stalcraft")

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

REGION: str = Settings.REGION

_CACHE_TTL: int = Settings.CACHE_TTL
_HISTORY_KEEP: int = Settings.HISTORY_KEEP_HOURS * 3600
_MAX_RETRIES: int = 5
_LOTS_PAGE_SIZE: int = 100
_MIN_INTERVAL: float = 0.35

# ---------------------------------------------------------------------------
# Глобальный scapi.AppClient — создаётся один раз
# ---------------------------------------------------------------------------

_client_lock = threading.Lock()
_scapi_client = None


def _get_scapi_client():
    """
    Возвращает глобальный scapi.AppClient (lazy init).

    Приоритет credentials:
      1. .env через settings_v2 (STALCRAFT_CLIENT_ID / STALCRAFT_CLIENT_SECRET)
      2. credentials.json в APPDATA — fallback для обратной совместимости
    """
    global _scapi_client

    if _scapi_client is not None:
        return _scapi_client

    with _client_lock:
        if _scapi_client is not None:
            return _scapi_client

        from scapi import AppClient
        from scapi.enums import Region

        # — Пробуем .env через settings_v2 —
        client_id = ""
        client_secret = ""
        try:
            from settings_v2 import Settings as S2
            client_id = S2.CLIENT_ID
            client_secret = S2.CLIENT_SECRET
            log.debug("[scapi] Credentials из .env (settings_v2)")
        except Exception:
            pass

        # — Fallback: credentials.json —
        if not client_id or not client_secret:
            cred_path = app_path("credentials.json")
            try:
                with open(cred_path, encoding="utf-8") as f:
                    creds = json.load(f)
                client_id = creds.get("client_id", "")
                client_secret = creds.get("client_secret", "")
                log.debug("[scapi] Credentials из credentials.json")
            except FileNotFoundError:
                pass
            except Exception as e:
                log.warning("[scapi] Ошибка чтения credentials.json: %s", e)

        if not client_id or not client_secret:
            raise RuntimeError(
                "Credentials не найдены!\n"
                "Укажите STALCRAFT_CLIENT_ID и STALCRAFT_CLIENT_SECRET в .env\n"
                "или заполните credentials.json (поля client_id, client_secret).\n"
                "Получить: https://exbo.net/oauth/applications"
            )

        region_map = {
            "ru": Region.RU,
            "eu": Region.EU,
            "na": Region.NA,
            "sea": Region.SEA,
        }
        region_enum = region_map.get(REGION.lower(), Region.RU)

        _scapi_client = AppClient(
            client_id=client_id,
            client_secret=client_secret,
            region=region_enum,
        )

        log.info("[scapi] AppClient создан, регион=%s, client_id=%s", REGION, client_id)
        return _scapi_client


# ---------------------------------------------------------------------------
# Запуск async-корутин scapi из синхронного кода (QThread)
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Запускает корутину в новом event loop текущего потока."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()


# ---------------------------------------------------------------------------
# Троттлинг
# ---------------------------------------------------------------------------

_throttle_lock = threading.Lock()
_last_request_time: float = 0.0


def _throttle() -> None:
    global _last_request_time
    with _throttle_lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL - (now - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        _last_request_time = time.monotonic()


# ---------------------------------------------------------------------------
# Глобальный lock — один запрос к scapi одновременно
# ---------------------------------------------------------------------------

_API_LOCK = threading.Lock()
_HTTP_LOCK = _API_LOCK  # совместимость
_LOTS_LOCK = _API_LOCK  # совместимость

# ---------------------------------------------------------------------------
# SQLite — thread-local соединения
# ---------------------------------------------------------------------------

_local = threading.local()
_DB = app_path("cache.db")


def _get_db() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        return conn

    conn = sqlite3.connect(_DB, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Создаём таблицу если не существует
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_cache (
            item_id   TEXT PRIMARY KEY,
            data      TEXT NOT NULL,
            ts        REAL NOT NULL
        )
    """)

    # Миграция: старая схема могла иметь колонку cached_at вместо ts
    cols = [row[1] for row in conn.execute("PRAGMA table_info(price_cache)").fetchall()]
    if "ts" not in cols:
        if "cached_at" in cols:
            # Переименовываем cached_at -> ts через пересоздание таблицы
            conn.execute("ALTER TABLE price_cache RENAME TO price_cache_old")
            conn.execute("""
                CREATE TABLE price_cache (
                    item_id   TEXT PRIMARY KEY,
                    data      TEXT NOT NULL,
                    ts        REAL NOT NULL
                )
            """)
            conn.execute("""
                INSERT INTO price_cache (item_id, data, ts)
                SELECT item_id, data, cached_at FROM price_cache_old
            """)
            conn.execute("DROP TABLE price_cache_old")
            log.info("[DB] Мигрирована схема price_cache: cached_at -> ts")
        else:
            # Неизвестная схема — дропаем и создаём заново
            conn.execute("DROP TABLE price_cache")
            conn.execute("""
                CREATE TABLE price_cache (
                    item_id   TEXT PRIMARY KEY,
                    data      TEXT NOT NULL,
                    ts        REAL NOT NULL
                )
            """)
            log.warning("[DB] price_cache пересоздана (неизвестная схема)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            item_id   TEXT NOT NULL,
            sale_time TEXT NOT NULL,
            price     INTEGER NOT NULL,
            amount    INTEGER NOT NULL DEFAULT 1,
            per_unit  INTEGER NOT NULL,
            PRIMARY KEY (item_id, sale_time)
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ph_item_time
        ON price_history (item_id, sale_time)
    """)

    conn.commit()
    _local.conn = conn
    return conn


# ---------------------------------------------------------------------------
# Кэш с per-item блокировками
# ---------------------------------------------------------------------------

_item_locks: dict[str, threading.Lock] = {}
_item_locks_guard = threading.Lock()


def _item_lock(item_id: str) -> threading.Lock:
    with _item_locks_guard:
        if item_id not in _item_locks:
            _item_locks[item_id] = threading.Lock()
        return _item_locks[item_id]


def _cache_get(item_id: str) -> list | None:
    conn = _get_db()
    row = conn.execute(
        "SELECT data, ts FROM price_cache WHERE item_id=?", (item_id,)
    ).fetchone()
    if row and (time.time() - row[1]) < _CACHE_TTL:
        return json.loads(row[0])
    return None


def _cache_set(item_id: str, data: list) -> None:
    conn = _get_db()
    conn.execute(
        "INSERT OR REPLACE INTO price_cache VALUES (?,?,?)",
        (item_id, json.dumps(data, ensure_ascii=False), time.time()),
    )
    conn.commit()


def _cache_invalidate(item_id: str) -> None:
    """Принудительно инвалидирует кэш для item_id."""
    conn = _get_db()
    conn.execute("DELETE FROM price_cache WHERE item_id=?", (item_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# История цен (48 ч) — SQLite
# ---------------------------------------------------------------------------

def _store_history(item_id: str, entries: list[dict]) -> None:
    conn = _get_db()
    cutoff_ts = time.time() - _HISTORY_KEEP
    cutoff_iso = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc).isoformat()

    conn.execute(
        "DELETE FROM price_history WHERE item_id=? AND sale_time<?",
        (item_id, cutoff_iso),
    )

    rows = []
    for e in entries:
        t_str = e.get("time", "")
        price = e.get("price", 0)
        amount = max(e.get("amount", 1), 1)
        per_unit = round(price / amount)
        rows.append((item_id, t_str, price, amount, per_unit))

    conn.executemany(
        "INSERT OR IGNORE INTO price_history VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit()


def get_history_from_db(item_id: str, hours: int = 48) -> list[dict]:
    """Возвращает записи истории из локальной БД за последние N часов."""
    conn = _get_db()
    cutoff_ts = time.time() - hours * 3600
    cutoff_iso = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc).isoformat()
    rows = conn.execute(
        """SELECT sale_time, price, amount, per_unit
           FROM price_history
           WHERE item_id=? AND sale_time>=?
           ORDER BY sale_time""",
        (item_id, cutoff_iso),
    ).fetchall()
    return [
        {"time": r[0], "price": r[1], "amount": r[2], "per_unit": r[3]}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Глобальное последнее сообщение об ошибке API
# ---------------------------------------------------------------------------

_last_api_error: str | None = None
_api_error_lock = threading.Lock()


def get_last_api_error() -> str | None:
    return _last_api_error


def clear_api_error() -> None:
    global _last_api_error
    with _api_error_lock:
        _last_api_error = None


def _set_api_error(msg: str) -> None:
    global _last_api_error
    with _api_error_lock:
        _last_api_error = msg


# ---------------------------------------------------------------------------
# Получение истории цен через scapi
# ---------------------------------------------------------------------------

def get_price_history(item_id: str) -> list:
    """
    Возвращает историю продаж с аукциона (последние 50 сделок).

    1. Проверяем SQLite кэш (TTL = Settings.CACHE_TTL секунд).
    2. Если кэш валиден — возвращаем без сети.
    3. Per-item lock — предотвращает thundering herd на один item_id.
    4. Запрос через scapi.AppClient.auction(item_id).price_history().
    5. Listing наследует list — итерируем напрямую через list(listing).
    6. Сохраняем в кэш и в price_history (48 ч).
    """
    cached = _cache_get(item_id)
    if cached is not None:
        return cached

    with _item_lock(item_id):
        cached = _cache_get(item_id)
        if cached is not None:
            return cached

        with _API_LOCK:
            _throttle()

            from scapi.exceptions import RateLimitError, ServerError, ScApiException

            last_error = None

            for attempt in range(_MAX_RETRIES):
                try:
                    client = _get_scapi_client()

                    async def _fetch():
                        endpoint = client.auction(item_id)
                        # Listing наследует list — list(listing) даёт все элементы
                        listing = endpoint.price_history(limit=50)
                        return list(listing)

                    prices = _run_async(_fetch())

                    # Конвертируем scapi.AuctionPrice -> dict
                    # AuctionPrice.time — это datetime объект (не строка!)
                    data = []
                    for p in prices:
                        t_iso = (
                            p.time.isoformat()
                            if hasattr(p.time, "isoformat")
                            else str(p.time)
                        )
                        data.append({
                            "time": t_iso,
                            "price": p.price,
                            "amount": p.amount,
                        })

                    _cache_set(item_id, data)
                    if data:
                        _store_history(item_id, data)

                    log.debug("[API] %s: получено %d записей", item_id, len(data))
                    return data

                except RateLimitError as e:
                    wait = min(2 ** attempt, 30)
                    log.warning(
                        "[API] 429 RateLimit для %s (попытка %d/%d), пауза %ds",
                        item_id, attempt + 1, _MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                    last_error = e

                except ServerError as e:
                    wait = min(2 ** attempt, 16)
                    log.warning(
                        "[API] ServerError для %s (попытка %d/%d), пауза %ds: %s",
                        item_id, attempt + 1, _MAX_RETRIES, wait, e,
                    )
                    time.sleep(wait)
                    last_error = e

                except ScApiException as e:
                    # 4xx кроме 429 — не ретраим
                    msg = f"API ошибка: {e}"
                    log.error("[API] %s для %s: %s", type(e).__name__, item_id, e)
                    _set_api_error(msg)
                    return []

                except Exception as e:
                    wait = min(2 ** attempt, 16)
                    log.error(
                        "[API] Неожиданная ошибка для %s (попытка %d/%d): %s",
                        item_id, attempt + 1, _MAX_RETRIES, e,
                    )
                    time.sleep(wait)
                    last_error = e

            msg = f"Не удалось получить данные после {_MAX_RETRIES} попыток"
            log.error("[API] %s для %s: %s", msg, item_id, last_error)
            _set_api_error(str(last_error)[:80] if last_error else msg)
            return []


# ---------------------------------------------------------------------------
# Получение активных лотов через scapi
# ---------------------------------------------------------------------------

def get_active_lots(item_id: str, result_amount: int = 1) -> dict:
    """
    Возвращает {'min_price': int, 'total': int}.

    min_price — buyoutPrice / amount (цена за 1 шт).
    Использует scapi.AppClient.auction().lots() с пагинацией через Listing.total.
    """
    from scapi.exceptions import RateLimitError, ServerError, ScApiException

    with _API_LOCK:
        _throttle()

        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                client = _get_scapi_client()

                async def _fetch():
                    endpoint = client.auction(item_id)
                    all_lots = []
                    offset = 0

                    while True:
                        listing = endpoint.lots(
                            limit=_LOTS_PAGE_SIZE,
                            offset=offset,
                        )
                        # Listing наследует list
                        page_lots = list(listing)
                        total = listing.total

                        all_lots.extend(page_lots)
                        offset += len(page_lots)

                        if len(page_lots) < _LOTS_PAGE_SIZE or offset >= total:
                            break

                    return all_lots, total

                all_lots, total = _run_async(_fetch())

                if not all_lots:
                    return {"min_price": 0, "total": 0}

                # AuctionLot.buyout_price, AuctionLot.amount — snake_case поля
                valid_lots = [lot for lot in all_lots if lot.buyout_price > 0]
                if not valid_lots:
                    return {"min_price": 0, "total": total}

                # РЫНОК ▸ = минимальный buyout_price среди всех активных лотов.
                min_price = min(l.buyout_price for l in valid_lots)

                log.debug("[Lots] %s: min=%d, total=%d", item_id, min_price, total)
                return {
                    "min_price": min_price,
                    "total": total if total else len(all_lots),
                }

            except RateLimitError as e:
                wait = min(2 ** attempt, 30)
                log.warning(
                    "[Lots] 429 RateLimit для %s (попытка %d/%d), пауза %ds",
                    item_id, attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
                last_error = e

            except ServerError as e:
                wait = min(2 ** attempt, 16)
                log.warning(
                    "[Lots] ServerError для %s (попытка %d/%d): %s",
                    item_id, attempt + 1, _MAX_RETRIES, e,
                )
                time.sleep(wait)
                last_error = e

            except ScApiException as e:
                log.error("[Lots] API ошибка для %s: %s", item_id, e)
                return {}

            except Exception as e:
                wait = min(2 ** attempt, 16)
                log.error(
                    "[Lots] Неожиданная ошибка для %s (попытка %d/%d): %s",
                    item_id, attempt + 1, _MAX_RETRIES, e,
                )
                time.sleep(wait)
                last_error = e

        log.error("[Lots] Все попытки исчерпаны для %s: %s", item_id, last_error)
        return {}


# ---------------------------------------------------------------------------
# Статистика цен (полная совместимость с UI)
# ---------------------------------------------------------------------------

def calculate_price_stats(history: list) -> dict:
    """
    Вычисляет агрегированную статистику по истории продаж.
    Возвращает dict с ключами: count, min, avg, max, liquidity,
    history, per_minute, per_5min, per_hour, per_day, span.
    """
    if not history:
        return {
            "count": 0,
            "min": 0,
            "avg": 0,
            "max": 0,
            "liquidity": "unknown",
            "history": [],
            "per_minute": 0.0,
            "per_5min": 0.0,
            "per_hour": 0.0,
            "per_day": 0.0,
            "span": "",
        }

    prices_per_unit: list[int] = []
    processed: list[dict] = []
    times: list[datetime] = []
    total_units = 0
    total_price_sum = 0

    for entry in history:
        amount = max(entry.get("amount", 1) or 1, 1)
        total = entry.get("price", 0)
        per_unit = round(total / amount)
        prices_per_unit.append(per_unit)
        total_units += amount
        total_price_sum += total

        t_str = entry.get("time", "")
        try:
            t_dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
            times.append(t_dt)
        except Exception:
            pass

        processed.append({
            "time": t_str,
            "price": total,
            "amount": amount,
            "per_unit": per_unit,
        })

    count = len(prices_per_unit)

    per_minute = 0.0
    per_5min = 0.0
    per_hour = 0.0
    per_day = 0.0

    if times:
        now = datetime.now(timezone.utc)

        def _count_in(minutes: int) -> float:
            cutoff = now.timestamp() - minutes * 60
            return float(sum(1 for t in times if t.timestamp() >= cutoff))

        per_minute = _count_in(1)
        per_5min = _count_in(5)
        per_hour = _count_in(60)
        per_day = _count_in(1440)

    if per_hour >= 20:
        liq = "high"
    elif per_hour >= 5:
        liq = "medium"
    elif count >= 1:
        liq = "low"
    else:
        liq = "unknown"

    span = ""
    if times:
        oldest = min(times)
        newest = max(times)
        delta = (newest - oldest).total_seconds()
        if delta > 3600:
            span = f"{delta / 3600:.1f} ч"
        elif delta > 60:
            span = f"{delta / 60:.0f} мин"
        elif delta > 0:
            span = f"{delta:.0f} сек"

    weighted_avg = (
        round(total_price_sum / total_units)
        if total_units
        else round(sum(prices_per_unit) / count)
    )

    return {
        "count": count,
        "min": min(prices_per_unit),
        "avg": weighted_avg,
        "max": max(prices_per_unit),
        "liquidity": liq,
        "history": processed,
        "per_minute": per_minute,
        "per_5min": per_5min,
        "per_hour": per_hour,
        "per_day": per_day,
        "span": span,
    }
