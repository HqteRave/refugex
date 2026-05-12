# id_aliases.py  [v3.0]
# Маппинг реальных хэш-ID из items_full.json → ключи CRAFT_LEVELS
# Источник ID: pump_id.py (вывод из items_full.json)
# Предметы без крафта в убежище (мякоти, аптечки, подсумки и т.д.) — не включены

REAL_ID_TO_CRAFT_KEY: dict[str, str] = {

    # ══════════════════════════════════════════════════════
    # МЕДИЦИНА
    # ══════════════════════════════════════════════════════
    "zzqk2": "drug_bandage",        # Бинт
    "y3knz": "drug_analgin",        # «Убийца Боли»
    "j5mq7": "drug_antidote",       # Антидот первого класса
    "qj9y6": "drug_antidote",       # Антидот второго класса
    "lynrj": "drug_antitoxin",      # Антидот третьего класса
    "1r2yq": "drug_stimulator",     # Силовой стимулятор
    "1r216": "drug_stimulator",     # «ТОПОТ»
    "p62q6": "drug_morphine",       # Морфин
    "2o9g0": "drug_hormone",        # «Озверин»
    "5lzyg": "drug_coagulant",      # «Гемостат»
    "6w59j": "drug_adrenaline",     # «УДАР»
    "vjy3n": "drug_adrenaline",     # Эпинефрин
    "6w5lj": "drug_schizoperch",    # «ШизоЁрш»
    "7lyd3": "drug_neurodeg",       # Анаболик «STARK»
    "964ow": "drug_aminoacid",      # Энергетик «Батарейка»
    "lynkj": "drug_aminoacid",      # Энергетик «Жидень EXTRA»
    "zzqo2": "drug_aminoacid",      # Анаболик «SALT»
    "g4l10": "drug_blood_plasma",   # Анаболик «ATLAS»
    "g4lk0": "drug_gnosis",         # Военная аптечка
    "g4lz0": "drug_mutagen",        # «Биозаплатка»
    "p6256": "drug_telomir",        # «Панацея»
    "zzqn2": "drug_nootrope",       # Нейротоник
    "1r2l6": "drug_antitoxin",      # «Астрикцин»
    "jowg":  "drug_psycho",         # Психореагент
    "964k0": "drug_burn_strong",    # Сильная мазь от ожогов
    "n4vw6": "drug_burn",           # Мазь от ожогов

    # ══════════════════════════════════════════════════════
    # ЕДА
    # ══════════════════════════════════════════════════════
    "1rn01": "food_bread",          # Кусок черного хлеба
    "96gqz": "food_bread",          # Кусок белого хлеба
    "j5456": "food_stew",           # Отличная тушенка
    "okrq0": "food_stew",           # Мясные консервы
    "p6056": "food_porridge",       # Каша гороховая с мясом
    "n4lg6": "food_porridge",       # Пшенка с мясом
    "5l23g": "food_soup",           # Солянка
    "wj2zp": "food_soup",           # Чесночный суп
    "y39yz": "food_soup",           # Гороховый суп
    "zz1o2": "food_soup",           # Фасолевый суп
    "dm165": "food_can_pasta",      # Макароны по-флотски
    "dmk95": "food_can_peas",       # Горох «Прошлогодний»
    "qjmjk": "food_can_peas",       # Боевой горох
    "lyn5j": "food_can_beans",      # Фасоль «Рождественская»
    "rwol5": "food_can_beans",      # Консервированная фасоль
    "4qg3p": "food_can_beans",      # Бобы «С новым счастьем!»
    "2dq0":  "food_dog_meat",       # Жареное мясо шавки
    "2dkm":  "food_dog_meat",       # Фарш из собаки
    "3r6z":  "food_pig_meat",       # Жареное мясо хрюши
    "3rjk":  "food_pig_meat",       # Фарш из хрюши
    "7rm3":  "food_boar_meat",      # Жареное мясо кабана
    "7rvr":  "food_boar_meat",      # Фарш из кабана
    "9mn0":  "food_fish",           # Рыбное филе
    "3g12z": "food_meat",           # Жаркое из мутантов
    "0row1": "food_can_groats",     # Рыбные консервы (условно как консерва-крупа)
    "vrwg":  "brew_mash",           # Сусло (идёт в самогоноварение)
    "5drg":  "brew_mash",           # Брага

    # Деликатесы / ИРП — без крафта в убежище:
    # 0rdjd, qj9n6, dm1ln, 4qdqn, wj2jo, wj2no — пропускаем

    # ══════════════════════════════════════════════════════
    # НАПИТКИ
    # ══════════════════════════════════════════════════════
    "1dwq":  "brew_mash",           # Базовое вино (условно брага/вино)
    "r2mv":  "brew_mash",           # Вино с осадком
    "2o9w0": "brew_moonshine",      # Грог
    "7lyo3": "brew_moonshine",      # «Алкобык»
    "3g1qz": "brew_vodka",          # Водка
    "2o900": "brew_vodka",          # Водка «Морозная»
    "964z0": "brew_vodka",          # Водка «Кривой Коготь»
    "6w5jj": "brew_vodka",          # Брусничная водка
    "g4lzg": "brew_vodka",          # Водка «Гейзер»
    "drmwj": "brew_spirit",         # Технический спирт

    # Безалкогольные / ивентовый алкоголь — без крафта:
    # rwow5, y75z, okdpo, n4vg6, dmk65, g07g, g4lp0, j5mg7, knop0, m0pyj, vjy0n, vjy5n, wjwzp, zzqn9

    # ══════════════════════════════════════════════════════
    # ГРАНАТЫ
    # ══════════════════════════════════════════════════════
    "29dm":  "pyro_grenade_f1",     # Ф-1
    "dkq9":  "pyro_grenade_rgd",    # РГД-5
    "p2r5":  "pyro_flashbang",      # M84
    "vyrg":  "pyro_flashbang",      # M84 QD
    "nvpw":  "pyro_flashbang",      # СЗГ «Вспышка»
    "g4rz0": "pyro_flashbang",      # Самодельный светошум
    "1r0y6": "pyro_dynamite",       # Ручная граната «Кустарник-1»

    # Остальные (гранатомётные, спец) — без крафта в убежище:
    # 12dq, 31rk, 65r6, 7yrr, 94mw, gl0g, jm94, lngq

    # ══════════════════════════════════════════════════════
    # ПАТРОНЫ (БАЗОВЫЕ)
    # ══════════════════════════════════════════════════════
    "9g6z":  "ammo_9x19",           # Патрон 9 мм
    "mj07":  "ammo_545x39",         # Патрон 5.45 мм
    "d1mn":  "ammo_556x45",         # Патрон 5.56 мм
    "1n91":  "ammo_762x39",         # Патрон 7.62 мм
    "l6y1":  "ammo_12x70",          # Дробь 12 калибра
    "52y0":  "ammo_23x75",          # Картечь 23x75
    "qm0k":  "ammo_large_bullet",   # Самодельный крупный
    "nln6":  "ammo_large_bullet",   # Серебряный крупный
    "1no1":  "ammo_127x55",         # Патрон 12.7 мм
    "3vog":  "ammo_127x55",         # Патрон 12.7 мм (ещё один ID)
    "nlk3":  "ammo_46x30",          # Патрон 10 мм
    "2p30":  "ammo_46x30",          # Патрон 10 мм СБП
    "j456":  "ammo_12x70",          # Картечь 12 калибра
    "0or1":  "ammo_large_bullet",   # Боевая пуля 12 калибра
    "z1kn":  "ammo_large_bullet",   # Боевая пуля 23x75
    "w20p":  "ammo_large_bullet",   # Крупнокалиберный жгучий патрон

    # Заготовки
    "ammo_gs":           "ammo_gs",           # Гильза (если придёт как item_id)
    "ammo_bullet_alloy": "ammo_bullet_alloy", # Пулевой сплав (если придёт как item_id)

    # Все остальные пули / сумки патронов — это уже готовые / комбинированные боеприпасы,
    # крафтятся по продвинутым рецептам; пока сознательно не отображаем как крафт убежища.

    # ══════════════════════════════════════════════════════
    # МАТЕРИАЛЫ
    # ══════════════════════════════════════════════════════
    "5njq":  "mat_aluminium",       # Алюминий
    "4nkr":  "mat_al_powder",       # Алюминиевый порошок
    "4njo":  "mat_al_chloride",     # Хлорид алюминия
    "q2yj":  "mat_strong_steel",    # Крепкая сталь
    "1731":  "mat_textil_kevlar",   # Кевлар
    "5n51":  "mat_gunpowder",       # Порох
    "z2om":  "mat_smoke_powder",    # Дымный порох
    "q224":  "mat_nitroglycerine",  # Нитроглицерин
    "gm2p":  "mat_nitrogel",        # Нитрожелатин
    "404p":  "mat_thermite",        # Термическая смесь
    "gmy0":  "mat_clean_reagents",  # Очищающий реагент
    "y7po":  "mat_reagents",        # Реагенты
    "6r0j":  "mat_flour",           # Мука
    "6rn6":  "mat_dough",           # Тесто
    "1dnq":  "mat_textile_bag",     # Тканевая сумка

    # ══════════════════════════════════════════════════════
    # СУМКИ БРОНЕПЛАСТИН
    # ══════════════════════════════════════════════════════
    "dmldj": "armor_bag_steel_3",   # Сумка стальных пластин III
    "2o6zl": "armor_bag_steel_4",   # Сумка стальных пластин IV
    "3g05l": "armor_bag_steel_5",   # Сумка стальных пластин V
    "96qjl": "armor_bag_ceram_3",   # Сумка керамических пластин III
    "1r0gg": "armor_bag_ceram_4",   # Сумка керамических пластин IV
    "g4rd6": "armor_bag_ceram_5",   # Сумка керамических пластин V
    "y31wk": "armor_bag_comp_3",    # Сумка композитных пластин III
    "wjn52": "armor_bag_comp_4",    # Сумка композитных пластин IV
    "4qzyr": "armor_bag_comp_5",    # Сумка композитных пластин V",
}


def get_craft_key(real_id: str) -> str:
    """Возвращает ключ CRAFT_LEVELS для данного хэш-ID, или сам ID если не найден."""
    return REAL_ID_TO_CRAFT_KEY.get(real_id, real_id)


def resolve_craft_info(real_id: str) -> dict | None:
    """Возвращает данные крафта по хэш-ID предмета."""
    from craft_levels import get_craft_info
    craft_key = get_craft_key(real_id)
    return get_craft_info(craft_key)