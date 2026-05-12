from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QScrollArea,
    QFrame,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QPushButton,
    QMenu,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap, QIcon, QPainter, QColor, QFont, QPainterPath, QImage

import theme_manager
theme_manager.init()

from ui.styles import build_style
from ui.sidebar import Sidebar
from ui.item_card import ItemCard
from ui.craft_filter import CraftFilterBar
from api_v2.qt_bridge import PriceSyncManager
import config
from data.crafts import CRAFT_CATEGORIES
from ui.craft_calculator import CraftCalculator
from ui.skeleton_card import SkeletonOverlay
from themes import THEMES


def _normalize_item(item: dict) -> dict:
    """items_full.json использует 'id', ItemCard ожидает 'item_id'."""
    return {
        "item_id": item.get("item_id") or item.get("id", ""),
        "name":    item.get("name", ""),
    }


# ── Главное окно ──────────────────────────────────────────────────────────


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CraftEx")
        self.setMinimumSize(1100, 680)
        self.resize(1360, 780)

        # ── Менеджер синхронизации (api_v2 / scapi) ──
        self._sync = PriceSyncManager(parent=self)
        self._sync.price_updated.connect(self._on_price_ready)
        self._sync.sync_finished.connect(self._on_prices_loaded)
        self._sync.error.connect(self._show_error_banner)

        self._cards: list = []
        self._card_index: dict = {}   # item_id -> card  O(1)
        self._refresh_timer = None
        self._remaining = 0
        self._is_best_mode = False
        self._current_is_favorites = False
        self._calculator_widget = None
        self._pending_items: list = []

        # Кэш последних 3 категорий
        from collections import deque
        self._cat_cache: deque = deque(maxlen=3)
        self._current_cat_key: str | None = None
        self._skeleton: SkeletonOverlay | None = None

        self._all_items: list[dict] = self._collect_all_items()

        self.setStyleSheet(build_style())
        self._build()

    # ── Сбор всех предметов ───────────────────────────────────────────────

    def _collect_all_items(self) -> list[dict]:
        result = []
        seen = set()
        for cat_name, data in CRAFT_CATEGORIES.items():
            if data.get("is_best") or data.get("is_favorites"):
                continue
            cat_key = data["cat_key"]
            for items in data["subcategories"].values():
                for item in items:
                    real_id = item.get("item_id") or item.get("id", "")
                    if real_id not in seen:
                        seen.add(real_id)
                        result.append({
                            "item_id": real_id,
                            "name":    item.get("name", ""),
                            "cat_key": cat_key,
                        })
        return result

    # ── Построение UI ─────────────────────────────────────────────────────

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._make_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = Sidebar(on_select=self._on_category)
        body.addWidget(self._sidebar)
        body.addWidget(self._make_right_panel(), stretch=1)

        body_widget = QWidget()
        body_widget.setLayout(body)
        body_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        root_layout.addWidget(body_widget, stretch=1)

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(52)

        row = QHBoxLayout(header)
        row.setContentsMargins(18, 0, 18, 0)
        row.setSpacing(14)

        from app_paths import asset_path

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setStyleSheet("background: transparent;")
        raw = QPixmap(asset_path("assets", "app_icon.ico"))
        if not raw.isNull():
            img = raw.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation).toImage()
            img = img.convertToFormat(QImage.Format.Format_ARGB32)
            for y in range(img.height()):
                for x in range(img.width()):
                    c = QColor(img.pixel(x, y))
                    if c.saturation() < 30 and c.value() > 130:
                        c.setAlpha(0)
                        img.setPixel(x, y, c.rgba())
            icon_lbl.setPixmap(QPixmap.fromImage(img))

        from PyQt6.QtGui import QFontMetrics

        class NeonLabel(QLabel):
            def __init__(self_, text):
                super().__init__(text)
                font = QFont("Segoe UI", 16)
                font.setBold(True)
                font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
                fm = QFontMetrics(font)
                self_.setFixedSize(fm.horizontalAdvance(text) + 24, 40)
                self_.setStyleSheet("background: transparent;")

            def paintEvent(self_, event):
                p = QPainter(self_)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
                font = QFont("Segoe UI", 16)
                font.setBold(True)
                font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
                p.setFont(font)
                p.setPen(QColor(255, 255, 255))
                p.drawText(self_.rect(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self_.text())
                p.end()

        title = NeonLabel("CraftEx")

        sub = QLabel("Твой помощник в крафтах и торговле!")
        sub.setObjectName("headerSub")

        row.addWidget(icon_lbl)
        row.addSpacing(6)
        row.addWidget(title)
        row.addWidget(sub)
        row.addStretch()

        self._search_box = QLineEdit()
        self._search_box.setObjectName("searchBox")
        self._search_box.setPlaceholderText("🔍  Поиск по названию...")
        self._search_box.setFixedWidth(280)
        self._search_box.textChanged.connect(self._on_search)
        row.addWidget(self._search_box)

        crash_btn = QPushButton("📋")
        crash_btn.setObjectName("crashBtn")
        crash_btn.setFixedSize(32, 32)
        crash_btn.setToolTip("Открыть журнал ошибок (crash.log)")
        crash_btn.clicked.connect(self._open_crash_log)
        row.addWidget(crash_btn)

        self._theme_btn = QPushButton("🎨 " + THEMES[theme_manager.get_theme_key()]["name"])
        self._theme_btn.setObjectName("themeBtn")
        self._theme_btn.setFixedHeight(32)
        self._theme_btn.clicked.connect(self._show_theme_menu)
        row.addWidget(self._theme_btn)

        self._status_lbl = QLabel("Готов")
        self._status_lbl.setObjectName("headerVer")
        row.addWidget(self._status_lbl)

        return header

    def _open_crash_log(self):
        from app_paths import app_path
        import os, subprocess
        log_path = app_path("crash.log")
        if not os.path.exists(log_path):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Журнал ошибок", "Журнал пуст — ошибок не зафиксировано.")
            return
        subprocess.Popen(["notepad.exe", log_path])

    def _show_theme_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {config.SURFACE2_COLOR};
                color: {config.TEXT_COLOR};
                border: 1px solid {config.FAINT_COLOR};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 7px 20px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background: {config.ACCENT_COLOR};
                color: #ffffff;
            }}
            QMenu::item:checked {{
                font-weight: bold;
            }}
        """)
        current = theme_manager.get_theme_key()
        for key, data in THEMES.items():
            action = QAction(data["name"], self)
            action.setCheckable(True)
            action.setChecked(key == current)
            action.setData(key)
            action.triggered.connect(lambda checked, k=key: self._apply_theme(k))
            menu.addAction(action)
        btn_pos = self._theme_btn.mapToGlobal(self._theme_btn.rect().bottomLeft())
        menu.exec(btn_pos)

    def _apply_theme(self, key: str):
        from ui.compare_window import CompareWindow
        from ui.craft_detail_window import _open_windows
        theme_manager.set_theme(key)
        config._refresh()
        self.setStyleSheet(build_style())
        self._theme_btn.setText("🎨 " + THEMES[key]["name"])
        self._update_info_bar_style()
        self._filter_bar.refresh_style()
        self._reset_calculator()
        for card in self._cards:
            card.refresh_theme()
        if CompareWindow._instance and CompareWindow._instance.isVisible():
            CompareWindow._instance.refresh_theme()
        # Обновляем открытые окна подробностей
        for win in list(_open_windows):
            try:
                win.refresh_theme()
            except Exception:
                pass

    def _make_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._filter_bar = CraftFilterBar(on_change=self._apply_filters)
        layout.addWidget(self._filter_bar)

        self._error_banner = self._make_error_banner()
        layout.addWidget(self._error_banner)

        layout.addWidget(self._make_info_bar())

        self._content_stack = QWidget()
        self._content_layout = QVBoxLayout(self._content_stack)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("border: none;")

        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(14, 14, 14, 14)
        self._cards_layout.setSpacing(10)
        self._cards_layout.addStretch()

        self._scroll.setWidget(self._cards_widget)
        self._content_layout.addWidget(self._scroll)

        layout.addWidget(self._content_stack, stretch=1)
        return panel

    def _make_error_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("apiBanner")
        banner.hide()
        row = QHBoxLayout(banner)
        row.setContentsMargins(14, 6, 14, 6)
        row.setSpacing(10)
        self._banner_lbl = QLabel()
        self._banner_lbl.setWordWrap(True)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setFlat(True)
        close_btn.clicked.connect(self._hide_error_banner)
        row.addWidget(self._banner_lbl, stretch=1)
        row.addWidget(close_btn)
        return banner

    def _show_error_banner(self, msg: str):
        self._banner_lbl.setText(f"⚠ API недоступен: {msg}. Данные из кэша.")
        self._error_banner.setStyleSheet("""
            QFrame#apiBanner {
                background-color: #c0392b;
                border: none;
                border-bottom: 2px solid #922b21;
            }
            QFrame#apiBanner QLabel {
                color: #ffffff;
                font-size: 11px;
                background: transparent;
            }
            QFrame#apiBanner QPushButton {
                color: #ffffff;
                border: none;
                font-size: 13px;
                background: transparent;
            }
            QFrame#apiBanner QPushButton:hover {
                color: #ffe0de;
            }
        """)
        self._error_banner.show()

    def _hide_error_banner(self):
        self._error_banner.hide()

    def _make_info_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("mainInfoBar")
        bar.setFixedHeight(32)
        self._info_bar = bar
        self._update_info_bar_style()
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 0, 14, 0)

        self._count_lbl = QLabel("Выберите категорию")
        self._count_lbl.setObjectName("mainCountLbl")
        self._filter_count_lbl = QLabel("")
        self._filter_count_lbl.setObjectName("mainFilterLbl")

        row.addWidget(self._count_lbl)
        row.addStretch()
        row.addWidget(self._filter_count_lbl)
        return bar

    def _update_info_bar_style(self):
        self._info_bar.setStyleSheet(f"""
            QFrame#mainInfoBar {{
                background: {config.BG_COLOR};
                border-bottom: 1px solid {config.BORDER_COLOR};
            }}
        """)
        if hasattr(self, "_count_lbl"):
            self._count_lbl.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 11px;")
        if hasattr(self, "_filter_count_lbl"):
            self._filter_count_lbl.setStyleSheet(f"color: {config.ACCENT_COLOR}; font-size: 11px;")

    # ── Загрузка категории ────────────────────────────────────────────────

    def _on_category(
        self, sub_name: str, cat_key: str, items: list, is_best: bool = False
    ):
        if cat_key == "calculator":
            self._show_calculator()
            return
        self._hide_calculator()

        self._search_box.clear()
        self._filter_bar.reset()

        # Останавливаем текущую синхронизацию
        self._sync.stop_sync()

        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None

        # Кэш категорий
        if self._current_cat_key and self._current_cat_key != cat_key:
            self._save_current_to_cache()

        if self._try_restore_from_cache(cat_key):
            return

        self._clear_cards()
        self._current_cat_key = cat_key
        self._is_best_mode = is_best

        self._current_is_favorites = False
        for cat_data in CRAFT_CATEGORIES.values():
            if cat_data.get("is_favorites") and cat_data["cat_key"] == cat_key:
                self._current_is_favorites = True
                break

        if callable(items):
            items = items()

        if is_best:
            self._set_status("⏳ Загружаю данные по всем предметам...")
            load_items = self._all_items
            self._pending_items = [(item, item.get("cat_key", cat_key)) for item in load_items]
            target_ids = [i["item_id"] for i in load_items]

        elif self._current_is_favorites:
            self._set_status("⏳ Загружаю избранные предметы...")
            if not items:
                self._set_status("⭐ Избранных предметов пока нет")
                self._count_lbl.setText("⭐ Избранных: 0")
                return

            normalized = []
            for item in items:
                norm = _normalize_item(item)
                item_cat_key = item.get("cat_key", cat_key)
                normalized.append((norm, item_cat_key))

            self._pending_items = normalized
            target_ids = [item.get("item_id") or item.get("id", "") for item in items]

        else:
            if not items:
                self._set_status("Нет предметов")
                return
            self._set_status(f"⏳ Загрузка «{sub_name}»...")

            normalized = []
            for item in items:
                norm = _normalize_item(item)
                normalized.append((norm, cat_key))

            self._pending_items = normalized
            target_ids = [item.get("item_id") or item.get("id", "") for item in items]

        self._hide_error_banner()

        # Создаём карточки синхронно — PriceLoader стартует после заполнения _card_index
        self._load_cards_batch()

        # ── Запускаем синхронизацию через api_v2 (scapi) ──
        self._sync.sync_prices(target_ids, include_lots=True, force_refresh=False)

    # ── Кэш категорий ────────────────────────────────────────────────────

    def _save_current_to_cache(self):
        if not self._current_cat_key or not self._cards:
            return
        for key, _ in self._cat_cache:
            if key == self._current_cat_key:
                return
        for card in self._cards:
            self._cards_layout.removeWidget(card)
            card.hide()
        snapshot = {
            "cards":      list(self._cards),
            "card_index": dict(self._card_index),
            "is_best":    self._is_best_mode,
            "is_favorites": self._current_is_favorites,
        }
        self._evict_old_cache()
        self._cat_cache.append((self._current_cat_key, snapshot))
        self._cards.clear()
        self._card_index.clear()

    def _try_restore_from_cache(self, cat_key: str) -> bool:
        for i, (key, snapshot) in enumerate(self._cat_cache):
            if key != cat_key:
                continue
            self._cards = snapshot["cards"]
            self._card_index = snapshot["card_index"]
            self._is_best_mode = snapshot["is_best"]
            self._current_is_favorites = snapshot["is_favorites"]
            self._current_cat_key = cat_key
            for card in self._cards:
                self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
                card.show()
            new_cache = [(k, s) for j, (k, s) in enumerate(self._cat_cache) if j != i]
            self._cat_cache.clear()
            for item in new_cache:
                self._cat_cache.append(item)
            self._update_counts()
            self._set_status("✅ Восстановлено из кэша")
            return True
        return False

    def _show_skeleton(self):
        self._remove_skeleton()
        self._skeleton = SkeletonOverlay(self._cards_layout, count=6)

    def _remove_skeleton(self):
        if self._skeleton:
            self._skeleton.remove()
            self._skeleton = None

    # ── Порционная загрузка карточек ──────────────────────────────────────

    def _load_cards_batch(self):
        import logging
        BATCH_SIZE = 15

        if not self._pending_items:
            self._remove_skeleton()
            self._update_counts()
            return

        self._remove_skeleton()

        batch = self._pending_items[:BATCH_SIZE]
        self._pending_items = self._pending_items[BATCH_SIZE:]

        for i, (item_data, item_cat_key) in enumerate(batch):
            try:
                card = ItemCard(item_data, item_cat_key)
            except Exception as e:
                logging.getLogger("ui").error(
                    "ItemCard(%s) failed: %s", item_data, e, exc_info=True
                )
                continue

            if self._is_best_mode:
                card.setVisible(False)

            card._star_btn.toggled.connect(lambda _, c=card: self._on_favorite_toggled(c))
            self._cards.append(card)
            self._card_index[card.item_id] = card
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

            if not self._is_best_mode:
                card.play_appear(delay=i * 35)

        if self._pending_items:
            loaded = len(self._cards)
            total = loaded + len(self._pending_items)
            self._set_status(f"⏳ Загружено {loaded}/{total}...")
            QTimer.singleShot(10, self._load_cards_batch)
        else:
            self._update_counts()

    # ── Обработка изменения избранного ───────────────────────────────────

    def _on_favorite_toggled(self, card):
        if self._current_is_favorites:
            if not card._favorites.is_favorite(card.item_id):
                if card in self._cards:
                    self._cards.remove(card)
                self._cards_layout.removeWidget(card)
                card.setVisible(False)
                card.deleteLater()
                visible = len(self._cards)
                self._count_lbl.setText(f"⭐ Избранных: {visible}")
                if visible == 0:
                    self._set_status("⭐ Избранных предметов пока нет")

    # ── Обновление цен ────────────────────────────────────────────────────

    def _on_price_ready(self, item_id: str, stats: dict):
        """
        Слот для price_updated от PriceSyncManager.
        stats — dict совместимый с форматом ItemCard.update_prices().
        """
        card = self._card_index.get(item_id)
        if card is None:
            return

        # Если только лоты (обратная совместимость со старым форматом)
        if stats.get("_lots_only"):
            card.update_market(stats["market_min"], stats.get("market_total", 0))
            return

        card.update_prices(stats)

        if self._is_best_mode:
            card.setVisible(stats.get("liquidity") == "high")
            self._update_counts()

    def _on_prices_loaded(self):
        total = len(self._cards)
        visible = sum(1 for c in self._cards if c.isVisible())

        if self._current_is_favorites:
            self._set_status(f"⭐ Избранных предметов: {visible}")
        elif self._is_best_mode:
            self._set_status(f"✅ Найдено {visible} предметов с высокой ликвидностью")
        else:
            self._set_status(f"✅ Загружено {total} предметов")

        self._update_counts()
        self._start_refresh_timer()

    def _start_refresh_timer(self):
        if self._refresh_timer:
            self._refresh_timer.stop()
        self._remaining = 15
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._tick_refresh)
        self._refresh_timer.start()

    def _tick_refresh(self):
        self._remaining -= 1
        if self._remaining > 0:
            self._status_lbl.setText(f"🔄 Обновление через {self._remaining} сек")
        else:
            self._refresh_timer.stop()
            self._status_lbl.setText("⏳ Обновляю цены...")
            ids = [c.item_id for c in self._cards]
            if ids:
                # force_refresh=True — инвалидирует SQLite кэш перед повтором
                self._sync.sync_prices(ids, include_lots=True, force_refresh=True)

    # ── Фильтрация ────────────────────────────────────────────────────────

    def _apply_filters(self):
        search_text = self._search_box.text().strip().lower()
        visible = 0
        for card in self._cards:
            if self._is_best_mode and not card.is_best:
                card.setVisible(False)
                continue

            craft_ok = self._filter_bar.matches(card)
            search_ok = search_text in card.item_name.lower() if search_text else True
            show = craft_ok and search_ok
            card.setVisible(show)
            if show:
                visible += 1
        self._update_counts(visible)

    def _on_search(self, _text: str):
        self._apply_filters()

    def _update_counts(self, visible: int = None):
        total = len(self._cards)

        if self._current_is_favorites:
            shown = sum(1 for c in self._cards if c.isVisible())
            self._count_lbl.setText(f"⭐ Избранных: {shown}")
            self._filter_count_lbl.setText("")
        elif self._is_best_mode:
            shown = sum(1 for c in self._cards if c.isVisible())
            self._count_lbl.setText(f"Высокая ликвидность: {shown}")
            self._filter_count_lbl.setText("")
        else:
            self._count_lbl.setText(f"Предметов: {total}")
            if visible is not None and visible != total:
                self._filter_count_lbl.setText(f"Показано: {visible}")
            else:
                self._filter_count_lbl.setText("")

    # ── Утилиты ───────────────────────────────────────────────────────────

    def _clear_cards(self):
        self._remove_skeleton()
        for card in self._cards:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._card_index.clear()
        self._update_counts()

    def _evict_old_cache(self):
        if len(self._cat_cache) == self._cat_cache.maxlen:
            _, old_snapshot = self._cat_cache[0]
            for card in old_snapshot.get("cards", []):
                card.hide()
                card.deleteLater()

    def _set_status(self, text: str):
        self._status_lbl.setText(text)

    def _show_calculator(self):
        self._scroll.hide()
        self._filter_bar.hide()
        self._search_box.hide()

        if self._calculator_widget is None:
            self._calculator_widget = CraftCalculator()
            self._content_layout.addWidget(self._calculator_widget)

        self._calculator_widget.show()
        self._set_status("Калькулятор крафта")
        self._count_lbl.setText("")
        self._filter_count_lbl.setText("")

    def _hide_calculator(self):
        if self._calculator_widget:
            self._calculator_widget.hide()

        self._scroll.show()
        self._filter_bar.show()
        self._search_box.show()

    def _reset_calculator(self):
        if self._calculator_widget is None:
            return
        was_visible = self._calculator_widget.isVisible()
        self._content_layout.removeWidget(self._calculator_widget)
        self._calculator_widget.deleteLater()
        self._calculator_widget = None
        if was_visible:
            self._show_calculator()

    def closeEvent(self, event):
        if self._refresh_timer:
            self._refresh_timer.stop()
        self._sync.cleanup()
        super().closeEvent(event)
