"""
api_v2/qt_bridge.py — Мост между scapi (async) и PyQt6 (sync event loop).

Архитектура:
  - AsyncWorker запускает СВОЙ asyncio event loop в QThread.
  - AppClient создаётся синхронно (его __init__ не async).
  - price_history() и lots() — async, вызываются через await напрямую.
  - client.close() — async, вызывается через await.
  - Каждый Worker создаёт и закрывает свой AppClient.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
import logging
import time
from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer

log = logging.getLogger("stalcraft.qt_bridge")


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательный поток
# ─────────────────────────────────────────────────────────────────────────────

class AsyncWorker(QThread):
    """Выполняет одну async-корутину в изолированном event loop."""

    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, coro_factory: Callable[[], object]):
        super().__init__()
        self._coro_factory = coro_factory
        self.result = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self.result = self._loop.run_until_complete(self._coro_factory())
            self.finished.emit()
        except asyncio.CancelledError:
            # Задача отменена - это нормально
            log.debug("AsyncWorker cancelled")
        except RuntimeError as e:
            if "Event loop stopped" in str(e):
                # Loop остановлен извне - не ошибка
                log.debug("AsyncWorker stopped: %s", e)
            else:
                log.error("AsyncWorker runtime error: %s", e, exc_info=True)
                self.error.emit(str(e))
        except Exception as e:
            log.error("AsyncWorker error: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            try:
                # Отменяем все оставшиеся задачи
                pending = asyncio.all_tasks(self._loop)
                for t in pending:
                    t.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                pass
            finally:
                self._loop.close()

    def stop(self):
        """Безопасная остановка worker'а."""
        if self._loop and not self._loop.is_closed():
            # Отменяем все задачи вместо жёсткой остановки loop
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    self._loop.call_soon_threadsafe(task.cancel)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Создание scapi AppClient
# ─────────────────────────────────────────────────────────────────────────────

