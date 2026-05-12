"""
settings.py — Централизованная конфигурация SC-CraftX

Поддерживает:
  - Загрузку из .env файла
  - Валидацию через Pydantic
  - Разумные дефолты для всех параметров
  - Автоматическую настройку логирования
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

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


def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


def _str(key: str, default: str) -> str:
    return os.getenv(key, default)


def _bool(key: str, default: bool) -> bool:
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


class Settings:
    """Настройки приложения SC-CraftX"""
    
    # ── API Credentials ──────────────────────────────────────────────────────
    CLIENT_ID: str = _str("STALCRAFT_CLIENT_ID", "")
    CLIENT_SECRET: str = _str("STALCRAFT_CLIENT_SECRET", "")
    
    # ── API Settings ─────────────────────────────────────────────────────────
    API_BASE: str = _str("STALCRAFT_API_BASE", "https://eapi.stalcraft.net")
    REGION: str = _str("STALCRAFT_REGION", "ru")
    
    # ── Cache & History ──────────────────────────────────────────────────────
    CACHE_TTL: int = _int("CACHE_TTL", 60)   # 1 минута — актуальные цены важнее скорости
    HISTORY_KEEP_HOURS: int = _int("HISTORY_KEEP_HOURS", 48)
    
    # ── Sync Settings ────────────────────────────────────────────────────────
    SYNC_INTERVAL: int = _int("SYNC_INTERVAL", 45)  # секунды между автообновлениями
    MAX_CONCURRENT_REQUESTS: int = _int("MAX_CONCURRENT_REQUESTS", 3)
    MIN_REQUEST_INTERVAL: float = _float("MIN_REQUEST_INTERVAL", 0.4)
    
    # ── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_BACKOFF_BASE: float = 2.0  # Базовая задержка для exponential backoff
    RATE_LIMIT_MAX_RETRIES: int = 5
    
    # ── Database ─────────────────────────────────────────────────────────────
    DB_PATH: str = _str("DB_PATH", "cache.db")
    
    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = _str("LOG_LEVEL", "INFO")
    LOG_TO_FILE: bool = _bool("LOG_TO_FILE", True)
    LOG_FILE_PATH: str = _str("LOG_FILE_PATH", "logs/stalcraft.log")
    
    @classmethod
    def validate(cls) -> list[str]:
        """Проверяет критичные настройки. Возвращает список ошибок."""
        errors = []
        
        if not cls.CLIENT_ID:
            errors.append("STALCRAFT_CLIENT_ID не установлен")
        if not cls.CLIENT_SECRET:
            errors.append("STALCRAFT_CLIENT_SECRET не установлен")
        
        if cls.REGION not in ("ru", "eu", "na", "sea"):
            errors.append(f"Некорректный STALCRAFT_REGION: {cls.REGION}")
        
        if cls.SYNC_INTERVAL < 30:
            errors.append(f"SYNC_INTERVAL слишком мал ({cls.SYNC_INTERVAL}s). Минимум: 30s")
        
        return errors


def configure_logging() -> None:
    """Настраивает систему логирования"""
    level = getattr(logging, Settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Формат логов
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Консольный handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # Файловый handler (опционально)
    if Settings.LOG_TO_FILE:
        try:
            log_path = Path(Settings.LOG_FILE_PATH)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logging.warning(f"Не удалось создать файловый логгер: {e}")
    
    # Отключаем лишние логи от библиотек
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
