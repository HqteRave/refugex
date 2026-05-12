"""
api/client.py — высокоуровневый клиент для UI.

Предоставляет:
  - PriceStats: Pydantic-модель результата запроса цены
  - ApiClient.get_price_stats() — история + статистика + fallback
  - ApiClient.get_price_history_local() — данные из локальной БД (48 ч, без API)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Literal

from .stalcraft import (
    calculate_price_stats,
    get_history_from_db,
    get_price_history,
)
from app_paths import asset_path

log = logging.getLogger("stalcraft.client")

_PRICES_DB_PATH = asset_path("prices_database.json")
_prices_db: dict | None = None


# ---------------------------------------------------------------------------
# Модель результата (dataclass — без внешних зависимостей)
# ---------------------------------------------------------------------------

@dataclass
class PriceStats:
    """Агрегированная статистика цен для одного предмета."""

    count: int = 0
    min: int = 0
    avg: int = 0
    max: int = 0
    liquidity: str = "unknown"
    history: list = field(default_factory=list)
    per_minute: float = 0.0
    per_5min: float = 0.0
    per_hour: float = 0.0
    per_day: float = 0.0
    span: str = ""
    from_cache_db: bool = False   # True — данные из prices_database.json, не из API
    market_min: int = 0           # мин. цена активного лота (для калькулятора)
    market_total: int = 0         # кол-во активных лотов

    def is_empty(self) -> bool:
        return self.count == 0 and self.avg == 0

    def model_dump(self) -> dict:
        """Совместимость с кодом, который ожидает Pydantic-интерфейс."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Загрузка локального снэпшота prices_database.json
# ---------------------------------------------------------------------------

def _load_prices_db() -> dict:
    global _prices_db
    if _prices_db is None:
        try:
            with open(_PRICES_DB_PATH, encoding="utf-8") as f:
                _prices_db = json.load(f)
            log.debug("prices_database.json загружен (%d записей)", len(_prices_db))
        except Exception as e:
            log.warning("Не удалось загрузить prices_database.json: %s", e)
            _prices_db = {}
    return _prices_db


def reload_prices_db() -> None:
    """Сбрасывает кэш prices_database.json — для вызова после collect_prices."""
    global _prices_db
    _prices_db = None


def _fallback_stats(item_id: str) -> PriceStats | None:
    """Возвращает статистику из prices_database.json если API недоступен."""
    db = _load_prices_db()
    entry = db.get(item_id)
    if not entry:
        return None
    p = entry.get("price") or {}
    if not p.get("avg_price"):
        return None
    return PriceStats(
        count=p.get("count", 0),
        min=p.get("min_price", 0),
        avg=p.get("avg_price", 0),
        max=p.get("max_price", 0),
        liquidity=p.get("liquidity", "unknown"),
        per_hour=p.get("per_hour", 0.0),
        per_day=p.get("per_day", 0.0),
        from_cache_db=True,
    )


# ---------------------------------------------------------------------------
# ApiClient
# ---------------------------------------------------------------------------

class ApiClient:
    def get_instant_stats(self, item_id: str) -> PriceStats | None:
        """
        Возвращает данные МГНОВЕННО из prices_database.json или SQLite-кэша.
        Не делает сетевых запросов. None если данных нет совсем.
        """
        # Сначала пробуем SQLite-кэш (свежее чем prices_database.json)
        from .stalcraft import _cache_get, calculate_price_stats
        cached = _cache_get(item_id)
        if cached:
            raw = calculate_price_stats(cached)
            s = PriceStats(**raw)
            if not s.is_empty():
                return s

        # Затем prices_database.json
        return _fallback_stats(item_id)

    def get_price_stats(
        self,
        item_id: str,
        use_fallback: bool = True,
    ) -> PriceStats:
        """
        Возвращает PriceStats для item_id через API (медленно, но актуально).

        Порядок:
          1. Запрос к API (get_price_history).
          2. Если API вернул данные — рассчитываем статистику.
          3. Если нет данных — пробуем локальный снэпшот prices_database.json.
          4. Если и он пуст — возвращаем пустой PriceStats.
        """
        history = get_price_history(item_id)
        raw_stats = calculate_price_stats(history)
        stats = PriceStats(**raw_stats)

        if stats.is_empty() and use_fallback:
            fallback = _fallback_stats(item_id)
            if fallback:
                log.debug("[Client] %s: используем fallback из prices_database.json", item_id)
                return fallback

        return stats

    def get_price_history_local(
        self,
        item_id: str,
        hours: int = 48,
    ) -> list[dict]:
        """
        Возвращает историю из локальной SQLite (без API).
        Удобно для построения графика цен за последние 48 ч.
        """
        return get_history_from_db(item_id, hours=hours)
