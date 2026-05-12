"""
api_v2/models.py — Pydantic модели для Stalcraft API

Все данные строго типизированы, что предотвращает ошибки
и упрощает работу с API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


# ═══════════════════════════════════════════════════════════════════════════
# Базовые модели API
# ═══════════════════════════════════════════════════════════════════════════

class AuctionPriceEntry(BaseModel):
    """Одна запись в истории продаж"""
    model_config = ConfigDict(extra="ignore")
    
    time: str  # ISO формат
    price: int  # Общая цена лота
    amount: int = 1  # Количество предметов в лоте
    
    @property
    def per_unit(self) -> int:
        """Цена за единицу"""
        return round(self.price / max(self.amount, 1))
    
    @property
    def timestamp(self) -> datetime:
        """Парсинг времени в datetime"""
        return datetime.fromisoformat(self.time.replace("Z", "+00:00"))


class AuctionLot(BaseModel):
    """Активный лот на аукционе"""
    model_config = ConfigDict(extra="ignore")
    
    item_id: str = Field(..., alias="itemId")
    amount: int
    buyout_price: int = Field(..., alias="buyoutPrice")
    current_price: int = Field(..., alias="currentPrice")
    start_price: int = Field(..., alias="startPrice")
    start_time: str = Field(..., alias="startTime")
    end_time: str = Field(..., alias="endTime")
    
    @property
    def per_unit(self) -> int:
        """Цена за единицу"""
        return round(self.buyout_price / max(self.amount, 1))


# ═══════════════════════════════════════════════════════════════════════════
# Статистика и агрегация
# ═══════════════════════════════════════════════════════════════════════════

class PriceStats(BaseModel):
    """Агрегированная статистика цен для предмета"""
    
    # Базовая статистика
    count: int = 0  # Количество сделок
    min_price: int = 0  # Минимальная цена за штуку
    avg_price: int = 0  # Средняя цена (взвешенная)
    max_price: int = 0  # Максимальная цена
    
    # Ликвидность
    liquidity: Literal["unknown", "low", "medium", "high"] = "unknown"
    
    # Скорость продаж
    sales_per_minute: float = 0.0
    sales_per_5min: float = 0.0
    sales_per_hour: float = 0.0
    sales_per_day: float = 0.0
    
    # Временной диапазон
    time_span: str = ""  # "3.5 ч", "45 мин", etc.
    
    # Данные аукциона (активные лоты)
    market_min_price: int = 0  # Минимальная цена активного лота
    market_total_lots: int = 0  # Количество активных лотов
    
    # Мета-информация
    from_cache: bool = False  # Данные из кэша?
    updated_at: Optional[datetime] = None  # Время последнего обновления
    
    # История (опционально)
    history: list[AuctionPriceEntry] = Field(default_factory=list)
    
    def is_empty(self) -> bool:
        """Проверка, есть ли данные"""
        return self.count == 0 and self.avg_price == 0


# ═══════════════════════════════════════════════════════════════════════════
# Модели для БД
# ═══════════════════════════════════════════════════════════════════════════

class CachedPrice(BaseModel):
    """Кэшированная запись цены в БД"""
    
    item_id: str
    data: list[AuctionPriceEntry]  # История продаж
    cached_at: datetime
    
    def is_stale(self, ttl_seconds: int = 180) -> bool:
        """Проверка устаревания кэша"""
        from datetime import datetime, timezone
        age = (datetime.now(timezone.utc) - self.cached_at).total_seconds()
        return age > ttl_seconds


class PriceHistoryEntry(BaseModel):
    """Одна запись в таблице price_history"""
    
    item_id: str
    sale_time: str  # ISO формат
    price: int
    amount: int
    per_unit: int


# ═══════════════════════════════════════════════════════════════════════════
# Модели для UI
# ═══════════════════════════════════════════════════════════════════════════

class ItemPriceUpdate(BaseModel):
    """Обновление цены для передачи в UI через сигналы"""
    
    item_id: str
    stats: PriceStats
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.error is None


class SyncProgress(BaseModel):
    """Прогресс синхронизации цен"""
    
    total_items: int
    completed_items: int
    current_item: Optional[str] = None
    errors: int = 0
    
    @property
    def progress_percent(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def is_complete(self) -> bool:
        return self.completed_items >= self.total_items
