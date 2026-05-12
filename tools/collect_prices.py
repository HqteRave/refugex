#!/usr/bin/env python3
"""
tools/collect_prices.py — сбор и обновление актуальных цен для калькулятора крафта.

Запускается ЛОКАЛЬНО (не из PyInstaller bundle).

Ключевые улучшения:
  - ThreadPoolExecutor: параллельные запросы (до 4 воркеров)
  - Умная синхронизация: пропускает предметы, обновлённые < SKIP_IF_FRESH_SEC назад
  - Не перезаписывает весь JSON — только обновившиеся записи
  - Инвалидирует SQLite-кэш после обновления, чтобы UI видел свежие данные
  - Retry + exponential backoff встроены в stalcraft._raw_get
  - Прогресс через logging, не print с эмодзи (совместимо с crontab/CI)
"""

from __future__ import annotations

import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Добавляем корень проекта в sys.path чтобы работали импорты api.*
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.stalcraft import (
    calculate_price_stats,
    get_price_history,
    _cache_invalidate,   # инвалидируем SQLite после обновления
)
from api.client import reload_prices_db  # сбрасываем in-memory кэш снэпшота
from settings import Settings, configure_logging

# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------

MAX_WORKERS = Settings.COLLECT_WORKERS
SKIP_IF_FRESH_SEC = Settings.COLLECT_SKIP_FRESH_SEC
REQUEST_DELAY = 0.15     # задержка между батчами (не настраивается через .env)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

configure_logging()
log = logging.getLogger("collect_prices")


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def load_recipes(recipes_file: Path) -> dict:
    with open(recipes_file, encoding="utf-8") as f:
        return json.load(f)


def collect_all_item_ids(recipes_db: dict) -> set[str]:
    all_ids: set[str] = set()
    for item_id, data in recipes_db.items():
        all_ids.add(item_id)
        craft = data.get("craft")
        if craft:
            for ingredient in craft.get("ingredients", []):
                ing_id = ingredient.get("id")
                if ing_id:
                    all_ids.add(ing_id)
    return all_ids


def _is_fresh(entry: dict) -> bool:
    """Проверяет, была ли запись обновлена меньше SKIP_IF_FRESH_SEC секунд назад."""
    updated_at = entry.get("price", {}).get("updated_at", "")
    if not updated_at:
        return False
    try:
        dt = datetime.fromisoformat(updated_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - dt).total_seconds()
        return age < SKIP_IF_FRESH_SEC
    except Exception:
        return False


def fetch_price_for_item(item_id: str) -> tuple[str, dict | None]:
    """
    Запрашивает историю цен для одного item_id и рассчитывает статистику.
    Возвращает (item_id, price_data) или (item_id, None) при ошибке.
    """
    try:
        history = get_price_history(item_id)
        stats = calculate_price_stats(history)
        price_data = {
            "avg_price": stats["avg"],
            "min_price": stats["min"],
            "max_price": stats["max"],
            "count": stats["count"],
            "liquidity": stats["liquidity"],
            "per_hour": stats["per_hour"],
            "per_day": stats["per_day"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        return item_id, price_data
    except Exception as e:
        log.error("Ошибка при запросе %s: %s", item_id, e)
        return item_id, None


def save_database(calculator_db: dict, output_file: Path) -> None:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(calculator_db, f, ensure_ascii=False, indent=2)


def print_stats(updated: int, skipped: int, failed: int, total: int) -> None:
    log.info("=" * 60)
    log.info("ИТОГО: %d предметов", total)
    log.info("  Обновлено:  %d", updated)
    log.info("  Пропущено:  %d (свежие данные)", skipped)
    log.info("  Ошибки:     %d", failed)
    log.info("=" * 60)


# ---------------------------------------------------------------------------
# Основной цикл
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("СБОР АКТУАЛЬНЫХ ЦЕН ДЛЯ КАЛЬКУЛЯТОРА")

    current_dir = Path.cwd()
    recipes_file = current_dir / "recipes_calculator.json"
    output_file = current_dir / "prices_database.json"

    log.info("Директория: %s", current_dir)

    if not recipes_file.exists():
        log.error("Файл %s не найден. Запустите скрипт из корня проекта.", recipes_file.name)
        sys.exit(1)

    # ── Загрузка рецептов ──────────────────────────────────────────────────
    log.info("Загрузка рецептов...")
    recipes_db = load_recipes(recipes_file)
    log.info("Загружено: %d предметов", len(recipes_db))

    # ── Сбор ID ────────────────────────────────────────────────────────────
    all_ids = collect_all_item_ids(recipes_db)
    log.info("Уникальных item_id: %d", len(all_ids))

    # ── Загрузка существующей базы для инкрементального обновления ─────────
    existing_db: dict = {}
    if output_file.exists():
        try:
            with open(output_file, encoding="utf-8") as f:
                existing_db = json.load(f)
            log.info("Существующая БД загружена: %d записей", len(existing_db))
        except Exception as e:
            log.warning("Не удалось загрузить существующую БД: %s", e)

    # ── Определяем что нужно обновить ──────────────────────────────────────
    to_update: list[str] = []
    skipped = 0

    for item_id in sorted(all_ids):
        entry = existing_db.get(item_id, {})
        if _is_fresh(entry):
            skipped += 1
        else:
            to_update.append(item_id)

    log.info("К обновлению: %d, пропущено (свежие): %d", len(to_update), skipped)

    if not to_update:
        log.info("Все данные актуальны — обновление не требуется.")
        return

    # ── Параллельный сбор цен ──────────────────────────────────────────────
    log.info("Запрашиваем цены (воркеров: %d)...", MAX_WORKERS)
    updated = 0
    failed = 0
    total = len(to_update)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_price_for_item, iid): iid for iid in to_update}

        for i, future in enumerate(as_completed(futures), 1):
            item_id, price_data = future.result()

            if price_data is not None:
                # Формируем запись для калькулятора
                recipe_data = recipes_db.get(item_id, {})
                existing_db[item_id] = {
                    "id": item_id,
                    "name": recipe_data.get("name", f"Unknown_{item_id}"),
                    "price": price_data,
                    "craft": recipe_data.get("craft"),
                    "barter": recipe_data.get("barter"),
                }

                # Инвалидируем SQLite-кэш чтобы UI получил свежие данные
                try:
                    _cache_invalidate(item_id)
                except Exception:
                    pass

                status = "OK" if price_data["count"] > 0 else "нет данных"
                log.info(
                    "[%d/%d] %s — avg: %s (%s)",
                    i,
                    total,
                    item_id,
                    f"{price_data['avg_price']:,}" if price_data["avg_price"] else "—",
                    status,
                )
                updated += 1
            else:
                failed += 1
                log.warning("[%d/%d] %s — ошибка, запись не обновлена", i, total, item_id)

            # Небольшая задержка между обработанными futures
            if i % MAX_WORKERS == 0:
                time.sleep(REQUEST_DELAY)

    # ── Сохранение ────────────────────────────────────────────────────────
    log.info("Сохранение в %s...", output_file)
    save_database(existing_db, output_file)

    # Сбрасываем in-memory кэш клиента чтобы он перечитал файл
    reload_prices_db()

    print_stats(updated, skipped, failed, total)
    log.info("Готово! Файл сохранён: %s", output_file)


if __name__ == "__main__":
    main()
