# ui/sidebar.py  [v1.3 - Избранное как обычная категория]
import os
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QPushButton,
                              QScrollArea, QWidget, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtGui import QPainter, QColor, QLinearGradient
from data.crafts import CRAFT_CATEGORIES


from app_paths import asset_path
_ICON_DIR = asset_path("assets", "cat_icons")


def _svg_path(name: str) -> str:
    return os.path.join(_ICON_DIR, f"{name}.svg")


class SvgIcon(QSvgWidget):
    def __init__(self, name: str, size: int = 18):
        super().__init__(_svg_path(name))
        self.setFixedSize(size, size)


# Белая линия-разделитель
class SeparatorLine(QFrame):
    """Горизонтальная градиентная линия-разделитель"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Градиентная белая линия
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        grad.setColorAt(0.2, QColor(255, 255, 255, 40))
        grad.setColorAt(0.5, QColor(255, 255, 255, 80))
        grad.setColorAt(0.8, QColor(255, 255, 255, 40))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        
        p.fillRect(0, 0, self.width(), 1, grad)
        p.end()


class Sidebar(QFrame):
    def __init__(self, on_select=None, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._on_select  = on_select
        self._active_sub = None
        self._cat_btns   = {}
        self._sub_frames = {}
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        label = QLabel("  КАТЕГОРИИ")
        label.setStyleSheet(
            "color: #444466; font-size: 10px; letter-spacing: 2px;"
            "padding: 14px 0 6px 14px; background: transparent;"
        )
        outer.addWidget(label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(8, 0, 8, 8)
        self._layout.setSpacing(1)

        # Добавляем категории с разделителями
        separator_added = False
        for cat_name, data in CRAFT_CATEGORIES.items():
            # Добавляем большой отступ ПЕРЕД Калькулятором
            if data.get("is_separator_before", False):
                # Используем stretch вместо фиксированной высоты
                self._layout.addStretch()
            
            self._add_category(cat_name, data)
            
            # Добавляем разделитель ПОСЛЕ категории "Избранное"
            if not separator_added and data.get("is_favorites", False):
                separator = SeparatorLine()
                separator.setStyleSheet("margin: 8px 6px;")
                self._layout.addWidget(separator)
                separator_added = True

        # addStretch() теперь добавляется перед Калькулятором
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

    def _make_cat_btn(self, icon_file: str, label: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("catBtn")
        row = QHBoxLayout(btn)
        row.setContentsMargins(10, 0, 10, 0)
        row.setSpacing(8)

        svg_path = _svg_path(icon_file)
        if os.path.exists(svg_path):
            icon_w = SvgIcon(icon_file, 18)
            icon_w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row.addWidget(icon_w)
        else:
            spacer = QLabel("·")
            spacer.setFixedWidth(18)
            spacer.setStyleSheet("color: #444466;")
            row.addWidget(spacer)

        lbl = QLabel(label)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lbl.setStyleSheet("background: transparent; font-size: 13px;")
        row.addWidget(lbl, stretch=1)
        btn.setFixedHeight(38)
        return btn

    def _make_calculator_btn(self, icon_file: str, label: str) -> QPushButton:
        """Создание специальной кнопки калькулятора с фоном"""
        btn = QPushButton()
        btn.setObjectName("calculatorBtn")
        row = QHBoxLayout(btn)
        row.setContentsMargins(10, 0, 10, 0)
        row.setSpacing(8)

        svg_path = _svg_path(icon_file)
        if os.path.exists(svg_path):
            icon_w = SvgIcon(icon_file, 18)
            icon_w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row.addWidget(icon_w)
        else:
            spacer = QLabel("·")
            spacer.setFixedWidth(18)
            spacer.setStyleSheet("color: #e94560;")
            row.addWidget(spacer)

        lbl = QLabel(label)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lbl.setStyleSheet("background: transparent; font-size: 13px; font-weight: 600;")
        row.addWidget(lbl, stretch=1)
        btn.setFixedHeight(42)
        return btn

    def _make_sub_btn(self, icon_file: str, label: str, is_favorites: bool = False, is_best: bool = False) -> QPushButton:
        """Создание кнопки подкатегории"""
        btn = QPushButton()
        btn.setObjectName("subcatBtn")
        row = QHBoxLayout(btn)
        row.setContentsMargins(28, 0, 10, 0)
        row.setSpacing(6)

        # Для Избранного - иконка звезды, для Лучшего - без иконки
        if is_favorites:
            # Добавляем иконку favorite.svg
            icon_w = SvgIcon("favorite", 14)
            icon_w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row.addWidget(icon_w)
        elif is_best:
            # Только текст, без иконки
            pass
        else:
            # Обычная логика для остальных категорий
            use_arrow = (icon_file == "")
            
            if not use_arrow:
                svg_path = _svg_path(icon_file)
                if os.path.exists(svg_path):
                    icon_w = SvgIcon(icon_file, 14)
                    icon_w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    row.addWidget(icon_w)
                else:
                    use_arrow = True  # Если SVG не найден - тоже стрелка
            
            if use_arrow:
                # Стрелка для "Все рецепты" и подобных
                spacer = QLabel("⭢")
                spacer.setFixedWidth(14)
                spacer.setStyleSheet("color: #6b7280; font-size: 14px; background: transparent;")
                spacer.setAlignment(Qt.AlignmentFlag.AlignCenter)
                row.addWidget(spacer)

        lbl = QLabel(label)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lbl.setStyleSheet("background: transparent; font-size: 12px;")
        row.addWidget(lbl, stretch=1)
        btn.setFixedHeight(32)
        return btn

    def _add_category(self, cat_name: str, data: dict):
        icon_file = data.get("icon_file", "")
        is_calculator = data.get("is_calculator", False)
        
        # Для калькулятора используем специальную кнопку
        if is_calculator:
            btn = self._make_calculator_btn(icon_file, cat_name)
        else:
            btn = self._make_cat_btn(icon_file, cat_name)
            
        self._cat_btns[cat_name] = btn

        sub_frame = QWidget()
        sub_frame.setStyleSheet("background: transparent;")
        sub_layout = QVBoxLayout(sub_frame)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(1)
        sub_frame.hide()

        is_best  = data.get("is_best", False)
        is_favorites = data.get("is_favorites", False)
        cat_key  = data["cat_key"]

        # Для Калькулятора - прямой клик без подкатегорий
        if is_calculator:
            # Берём первую (и единственную) подкатегорию
            first_sub = list(data["subcategories"].items())[0]
            sub_key, items = first_sub
            
            if "||" in sub_key:
                sub_icon, sub_label = sub_key.split("||", 1)
            else:
                sub_icon  = ""
                sub_label = sub_key
            
            # Клик сразу открывает калькулятор
            btn.clicked.connect(
                lambda _, sn=sub_label, it=items, ck=cat_key:
                    self._select_calculator(sn, it, ck)
            )
        else:
            # Обычная логика для остальных категорий
            for sub_key, items in data["subcategories"].items():
                if "||" in sub_key:
                    sub_icon, sub_label = sub_key.split("||", 1)
                else:
                    sub_icon  = ""
                    sub_label = sub_key

                sub_btn = self._make_sub_btn(sub_icon, sub_label, is_favorites, is_best)
                sub_btn.clicked.connect(
                    lambda _,
                           sn=sub_label,
                           it=items,
                           ck=cat_key,
                           ib=is_best:
                        self._select_sub(sn, it, ck, is_best=ib)
                )
                sub_layout.addWidget(sub_btn)
                self._sub_frames[sub_label] = sub_btn

            btn.clicked.connect(
                lambda _, cn=cat_name, sf=sub_frame: self._toggle_cat(cn, sf)
            )

        self._layout.addWidget(btn)
        # Для калькулятора не добавляем sub_frame
        if not is_calculator:
            self._layout.addWidget(sub_frame)

    def _toggle_cat(self, cat_name: str, sub_frame: QWidget):
        visible = sub_frame.isVisible()
        sub_frame.setVisible(not visible)
        for name, b in self._cat_btns.items():
            b.setProperty("active", name == cat_name and not visible)
            b.style().unpolish(b)
            b.style().polish(b)

    def _select_sub(self, sub_name: str, items: list,
                    cat_key: str, is_best: bool = False):
        if self._active_sub:
            self._active_sub.setProperty("active", False)
            self._active_sub.style().unpolish(self._active_sub)
            self._active_sub.style().polish(self._active_sub)

        btn = self._sub_frames.get(sub_name)
        if btn:
            btn.setProperty("active", True)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            self._active_sub = btn

        if self._on_select:
            self._on_select(sub_name, cat_key, items, is_best)
    
    def _select_calculator(self, sub_name: str, items: list, cat_key: str):
        """Специальная активация калькулятора"""
        # Сбрасываем активность подкатегорий
        if self._active_sub:
            self._active_sub.setProperty("active", False)
            self._active_sub.style().unpolish(self._active_sub)
            self._active_sub.style().polish(self._active_sub)
            self._active_sub = None
        
        # Активируем кнопку калькулятора
        calc_btn = self._cat_btns.get("Калькулятор")
        if calc_btn:
            calc_btn.setProperty("active", True)
            calc_btn.style().unpolish(calc_btn)
            calc_btn.style().polish(calc_btn)
        
        if self._on_select:
            self._on_select(sub_name, cat_key, items, is_best=False)
