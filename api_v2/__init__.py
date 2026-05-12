"""
api_v2 — Современная асинхронная архитектура для Stalcraft API

Основные компоненты:
  - StalcraftClient: Асинхронный клиент (stalcraft-api)
  - Database: Асинхронная работа с SQLite
  - PriceSyncManager: Интеграция с PyQt6
  - Models: Pydantic модели для типизации

Quick Start:
    >>> from api_v2 import create_client, PriceStats
    >>> 
    >>> async def main():
    >>>     async with create_client() as client:
    >>>         stats = await client.get_price_stats("pistol-pm")
    >>>         print(f"Средняя цена: {stats.avg_price}")
"""

from .client import StalcraftClient, create_client
from .database import Database, get_database
from .models import (
    AuctionPriceEntry,
    AuctionLot,
    PriceStats,
    ItemPriceUpdate,
    SyncProgress
)
from .qt_bridge import PriceSyncManager, AutoSyncManager

__all__ = [
    # Client
    "StalcraftClient",
    "create_client",
    
    # Database
    "Database",
    "get_database",
    
    # Models
    "AuctionPriceEntry",
    "AuctionLot",
    "PriceStats",
    "ItemPriceUpdate",
    "SyncProgress",
    
    # Qt Integration
    "PriceSyncManager",
    "AutoSyncManager",
]

__version__ = "2.0.0"
