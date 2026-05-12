# craft_levels.py
# Данные об уровнях крафта предметов в убежище
# Источник: stalcraft.fandom.com/ru/wiki/Крафт
#
# Навыки (8 штук, каждый до 5 уровня):
#   ammo         — Боеприпасы       (верстак)
#   pyro         — Пиротехника      (верстак)
#   armor        — Защитное снаряжение (верстак)
#   engineering  — Инженерия        (верстак)
#   cooking      — Кулинария        (кухонный стол)
#   brewing      — Самогоноварение  (кухонный стол)
#   medicine     — Медицина         (лабораторный стол)
#   materials    — Сырьё и материалы (верстак + лаб. стол)
#
# Формат: "item_id": {"skill": "навык", "level": уровень, "station": "станция", "name": "название"}
#
# Добавляй новые предметы в этот словарь по мере необходимости.
# item_id берётся из API Stalcraft (поле item_id в ответе /items)


SKILL_NAMES = {
    "ammo":        "Боеприпасы",
    "pyro":        "Пиротехника",
    "armor":       "Защитное снаряжение",
    "engineering": "Инженерия",
    "cooking":     "Кулинария",
    "brewing":     "Самогоноварение",
    "medicine":    "Медицина",
    "materials":   "Сырьё и материалы",
}


STATION_NAMES = {
    "workbench": "Верстак",
    "lab":       "Лабораторный стол",
    "kitchen":   "Кухонный стол",
}


