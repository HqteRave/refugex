"""
NON-TRADEABLE ITEMS - STALCRAFT
Предметы, которые нельзя продать на аукционе ИЛИ не крафтятся/не бартерятся

Последнее обновление: 15 мая 2026
Источник: stalcraft-database (EXBO-Studio/stalcraft-database)
База данных обновлена: 11 мая 2026
"""

# Множество ID всех предметов которые нужно скрыть из калькулятора
# Причины: PERSONAL статус (55) + нет крафта/бартера (11) = 66 предметов
NON_TRADEABLE_ITEMS = {
    # ═══════════════════════════════════════════════════════════════════
    # АВТОМАТИЧЕСКИ НАЙДЕННЫЕ НЕПРОДАВАЕМЫЕ (55 шт)
    # Статусы: PERSONAL_DROP_ON_GET и PERSONAL_ON_GET
    # ═══════════════════════════════════════════════════════════════════
    "009o9", "00rny", "0r52r", "191kg", "191ng", "19402", "21365", 
    "21gkl", "21gpl", "34305", "34zjl", "556z1", "55j6o", "6o7m0",
    "6ol3p", "77o96", "77ov6", "7lwvj", "96kkq", "9d1qy", "9dk7l",
    "9dkgl", "9dknl", "9dz1z", "dr6nj", "gn9l6", "j0wzl", "j0z30",
    "j0zy0", "kr54y", "kr5ky", "kr5oy", "krznp", "l093k", "l09qk",
    "m0lmr", "mr1jy", "nkgv1", "ol6z5", "olzr6", "pj52w", "q03dj",
    "q0p34", "rj6gv", "rj6ov", "rw32l", "vn0wr", "vn0yr", "w3022",
    "w30g2", "y405k", "y4y13", "z30mm", "z30qy", "z3n0k",
    
    # ═══════════════════════════════════════════════════════════════════
    # ВРУЧНУЮ ДОБАВЛЕННЫЕ (11 шт)
    # Причина: НЕ КРАФТЯТСЯ и НЕ БАРТЕРЯТСЯ (только дроп/ивент)
    # ═══════════════════════════════════════════════════════════════════
    "knoz0",  # Половинка мандарина
    "5lz3g",  # Дольки мандарина
    "rw1pg",  # Свежий мандарин
    "n4vo6",  # Аномальный мандарин
    "okdno",  # Кукуруза «Сладкий декабрь»
    "0rdjd",  # Шоколадный пломбир
    "y3kyz",  # Стаканчик мороженого
    "lyn5j",  # Фасоль «Рождественская»
    "dmk65",  # Праздничный пунш
    "2o9w0",  # Грог
    "7lyd3",  # Анаболик «STARK»
}


def is_tradeable(item_id: str) -> bool:
    """
    Проверяет, нужно ли показывать предмет в калькуляторе
    
    Args:
        item_id: ID предмета из базы данных
        
    Returns:
        True если предмет можно показать, False если нужно скрыть
        
    Examples:
        >>> is_tradeable("7lyd3")  # Анаболик STARK
        False
        >>> is_tradeable("knoz0")  # Половинка мандарина
        False
        >>> is_tradeable("dj7qe")  # Обычный предмет с крафтом
        True
    """
    return item_id not in NON_TRADEABLE_ITEMS


def get_non_tradeable_count() -> int:
    """Возвращает количество скрытых предметов"""
    return len(NON_TRADEABLE_ITEMS)


def get_non_tradeable_list() -> set:
    """Возвращает полный набор скрытых ID"""
    return NON_TRADEABLE_ITEMS.copy()


# Для удобства импорта
__all__ = [
    'NON_TRADEABLE_ITEMS',
    'is_tradeable',
    'get_non_tradeable_count',
    'get_non_tradeable_list'
]


if __name__ == "__main__":
    print(f"📊 Всего скрытых предметов: {get_non_tradeable_count()}")
    print()
    print("📋 Категории:")
    print("  • 55 - PERSONAL статусы (квестовые дропы, части схем)")
    print("  • 11 - нет крафта/бартера (только дроп/ивент)")
    print()
    print("📦 Примеры проверки:")
    print(f"  • '7lyd3' (Анаболик STARK) торгуется? {is_tradeable('7lyd3')}")
    print(f"  • 'knoz0' (Половинка мандарина) торгуется? {is_tradeable('knoz0')}")
    print(f"  • 'dj7qe' (Обычный предмет) торгуется? {is_tradeable('dj7qe')}")
