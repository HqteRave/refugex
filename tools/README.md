# 🛠️ Утилиты SC-CraftX

Вспомогательные скрипты для обслуживания приложения.

## 📥 download_icons.py
Скачивает иконки предметов из репозитория EXBO-Studio/stalcraft-database.

**Использование:**
```bash
python tools/download_icons.py
```

Скачивает иконки для всех категорий из `items_full.json` в папку `assets/icons/`.

---

## 📦 get_items.py
Обновляет базу предметов `items_full.json` из GitHub репозитория.

**Использование:**
```bash
# Обновить все категории
python tools/get_items.py

# Обновить конкретные категории
python tools/get_items.py materials armor_bags
```

**Доступные категории:**
- `materials` - крафтовые материалы
- `armor_bags` - сумки бронепластин
- `grenade` - гранаты
- `bullet` - патроны

---

## 💰 collect_prices.py
Собирает актуальные цены для калькулятора крафта через STALCRAFT API.

**Использование:**
```bash
python tools/collect_prices.py
```

Создаёт/обновляет файл `prices_database.json` с текущими ценами всех предметов из `recipes_calculator.json`.

⏱️ Время выполнения: 3-5 минут (зависит от количества предметов).

---

## ⚠️ Важно

Все скрипты запускаются из **корня проекта** (где находится `main.py`).

Пример:
```bash
cd SC-CraftX
python tools/download_icons.py
```
