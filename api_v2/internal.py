"""
api_v2/internal.py — Доступ к внутреннему (unofficial) API STALCRAFT

Источник: https://github.com/Art3mLapa/unofficial-stalcraft-api

ВОЗМОЖНОСТИ:
  - Получение скрытых предметов (не в официальном EAPI)
  - Список игровых серверов
  - Расширенная история аукциона (до 200 записей)
  - Информация о персонажах
  
ВАЖНО: Это unofficial API, используйте с осторожностью!
"""

import aiohttp
import logging
from typing import List, Dict, Optional
from datetime import datetime

log = logging.getLogger("stalcraft.internal")


class InternalAPI:
    """
    Доступ к внутреннему API игры
    
    НЕ ТРЕБУЕТ API КЛЮЧЕЙ!
    """
    
    # Backend API (требует login/session для некоторых эндпоинтов)
    BACKEND_URL = "https://backend.stalcraftx.ru"
    
    # Unofficial зеркала официального API
    STALNOTE_URL = "https://backend.stalnote.ru"
    LUNAR_URL = "https://lunar-client.ru/web-api/stalcraft"
    WIKI_CDN = "https://cdn.stalcraft.wiki/exbo_item_parser"
    
    def __init__(self, timeout: int = 10):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать сессию"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session
    
    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    # ═══════════════════════════════════════════════════════════════════════
    # Скрытые предметы (НЕ в официальном EAPI!)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_hidden_items(self) -> List[Dict]:
        """
        Получить список ВСЕХ предметов (включая скрытые)
        
        Эти предметы есть в игре, но отсутствуют в:
        - Официальном EAPI
        - stalcraft-database
        
        Returns:
            [
                {
                    "id": 245602,
                    "name": "Самодельный светошум",
                    "type": "grenade",
                    "color": "DEFAULT"
                },
                ...
            ]
        """
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.STALNOTE_URL}/noauthorize/GameItems/uniq") as resp:
                resp.raise_for_status()
                items = await resp.json()
                
                log.info(f"✅ Получено {len(items)} предметов (включая скрытые)")
                return items
        
        except Exception as e:
            log.error(f"❌ Ошибка при получении скрытых предметов: {e}")
            return []
    
    async def get_compact_database(self) -> List[Dict]:
        """
        Получить сжатую версию stalcraft-database
        
        Более быстрая альтернатива EXBO-Studio/stalcraft-database
        
        Returns:
            [
                {
                    "id": "1rk6g",
                    "category": "armor/clothes",
                    "name": {"ru": "Бандитский кожак", "en": "Bandit Coat"},
                    "color": "DEFAULT"
                },
                ...
            ]
        """
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.WIKI_CDN}/listing.json") as resp:
                resp.raise_for_status()
                items = await resp.json()
                
                log.info(f"✅ Получено {len(items)} предметов из compact database")
                return items
        
        except Exception as e:
            log.error(f"❌ Ошибка при получении compact database: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════
    # Расширенная история аукциона (до 200 записей!)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_extended_auction_history(
        self,
        item_id: str,
        region: str = "ru",
        limit: int = 200
    ) -> List[Dict]:
        """
        Получить расширенную историю аукциона
        
        ПРЕИМУЩЕСТВА:
        - До 200 записей (вместо 50 в официальном API)
        - Дополнительные поля в 'additional'
        - Информация о покупателях
        
        Args:
            item_id: ID предмета (из stalcraft-database)
            region: Регион (ru, eu, na, sea)
            limit: Лимит записей (макс 200)
        
        Returns:
            [
                {
                    "amount": 1,
                    "price": 750000000,
                    "time": "2025-12-30T21:08:23Z",
                    "additional": {
                        "buyer": "ЗолотойНоми",
                        "it_transf_count": 2,
                        ...
                    }
                },
                ...
            ]
        """
        session = await self._get_session()
        
        params = {
            "action": "history",
            "item": item_id,
            "region": region,
            "limit": min(limit, 200)  # Макс 200
        }
        
        try:
            async with session.get(f"{self.LUNAR_URL}/auction.php", params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
                prices = data.get("prices", [])
                log.info(f"✅ Получено {len(prices)} записей истории для {item_id}")
                
                return prices
        
        except Exception as e:
            log.error(f"❌ Ошибка при получении расширенной истории: {e}")
            return []
    
    async def get_extended_auction_lots(
        self,
        item_id: str,
        region: str = "ru",
        limit: int = 200
    ) -> List[Dict]:
        """
        Получить расширенные активные лоты
        
        Args:
            item_id: ID предмета
            region: Регион
            limit: Лимит записей
        
        Returns:
            Список активных лотов с дополнительными полями
        """
        session = await self._get_session()
        
        params = {
            "action": "lots",
            "item": item_id,
            "region": region,
            "limit": min(limit, 200)
        }
        
        try:
            async with session.get(f"{self.LUNAR_URL}/auction.php", params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
                lots = data.get("lots", [])
                log.info(f"✅ Получено {len(lots)} активных лотов для {item_id}")
                
                return lots
        
        except Exception as e:
            log.error(f"❌ Ошибка при получении активных лотов: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════
    # Backend API (требует авторизацию)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_server_list(self, login: str) -> Dict:
        """
        Получить список игровых серверов
        
        Args:
            login: Логин пользователя EXBO или stm:STEAMID
        
        Returns:
            {
                "mode": "roxy",
                "pools": [
                    {
                        "name": "MSK2",
                        "tunnels": [
                            {"address": "111.222.33.444:12345", "name": "MSK2-1"},
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        session = await self._get_session()
        
        params = {"login": login}
        
        try:
            async with session.get(f"{self.BACKEND_URL}/address_list", params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
                log.info(f"✅ Получен список серверов для {login}")
                return data
        
        except Exception as e:
            log.error(f"❌ Ошибка при получении списка серверов: {e}")
            return {}
    
    async def get_arsenal_prices(self) -> Dict:
        """
        Получить таблицу предметов для фарма репутации Арсена
        
        С учётом цен на аукционе в реальном времени!
        
        Returns:
            {
                "success": true,
                "data": {
                    "items": [
                        {
                            "name": "Малый артефактный фрагмент",
                            "id": "z3k1m",
                            "reputation": 1,
                            "avgPrice": 404,
                            "totalPrice": 4040000,
                            ...
                        },
                        ...
                    ]
                }
            }
        """
        session = await self._get_session()
        
        params = {"action": "prices"}
        
        try:
            async with session.get(f"{self.LUNAR_URL}/arsenal.php", params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
                log.info("✅ Получена таблица предметов Арсена")
                return data
        
        except Exception as e:
            log.error(f"❌ Ошибка при получении таблицы Арсена: {e}")
            return {}


# ═══════════════════════════════════════════════════════════════════════
# Удобные функции
# ═══════════════════════════════════════════════════════════════════════

async def get_all_items_including_hidden() -> List[Dict]:
    """
    Получить ВСЕ предметы игры (официальные + скрытые)
    
    Объединяет:
    - stalcraft-database (compact)
    - Скрытые предметы из Stalnote
    
    Returns:
        Полный список всех предметов игры
    """
    async with InternalAPI() as api:
        # Получаем оба источника
        compact_db = await api.get_compact_database()
        hidden_items = await api.get_hidden_items()
        
        # Объединяем (убираем дубликаты по ID)
        all_items = {}
        
        # Добавляем из compact database
        for item in compact_db:
            all_items[item["id"]] = item
        
        # Добавляем скрытые (если их нет в базе)
        for item in hidden_items:
            item_id = str(item["id"])
            if item_id not in all_items:
                all_items[item_id] = {
                    "id": item_id,
                    "name": {"ru": item["name"]},
                    "category": item["type"],
                    "color": item.get("color", "DEFAULT"),
                    "hidden": True  # Помечаем как скрытый
                }
        
        log.info(f"✅ Всего предметов (включая скрытые): {len(all_items)}")
        
        return list(all_items.values())