def _make_scapi_client():
    """
    Создаёт scapi.AppClient синхронно.
    Читает credentials из .env (settings_v2) или credentials.json.
    """
    from scapi import AppClient
    from scapi.enums import Region

    client_id = ""
    client_secret = ""
    region_str = "ru"

    # 1. .env через settings_v2
    try:
        from settings_v2 import Settings
        client_id    = Settings.CLIENT_ID
        client_secret = Settings.CLIENT_SECRET
        region_str   = Settings.REGION
    except Exception:
        pass

    # 2. credentials.json (fallback)
    if not client_id or not client_secret:
        try:
            from app_paths import app_path
            with open(app_path("credentials.json"), encoding="utf-8") as f:
                creds = json.load(f)
            client_id     = creds.get("client_id", "")
            client_secret = creds.get("client_secret", "")
        except Exception:
            pass

    if not client_id or not client_secret:
        raise RuntimeError(
            "Credentials не найдены. Заполните .env или credentials.json."
        )

    region_map = {
        "ru": Region.RU, "eu": Region.EU,
        "na": Region.NA, "sea": Region.SEA,
    }
    region = region_map.get(region_str.lower(), Region.RU)

    # AppClient.__init__ — синхронный
    return AppClient(
        client_id=client_id,
        client_secret=client_secret,
        region=region,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные async-функции для работы с scapi
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_history(client, item_id: str) -> list:
    """
    Получает историю цен через await endpoint.price_history().
    Возвращает list[dict] совместимый с calculate_price_stats.
    """
    from scapi.exceptions import RateLimitError, ServerError

    endpoint = client.auction(item_id)   # синхронный

    for attempt in range(5):
        try:
            # price_history() — async метод, нужен await
            listing = await endpoint.price_history(limit=50)
            # Listing наследует list
            prices = list(listing)
            return [
                {
                    "time": (
                        p.time.isoformat()
                        if hasattr(p.time, "isoformat")
                        else str(p.time)
                    ),
                    "price":  p.price,
                    "amount": p.amount,
                }
                for p in prices
            ]
        except RateLimitError:
            wait = min(2 ** attempt, 30)
            log.warning("[history] RateLimit %s, пауза %ds", item_id, wait)
            await asyncio.sleep(wait)
        except ServerError:
            wait = min(2 ** attempt, 16)
            log.warning("[history] ServerError %s, пауза %ds", item_id, wait)
            await asyncio.sleep(wait)

    return []


async def _fetch_lots(client, item_id: str, result_amount: int = 1, history_avg: int = 0) -> dict:
    """
    Получает активные лоты через await endpoint.lots().
    Возвращает {'market_min': int, 'market_lot_size': int, 'market_total': int}.

    result_amount — сколько штук даёт один крафт. Ищем лоты с amount >= result_amount
    чтобы цена была релевантна для продавца крафтованной пачки.
    history_avg — средняя из истории для фильтрации аномальных лотов (фейков).
    """
    from scapi.exceptions import RateLimitError, ServerError

    endpoint = client.auction(item_id)

    for attempt in range(5):
        try:
            # ФИКС: Увеличен limit до 500 чтобы видеть все лоты на аукционе
            # (у популярных предметов может быть 300+ лотов)
            listing = await endpoint.lots(limit=500, additional=True)
            lots  = list(listing)
            total = listing.total
            
            # ЛОГИ: Сырые данные с API
            log.info(f"[LOTS] {item_id}: получено {len(lots)} лотов из {total}")
            if lots:
                log.info(f"[LOTS] {item_id}: первые 3 лота = {[(l.amount, l.buyout_price, getattr(l, 'additional', None)) for l in lots[:3]]}")

            # Фильтр 1: только лоты с buyout_price > 0
            valid = [l for l in lots if l.buyout_price > 0]
            log.info(f"[LOTS] {item_id}: после фильтра buyout>0 = {len(valid)} лотов")
            if not valid:
                return {"market_min": 0, "market_lot_size": 1, "market_total": total}

            # Фильтр 2: убираем явные фейки (цена > 100x от средней по истории).
            # Используем очень широкий множитель — лучше показать дорогой реальный
            # лот чем ошибочно отфильтровать его как фейк.
            if history_avg > 0:
                MAX_MULTIPLIER = 100
                filtered_fake = [
                    l for l in valid
                    if (l.buyout_price / max(l.amount, 1)) <= history_avg * MAX_MULTIPLIER
                ]
                if filtered_fake:
                    fake_count = len(valid) - len(filtered_fake)
                    if fake_count > 0:
                        log.info(f"[LOTS] {item_id}: отфильтровано {fake_count} фейков (>{MAX_MULTIPLIER}x от avg={history_avg})")
                    valid = filtered_fake
                # Если всё отфильтровалось — оставляем как есть

            # Фильтр 3: схроны — только лоты с 100% HP
            def _durability(lot) -> int | None:
                if lot.additional and isinstance(lot.additional, dict):
                    return lot.additional.get("stash_durability")
                return None

            dur_values = [_durability(l) for l in valid]
            has_durability = any(d is not None for d in dur_values)
            log.info(f"[LOTS] {item_id}: has_durability={has_durability}")
            
            if has_durability:
                max_dur = max((d for d in dur_values if d is not None), default=0)
                log.info(f"[LOTS] {item_id}: max_durability={max_dur}")
                # Только лоты с полным HP (100%)
                full_hp = [l for l, d in zip(valid, dur_values)
                           if d is None or d >= max_dur]
                if full_hp:
                    hp_count = len(valid) - len(full_hp)
                    if hp_count > 0:
                        log.info(f"[LOTS] {item_id}: отфильтровано {hp_count} лотов с HP<{max_dur}")
                    valid = full_hp
                else:
                    # Нет лотов с полным HP — берём лот с максимальным HP
                    # (крафт только что сделанных схронов может давать не 100%)
                    best_dur = max(
                        ((d if d is not None else 0), l)
                        for l, d in zip(valid, dur_values)
                    )
                    valid = [best_dur[1]]
                    log.info(f"[LOTS] {item_id}: все лоты битые, взят лучший HP={best_dur[0]}")

            # Логика выбора цены:
            # 1. Берём поштучные лоты (amount==1) — именно они видны как
            #    "Цена выкупа" в игровом аукционе поштучно.
            # 2. Если поштучных нет — минимум buyout/amount среди всех.
            # Оптовые лоты (amount>1) НЕ участвуют когда есть поштучные —
            # они дешевле за шт но игрок не может продать 1 шт из пачки.
            single = [l for l in valid if l.amount == 1]
            log.info(f"[LOTS] {item_id}: поштучных (amount=1) = {len(single)} из {len(valid)}")
            
            if single:
                # Сортируем для логов
                single_sorted = sorted(single, key=lambda l: l.buyout_price)
                log.info(f"[LOTS] {item_id}: поштучные цены = {[l.buyout_price for l in single_sorted[:5]]}")
                best = min(single, key=lambda l: l.buyout_price)
                min_price_per_unit = best.buyout_price
                log.info(f"[LOTS] {item_id}: выбран минимум поштучный = {min_price_per_unit}₽")
            else:
                log.info(f"[LOTS] {item_id}: поштучных нет, ищем минимум среди оптовых")
                best = min(valid, key=lambda l: l.buyout_price / max(l.amount, 1))
                min_price_per_unit = round(best.buyout_price / max(best.amount, 1))
                log.info(f"[LOTS] {item_id}: выбран минимум оптовый = {best.buyout_price}₽ / {best.amount}шт = {min_price_per_unit}₽/шт")



            return {
                "market_min":      min_price_per_unit,
                "market_lot_size": best.amount,
                "market_total":    total,
            }

        except RateLimitError:
            wait = min(2 ** attempt, 30)
            log.warning("[lots] RateLimit %s, пауза %ds", item_id, wait)
            await asyncio.sleep(wait)
        except ServerError:
            wait = min(2 ** attempt, 16)
            log.warning("[lots] ServerError %s, пауза %ds", item_id, wait)
            await asyncio.sleep(wait)

    return {"market_min": 0, "market_lot_size": 1, "market_total": 0}


# ─────────────────────────────────────────────────────────────────────────────
# PriceSyncManager
# ─────────────────────────────────────────────────────────────────────────────

class PriceSyncManager(QObject):
    """
    Менеджер синхронизации цен для PyQt6.

    Signals:
        price_updated(item_id, stats_dict)
        sync_progress(done, total)
        sync_started()
        sync_finished()
        error(message)
    """

    price_updated = pyqtSignal(str, dict)
    sync_progress = pyqtSignal(int, int)
    sync_started  = pyqtSignal()
    sync_finished = pyqtSignal()
    error         = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list[AsyncWorker] = []
        self._is_syncing = False
        self._should_stop = False

    # ── одиночный запрос ────────────────────────────────────────────────────

    def fetch_price(
        self,
        item_id: str,
        include_lots: bool = True,
        callback: Optional[Callable[[dict], None]] = None,
    ) -> None:
        """Запросить цену одного предмета асинхронно."""

        def _coro_factory():
            async def _run():
                client = _make_scapi_client()
                try:
                    from api.stalcraft import (
                        calculate_price_stats, _cache_get,
                        _cache_set, _store_history,
                    )

                    # Пробуем кэш
                    cached = _cache_get(item_id)
                    if cached:
                        stats = calculate_price_stats(cached)
                        if include_lots:
                            lot_data = await _fetch_lots(client, item_id)
                            stats.update(lot_data)
                        return stats

                    history = await _fetch_history(client, item_id)
                    stats = calculate_price_stats(history)

                    if history:
                        _cache_set(item_id, history)
                        _store_history(item_id, history)

                    if include_lots:
                        lot_data = await _fetch_lots(client, item_id)
                        stats.update(lot_data)

                    return stats
                finally:
                    await client.close()

            return _run()

        worker = AsyncWorker(_coro_factory)

        def _on_done():
            if worker.result is not None:
                self.price_updated.emit(item_id, worker.result)
                if callback:
                    callback(worker.result)
            _remove(worker)

        def _on_err(msg: str):
            self.error.emit(f"Ошибка загрузки {item_id}: {msg}")
            _remove(worker)

        def _remove(w):
            if w in self._workers:
                self._workers.remove(w)

        worker.finished.connect(_on_done)
        worker.error.connect(_on_err)
        self._workers.append(worker)
        worker.start()

    # ── массовая синхронизация ───────────────────────────────────────────────

    def sync_prices(
        self,
        item_ids: list[str],
        include_lots: bool = True,
        force_refresh: bool = False,
        workers: int = 3,
    ) -> None:
        """
        Синхронизировать цены параллельно через N воркеров.
        Список делится на чанки — каждый чанк в своём AsyncWorker/AppClient.
        workers=6 даёт ~6x ускорение по сравнению с последовательным обходом.
        """
        if self._is_syncing:
            log.info("Перезапуск синхронизации")
            self._should_stop = True
            # Останавливаем воркеры
            for w in list(self._workers):
                w.stop()
            # ФИКС: Ждём завершения всех воркеров перед созданием новых
            for w in list(self._workers):
                if w.isRunning():
                    w.wait(500)  # Увеличен таймаут до 500мс
            self._workers.clear()
            self._is_syncing = False

        if not item_ids:
            self.sync_finished.emit()
            return

        self._is_syncing   = True
        self._should_stop  = False
        self.sync_started.emit()

        total     = len(item_ids)
        # Счётчик завершённых чанков (через список чтобы захватывался в замыкании)
        done_counter  = [0]    # обработано предметов
        chunks_done   = [0]    # завершённых воркеров
        n_workers     = min(workers, total)

        # Делим список на n_workers чанков
        chunks: list[list[str]] = [[] for _ in range(n_workers)]
        for i, iid in enumerate(item_ids):
            chunks[i % n_workers].append(iid)

        def _make_coro(chunk: list[str]):
            def _coro_factory():
                async def _run():
                    from api.stalcraft import (
                        calculate_price_stats,
                        _cache_get, _cache_set, _store_history, _cache_invalidate,
                    )
                    client = _make_scapi_client()
                    try:
                        for item_id in chunk:
                            if self._should_stop:
                                break
                            try:
                                # ФИКС: При force_refresh принудительно инвалидируем кэш
                                # чтобы история и лоты загружались свежими с API
                                if force_refresh:
                                    _cache_invalidate(item_id)

                                history = None
                                # При force_refresh не используем кэш вообще
                                if not force_refresh:
                                    cached = _cache_get(item_id)
                                    if cached:
                                        history = cached

                                # Если нет кэша или force_refresh — загружаем с API
                                if history is None:
                                    history = await _fetch_history(client, item_id)
                                    if history:
                                        _cache_set(item_id, history)
                                        _store_history(item_id, history)

                                stats = calculate_price_stats(history or [])

                                if include_lots:
                                    # ФИКС: Принудительно инвалидируем кэш лотов при force_refresh
                                    # чтобы получить актуальные цены с аукциона
                                    # Передаём avg из истории для фильтрации фейков
                                    history_avg = stats.get("avg", 0)
                                    lot_data = await _fetch_lots(
                                        client, item_id,
                                        history_avg=history_avg,
                                    )
                                    stats.update(lot_data)
                                    # last_sale — последняя сделка из истории (цена/шт)
                                    hist = stats.get("history", [])
                                    stats["last_sale"] = hist[0].get("per_unit", 0) if hist else 0

                                self.price_updated.emit(item_id, stats)

                                # Throttle — 3 воркера × 0.25с = ~12 req/sec, ниже rate limit
                                await asyncio.sleep(0.25)

                            except Exception as e:
                                log.error("Sync error %s: %s", item_id, e)

                            done_counter[0] += 1
                            self.sync_progress.emit(done_counter[0], total)

                    finally:
                        try:
                            await client.close()
                        except Exception:
                            pass
                return _run()
            return _coro_factory

        for chunk in chunks:
            if not chunk:
                continue

            worker = AsyncWorker(_make_coro(chunk))

            def _on_done(w=worker):
                chunks_done[0] += 1
                if w in self._workers:
                    self._workers.remove(w)
                # Все чанки завершены — emit sync_finished
                if chunks_done[0] >= n_workers:
                    self._is_syncing = False
                    self.sync_finished.emit()

            def _on_err(msg: str, w=worker):
                chunks_done[0] += 1
                if w in self._workers:
                    self._workers.remove(w)
                self.error.emit(f"Ошибка синхронизации: {msg}")
                if chunks_done[0] >= n_workers:
                    self._is_syncing = False
                    self.sync_finished.emit()

            worker.finished.connect(_on_done)
            worker.error.connect(_on_err)
            self._workers.append(worker)
            worker.start()

    # ── управление ──────────────────────────────────────────────────────────

    def stop_sync(self) -> None:
        self._should_stop = True
        for w in list(self._workers):
            w.stop()

    def cleanup(self) -> None:
        self.stop_sync()
        for w in list(self._workers):
            w.wait()
        self._workers.clear()


# ─────────────────────────────────────────────────────────────────────────────
# AutoSyncManager — PriceSyncManager + QTimer
# ─────────────────────────────────────────────────────────────────────────────

class AutoSyncManager(PriceSyncManager):
    """PriceSyncManager с автоматическим обновлением по таймеру."""

    def __init__(
        self,
        item_ids: list[str],
        interval_seconds: int = 45,
        include_lots: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.item_ids = item_ids
        self.interval_seconds = interval_seconds
        self.include_lots = include_lots
        self._timer: Optional[QTimer] = None
        self._auto_running = False

    def start_auto_sync(self, force_first: bool = True) -> None:
        if self._auto_running:
            return
        self._auto_running = True

        if force_first:
            self.sync_prices(self.item_ids, include_lots=self.include_lots)

        self._timer = QTimer(self)
        self._timer.timeout.connect(
            lambda: self.sync_prices(self.item_ids, include_lots=self.include_lots)
        )
        self._timer.start(self.interval_seconds * 1000)
        log.info("AutoSyncManager: интервал %ds", self.interval_seconds)

    def stop_auto_sync(self) -> None:
        if not self._auto_running:
            return
        self._auto_running = False
        if self._timer:
            self._timer.stop()
            self._timer = None
        self.stop_sync()

    def set_interval(self, seconds: int) -> None:
        self.interval_seconds = seconds
        if self._timer:
            self._timer.setInterval(seconds * 1000)

    def cleanup(self) -> None:
        self.stop_auto_sync()
        super().cleanup()
