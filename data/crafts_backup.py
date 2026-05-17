import json, os
from app_paths import asset_path

_ITEMS_FILE = asset_path("items_full.json")


def _load_items() -> dict:
    if not os.path.exists(_ITEMS_FILE):
        return {}
    with open(_ITEMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


_RAW = _load_items()


def _pick(cat: str, names: list[str]) -> list:
    pool = {i["name"]: i["id"] for i in _RAW.get(cat, [])}
    result = []
    for name in names:
        if name in pool:
            result.append({"name": name, "item_id": pool[name]})
    return result


def _all(cat: str) -> list:
    return [{"name": i["name"], "item_id": i["id"]} for i in _RAW.get(cat, [])]


def _filter_bullets_bags_only(cat: str) -> list:
    """Возвращает только сумки патронов (фильтрует одинарные)"""
    all_items = _RAW.get(cat, [])
    result = []
    for item in all_items:
        name = item.get("name", "")
        # Оставляем только те, где в названии есть "Сумка"
        if "Сумка" in name or "сумка" in name:
            result.append({"name": name, "item_id": item["id"]})
    return result


# Функция для получения избранных предметов
def _get_favorites() -> list:
    """Возвращает список избранных предметов для категории"""
    from favorites_manager import get_favorites_manager

    fav_ids = get_favorites_manager().get_all()
    result = []

    for cat_key, cat_items in _RAW.items():
        for item in cat_items:
            if item["id"] in fav_ids:
                result.append(
                    {
                        "name": item["name"],
                        "item_id": item["id"],
                        "cat_key": cat_key,
                    }
                )

    return result


# ══════════════════════════════════════════════════════════════════════════
#  МЕДИКАМЕНТЫ — 15 подкатегорий (как в официальной вики STALCRAFT)
# ══════════════════════════════════════════════════════════════════════════


_MED_HEALING = [
    "Бинт",
    "«Гемостат»",
    "Морфин",
    "Эпинефрин",
    "«Биозаплатка»",
    "«Панацея»",
    "Аптечка индивидуальная",
    "Аптечка для экстремальных условий",
    "Военная аптечка",
    "Аптечка проводника",
    "Аптечка ученых",
    "Подсумок с индивидуальными аптечками",
    "Подсумок с военными аптечками",
    "Подсумок с аптечками проводника",
    "Подсумок с аптечками ученых",
]

_MED_BLEEDING_REMOVE = [
    "Бинт",
    "«Гемостат»",
]

_MED_BLEEDING_PROTECT = [
    "«Биозаплатка»",
]

_MED_RADIATION_REMOVE = [
    "Антирад Б-191",
    "Антирад Б-292",
    "Антирад Б-393",
]

_MED_ENDURANCE = [
    "«ТОПОТ»",
    "«Озверин»",
    "«УДАР»",
    "Энергетик «Батарейка»",
    "Энергетик «Жидень EXTRA»",
]

_MED_STRENGTH = [
    "«ШизоЁрш»",
    "Тоник «Арни»",
    "«Убийца Боли»",
]

_MED_SHORT_BUFF = [
    "«ТОПОТ»",
    "«Озверин»",
    "«ШизоЁрш»",
    "«УДАР»",
    "Тоник «Арни»",
    "«Убийца Боли»",
    "Энергетик «Батарейка»",
    "Энергетик «Жидень EXTRA»",
]

_MED_PSI_REMOVE = [
    "«ClearMind+»",
]

_MED_WEAK_RADIATION = [
    "Антирад Б-191",
]

_MED_RADIATION_PROTECT = [
    "Радиопротектор первого класса",
    "Радиопротектор второго класса",
    "Радиопротектор третьего класса",
]

_MED_PSI_PROTECT = [
    "Пси-блок «Нейрон-11»",
    "Пси-блок «Нейрон-22»",
    "Пси-блок «Нейрон-33»",
]

_MED_BIO_PROTECT = [
    "Антидот первого класса",
    "Антидот второго класса",
    "Антидот третьего класса",
    "Десперол",
    "Кларинол",
]

_MED_TEMPERATURE_PROTECT = [
    "Мазь от ожогов",
    "Сильная мазь от ожогов",
    "«Термобарьер» первого класса",
    "«Термобарьер» второго класса",
    "«Термобарьер» третьего класса",
]

_MED_COLD_RESIST = [
    "Согревающая сыворотка",
]

_MED_STRONG_BUFF = [
    "Анаболик «STARK»",
    "Анаболик «ATLAS»",
    "Анаболик «SALT»",
    "Силовой стимулятор",
    "Нейротоник",
    "«Астрикцин»",
    "Коктейль «Незабываемый»",
    "«Шапочка из фольги»",
]


# ══════════════════════════════════════════════════════════════════════════
#  БРОНЕПЛАСТИНЫ — 3 подкатегории
# ══════════════════════════════════════════════════════════════════════════


_ARMOR_STEEL = [
    "Сумка стальных пластин III",
    "Сумка стальных пластин IV",
    "Сумка стальных пластин V",
]

_ARMOR_CERAMIC = [
    "Сумка керамических пластин III",
    "Сумка керамических пластин IV",
    "Сумка керамических пластин V",
]

_ARMOR_COMPOSITE = [
    "Сумка композитных пластин III",
    "Сумка композитных пластин IV",
    "Сумка композитных пластин V",
]


# ══════════════════════════════════════════════════════════════════════════
#  СХРОНЫ — 2 подкатегории
# ══════════════════════════════════════════════════════════════════════════


_STASH_MASTER = [
    "Схрон мастера",
    "Экранированный схрон мастера",
]

_STASH_VETERAN = [
    "Схрон ветерана",
    "Экранированный схрон ветерана",
]


# ══════════════════════════════════════════════════════════════════════════
#  CRAFT_CATEGORIES — ФИНАЛЬНАЯ СТРУКТУРА
# ══════════════════════════════════════════════════════════════════════════


CRAFT_CATEGORIES = {
    # ═══ ИЗБРАННОЕ ═════════════════════════════════════════════════════════
    "Избранное": {
        "icon_file": "favorite",
        "subcategories": {
            "||Избранные предметы": _get_favorites,
        },
        "cat_key": "favorites",
        "is_best": False,
        "is_favorites": True,
    },
    
    # ═══ ЛУЧШЕЕ ════════════════════════════════════════════════════════════
    "Лучшее": {
        "icon_file": "best",
        "subcategories": {
            "🔥 Топ ликвидности": [],
        },
        "cat_key": "best",
        "is_best": True,
    },
    
    # ═══ МЕДИКАМЕНТЫ (15 подкатегорий) ════════════════════════════════════
    "Медикаменты": {
        "icon_file": "medicine",
        "subcategories": {
            "healing||Лечение": _pick("medicine", _MED_HEALING),
            "bleeding_remove||Устранение кровотечения": _pick("medicine", _MED_BLEEDING_REMOVE),
            "bleeding_protect||Защита от кровотечения": _pick("medicine", _MED_BLEEDING_PROTECT),
            "radiation_remove||Вывод радиации": _pick("medicine", _MED_RADIATION_REMOVE),
            "endurance||Повышение выносливости": _pick("medicine", _MED_ENDURANCE),
            "strength||Повышение силы": _pick("medicine", _MED_STRENGTH),
            "short_buff||Кратковременное усиление": _pick("medicine", _MED_SHORT_BUFF),
            "psi_remove||Вывод пси-излучения": _pick("medicine", _MED_PSI_REMOVE),
            "weak_radiation||Слабый вывод радиации": _pick("medicine", _MED_WEAK_RADIATION),
            "radiation_protect||Защита от радиации": _pick("medicine", _MED_RADIATION_PROTECT),
            "psi_protect||Защита от пси-излучения": _pick("medicine", _MED_PSI_PROTECT),
            "bio_protect||Защита от биозаражения": _pick("medicine", _MED_BIO_PROTECT),
            "temp_protect||Защита от температуры": _pick("medicine", _MED_TEMPERATURE_PROTECT),
            "cold_resist||Сопротивление холоду": _pick("medicine", _MED_COLD_RESIST),
            "strong_buff||Мощное усиление": _pick("medicine", _MED_STRONG_BUFF),
        },
        "cat_key": "medicine",
        "is_best": False,
    },
    
    # ═══ ЕДА (без подкатегорий) ════════════════════════════════════════════
    "Еда": {
        "icon_file": "food",
        "subcategories": {
            "food||Вся еда": _all("food"),
        },
        "cat_key": "food",
        "is_best": False,
    },
    
    # ═══ НАПИТКИ (без подкатегорий) ════════════════════════════════════════
    "Напитки": {
        "icon_file": "drink",
        "subcategories": {
            "drink||Все напитки": _all("drink"),
        },
        "cat_key": "drink",
        "is_best": False,
    },
    
    # ═══ ГРАНАТЫ (без подкатегорий) ════════════════════════════════════════
    "Гранаты": {
        "icon_file": "grenade",
        "subcategories": {
            "grenade||Все гранаты": _all("grenade"),
        },
        "cat_key": "grenade",
        "is_best": False,
    },
    
    # ═══ БОЕПРИПАСЫ (ТОЛЬКО СУМКИ) ═════════════════════════════════════════
    "Боеприпасы": {
        "icon_file": "bullet",
        "subcategories": {
            "bullet||Сумки патронов": _filter_bullets_bags_only("bullet"),
        },
        "cat_key": "bullet",
        "is_best": False,
    },
    
    # ═══ МАТЕРИАЛЫ (без подкатегорий) ══════════════════════════════════════
    "Материалы": {
        "icon_file": "materials",
        "subcategories": {
            "materials||Все материалы": _all("materials"),
        },
        "cat_key": "materials",
        "is_best": False,
    },
    
    # ═══ БРОНЕПЛАСТИНЫ (3 подкатегории) ════════════════════════════════════
    "Бронепластины": {
        "icon_file": "armor_bags",
        "subcategories": {
            "armor_steel||Стальные": _pick("armor_bags", _ARMOR_STEEL),
            "armor_ceramic||Керамические": _pick("armor_bags", _ARMOR_CERAMIC),
            "armor_composite||Композитные": _pick("armor_bags", _ARMOR_COMPOSITE),
        },
        "cat_key": "armor_bags",
        "is_best": False,
    },
    
    # ═══ СХРОНЫ (2 подкатегории) ═══════════════════════════════════════════
    "Схроны": {
        "icon_file": "stash",
        "subcategories": {
            "stash_master||Схроны мастера": _pick("containers", _STASH_MASTER),
            "stash_veteran||Схроны ветерана": _pick("containers", _STASH_VETERAN),
        },
        "cat_key": "containers",
        "is_best": False,
    },
    
    # ═══ КАЛЬКУЛЯТОР КРАФТА ════════════════════════════════════════════════
    "Калькулятор": {
        "icon_file": "calculator",
        "subcategories": {"calculator||Все рецепты": []},
        "cat_key": "calculator",
        "is_calculator": True,
        "is_best": False,
        "is_separator_before": True,
    },
}