CRAFT_LEVELS: dict[str, dict] = {

    # ══════════════════════════════════════════════════════
    # МЕДИЦИНА (Лабораторный стол)
    # ══════════════════════════════════════════════════════
    "drug_schizoperch":       {"skill": "medicine", "level": 5, "station": "lab", "name": "Шизоёрш"},
    "drug_analgin":           {"skill": "medicine", "level": 1, "station": "lab", "name": "Анальгин"},
    "drug_bandage":           {"skill": "medicine", "level": 1, "station": "lab", "name": "Жгут"},
    "drug_antidote":          {"skill": "medicine", "level": 2, "station": "lab", "name": "Антидот"},
    "drug_stimulator":        {"skill": "medicine", "level": 2, "station": "lab", "name": "Стимулятор"},
    "drug_morphine":          {"skill": "medicine", "level": 3, "station": "lab", "name": "Морфин"},
    "drug_antitoxin":         {"skill": "medicine", "level": 3, "station": "lab", "name": "Антитоксин"},
    "drug_blood_plasma":      {"skill": "medicine", "level": 4, "station": "lab", "name": "Плазма крови"},
    "drug_coagulant":         {"skill": "medicine", "level": 4, "station": "lab", "name": "Коагулянт"},
    "drug_adrenaline":        {"skill": "medicine", "level": 5, "station": "lab", "name": "Адреналин"},
    "drug_neurodeg":          {"skill": "medicine", "level": 5, "station": "lab", "name": "Нейродегенерант"},
    "drug_nootrope":          {"skill": "medicine", "level": 4, "station": "lab", "name": "Ноотроп"},
    "drug_psycho":            {"skill": "medicine", "level": 3, "station": "lab", "name": "Психореагент"},
    "drug_telomir":           {"skill": "medicine", "level": 5, "station": "lab", "name": "Теломераза"},
    "drug_gnosis":            {"skill": "medicine", "level": 5, "station": "lab", "name": "Гнозис"},
    "drug_mutagen":           {"skill": "medicine", "level": 4, "station": "lab", "name": "Мутаген"},
    "drug_hormone":           {"skill": "medicine", "level": 3, "station": "lab", "name": "Гормоны"},
    "drug_aminoacid":         {"skill": "medicine", "level": 2, "station": "lab", "name": "Аминокислота"},
    # мази от ожогов — добавлены
    "drug_burn":              {"skill": "medicine", "level": 2, "station": "lab", "name": "Мазь от ожогов"},
    "drug_burn_strong":       {"skill": "medicine", "level": 3, "station": "lab", "name": "Сильная мазь от ожогов"},

    # ══════════════════════════════════════════════════════
    # БОЕПРИПАСЫ (Верстак)
    # ══════════════════════════════════════════════════════
    "ammo_9x18":              {"skill": "ammo", "level": 1, "station": "workbench", "name": "Патрон 9×18 мм"},
    "ammo_9x19":              {"skill": "ammo", "level": 2, "station": "workbench", "name": "Патрон 9×19 мм"},
    "ammo_545x39":            {"skill": "ammo", "level": 2, "station": "workbench", "name": "Патрон 5.45×39 мм"},
    "ammo_556x45":            {"skill": "ammo", "level": 3, "station": "workbench", "name": "Патрон 5.56×45 мм"},
    "ammo_762x39":            {"skill": "ammo", "level": 2, "station": "workbench", "name": "Патрон 7.62×39 мм"},
    "ammo_762x51":            {"skill": "ammo", "level": 3, "station": "workbench", "name": "Патрон 7.62×51 мм"},
    "ammo_762x54":            {"skill": "ammo", "level": 3, "station": "workbench", "name": "Патрон 7.62×54R мм"},
    "ammo_12x70":             {"skill": "ammo", "level": 1, "station": "workbench", "name": "Дробь 12×70 мм"},
    "ammo_23x75":             {"skill": "ammo", "level": 4, "station": "workbench", "name": "Патрон 23×75 мм"},
    "ammo_50bmg":             {"skill": "ammo", "level": 5, "station": "workbench", "name": "Патрон .50 BMG"},
    "ammo_127x55":            {"skill": "ammo", "level": 4, "station": "workbench", "name": "Патрон 12.7×55 мм"},
    "ammo_46x30":             {"skill": "ammo", "level": 3, "station": "workbench", "name": "Патрон 4.6×30 мм"},
    "ammo_gs":                {"skill": "ammo", "level": 1, "station": "workbench", "name": "Гильза"},
    "ammo_large_bullet":      {"skill": "ammo", "level": 3, "station": "workbench", "name": "Крупнокалиберная пуля"},
    "ammo_bullet_alloy":      {"skill": "ammo", "level": 2, "station": "workbench", "name": "Пулевой сплав"},

    # ══════════════════════════════════════════════════════
    # ПИРОТЕХНИКА (Верстак)
    # ══════════════════════════════════════════════════════
    "pyro_grenade_f1":        {"skill": "pyro", "level": 2, "station": "workbench", "name": "Граната Ф-1"},
    "pyro_grenade_rgd":       {"skill": "pyro", "level": 1, "station": "workbench", "name": "Граната РГД-5"},
    "pyro_smoke":             {"skill": "pyro", "level": 1, "station": "workbench", "name": "Дымовая граната"},
    "pyro_molotov":           {"skill": "pyro", "level": 2, "station": "workbench", "name": "Коктейль Молотова"},
    "pyro_flashbang":         {"skill": "pyro", "level": 3, "station": "workbench", "name": "Светошумовая граната"},
    "pyro_dynamite":          {"skill": "pyro", "level": 3, "station": "workbench", "name": "Динамит"},
    "pyro_claymore":          {"skill": "pyro", "level": 5, "station": "workbench", "name": "M18 Claymore"},
    "pyro_gunpowder":         {"skill": "pyro", "level": 1, "station": "workbench", "name": "Порох"},
    "pyro_nitro":             {"skill": "pyro", "level": 4, "station": "workbench", "name": "Нитроглицерин"},
    "pyro_smoke_powder":      {"skill": "pyro", "level": 2, "station": "workbench", "name": "Дымный порох"},
    "pyro_thermite":          {"skill": "pyro", "level": 3, "station": "workbench", "name": "Термическая смесь"},
    "pyro_nitrogel":          {"skill": "pyro", "level": 4, "station": "workbench", "name": "Нитрожелатин"},

    # ══════════════════════════════════════════════════════
    # ЗАЩИТНОЕ СНАРЯЖЕНИЕ (Верстак)
    # ══════════════════════════════════════════════════════
    "armor_plate_light":      {"skill": "armor", "level": 1, "station": "workbench", "name": "Лёгкая бронеплита"},
    "armor_plate_medium":     {"skill": "armor", "level": 2, "station": "workbench", "name": "Средняя бронеплита"},
    "armor_plate_heavy":      {"skill": "armor", "level": 3, "station": "workbench", "name": "Тяжёлая бронеплита"},
    "armor_plate_super":      {"skill": "armor", "level": 4, "station": "workbench", "name": "Сверхпрочная пластина"},
    "armor_plate_anomal":     {"skill": "armor", "level": 5, "station": "workbench", "name": "Аномальная пластина"},
    "armor_plate_hunt":       {"skill": "armor", "level": 3, "station": "workbench", "name": "Охотничья пластина"},
    "armor_kevlar":           {"skill": "armor", "level": 4, "station": "workbench", "name": "Кевлар"},
    "armor_vest":             {"skill": "armor", "level": 2, "station": "workbench", "name": "Плитоноска"},
    "armor_gear":             {"skill": "armor", "level": 1, "station": "workbench", "name": "Защитное снаряжение"},

    # ══════════════════════════════════════════════════════
    # ИНЖЕНЕРИЯ (Верстак)
    # ══════════════════════════════════════════════════════
    "eng_cart":               {"skill": "engineering", "level": 1, "station": "workbench", "name": "Тележка с инструментами"},
    "eng_welder":             {"skill": "engineering", "level": 2, "station": "workbench", "name": "Сварочное оборудование"},
    "eng_electronics":        {"skill": "engineering", "level": 2, "station": "workbench", "name": "Набор для работы с электроникой"},
    "eng_lathe":              {"skill": "engineering", "level": 3, "station": "workbench", "name": "Токарный станок"},
    "eng_lab_table":          {"skill": "engineering", "level": 2, "station": "workbench", "name": "Лабораторный стол"},
    "eng_kitchen_table":      {"skill": "engineering", "level": 1, "station": "workbench", "name": "Кухонный стол"},
    "eng_inverter":           {"skill": "engineering", "level": 3, "station": "workbench", "name": "Инвертор"},
    "eng_water":              {"skill": "engineering", "level": 1, "station": "workbench", "name": "Водосборник"},
    "eng_conditioner":        {"skill": "engineering", "level": 4, "station": "workbench", "name": "Система кондиционирования"},
    "eng_reactor":            {"skill": "engineering", "level": 5, "station": "workbench", "name": "Химический реактор"},
    "eng_keychain_s":         {"skill": "engineering", "level": 1, "station": "workbench", "name": "Маленькая ключница"},
    "eng_keychain_m":         {"skill": "engineering", "level": 2, "station": "workbench", "name": "Ключница"},
    "eng_keychain_l":         {"skill": "engineering", "level": 3, "station": "workbench", "name": "Большая ключница"},
    "eng_keychain_xl":        {"skill": "engineering", "level": 5, "station": "workbench", "name": "Особая ключница"},
    "eng_rotor":              {"skill": "engineering", "level": 4, "station": "workbench", "name": "Роторная система"},
    "eng_electric_motor":     {"skill": "engineering", "level": 3, "station": "workbench", "name": "Электродвигатель"},
    "eng_auto_transformer":   {"skill": "engineering", "level": 4, "station": "workbench", "name": "Автотрансформатор"},
    "eng_precise_tools":      {"skill": "engineering", "level": 4, "station": "workbench", "name": "Точные электроинструменты"},
    "eng_gas_station":        {"skill": "engineering", "level": 2, "station": "workbench", "name": "Станция для приёма баллонов с газом"},
    "eng_battery_station":    {"skill": "engineering", "level": 2, "station": "workbench", "name": "Станция для приёма батарей"},
    "eng_fuel_filter":        {"skill": "engineering", "level": 1, "station": "workbench", "name": "Топливный фильтр"},
    "eng_marli_filter":       {"skill": "engineering", "level": 1, "station": "workbench", "name": "Фильтр из марли"},

    # ══════════════════════════════════════════════════════
    # КУЛИНАРИЯ (Кухонный стол)
    # ══════════════════════════════════════════════════════
    "food_bread":             {"skill": "cooking", "level": 1, "station": "kitchen", "name": "Хлеб"},
    "food_stew":              {"skill": "cooking", "level": 1, "station": "kitchen", "name": "Тушёнка"},
    "food_porridge":          {"skill": "cooking", "level": 2, "station": "kitchen", "name": "Каша"},
    "food_meat":              {"skill": "cooking", "level": 2, "station": "kitchen", "name": "Жареное мясо"},
    "food_soup":              {"skill": "cooking", "level": 3, "station": "kitchen", "name": "Суп"},
    "food_can_pasta":         {"skill": "cooking", "level": 1, "station": "kitchen", "name": "Банка с макаронами"},
    "food_can_peas":          {"skill": "cooking", "level": 1, "station": "kitchen", "name": "Банка с горохом"},
    "food_can_beans":         {"skill": "cooking", "level": 1, "station": "kitchen", "name": "Банка с фасолью"},
    "food_can_groats":        {"skill": "cooking", "level": 1, "station": "kitchen", "name": "Банка с пшеном"},
    "food_milk":              {"skill": "cooking", "level": 1, "station": "kitchen", "name": "Молоко"},
    "food_coffee":            {"skill": "cooking", "level": 2, "station": "kitchen", "name": "Кофе"},
    "food_dough":             {"skill": "cooking", "level": 2, "station": "kitchen", "name": "Тесто"},
    "food_flour":             {"skill": "cooking", "level": 1, "station": "kitchen", "name": "Мука"},
    "food_fat":               {"skill": "cooking", "level": 1, "station": "kitchen", "name": "Очищенный жир"},
    "food_dog_meat":          {"skill": "cooking", "level": 2, "station": "kitchen", "name": "Мясо шавки"},
    "food_boar_meat":         {"skill": "cooking", "level": 2, "station": "kitchen", "name": "Мясо кабана"},
    "food_pig_meat":          {"skill": "cooking", "level": 2, "station": "kitchen", "name": "Мясо хрюши"},
    "food_fish":              {"skill": "cooking", "level": 3, "station": "kitchen", "name": "Полутухлая рыба"},

    # ══════════════════════════════════════════════════════
    # САМОГОНОВАРЕНИЕ (Кухонный стол)
    # ══════════════════════════════════════════════════════
    "brew_yeast":             {"skill": "brewing", "level": 1, "station": "kitchen", "name": "Дрожжи"},
    "brew_mash":              {"skill": "brewing", "level": 1, "station": "kitchen", "name": "Брага"},
    "brew_moonshine":         {"skill": "brewing", "level": 2, "station": "kitchen", "name": "Самогон"},
    "brew_vodka":             {"skill": "brewing", "level": 3, "station": "kitchen", "name": "Водка"},
    "brew_spirit":            {"skill": "brewing", "level": 4, "station": "kitchen", "name": "Спирт"},
    "brew_anomal_yeast":      {"skill": "brewing", "level": 3, "station": "kitchen", "name": "Аномальные дрожжи"},
    "brew_shining_sugar":     {"skill": "brewing", "level": 4, "station": "kitchen", "name": "«Светящийся сахар»"},
    "brew_biogas":            {"skill": "brewing", "level": 2, "station": "kitchen", "name": "Биогаз"},

    # ══════════════════════════════════════════════════════
    # СЫРЬЁ И МАТЕРИАЛЫ (Верстак + Лабораторный стол)
    # ══════════════════════════════════════════════════════
    "mat_iron":               {"skill": "materials", "level": 1, "station": "workbench", "name": "Железо"},
    "mat_steel":              {"skill": "materials", "level": 2, "station": "workbench", "name": "Сталь"},
    "mat_strong_steel":       {"skill": "materials", "level": 3, "station": "workbench", "name": "Крепкая сталь"},
    "mat_hard_steel":         {"skill": "materials", "level": 4, "station": "workbench", "name": "Прочный металл"},
    "mat_copper":             {"skill": "materials", "level": 1, "station": "workbench", "name": "Медь"},
    "mat_brass":              {"skill": "materials", "level": 2, "station": "workbench", "name": "Латунь"},
    "mat_lead":               {"skill": "materials", "level": 1, "station": "workbench", "name": "Свинец"},
    "mat_aluminium":          {"skill": "materials", "level": 2, "station": "workbench", "name": "Алюминий"},
    "mat_zinc":               {"skill": "materials", "level": 2, "station": "workbench", "name": "Цинк"},
    "mat_mercury":            {"skill": "materials", "level": 3, "station": "lab", "name": "Ртуть"},
    "mat_carbon":             {"skill": "materials", "level": 3, "station": "workbench", "name": "Карбоноволокно"},
    "mat_polymers":           {"skill": "materials", "level": 2, "station": "workbench", "name": "Полимеры"},
    "mat_polyprop":           {"skill": "materials", "level": 3, "station": "workbench", "name": "Полипропилен"},
    "mat_polyethylene":       {"skill": "materials", "level": 3, "station": "workbench", "name": "Полиэтиленовая основа"},
    "mat_boards":             {"skill": "materials", "level": 1, "station": "workbench", "name": "Доски"},
    "mat_chips":              {"skill": "materials", "level": 1, "station": "workbench", "name": "Щепки"},
    "mat_cloth":              {"skill": "materials", "level": 1, "station": "workbench", "name": "Ткань"},
    "mat_sewing_kit":         {"skill": "materials", "level": 1, "station": "workbench", "name": "Набор для шитья"},
    "mat_thread":             {"skill": "materials", "level": 1, "station": "workbench", "name": "Моток ниток"},
    "mat_textile_bag":        {"skill": "materials", "level": 2, "station": "workbench", "name": "Тканевая сумка"},
    "mat_glue":               {"skill": "materials", "level": 1, "station": "workbench", "name": "Клей"},
    "mat_microelectronics":   {"skill": "materials", "level": 3, "station": "lab", "name": "Микроэлектроника"},
    "mat_control_board":      {"skill": "materials", "level": 4, "station": "lab", "name": "Контрольная плата"},
    "mat_opsamp":             {"skill": "materials", "level": 4, "station": "lab", "name": "Операционный усилитель"},
    "mat_ammonia":            {"skill": "materials", "level": 2, "station": "lab", "name": "Аммиак"},
    "mat_chlorine":           {"skill": "materials", "level": 2, "station": "lab", "name": "Хлор"},
    "mat_acid":               {"skill": "materials", "level": 2, "station": "lab", "name": "Кислота"},
    "mat_sulfur_acid":        {"skill": "materials", "level": 3, "station": "lab", "name": "Серная кислота"},
    "mat_nitric_acid":        {"skill": "materials", "level": 3, "station": "lab", "name": "Азотная кислота"},
    "mat_hydrogen":           {"skill": "materials", "level": 3, "station": "lab", "name": "Водород"},
    "mat_ethylene":           {"skill": "materials", "level": 3, "station": "lab", "name": "Этилен"},
    "mat_ethylalum":          {"skill": "materials", "level": 4, "station": "lab", "name": "Этилалюмин"},
    "mat_methane":            {"skill": "materials", "level": 2, "station": "lab", "name": "Метан"},
    "mat_co2":                {"skill": "materials", "level": 2, "station": "lab", "name": "Углекислый газ"},
    "mat_glycerin":           {"skill": "materials", "level": 2, "station": "lab", "name": "Глицерин"},
    "mat_anilinium":          {"skill": "materials", "level": 4, "station": "lab", "name": "Анилин"},
    "mat_catalyst":           {"skill": "materials", "level": 5, "station": "lab", "name": "Катализатор"},
    "mat_abrasive":           {"skill": "materials", "level": 1, "station": "workbench", "name": "Абразив"},
    "mat_isolenta":           {"skill": "materials", "level": 1, "station": "workbench", "name": "Изолента"},
    "mat_oil":                {"skill": "materials", "level": 2, "station": "workbench", "name": "Нефть"},
    "mat_oil_coke":           {"skill": "materials", "level": 3, "station": "workbench", "name": "Нефтяной кокс"},
    "mat_lube":               {"skill": "materials", "level": 2, "station": "workbench", "name": "Смазочные материалы"},
    "mat_solvent":            {"skill": "materials", "level": 2, "station": "workbench", "name": "Промышленный растворитель"},
    "mat_sulfate":            {"skill": "materials", "level": 3, "station": "lab", "name": "Серная соль"},
    "mat_saltpeter":          {"skill": "materials", "level": 2, "station": "workbench", "name": "Селитра"},
    "mat_potash":             {"skill": "materials", "level": 2, "station": "lab", "name": "Поташ"},
    "mat_caustic_soda":       {"skill": "materials", "level": 3, "station": "lab", "name": "Едкий натрий"},
    "mat_al_chloride":        {"skill": "materials", "level": 4, "station": "lab", "name": "Хлорид алюминия"},
    "mat_al_powder":          {"skill": "materials", "level": 3, "station": "workbench", "name": "Алюминиевый порошок"},
    "mat_alpha_bio":          {"skill": "materials", "level": 3, "station": "lab", "name": "Альфа биоматериал"},
    "mat_protein":            {"skill": "materials", "level": 3, "station": "lab", "name": "Белковый субстрат"},
    "mat_anomal_materials":   {"skill": "materials", "level": 4, "station": "lab", "name": "Аномальные материалы"},
    "mat_anomal_plasma":      {"skill": "materials", "level": 5, "station": "lab", "name": "Аномальная плазма"},
    "mat_anomal_genes":       {"skill": "materials", "level": 5, "station": "lab", "name": "Аномальные гены"},
    "mat_dust_change":        {"skill": "materials", "level": 4, "station": "lab", "name": "Пыль изменения"},
    "mat_anomal_dust":        {"skill": "materials", "level": 3, "station": "lab", "name": "Аномальная пыль"},
    "mat_reagents":           {"skill": "materials", "level": 2, "station": "lab", "name": "Реагенты"},
    "mat_chrono_dust":        {"skill": "materials", "level": 5, "station": "lab", "name": "Хронопыль"},
    "mat_plastic_bottle":     {"skill": "materials", "level": 1, "station": "workbench", "name": "Пластиковая бутылка"},
    "mat_bottle":             {"skill": "materials", "level": 1, "station": "workbench", "name": "Консервная банка"},
    "mat_colba":              {"skill": "materials", "level": 3, "station": "lab", "name": "Колба с раствором"},
    "mat_iodide":             {"skill": "materials", "level": 3, "station": "lab", "name": "Йодид калия"},
    "mat_iodine":             {"skill": "materials", "level": 2, "station": "lab", "name": "Раствор йода"},
    "mat_protrombin":         {"skill": "materials", "level": 3, "station": "lab", "name": "Протромбин"},
    "mat_cover_protect":      {"skill": "materials", "level": 3, "station": "workbench", "name": "Защитное покрытие"},
    "mat_cover_fire":         {"skill": "materials", "level": 4, "station": "workbench", "name": "Зажигательное покрытие"},
    "mat_cover_damp":         {"skill": "materials", "level": 3, "station": "workbench", "name": "Амортизирующее покрытие"},
    "mat_gunpowder":          {"skill": "materials", "level": 1, "station": "workbench", "name": "Порох (сырьё)"},
    "mat_smoke_powder":       {"skill": "materials", "level": 2, "station": "workbench", "name": "Дымный порох"},
    "mat_nitroglycerine":     {"skill": "materials", "level": 3, "station": "lab", "name": "Нитроглицерин"},
    "mat_nitrogel":           {"skill": "materials", "level": 4, "station": "lab", "name": "Нитрожелатин"},
    "mat_thermite":           {"skill": "materials", "level": 3, "station": "workbench", "name": "Термическая смесь"},
    "mat_textil_kevlar":      {"skill": "materials", "level": 3, "station": "workbench", "name": "Кевлар"},
    "mat_flour":              {"skill": "materials", "level": 1, "station": "kitchen", "name": "Мука"},
    "mat_dough":              {"skill": "materials", "level": 2, "station": "kitchen", "name": "Тесто"},
    "mat_clean_reagents":     {"skill": "materials", "level": 2, "station": "lab", "name": "Очищающий реагент"},

    # ══════════════════════════════════════════════════════
    # СУМКИ БРОНЕПЛАСТИН (Верстак — навык "armor")
    # ══════════════════════════════════════════════════════
    "armor_bag_steel_3":      {"skill": "armor", "level": 1, "station": "workbench", "name": "Сумка стальных пластин III"},
    "armor_bag_steel_4":      {"skill": "armor", "level": 2, "station": "workbench", "name": "Сумка стальных пластин IV"},
    "armor_bag_steel_5":      {"skill": "armor", "level": 3, "station": "workbench", "name": "Сумка стальных пластин V"},
    "armor_bag_ceram_3":      {"skill": "armor", "level": 2, "station": "workbench", "name": "Сумка керамических пластин III"},
    "armor_bag_ceram_4":      {"skill": "armor", "level": 3, "station": "workbench", "name": "Сумка керамических пластин IV"},
    "armor_bag_ceram_5":      {"skill": "armor", "level": 4, "station": "workbench", "name": "Сумка керамических пластин V"},
    "armor_bag_comp_3":       {"skill": "armor", "level": 3, "station": "workbench", "name": "Сумка композитных пластин III"},
    "armor_bag_comp_4":       {"skill": "armor", "level": 4, "station": "workbench", "name": "Сумка композитных пластин IV"},
    "armor_bag_comp_5":       {"skill": "armor", "level": 5, "station": "workbench", "name": "Сумка композитных пластин V"},
}


def get_craft_info(item_id: str) -> dict | None:
    """
    Возвращает информацию о крафте предмета по его item_id.
    Если предмет не крафтится в убежище — возвращает None.
    """
    return CRAFT_LEVELS.get(item_id)


def format_craft_label(item_id: str) -> str:
    """
    Возвращает читаемую строку вида:
      "🔧 Медицина ур.5 · Лабораторный стол"
    или пустую строку если предмет не крафтится.
    """
    info = get_craft_info(item_id)
    if not info:
        return ""
    skill   = SKILL_NAMES.get(info["skill"], info["skill"])
    level   = info["level"]
    station = STATION_NAMES.get(info["station"], info["station"])
    return f"🔧 {skill} ур.{level} · {station}"