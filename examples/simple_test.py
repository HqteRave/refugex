"""
examples/simple_test.py — Простой тест для проверки работы API v2

Запуск:
    python examples/simple_test.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api_v2 import create_client, get_database
from settings_v2 import Settings, configure_logging


async def test_single_item():
    """Тест: получение цены одного предмета"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Получение цены одного предмета")
    print("="*60)
    
    item_id = "pistol-pm"
    
    async with create_client() as client:
        print(f"\nЗапрос цены для: {item_id}")
        
        # Первый запрос (из API)
        stats = await client.get_price_stats(item_id, include_lots=True)
        
        print(f"\n📊 Статистика для {item_id}:")
        print(f"  Сделок: {stats.count}")
        print(f"  Мин. цена: {stats.min_price:,} ₽")
        print(f"  Средняя: {stats.avg_price:,} ₽")
        print(f"  Макс. цена: {stats.max_price:,} ₽")
        print(f"  Ликвидность: {stats.liquidity}")
        print(f"  Продаж в час: {stats.sales_per_hour:.1f}")
        print(f"  Временной диапазон: {stats.time_span}")
        
        if stats.market_total_lots > 0:
            print(f"\n🛒 Активные лоты:")
            print(f"  Всего лотов: {stats.market_total_lots}")
            print(f"  Мин. цена: {stats.market_min_price:,} ₽")
        
        # Второй запрос (из кэша)
        print(f"\n⚡ Второй запрос (должен быть из кэша)...")
        stats2 = await client.get_price_stats(item_id)
        print(f"  Из кэша: {stats2.from_cache}")
        
        # Статистика клиента
        print(f"\n📈 Статистика API:")
        print(f"  Всего запросов: {client.stats['total_requests']}")
        print(f"  Cache hits: {client.stats['cache_hits']}")
        print(f"  Cache misses: {client.stats['cache_misses']}")
        print(f"  Rate limit hits: {client.stats['rate_limit_hits']}")
        print(f"  Ошибок: {client.stats['errors']}")


async def test_multiple_items():
    """Тест: массовая синхронизация"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Массовая синхронизация")
    print("="*60)
    
    items = [
        "pistol-pm",
        "rifle-akm",
        "ammo-9x18-pm",
        "detector-echo",
        "artifact-moonlight"
    ]
    
    async with create_client() as client:
        print(f"\nСинхронизация {len(items)} предметов...")
        
        def progress_cb(progress):
            percent = progress.progress_percent
            print(f"  Прогресс: {percent:.0f}% ({progress.completed_items}/{progress.total_items})")
        
        results = await client.sync_prices(
            items,
            include_lots=False,
            progress_callback=progress_cb
        )
        
        print(f"\n✅ Завершено!")
        print(f"\nРезультаты:")
        
        for item_id, update in results.items():
            if update.success:
                stats = update.stats
                print(f"  {item_id}: {stats.avg_price:,} ₽ (сделок: {stats.count})")
            else:
                print(f"  {item_id}: ОШИБКА - {update.error}")


async def test_database():
    """Тест: работа с базой данных"""
    print("\n" + "="*60)
    print("ТЕСТ 3: База данных")
    print("="*60)
    
    db = await get_database()
    
    # Статистика БД
    stats = await db.get_stats()
    print(f"\n📁 Статистика БД:")
    print(f"  Кэшированных предметов: {stats['cached_items']}")
    print(f"  Записей истории: {stats['history_records']}")
    print(f"  Размер БД: {stats['db_size_mb']} MB")
    
    # Получение истории из БД
    item_id = "pistol-pm"
    history = await db.get_history(item_id, hours=24)
    
    print(f"\n📜 История для {item_id} (24ч):")
    print(f"  Записей: {len(history)}")
    
    if history:
        print(f"  Первая запись: {history[0].time}")
        print(f"  Последняя: {history[-1].time}")
    
    # Очистка старых данных
    print(f"\n🧹 Очистка устаревших данных...")
    deleted_cache = await db.cleanup_stale_cache(ttl_seconds=3600)
    deleted_history = await db.cleanup_old_history_all(keep_hours=48)
    print(f"  Удалено кэша: {deleted_cache}")
    print(f"  Удалено истории: {deleted_history}")


async def main():
    """Запуск всех тестов"""
    # Проверка конфигурации
    errors = Settings.validate()
    if errors:
        print("❌ ОШИБКИ КОНФИГУРАЦИИ:")
        for err in errors:
            print(f"  - {err}")
        print("\n💡 Создай .env файл на основе .env.example")
        return
    
    print("="*60)
    print("SC-CraftX API v2 — Тестирование")
    print("="*60)
    print(f"\nРегион: {Settings.REGION}")
    print(f"API Base: {Settings.API_BASE}")
    print(f"Cache TTL: {Settings.CACHE_TTL}s")
    print(f"Sync Interval: {Settings.SYNC_INTERVAL}s")
    
    try:
        await test_single_item()
        await test_multiple_items()
        await test_database()
        
        print("\n" + "="*60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("="*60)
    
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Настройка логирования
    configure_logging()
    
    # Запуск
    asyncio.run(main())
