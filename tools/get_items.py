# get_items.py  [v1.1]
# Скачивает предметы из GitHub репозитория EXBO-Studio/stalcraft-database
# и обновляет items_full.json нужными категориями.
#
# Использование:
#   python get_items.py                          — обновить все категории
#   python get_items.py bullet grenade           — только патроны и гранаты
#   python get_items.py materials armor_bags     — материалы и сумки пластин

import sys
import os
import json
import time
import requests

# ── Настройки ──────────────────────────────────────────────────

GITHUB_API = "https://api.github.com/repos/EXBO-Studio/stalcraft-database"
GITHUB_RAW = "https://raw.githubusercontent.com/EXBO-Studio/stalcraft-database/main"
REALM      = "ru"
HEADERS    = {"Accept": "application/vnd.github+json"}

_ROOT      = os.path.dirname(os.path.abspath(__file__))
_OUT_FILE  = os.path.join(_ROOT, "items_full.json")

# ── Маппинг категорий ───────────────────────────────────────────
#
# "наш_ключ": ("папка_в_репо", фильтр_или_None)
# фильтр — функция(name) -> bool, если None — берём все предметы из папки

def _is_material(name: str) -> bool:
    """Фильтр для misc: только крафтуемые материалы и сырьё."""
    KW = [
        "Порох", "Мука", "Реагент", "Термическ", "Нитро",
        "Смола", "Алюмини", "Тесто", "Краситель", "Крепкая",
        "Закалённая", "Мягк", "Жёстк", "Резин", "Тканевая",
        "Кевлар", "заготов", "Дымный",
    ]
    return any(kw.lower() in name.lower() for kw in KW)

def _is_armor_bag(name: str) -> bool:
    """Фильтр для misc: только сумки бронепластин."""
    BAG_KW = ["Сумка", "Ящик"]
    PLATE_KW = ["пластин", "стальн", "керамич", "композит", "бронепласт"]
    return (
        any(kw in name for kw in BAG_KW) and
        any(kw.lower() in name.lower() for kw in PLATE_KW)
    )

CATEGORY_MAP = {
    # Папка в репо — без вложенных подпапок
    "medicine":  ("misc_skip", None),          # уже есть, не трогаем
    "food":      ("misc_skip", None),
    "drink":     ("misc_skip", None),
    "grenade":   ("grenade",   None),          # корень: ru/items/grenade/
    "bullet":    ("bullet",    None),          # корень: ru/items/bullet/
    # Новые:
    "materials": ("misc",      _is_material),  # сырьё/материалы из misc
    "armor_bags":("misc",      _is_armor_bag), # сумки бронепластин из misc
}

# ── Вспомогательные функции ─────────────────────────────────────

def _get_raw(url: str, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 403:
                print(f"    ⚠️  GitHub rate limit. Ждём 60 сек...")
                time.sleep(60)
            elif r.status_code == 404:
                return None
        except Exception as e:
            print(f"    ⚠️  Ошибка ({attempt+1}/{retries}): {e}")
            time.sleep(2)
    return None


def _parse_name(data: dict, item_id: str) -> str | None:
    name_obj = data.get("name", {})
    if isinstance(name_obj, dict):
        lines = name_obj.get("lines", {})
        name = lines.get("ru", "") or lines.get("en", "")
        if not name:
            text = name_obj.get("text", "")
            name = text if text else item_id
    else:
        name = str(name_obj) if name_obj else item_id
    # Пропускаем непереведённые ключи
    if name.startswith("item.") and ".name" in name:
        return None
    return name


def _fetch_flat_folder(folder: str) -> list[dict]:
    """Скачать все предметы из одной папки (не рекурсивно)."""
    result = []
    url    = f"{GITHUB_API}/contents/{REALM}/items/{folder}"
    data   = _get_raw(url)
    if not data:
        print(f"    ❌ Папка не найдена: {REALM}/items/{folder}")
        return result

    files = [e for e in data if e.get("type") == "file" and e["name"].endswith(".json")]
    print(f"    📂 {folder}: {len(files)} файлов")

    for entry in files:
        item_id = entry["name"].replace(".json", "")
        raw_url = f"{GITHUB_RAW}/{REALM}/items/{folder}/{item_id}.json"
        item_data = _get_raw(raw_url)
        if item_data:
            name = _parse_name(item_data, item_id)
            if name:
                result.append({"id": item_id, "name": name})
        time.sleep(0.07)

    return result


def _fetch_misc_filtered(filter_fn) -> list[dict]:
    """Скачать misc и применить фильтр по имени предмета."""
    result = []
    # Получаем список файлов через Git Tree (1 запрос)
    tree_data = _get_raw(f"{GITHUB_API}/git/trees/main?recursive=1")
    if not tree_data:
        return result

    misc_ids = [
        e["path"].split("/")[-1].replace(".json", "")
        for e in tree_data.get("tree", [])
        if e["path"].startswith(f"{REALM}/items/misc/") and e["path"].endswith(".json")
    ]
    print(f"    📂 misc: {len(misc_ids)} файлов, применяю фильтр...")

    for i, item_id in enumerate(misc_ids):
        raw_url   = f"{GITHUB_RAW}/{REALM}/items/misc/{item_id}.json"
        item_data = _get_raw(raw_url)
        if item_data:
            name = _parse_name(item_data, item_id)
            if name and filter_fn(name):
                result.append({"id": item_id, "name": name})
        if i % 50 == 49:
            print(f"    ...обработано {i+1}/{len(misc_ids)}")
        time.sleep(0.07)

    return result


# ── Основная логика ─────────────────────────────────────────────

def load_existing() -> dict:
    if os.path.exists(_OUT_FILE):
        with open(_OUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(data: dict):
    with open(_OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_categories(targets: list[str]):
    existing = load_existing()

    for cat_key in targets:
        if cat_key not in CATEGORY_MAP:
            print(f"  ⚠️  Неизвестная категория: {cat_key}")
            continue

        folder, filter_fn = CATEGORY_MAP[cat_key]

        if folder == "misc_skip":
            print(f"\n[{cat_key.upper()}] Пропуск (уже в файле)")
            continue

        print(f"\n[{cat_key.upper()}] Скачиваю...")

        if folder == "misc" and filter_fn:
            items = _fetch_misc_filtered(filter_fn)
        else:
            items = _fetch_flat_folder(folder)

        if items:
            existing[cat_key] = items
            print(f"  ✅ {cat_key}: {len(items)} предметов добавлено")
        else:
            print(f"  ⚠️  {cat_key}: предметы не найдены")

    save(existing)
    print(f"\n💾 Сохранено: {_OUT_FILE}")
    print("\n=== ИТОГ ===")
    for key, items in load_existing().items():
        print(f"  {key:<15} {len(items)} предметов")


# ── Запуск ──────────────────────────────────────────────────────

if __name__ == "__main__":
    valid = [k for k in CATEGORY_MAP if CATEGORY_MAP[k][0] != "misc_skip"]
    requested = sys.argv[1:] if len(sys.argv) > 1 else valid

    unknown = [c for c in requested if c not in CATEGORY_MAP]
    if unknown:
        print(f"❌ Неизвестные категории: {unknown}")
        print(f"   Доступные: {valid}")
        sys.exit(1)

    print("SC-CraftX — Обновление items_full.json [v1.1]")
    print(f"Категории: {requested}")
    print(f"Источник:  github.com/EXBO-Studio/stalcraft-database")
    print("=" * 55)

    update_categories(requested)
