"""
settings.py — централизованная конфигурация приложения.

Читает значения из .env (если файл есть), с разумными дефолтами.
python-dotenv опционален — если не установлен, работает без .env.

Импортируй откуда угодно:
    from settings import Settings
    print(Settings.API_BASE)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

# Пытаемся подгрузить .env — не падаем если python-dotenv не установлен
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env", override=False)
except ImportError:
    pass


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


def _str(key: str, default: str) -> str:
    return os.getenv(key, default)


class Settings:
    # ── API ──────────────────────────────────────────────────────────────────
    API_BASE: str = _str("STALCRAFT_API_BASE", "https://eapi.stalcraft.net")
    REGION: str = _str("STALCRAFT_REGION", "ru")

    # ── Кэш / история ────────────────────────────────────────────────────────
    CACHE_TTL: int = _int("CACHE_TTL", 180)
    HISTORY_KEEP_HOURS: int = _int("HISTORY_KEEP_HOURS", 48)

    # ── Concurrency ───────────────────────────────────────────────────────────
    HTTP_CONCURRENCY: int = _int("HTTP_CONCURRENCY", 6)
    LOTS_CONCURRENCY: int = _int("LOTS_CONCURRENCY", 2)

    # ── collect_prices ────────────────────────────────────────────────────────
    COLLECT_WORKERS: int = _int("COLLECT_WORKERS", 4)
    COLLECT_SKIP_FRESH_SEC: int = _int("COLLECT_SKIP_FRESH_SEC", 300)

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = _str("LOG_LEVEL", "INFO")


def configure_logging() -> None:
    """Настраивает корневой логгер по значению Settings.LOG_LEVEL."""
    level = getattr(logging, Settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
