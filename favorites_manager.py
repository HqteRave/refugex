# favorites_manager.py
"""
Менеджер избранного для STALCRAFT Market
Хранит избранные предметы в favorites.json
Поддерживает два типа: 'auction' (аукцион) и 'craft' (калькулятор)
"""

import json
import os
from typing import List, Set
from app_paths import app_path


class FavoritesManager:
    """Управление избранными предметами"""

    def __init__(self, filepath: str = None):
        if filepath is None:
            filepath = app_path("favorites.json")
        self.filepath = filepath
        self._favorites_auction: Set[str] = set()  # Избранное аукциона
        self._favorites_craft: Set[str] = set()    # Избранное калькулятора
        self._saving = False  # Флаг для предотвращения двойного сохранения
        self.load()
    
    def load(self):
        """Загрузить избранное из файла"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Старый формат (только items) - миграция в auction
                    if 'items' in data and 'auction' not in data:
                        self._favorites_auction = set(data.get('items', []))
                        self._favorites_craft = set()
                    else:
                        # Новый формат
                        self._favorites_auction = set(data.get('auction', []))
                        self._favorites_craft = set(data.get('craft', []))
            except Exception as e:
                print(f"Ошибка загрузки избранного: {e}")
                self._favorites_auction = set()
                self._favorites_craft = set()
        else:
            self._favorites_auction = set()
            self._favorites_craft = set()
    
    def save(self):
        """Сохранить избранное в файл (с защитой от двойных вызовов)"""
        if self._saving:
            return  # Предотвращаем повторный вызов
        
        self._saving = True
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'auction': list(self._favorites_auction),
                    'craft': list(self._favorites_craft)
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения избранного: {e}")
        finally:
            self._saving = False
    
    def add(self, item_id: str, fav_type: str = 'auction') -> bool:
        """
        Добавить предмет в избранное
        fav_type: 'auction' (аукцион) или 'craft' (калькулятор)
        Возвращает True если добавлен, False если уже был
        """
        favorites = self._favorites_auction if fav_type == 'auction' else self._favorites_craft
        if item_id not in favorites:
            favorites.add(item_id)
            self.save()
            return True
        return False
    
    def remove(self, item_id: str, fav_type: str = 'auction') -> bool:
        """
        Убрать предмет из избранного
        fav_type: 'auction' (аукцион) или 'craft' (калькулятор)
        Возвращает True если удалён, False если не был в избранном
        """
        favorites = self._favorites_auction if fav_type == 'auction' else self._favorites_craft
        if item_id in favorites:
            favorites.remove(item_id)
            self.save()
            return True
        return False
    
    def toggle(self, item_id: str, fav_type: str = 'auction') -> bool:
        """
        Переключить статус избранного
        fav_type: 'auction' (аукцион) или 'craft' (калькулятор)
        Возвращает True если теперь в избранном, False если убран
        """
        favorites = self._favorites_auction if fav_type == 'auction' else self._favorites_craft
        if item_id in favorites:
            favorites.remove(item_id)
            self.save()
            return False
        else:
            favorites.add(item_id)
            self.save()
            return True
    
    def is_favorite(self, item_id: str, fav_type: str = 'auction') -> bool:
        """
        Проверить в избранном ли предмет
        fav_type: 'auction' (аукцион) или 'craft' (калькулятор)
        """
        favorites = self._favorites_auction if fav_type == 'auction' else self._favorites_craft
        return item_id in favorites
    
    def get_all(self, fav_type: str = 'auction') -> List[str]:
        """
        Получить список всех избранных ID
        fav_type: 'auction' (аукцион) или 'craft' (калькулятор)
        """
        favorites = self._favorites_auction if fav_type == 'auction' else self._favorites_craft
        return list(favorites)
    
    def count(self, fav_type: str = 'auction') -> int:
        """
        Количество избранных предметов
        fav_type: 'auction' (аукцион) или 'craft' (калькулятор)
        """
        favorites = self._favorites_auction if fav_type == 'auction' else self._favorites_craft
        return len(favorites)
    
    def clear(self, fav_type: str = 'auction'):
        """
        Очистить избранное
        fav_type: 'auction' (аукцион), 'craft' (калькулятор) или 'all' (всё)
        """
        if fav_type == 'all':
            self._favorites_auction.clear()
            self._favorites_craft.clear()
        elif fav_type == 'auction':
            self._favorites_auction.clear()
        else:
            self._favorites_craft.clear()
        self.save()


# Глобальный экземпляр менеджера
_favorites_manager = None

def get_favorites_manager() -> FavoritesManager:
    """Получить глобальный экземпляр менеджера избранного"""
    global _favorites_manager
    if _favorites_manager is None:
        _favorites_manager = FavoritesManager()
    return _favorites_manager
