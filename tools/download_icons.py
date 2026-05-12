#!/usr/bin/env python3
"""
SC-CraftX - Загрузка иконок предметов
Объединённая версия для всех категорий
"""
import os, requests, json, time

ICON_BASE = "https://raw.githubusercontent.com/EXBO-Studio/stalcraft-database/main/ru/icons"
GITHUB_API = "https://api.github.com/repos/EXBO-Studio/stalcraft-database"
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "SC-CraftX-IconDownloader"}

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ITEMS_FILE = os.path.join(_ROOT, "items_full.json")
_ICONS_DIR = os.path.join(_ROOT, "assets", "icons")

# Категории с простым путём (корневые папки)
SIMPLE_CATEGORIES = {
    "medicine": "medicine",
    "food": "food",
    "drink": "drink",
    "grenade": "grenade",
    "bullet": "bullet",
}

# Категории с поиском через Git Tree (misc подпапки)
COMPLEX_CATEGORIES = ["materials", "armor_bags"]


def load_items() -> dict:
    """Загрузка базы предметов"""
    with open(_ITEMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_icon_map(session: requests.Session) -> dict[str, str]:
    """
    Загружает полное дерево репо один раз и строит маппинг item_id -> raw_url
    для всех иконок в ru/icons/
    """
    print("  📡 Загружаю дерево репозитория...")
    url = f"{GITHUB_API}/git/trees/main?recursive=1"
    r = session.get(url, headers=HEADERS, timeout=60)

    if r.status_code == 200:
        tree = r.json().get("tree", [])
        icon_map = {}
        for node in tree:
            path = node.get("path", "")
            if path.startswith("ru/icons/") and path.endswith(".png"):
                item_id = os.path.splitext(os.path.basename(path))[0]
                icon_map[item_id] = f"{ICON_BASE.replace('/ru/icons', '')}/{path}"
        print(f"  ✅ Найдено {len(icon_map)} иконок в репозитории")
        return icon_map
    else:
        print(f"  ❌ GitHub API ошибка: {r.status_code}")
        return {}


def download_icon(url: str, dest_path: str, session: requests.Session) -> bool:
    """Скачивание одной иконки"""
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 100:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return True
        return False
    except Exception:
        return False


def process_simple_category(cat_key: str, cat_folder: str, items: list, session: requests.Session):
    """Обработка простых категорий (прямые пути)"""
    icon_dir = os.path.join(_ICONS_DIR, cat_key)
    os.makedirs(icon_dir, exist_ok=True)

    total = len(items)
    ok = skip = fail = 0

    print(f"\n[{cat_key.upper()}] {total} предметов -> {icon_dir}")

    for i, item in enumerate(items, 1):
        item_id = item["id"]
        name = item["name"]
        dest = os.path.join(icon_dir, f"{item_id}.png")

        if os.path.exists(dest) and os.path.getsize(dest) > 100:
            skip += 1
            continue

        url = f"{ICON_BASE}/{cat_folder}/{item_id}.png"
        
        if download_icon(url, dest, session):
            ok += 1
            print(f"  ✅ [{i}/{total}] {name} ({item_id})")
        else:
            fail += 1
            print(f"  ❌ [{i}/{total}] {name} ({item_id}) — ошибка загрузки")

        time.sleep(0.05)

    print(f"  Итог: скачано {ok}, пропущено {skip}, ошибок {fail}")


def process_complex_category(cat_key: str, items: list, icon_map: dict, session: requests.Session):
    """Обработка сложных категорий (поиск через дерево)"""
    icon_dir = os.path.join(_ICONS_DIR, cat_key)
    os.makedirs(icon_dir, exist_ok=True)

    total = len(items)
    ok = skip = fail = 0

    print(f"\n[{cat_key.upper()}] {total} предметов -> {icon_dir}")

    for i, item in enumerate(items, 1):
        item_id = item["id"]
        name = item["name"]
        dest = os.path.join(icon_dir, f"{item_id}.png")

        if os.path.exists(dest) and os.path.getsize(dest) > 100:
            skip += 1
            continue

        url = icon_map.get(item_id)
        if not url:
            fail += 1
            print(f"  ❌ [{i}/{total}] {name} ({item_id}) — нет в репозитории")
            continue

        if download_icon(url, dest, session):
            ok += 1
            print(f"  ✅ [{i}/{total}] {name} ({item_id})")
        else:
            fail += 1
            print(f"  ❌ [{i}/{total}] {name} ({item_id}) — ошибка загрузки")

        time.sleep(0.05)

    print(f"  Итог: скачано {ok}, пропущено {skip}, не найдено {fail}")


def main():
    print("SC-CraftX — Скачивание иконок предметов")
    print("=" * 60)

    items_data = load_items()
    session = requests.Session()
    session.headers.update({"User-Agent": "SC-CraftX-IconDownloader/3.0"})

    # Обработка простых категорий
    for cat_key, cat_folder in SIMPLE_CATEGORIES.items():
        items = items_data.get(cat_key, [])
        if not items:
            print(f"\n[{cat_key.upper()}] — нет предметов, пропускаю")
            continue
        process_simple_category(cat_key, cat_folder, items, session)

    # Обработка сложных категорий (требуется дерево репо)
    if any(items_data.get(cat) for cat in COMPLEX_CATEGORIES):
        icon_map = build_icon_map(session)
        if not icon_map:
            print("\n❌ Не удалось получить дерево иконок из GitHub")
            return

        for cat_key in COMPLEX_CATEGORIES:
            items = items_data.get(cat_key, [])
            if not items:
                print(f"\n[{cat_key.upper()}] — нет предметов, пропускаю")
                continue
            process_complex_category(cat_key, items, icon_map, session)

    print("\n✅ Готово!")


if __name__ == "__main__":
    main()
