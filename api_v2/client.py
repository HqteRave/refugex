"""
api_v2/client.py — Улучшенный асинхронный клиент для Stalcraft API

ОБНОВЛЕНИЯ v2.1.2:
  - Использует scapi 2.1.2 (последняя версия)
  - DatabaseLookup для поиска предметов по названию
  - Автоматический rate limiting через rate_limit_info
  - Pydantic модели для типизации ответов
  - Поддержка OAuth 2.0 для User API
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Callable

from scapi import AppClient, DatabaseLookup
from scapi.enums import Region
from scapi.exceptions import (
    ScApiException,
    RateLimitError,
    UnauthorizedError,
    ClientError,
    ServerError
)
from scapi.client.models import AuctionPrice, AuctionLot
from scapi.http.types import Listing

from .models import (
    AuctionPriceEntry,
    PriceStats,
    ItemPriceUpdate,
    SyncProgress
)
from .database import get_database

try:
    from settings_v2 import Settings
except ImportError:
    class Settings:
        CLIENT_ID = ""
        CLIENT_SECRET = ""
        API_BASE = "https://eapi.stalcraft.net"
        REGION = "ru"
        CACHE_TTL = 180
        MAX_CONCURRENT_REQUESTS = 3
        MIN_REQUEST_INTERVAL = 0.4
        RATE_LIMIT_BACKOFF_BASE = 2.0
        RATE_LIMIT_MAX_RETRIES = 5

log = logging.getLogger("stalcraft.client")


class StalcraftClient:
    """
    Асинхронный клиент для Stalcraft API
    
    Обёртка над scapi.AppClient с асинхронной поддержкой и умным кэшированием
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        region: str = "ru",
        user_token: Optional[str] = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_token = user_token
        
        # Маппинг региона
        region_map = {
            "ru": Region.RU,
            "eu": Region.EU,
            "na": Region.NA,
            "sea": Region.SEA,
            "nea": Region.NEA
        }
        self.region = region_map.get(region.lower(), Region.RU)
        
        # scapi клиент (синхронный, обернём в async)
        self._client: Optional[AppClient] = None
        
        # DatabaseLookup для поиска предметов (НОВОЕ!)
        self._db_lookup: Optional[DatabaseLookup] = None
        
        # Rate limiting
        self._semaphore = asyncio.Semaphore(Settings.MAX_CONCURRENT_REQUESTS)
        self._last_request_time = 0.0
        self._request_lock = asyncio.Lock()
        
        # Статистика
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "rate_limit_hits": 0,
            "errors": 0
        }
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self) -> None:
        """Подключение к API"""
        if self._client is not None:
            return
        
        # Создаём scapi.AppClient в отдельном потоке
        def _create_client():
            return AppClient(
                client_id=self.client_id,
                client_secret=self.client_secret,
                token=self.user_token,
                base_url=Settings.API_BASE,
                region=self.region
            )
        
        self._client = await asyncio.to_thread(_create_client)
        
        # Инициализируем DatabaseLookup (НОВОЕ!)
        self._db_lookup = DatabaseLookup()
        
        log.info(f"Stalcraft API подключен (регион: {self.region.value})")
        log.info(f"DatabaseLookup загружен ({len(self._db_lookup._items)} предметов)")
    
    async def close(self) -> None:
        """Закрытие соединений"""
        if self._client:
            # close() у AppClient — async метод, вызываем напрямую
            try:
                await self._client.close()
            except Exception as e:
                log.warning(f"Ошибка при закрытии клиента: {e}")
            self._client = None
            log.info("Stalcraft API отключен")
    
    async def _throttle(self) -> None:
        """Контроль минимального интервала между запросами"""
        async with self._request_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            
            if elapsed < Settings.MIN_REQUEST_INTERVAL:
                wait_time = Settings.MIN_REQUEST_INTERVAL - elapsed
                await asyncio.sleep(wait_time)
            
            self._last_request_time = asyncio.get_event_loop().time()
    
    async def _execute_with_retry(
        self,
        coro_func: Callable,
        *args,
        max_retries: int = None,
        **kwargs
    ):
        """
        Выполнить асинхронную функцию с retry при 429
        
        Args:
            coro_func: Асинхронная функция (корутина)
            max_retries: Максимальное количество попыток
        """
        if max_retries is None:
            max_retries = Settings.RATE_LIMIT_MAX_RETRIES
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with self._semaphore:
                    await self._throttle()
                    
                    self.stats["total_requests"] += 1
                    
                    # Выполняем асинхронную функцию напрямую
                    result = await coro_func(*args, **kwargs)
                    
                    return result
            
            except RateLimitError as e:
                # 429 Too Many Requests
                self.stats["rate_limit_hits"] += 1
                
                wait_time = Settings.RATE_LIMIT_BACKOFF_BASE ** attempt
                
                log.warning(
                    f"Rate limit (попытка {attempt + 1}/{max_retries}). "
                    f"Ожидание {wait_time:.1f}s..."
                )
                
                await asyncio.sleep(wait_time)
                last_error = e
            
            except UnauthorizedError as e:
                # 401 Unauthorized
                log.error(f"Ошибка авторизации: {e}")
                self.stats["errors"] += 1
                raise
            
            except (ClientError, ServerError) as e:
                # 4xx, 5xx ошибки
                log.error(f"HTTP ошибка: {e}")
                self.stats["errors"] += 1
                
                # Не ретраим на 404, 400
                if isinstance(e, ClientError):
                    raise
                
                last_error = e
                await asyncio.sleep(1.0)
            
            except Exception as e:
                log.error(f"Неожиданная ошибка: {e}", exc_info=True)
                self.stats["errors"] += 1
                last_error = e
                await asyncio.sleep(1.0)
        
        # Все попытки исчерпаны
        log.error(f"Все {max_retries} попытки исчерпаны")
        if last_error:
            raise last_error
        raise Exception("Max retries exceeded")
    
    # ═══════════════════════════════════════════════════════════════════════
    # Получение истории цен
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_price_history(
        self,
        item_id: str,
        use_cache: bool = True
    ) -> list[AuctionPriceEntry]:
        """
        Получить историю продаж предмета
        
        Args:
            item_id: ID предмета
            use_cache: Использовать кэш (default: True)
        
        Returns:
            Список сделок (до 50 последних)
        """
        db = await get_database()
        
        # Проверяем кэш
        if use_cache:
            cached = await db.get_cached_price(item_id, Settings.CACHE_TTL)
            if cached is not None:
                self.stats["cache_hits"] += 1
                log.debug(f"Кэш HIT для {item_id}")
                return cached
        
        self.stats["cache_misses"] += 1
        log.debug(f"Кэш MISS для {item_id}, запрос к API...")
        
        # Запрос к API через scapi
        try:
            async def _fetch():
                # client.auction(item_id) возвращает AuctionEndpoint
                auction = self._client.auction(item_id, region=self.region)
                # price_history() — АСИНХРОННЫЙ метод, нужен await
                result = await auction.price_history(limit=50)
                # Listing наследует list — list(result) даёт все элементы
                return list(result)
            
            prices: list[AuctionPrice] = await self._execute_with_retry(_fetch)
            
            # Конвертация scapi моделей в наши модели
            entries = [
                AuctionPriceEntry(
                    time=price.time.isoformat(),
                    price=price.price,
                    amount=price.amount
                )
                for price in prices
            ]
            
            # Сохраняем в кэш и историю
            if entries:
                await db.set_cached_price(item_id, entries)
                await db.store_history(item_id, entries)
            
            return entries
        
        except Exception as e:
            log.error(f"Ошибка получения истории для {item_id}: {e}")
            
            # Fallback: старый кэш
            cached = await db.get_cached_price(item_id, ttl_seconds=3600)
            if cached:
                log.warning(f"Используем устаревший кэш для {item_id}")
                return cached
            
            return []
    
    # ═══════════════════════════════════════════════════════════════════════
    # Получение активных лотов
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_active_lots(
        self,
        item_id: str,
        min_amount: int = 1
    ) -> dict[str, int]:
        """
        Получить информацию об активных лотах
        
        Args:
            item_id: ID предмета
            min_amount: Минимальное количество в лоте
        
        Returns:
            {"min_price": int, "total_lots": int}
        """
        try:
            async def _fetch():
                auction = self._client.auction(item_id, region=self.region)
                # lots() — АСИНХРОННЫЙ метод, нужен await
                listing = await auction.lots(limit=100, additional=True)
                # Listing наследует list, total — атрибут Listing
                return list(listing), listing.total
            
            lots, total = await self._execute_with_retry(_fetch)
            
            if not lots:
                return {"min_price": 0, "total_lots": 0}
            
            # Фильтруем по количеству
            valid_lots = [
                lot for lot in lots
                if lot.amount >= min_amount and lot.buyout_price > 0
            ]
            
            if not valid_lots:
                # Fallback: любые лоты с buyout_price
                valid_lots = [lot for lot in lots if lot.buyout_price > 0]
            
            if not valid_lots:
                return {"min_price": 0, "total_lots": total}
            
            # Минимальная цена за единицу
            min_price = min(
                round(lot.buyout_price / max(lot.amount, 1))
                for lot in valid_lots
            )
            
            return {
                "min_price": min_price,
                "total_lots": total
            }
        
        except Exception as e:
            log.error(f"Ошибка получения лотов для {item_id}: {e}")
            return {"min_price": 0, "total_lots": 0}
    
    # ═══════════════════════════════════════════════════════════════════════
    # Статистика и агрегация
    # ═══════════════════════════════════════════════════════════════════════
    
    def calculate_stats(self, entries: list[AuctionPriceEntry]) -> PriceStats:
        """
        Рассчитать статистику по истории продаж
        
        Использует взвешенное среднее для корректного учёта
        оптовых и поштучных продаж
        """
        if not entries:
            return PriceStats()
        
        # Цены за единицу
        prices_per_unit = [entry.per_unit for entry in entries]
        
        # Взвешенное среднее
        total_units = sum(entry.amount for entry in entries)
        total_price = sum(entry.price for entry in entries)
        weighted_avg = round(total_price / total_units) if total_units > 0 else 0
        
        # Временные метки
        now = datetime.now(timezone.utc)
        timestamps = [entry.timestamp for entry in entries]
        
        # Скорость продаж
        def count_in_window(minutes: int) -> float:
            cutoff = now.timestamp() - minutes * 60
            return sum(1 for ts in timestamps if ts.timestamp() >= cutoff)
        
        sales_per_minute = count_in_window(1)
        sales_per_5min = count_in_window(5)
        sales_per_hour = count_in_window(60)
        sales_per_day = count_in_window(1440)
        
        # Ликвидность
        if sales_per_hour >= 20:
            liquidity = "high"
        elif sales_per_hour >= 5:
            liquidity = "medium"
        elif len(entries) >= 1:
            liquidity = "low"
        else:
            liquidity = "unknown"
        
        # Временной диапазон
        if timestamps:
            oldest = min(timestamps)
            newest = max(timestamps)
            delta_seconds = (newest - oldest).total_seconds()
            
            if delta_seconds > 3600:
                time_span = f"{delta_seconds / 3600:.1f} ч"
            elif delta_seconds > 60:
                time_span = f"{delta_seconds / 60:.0f} мин"
            else:
                time_span = f"{delta_seconds:.0f} сек"
        else:
            time_span = ""
        
        return PriceStats(
            count=len(entries),
            min_price=min(prices_per_unit),
            avg_price=weighted_avg,
            max_price=max(prices_per_unit),
            liquidity=liquidity,
            sales_per_minute=sales_per_minute,
            sales_per_5min=sales_per_5min,
            sales_per_hour=sales_per_hour,
            sales_per_day=sales_per_day,
            time_span=time_span,
            history=entries,
            updated_at=datetime.now(timezone.utc)
        )
    
    async def get_price_stats(
        self,
        item_id: str,
        include_lots: bool = False,
        use_cache: bool = True
    ) -> PriceStats:
        """
        Получить полную статистику цен для предмета
        
        Args:
            item_id: ID предмета
            include_lots: Включить данные активных лотов
            use_cache: Использовать кэш
        
        Returns:
            PriceStats с полной информацией
        """
        # Получаем историю
        history = await self.get_price_history(item_id, use_cache=use_cache)
        
        # Запоминаем: был ли это cache hit (cache_misses не вырос)
        misses_before = self.stats["cache_misses"]
        stats = self.calculate_stats(history)
        
        # Опционально: активные лоты
        if include_lots:
            lots_data = await self.get_active_lots(item_id)
            stats.market_min_price = lots_data["min_price"]
            stats.market_total_lots = lots_data["total_lots"]
        
        # from_cache = True если данные пришли из кэша (cache_misses не изменился)
        stats.from_cache = use_cache and (self.stats["cache_misses"] == misses_before)
        
        return stats
    
    # ═══════════════════════════════════════════════════════════════════════
    # Массовая синхронизация
    # ═══════════════════════════════════════════════════════════════════════
    
    async def sync_prices(
        self,
        item_ids: list[str],
        include_lots: bool = False,
        progress_callback: Optional[Callable[[SyncProgress], None]] = None
    ) -> dict[str, ItemPriceUpdate]:
        """
        Синхронизировать цены для списка предметов
        
        Args:
            item_ids: Список ID предметов
            include_lots: Запрашивать активные лоты
            progress_callback: Колбэк для отслеживания прогресса
        
        Returns:
            Словарь {item_id: ItemPriceUpdate}
        """
        total = len(item_ids)
        results = {}
        errors = 0
        
        for idx, item_id in enumerate(item_ids, 1):
            # Обновляем прогресс
            if progress_callback:
                progress = SyncProgress(
                    total_items=total,
                    completed_items=idx - 1,
                    current_item=item_id,
                    errors=errors
                )
                progress_callback(progress)
            
            try:
                stats = await self.get_price_stats(
                    item_id,
                    include_lots=include_lots,
                    use_cache=False  # Принудительное обновление
                )
                
                results[item_id] = ItemPriceUpdate(
                    item_id=item_id,
                    stats=stats
                )
            
            except Exception as e:
                errors += 1
                log.error(f"Ошибка синхронизации {item_id}: {e}")
                
                results[item_id] = ItemPriceUpdate(
                    item_id=item_id,
                    stats=PriceStats(),
                    error=str(e)
                )
        
        # Финальный прогресс
        if progress_callback:
            progress = SyncProgress(
                total_items=total,
                completed_items=total,
                errors=errors
            )
            progress_callback(progress)
        
        log.info(
            f"Синхронизация завершена: {total} предметов, "
            f"{errors} ошибок"
        )
        
        return results


    # ═══════════════════════════════════════════════════════════════════════
    # DatabaseLookup методы (НОВОЕ!)
    # ═══════════════════════════════════════════════════════════════════════
    
    def search_items(self, query: str) -> list[dict]:
        """
        Поиск предметов по названию через DatabaseLookup
        
        Args:
            query: Поисковый запрос (название предмета)
        
        Returns:
            Список найденных предметов
        
        Example:
            >>> items = client.search_items("анаболик")
            >>> print(items[0])
            {'id': '7lyd3', 'name': 'Анаболик «STARK»', 'category': 'medicine'}
        """
        if not self._db_lookup:
            return []
        
        return self._db_lookup.search(query)
    
    def get_item_info(self, item_id: str) -> Optional[dict]:
        """
        Получить информацию о предмете по ID
        
        Args:
            item_id: ID предмета
        
        Returns:
            Информация о предмете или None
        """
        if not self._db_lookup:
            return None
        
        return self._db_lookup.get(item_id)


# ═══════════════════════════════════════════════════════════════════════════
# Фабрика для создания клиента
# ═══════════════════════════════════════════════════════════════════════════

def create_client(user_token: Optional[str] = None) -> StalcraftClient:
    """Создать экземпляр StalcraftClient с настройками из Settings"""
    return StalcraftClient(
        client_id=Settings.CLIENT_ID,
        client_secret=Settings.CLIENT_SECRET,
        region=Settings.REGION,
        user_token=user_token
    )
