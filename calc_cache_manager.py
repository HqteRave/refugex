"""
calc_cache_manager.py — Кэш цен для калькулятора крафта.

Хранит последние известные цены каждого предмета в calc_cache.json.
Позволяет мгновенно загружать калькулятор без обращения к API.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app_paths import app_path

log = logging.getLogger("calc_cache")

_CACHE_FILE = app_path("calc_cache.json")
_cache: dict = {}
_dirty = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load():
    global _cache
    try:
        with open(_CACHE_FILE, encoding="utf-8") as f:
            _cache = json.load(f)
    except FileNotFoundError:
        _cache = {}
    except Exception as e:
        log.warning("Ошибка загрузки calc_cache.json: %s", e)
        _cache = {}


def _save():
    global _dirty
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
        _dirty = False
    except Exception as e:
        log.error("Ошибка сохранения calc_cache.json: %s", e)


def get(item_id: str) -> Optional[dict]:
    """Возвращает кэшированные данные предмета или None."""
    if not _cache:
        _load()
    return _cache.get(item_id)


def get_stats(item_id: str) -> Optional[dict]:
    """Возвращает только stats из кэша."""
    entry = get(item_id)
    return entry.get("stats") if entry else None


def get_updated_at(item_id: str) -> Optional[datetime]:
    """Возвращает datetime последнего обновления или None."""
    entry = get(item_id)
    if not entry:
        return None
    try:
        return datetime.fromisoformat(entry["updated_at"])
    except Exception:
        return None


def set(item_id: str, stats: dict):
    """Сохраняет stats предмета с текущим временем."""
    global _dirty
    if not _cache and Path(_CACHE_FILE).exists():
        _load()
    _cache[item_id] = {
        "updated_at": _now_iso(),
        "stats": stats,
    }
    _dirty = True


def save_if_dirty():
    """Сохраняет файл только если были изменения."""
    if _dirty:
        _save()


def save():
    """Принудительно сохраняет файл."""
    _save()


def has_any() -> bool:
    """Есть ли хоть какие-то данные в кэше."""
    if not _cache:
        _load()
    return bool(_cache)


def is_stale(item_id: str, hours: int = 24) -> bool:
    """Возвращает True если данные устарели (> hours часов)."""
    updated = get_updated_at(item_id)
    if not updated:
        return True
    now = datetime.now(timezone.utc)
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (now - updated).total_seconds() > hours * 3600


def all_ids() -> list[str]:
    """Все item_id в кэше."""
    if not _cache:
        _load()
    return list(_cache.keys())


def load():
    """Явная загрузка кэша при старте."""
    _load()
