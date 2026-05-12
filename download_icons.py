"""
download_icons.py — Скачивает иконки предметов из рецептов с GitHub.
Запускать из корня проекта: python download_icons.py
"""

import json
import time
import urllib.request
from pathlib import Path

ROOT      = Path(__file__).parent
ICONS_DIR = ROOT / "assets" / "icons"
RECIPES   = ROOT / "recipes_calculator.json"

RAW_BASE = "https://raw.githubusercontent.com/EXBO-Studio/stalcraft-database/main/ru/icons"
API_BASE = "https://api.github.com/repos/EXBO-Studio/stalcraft-database/contents/ru/icons"
HEADERS  = {"User-Agent": "SC-CraftX/1.0", "Accept": "application/vnd.github+json"}


def get_json(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  [err] {e}")
        return None


def get_recipe_ids():
    with open(RECIPES, encoding="utf-8") as f:
        recipes = json.load(f)
    ids = set()
    for item_id, data in recipes.items():
        ids.add(item_id)
        for ing in data.get("craft", {}).get("ingredients", []):
            ids.add(ing["id"])
    return ids


def main():
    print("=== SC-CraftX Icon Downloader ===")
    print(f"Папка иконок: {ICONS_DIR}")
    print()

    # Собираем ID из рецептов
    ids = get_recipe_ids()
    print(f"Предметов в рецептах: {len(ids)}")

    # Проверяем что уже есть локально
    existing = set()
    for f in ICONS_DIR.rglob("*.png"):
        existing.add(f.stem)
    print(f"Иконок уже есть: {len(existing)}")

    missing = ids - existing
    print(f"Нужно скачать: {len(missing)}")
    print()

    if not missing:
        print("Все иконки уже скачаны!")
        return

    # Строим индекс GitHub: item_id -> category
    print("Получаю индекс с GitHub...")
    cats = get_json(API_BASE)
    if not cats:
        print("Не удалось получить список категорий с GitHub")
        return

    index = {}  # item_id -> category
    for cat in cats:
        if cat["type"] != "dir":
            continue
        cat_name = cat["name"]
        files = get_json(cat["url"])
        if not files:
            continue
        for f in files:
            if f["name"].endswith(".png"):
                iid = f["name"].replace(".png", "")
                index[iid] = cat_name
        print(f"  {cat_name}: {len([f for f in files if f['name'].endswith('.png')])} иконок")
        time.sleep(0.15)

    print(f"\nИндекс построен: {len(index)} иконок на GitHub")
    print()

    ok = fail = skip = 0
    for i, item_id in enumerate(sorted(missing), 1):
        cat = index.get(item_id)
        if not cat:
            print(f"  [{i}/{len(missing)}] SKIP {item_id} (не найден на GitHub)")
            skip += 1
            continue

        dest = ICONS_DIR / cat / f"{item_id}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)

        url = f"{RAW_BASE}/{cat}/{item_id}.png"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SC-CraftX/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 200:
                    dest.write_bytes(r.read())
                    ok += 1
                    print(f"  [{i}/{len(missing)}] OK   {cat}/{item_id}.png")
                else:
                    fail += 1
                    print(f"  [{i}/{len(missing)}] ERR  {item_id} (HTTP {r.status})")
        except Exception as e:
            fail += 1
            print(f"  [{i}/{len(missing)}] ERR  {item_id}: {e}")

        time.sleep(0.1)

    print()
    print(f"Готово: {ok} скачано, {skip} не найдено на GitHub, {fail} ошибок")


if __name__ == "__main__":
    main()
