"""
api_v2/database.py — Асинхронная работа с SQLite через aiosqlite

Преимущества перед sync версией:
  - Не блокирует event loop
  - Поддержка asyncio/await
  - Автоматическое управление соединениями
  - Безопасная конкурентная работа
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import aiosqlite

from .models import AuctionPriceEntry, PriceStats, CachedPrice, PriceHistoryEntry
from app_paths import app_path

log = logging.getLogger("stalcraft.database")


class Database:
    """Асинхронная обёртка над SQLite для кэширования цен"""
    
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = app_path(db_path)
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """Подключение к БД и инициализация схемы"""
        if self._connection is not None:
            return
        
        async with self._lock:
            if self._connection is not None:
                return
            
            self._connection = await aiosqlite.connect(
                self.db_path,
                isolation_level=None  # autocommit режим
            )
            
            # Оптимизация SQLite для наших задач
            await self._connection.execute("PRAGMA journal_mode=WAL")
            await self._connection.execute("PRAGMA synchronous=NORMAL")
            await self._connection.execute("PRAGMA cache_size=-64000")  # 64MB кэш
            await self._connection.execute("PRAGMA temp_store=MEMORY")
            
            await self._init_schema()
            
            log.info(f"База данных подключена: {self.db_path}")
    
    async def _init_schema(self) -> None:
        """Создание таблиц если их нет"""
        
        # Проверяем существующую схему и мигрируем при необходимости
        await self._migrate_schema()
        
        # Таблица кэша цен (TTL-based)
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS price_cache (
                item_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                cached_at REAL NOT NULL
            )
        """)
        
        # Таблица истории (хранение за 48 часов)
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                item_id TEXT NOT NULL,
                sale_time TEXT NOT NULL,
                price INTEGER NOT NULL,
                amount INTEGER NOT NULL DEFAULT 1,
                per_unit INTEGER NOT NULL,
                PRIMARY KEY (item_id, sale_time)
            )
        """)
        
        # Индексы для быстрого поиска
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_ph_item_time
            ON price_history (item_id, sale_time DESC)
        """)
        
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_time
            ON price_cache (cached_at)
        """)
        
        await self._connection.commit()
    
    async def _migrate_schema(self) -> None:
        """Миграция старой схемы БД (ts -> cached_at)"""
        try:
            # Проверяем существует ли таблица
            cursor = await self._connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='price_cache'"
            )
            table_exists = await cursor.fetchone()
            
            if not table_exists:
                return  # Таблицы нет, миграция не нужна
            
            # Проверяем схему
            cursor = await self._connection.execute("PRAGMA table_info(price_cache)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Если есть старая колонка 'ts' но нет 'cached_at' — мигрируем
            if 'ts' in column_names and 'cached_at' not in column_names:
                log.info("Обнаружена старая схема БД, выполняю миграцию...")
                
                # Создаём новую таблицу
                await self._connection.execute("""
                    CREATE TABLE price_cache_new (
                        item_id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        cached_at REAL NOT NULL
                    )
                """)
                
                # Копируем данные
                await self._connection.execute("""
                    INSERT INTO price_cache_new (item_id, data, cached_at)
                    SELECT item_id, data, ts FROM price_cache
                """)
                
                # Удаляем старую таблицу
                await self._connection.execute("DROP TABLE price_cache")
                
                # Переименовываем новую
                await self._connection.execute(
                    "ALTER TABLE price_cache_new RENAME TO price_cache"
                )
                
                await self._connection.commit()
                log.info("Миграция БД завершена успешно")
        
        except Exception as e:
            log.warning(f"Ошибка миграции БД (не критично): {e}")
    
    async def close(self) -> None:
        """Закрытие соединения"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            log.info("База данных закрыта")
    
    # ═══════════════════════════════════════════════════════════════════════
    # Работа с кэшем цен
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_cached_price(
        self,
        item_id: str,
        ttl_seconds: int = 180
    ) -> Optional[list[AuctionPriceEntry]]:
        """
        Получить кэшированную историю цен
        
        Returns:
            None если кэш отсутствует или устарел
        """
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT data, cached_at FROM price_cache WHERE item_id = ?",
                (item_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            data_json, cached_at = row
            
            # Проверка TTL
            age = datetime.now(timezone.utc).timestamp() - cached_at
            if age > ttl_seconds:
                log.debug(f"Кэш для {item_id} устарел ({age:.0f}s)")
                return None
            
            # Парсинг JSON в модели
            data_list = json.loads(data_json)
            return [AuctionPriceEntry(**entry) for entry in data_list]
    
    async def set_cached_price(
        self,
        item_id: str,
        entries: list[AuctionPriceEntry]
    ) -> None:
        """Сохранить историю цен в кэш"""
        data_json = json.dumps(
            [entry.model_dump() for entry in entries],
            ensure_ascii=False
        )
        
        cached_at = datetime.now(timezone.utc).timestamp()
        
        async with self._lock:
            await self._connection.execute(
                "INSERT OR REPLACE INTO price_cache (item_id, data, cached_at) VALUES (?, ?, ?)",
                (item_id, data_json, cached_at)
            )
            await self._connection.commit()
        
        log.debug(f"Кэш обновлён для {item_id} ({len(entries)} записей)")
    
    async def invalidate_cache(self, item_id: str) -> None:
        """Принудительно удалить кэш для item_id"""
        async with self._lock:
            await self._connection.execute(
                "DELETE FROM price_cache WHERE item_id = ?",
                (item_id,)
            )
            await self._connection.commit()
        
        log.debug(f"Кэш инвалидирован для {item_id}")
    
    async def cleanup_stale_cache(self, ttl_seconds: int = 3600) -> int:
        """
        Удалить устаревший кэш
        
        Returns:
            Количество удалённых записей
        """
        cutoff = datetime.now(timezone.utc).timestamp() - ttl_seconds
        
        async with self._lock:
            cursor = await self._connection.execute(
                "DELETE FROM price_cache WHERE cached_at < ?",
                (cutoff,)
            )
            await self._connection.commit()
            deleted = cursor.rowcount
        
        if deleted > 0:
            log.info(f"Удалено {deleted} устаревших записей кэша")
        
        return deleted
    
    # ═══════════════════════════════════════════════════════════════════════
    # Работа с историей цен (48 часов)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def store_history(
        self,
        item_id: str,
        entries: list[AuctionPriceEntry]
    ) -> None:
        """
        Добавить новые записи в историю
        
        - Дубликаты игнорируются (PRIMARY KEY)
        - Старые записи автоматически удаляются
        """
        if not entries:
            return
        
        # Подготовка данных
        rows = [
            (
                item_id,
                entry.time,
                entry.price,
                entry.amount,
                entry.per_unit
            )
            for entry in entries
        ]
        
        async with self._lock:
            # Удаляем старые записи
            await self._cleanup_old_history(item_id)
            
            # Вставляем новые (игнорируем дубли)
            await self._connection.executemany(
                "INSERT OR IGNORE INTO price_history VALUES (?, ?, ?, ?, ?)",
                rows
            )
            await self._connection.commit()
        
        log.debug(f"История обновлена для {item_id} (+{len(entries)} записей)")
    
    async def get_history(
        self,
        item_id: str,
        hours: int = 48
    ) -> list[AuctionPriceEntry]:
        """
        Получить историю из БД за последние N часов
        
        Полезно для построения графиков без обращения к API
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_iso = cutoff.isoformat()
        
        async with self._lock:
            cursor = await self._connection.execute(
                """
                SELECT sale_time, price, amount, per_unit
                FROM price_history
                WHERE item_id = ? AND sale_time >= ?
                ORDER BY sale_time ASC
                """,
                (item_id, cutoff_iso)
            )
            rows = await cursor.fetchall()
        
        return [
            AuctionPriceEntry(
                time=row[0],
                price=row[1],
                amount=row[2]
            )
            for row in rows
        ]
    
    async def _cleanup_old_history(
        self,
        item_id: str,
        keep_hours: int = 48
    ) -> None:
        """Удалить записи старше N часов для конкретного item_id"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=keep_hours)
        cutoff_iso = cutoff.isoformat()
        
        await self._connection.execute(
            "DELETE FROM price_history WHERE item_id = ? AND sale_time < ?",
            (item_id, cutoff_iso)
        )
    
    async def cleanup_old_history_all(self, keep_hours: int = 48) -> int:
        """
        Глобальная очистка истории для всех предметов
        
        Returns:
            Количество удалённых записей
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=keep_hours)
        cutoff_iso = cutoff.isoformat()
        
        async with self._lock:
            cursor = await self._connection.execute(
                "DELETE FROM price_history WHERE sale_time < ?",
                (cutoff_iso,)
            )
            await self._connection.commit()
            deleted = cursor.rowcount
        
        if deleted > 0:
            log.info(f"Удалено {deleted} старых записей истории")
        
        return deleted
    
    # ═══════════════════════════════════════════════════════════════════════
    # Статистика БД
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_stats(self) -> dict:
        """Получить статистику использования БД"""
        async with self._lock:
            # Количество кэшированных предметов
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM price_cache"
            )
            cache_count = (await cursor.fetchone())[0]
            
            # Количество записей истории
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM price_history"
            )
            history_count = (await cursor.fetchone())[0]
            
            # Размер БД
            db_size = Path(self.db_path).stat().st_size / (1024 * 1024)  # MB
        
        return {
            "cached_items": cache_count,
            "history_records": history_count,
            "db_size_mb": round(db_size, 2)
        }


# ═══════════════════════════════════════════════════════════════════════════
# Singleton для глобального доступа
# ═══════════════════════════════════════════════════════════════════════════

_db_instance: Optional[Database] = None


async def get_database() -> Database:
    """Получить глобальный экземпляр БД (singleton)"""
    global _db_instance
    
    if _db_instance is None:
        from settings_v2 import Settings
        _db_instance = Database(Settings.DB_PATH)
        await _db_instance.connect()
    
    return _db_instance
