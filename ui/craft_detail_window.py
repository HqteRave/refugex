"""
ui/craft_detail_window.py — Окно подробной информации о крафте предмета.

- Фиксированный размер 920×580
- Максимум 3 окна одновременно
- Поддержка тем через config
- Иконки из assets/icons/*/<item_id>.png
  Fallback: скачивание с GitHub EXBO-Studio/stalcraft-database
- Открытие: двойной клик или ПКМ → "Подробнее"
"""

from __future__ import annotations

import asyncio
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPointF, QThread, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPixmap, QPainterPath, QPen, QPolygonF,
)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget, QPushButton, QGridLayout,
)

import config
from app_paths import asset_path

# ─── Константы ────────────────────────────────────────────────────────────────

_MAX_WINDOWS  = 3
_WIN_W, _WIN_H = 920, 580
_ICONS_DIR    = Path(asset_path("assets", "icons"))
_RAW_BASE     = "https://raw.githubusercontent.com/EXBO-Studio/stalcraft-database/main/ru/icons"
_GITHUB_API   = "https://api.github.com/repos/EXBO-Studio/stalcraft-database/contents/ru/icons"

_BENCH_NAMES = {
    "workbench":       "Верстак",
    "kitchen_table":   "Кухонный стол",
    "laboratory_table": "Лабораторный стол",
}

# Предметы которые пропадают с аукциона после полуночи (МСК) — только с рук
_MIDNIGHT_ITEMS: set[str] = {
    "5ddo",  # Мякоть куборбуза
    "y770",  # Мякоть лимонника
    "1ddr",  # Мякоть мятноплода
    "g00n",  # Мякоть сластены
    "9mmq",  # Мякоть солевика
    "z77k",  # Мякоть спиртня
}

AUCTION_FEE = 0.05

# Реестр открытых окон
_open_windows: list["CraftDetailWindow"] = []

# Кэш: item_id -> Path (найденная иконка)
_icon_cache: dict[str, Optional[Path]] = {}

# GitHub индекс: category -> [item_ids]
_github_index: dict[str, list[str]] = {}
_github_index_loaded = False


# ─── Утилиты ──────────────────────────────────────────────────────────────────

def _fmt(v: int) -> str:
    return f"{v:,} ₽".replace(",", " ")

def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%d.%m %H:%M")

def _calc_trend(prices: list[float]) -> tuple[str, float]:
    if len(prices) < 3:
        return "stable", 0.0
    old_avg = sum(prices[:len(prices)//2]) / max(len(prices)//2, 1)
    new_avg = sum(prices[len(prices)//2:]) / max(len(prices) - len(prices)//2, 1)
    if old_avg == 0:
        return "stable", 0.0
    pct = (new_avg - old_avg) / old_avg * 100
    if pct > 2:
        return "up", pct
    if pct < -2:
        return "down", pct
    return "stable", pct

def _find_icon_local(item_id: str) -> Optional[Path]:
    """Ищет иконку item_id по всем папкам assets/icons/."""
    if item_id in _icon_cache:
        return _icon_cache[item_id]
    for cat_dir in _ICONS_DIR.iterdir():
        if not cat_dir.is_dir():
            continue
        p = cat_dir / f"{item_id}.png"
        if p.exists():
            _icon_cache[item_id] = p
            return p
    _icon_cache[item_id] = None
    return None


# ─── Поток загрузки иконок с GitHub ───────────────────────────────────────────

class IconDownloadWorker(QThread):
    """Скачивает одну иконку в фоне."""
    done = pyqtSignal(str, str)  # item_id, path

    def __init__(self, item_id: str):
        super().__init__()
        self.item_id = item_id

    def run(self):
        global _github_index, _github_index_loaded
        import json

        headers = {"User-Agent": "SC-CraftX/1.0",
                   "Accept": "application/vnd.github+json"}

        # Загружаем индекс GitHub если ещё не загружен
        if not _github_index_loaded:
            try:
                req = urllib.request.Request(_GITHUB_API, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as r:
                    cats = json.loads(r.read())
                for cat in cats:
                    if cat["type"] != "dir":
                        continue
                    req2 = urllib.request.Request(cat["url"], headers=headers)
                    with urllib.request.urlopen(req2, timeout=10) as r2:
                        files = json.loads(r2.read())
                    _github_index[cat["name"]] = [
                        f["name"].replace(".png", "")
                        for f in files if f["name"].endswith(".png")
                    ]
                _github_index_loaded = True
            except Exception:
                return

        # Ищем категорию
        cat = None
        for c, ids in _github_index.items():
            if self.item_id in ids:
                cat = c
                break
        if not cat:
            return

        # Скачиваем
        url  = f"{_RAW_BASE}/{cat}/{self.item_id}.png"
        dest = _ICONS_DIR / cat / f"{self.item_id}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SC-CraftX/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 200:
                    dest.write_bytes(r.read())
                    _icon_cache[self.item_id] = dest
                    self.done.emit(self.item_id, str(dest))
        except Exception:
            pass


# ─── Виджет иконки предмета ───────────────────────────────────────────────────

class ItemIconWidget(QLabel):
    """32×32 иконка предмета. Загружает из локального кэша или GitHub."""

    def __init__(self, item_id: str, size: int = 32, parent=None):
        super().__init__(parent)
        self._item_id = item_id
        self._size    = size
        self.setFixedSize(size, size)
        self.setStyleSheet(
            f"border-radius:6px; background:{config.SURFACE2_COLOR};"
            f"border:0.5px solid {config.BORDER_COLOR};"
        )
        self._load()

    def _load(self):
        path = _find_icon_local(self._item_id)
        if path:
            self._set_pixmap(path)
            return
        # Заглушка — первая буква названия
        self.setText(self._item_id[:1].upper())
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"border-radius:6px; background:{config.SURFACE2_COLOR};"
            f"border:0.5px solid {config.BORDER_COLOR};"
            f"color:{config.MUTED_COLOR}; font-size:12px; font-weight:600;"
        )
        # Запускаем загрузку с GitHub
        self._worker = IconDownloadWorker(self._item_id)
        self._worker.done.connect(self._on_downloaded)
        self._worker.start()

    def _on_downloaded(self, item_id: str, path: str):
        if item_id == self._item_id:
            self._set_pixmap(Path(path))

    def _set_pixmap(self, path: Path):
        px = QPixmap(str(path))
        if not px.isNull():
            self.setPixmap(
                px.scaled(self._size, self._size,
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )
            self.setStyleSheet(
                f"border-radius:6px; background:{config.SURFACE2_COLOR};"
                f"border:0.5px solid {config.BORDER_COLOR};"
            )


# ─── Мини спарклайн ───────────────────────────────────────────────────────────

class MiniSparkline(QWidget):
    def __init__(self, prices: list[float], trend: str, w=52, h=16, parent=None):
        super().__init__(parent)
        self._prices = prices
        self._trend  = trend
        self.setFixedSize(w, h)

    def paintEvent(self, _):
        if len(self._prices) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color_map = {"up": config.SUCCESS_COLOR, "down": config.DANGER_COLOR, "stable": config.MUTED_COLOR}
        color = QColor(color_map.get(self._trend, config.MUTED_COLOR))
        w, h, pad = self.width(), self.height(), 2
        prices = self._prices
        mn, mx = min(prices), max(prices)
        rng = mx - mn if mx != mn else 1

        def _pt(i, price):
            x = pad + (i / (len(prices) - 1)) * (w - pad * 2)
            y = h - pad - ((price - mn) / rng) * (h - pad * 2)
            return QPointF(x, y)

        path = QPainterPath()
        path.moveTo(_pt(0, prices[0]))
        for i in range(1, len(prices)):
            path.lineTo(_pt(i, prices[i]))

        pen = QPen(color, 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(path)

        last = _pt(len(prices) - 1, prices[-1])
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(last, 2.0, 2.0)
        p.end()


# ─── График цен ───────────────────────────────────────────────────────────────

class PriceChart(QWidget):
    def __init__(self, prices: list[float], parent=None):
        super().__init__(parent)
        self._prices = prices
        self.setMinimumHeight(70)

    def paintEvent(self, _):
        if len(self._prices) < 2:
            p = QPainter(self)
            p.setPen(QColor(config.MUTED_COLOR))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет данных")
            p.end()
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h, pad = self.width(), self.height(), 8
        prices = self._prices
        mn = min(prices) * 0.98
        mx = max(prices) * 1.02
        rng = mx - mn if mx != mn else 1

        def _pt(i, price):
            x = pad + (i / (len(prices) - 1)) * (w - pad * 2)
            y = h - pad - ((price - mn) / rng) * (h - pad * 2)
            return QPointF(x, y)

        # Заливка
        fill = QPainterPath()
        fill.moveTo(_pt(0, prices[0]))
        for i in range(1, len(prices)):
            fill.lineTo(_pt(i, prices[i]))
        fill.lineTo(QPointF(w - pad, h - pad))
        fill.lineTo(QPointF(pad, h - pad))
        fill.closeSubpath()

        accent = QColor(config.ACCENT_COLOR)
        accent.setAlpha(25)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawPath(fill)

        # Линия
        line = QPainterPath()
        line.moveTo(_pt(0, prices[0]))
        for i in range(1, len(prices)):
            line.lineTo(_pt(i, prices[i]))

        pen = QPen(QColor(config.ACCENT_COLOR), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(line)

        # Точки
        p.setBrush(QColor(config.ACCENT_COLOR))
        p.setPen(Qt.PenStyle.NoPen)
        for i, price in enumerate(prices):
            p.drawEllipse(_pt(i, price), 2.5, 2.5)

        p.end()


# ─── Главное окно подробностей ────────────────────────────────────────────────

class CraftDetailWindow(QDialog):
    """Окно подробной информации о крафте предмета."""

    def __init__(
        self,
        item_id: str,
        item_name: str,
        recipe: dict,
        live_prices: dict,
        parent=None,
    ):
        super().__init__(parent)
        self._item_id    = item_id
        self._item_name  = item_name
        self._recipe     = recipe  # данные из recipes_calculator.json
        self._prices     = live_prices
        self._workers: list[IconDownloadWorker] = []

        self.setWindowTitle(f"Подробнее — {item_name}")
        self.setFixedSize(_WIN_W, _WIN_H)
        self.setWindowFlag(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._apply_style()
        self._build()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: {config.BG_COLOR};
            }}
            QScrollBar:vertical {{
                background: {config.SURFACE_COLOR};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {config.FAINT_COLOR};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

    def closeEvent(self, event):
        if self in _open_windows:
            _open_windows.remove(self)
        super().closeEvent(event)

    # ── Построение UI ──────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._make_left_panel(), stretch=4)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {config.BORDER_COLOR};")
        body.addWidget(sep)

        body.addWidget(self._make_right_panel(), stretch=5)

        body_widget = QWidget()
        body_widget.setLayout(body)
        root.addWidget(body_widget, stretch=1)

        root.addWidget(self._make_footer())

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(
            f"QFrame {{ background:{config.SURFACE_COLOR};"
            f"border-bottom:1px solid {config.BORDER_COLOR}; }}"
        )
        row = QHBoxLayout(header)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(10)

        icon = ItemIconWidget(self._item_id, size=36)
        row.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(self._item_name)
        name_lbl.setStyleSheet(
            f"color:{config.TEXT_COLOR};font-size:14px;font-weight:600;"
        )
        info.addWidget(name_lbl)

        craft = self._recipe.get("craft", {})
        bench = _BENCH_NAMES.get(craft.get("bench", ""), craft.get("bench", ""))
        cat   = craft.get("category", "")
        meta_lbl = QLabel(f"{bench}  ·  {cat}")
        meta_lbl.setStyleSheet(
            f"color:{config.ACCENT_COLOR};"  # Красный цвет вместо серого
            f"font-size:11px;"
            "border:none; background:transparent;"  # Убираем линии
        )
        info.addWidget(meta_lbl)
        row.addLayout(info)
        row.addStretch()

        # Теги
        result_amount = craft.get("result_amount", 1)
        if result_amount > 1:
            tag = QLabel(f"×{result_amount} с крафта")
            tag.setStyleSheet(
                f"color:{config.ACCENT_COLOR};"
                "padding:2px 8px; font-size:11px; border:none; background:transparent;"
            )
            row.addWidget(tag)

        # Прибыль
        profit = self._calc_profit()
        if profit != 0:
            pc = config.SUCCESS_COLOR if profit > 0 else config.DANGER_COLOR
            sign = "+" if profit > 0 else "−"
            profit_lbl = QLabel(f"{sign}{_fmt(abs(profit))}")
            profit_lbl.setStyleSheet(
                f"color:{pc}; font-size:12px; font-weight:600;"
                "padding:2px 8px; border:none; background:transparent;"
            )
            row.addWidget(profit_lbl)

        # Кнопка обновить
        refresh_btn = QPushButton("↻  Обновить")
        refresh_btn.setFixedHeight(28)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 0.5px solid {config.BORDER_COLOR};
                border-radius: 6px;
                padding: 0 12px;
                color: {config.MUTED_COLOR};
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {config.ACCENT_COLOR};
                color: {config.ACCENT_COLOR};
            }}
        """)
        refresh_btn.clicked.connect(self._refresh)
        row.addWidget(refresh_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {config.MUTED_COLOR};
                font-size: 14px;
            }}
            QPushButton:hover {{ color: {config.DANGER_COLOR}; }}
        """)
        close_btn.clicked.connect(self.close)
        row.addWidget(close_btn)

        return header

    def _make_left_panel(self) -> QWidget:
        """Левая панель: ингредиенты."""
        panel = QWidget()
        panel.setStyleSheet(f"background: {config.BG_COLOR};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title = QLabel("ИНГРЕДИЕНТЫ")
        title.setStyleSheet(
            f"color:{config.MUTED_COLOR};font-size:10px;font-weight:600;letter-spacing:1px;"
        )
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border:none; background:transparent;")

        ing_widget = QWidget()
        ing_layout = QVBoxLayout(ing_widget)
        ing_layout.setContentsMargins(0, 0, 0, 0)
        ing_layout.setSpacing(5)

        craft      = self._recipe.get("craft", {})
        ingredients = craft.get("ingredients", [])
        total_cost = 0

        for ing in ingredients:
            iid    = ing["id"]
            iname  = ing["name"]
            amount = ing["amount"]
            stats  = self._prices.get(iid, {})
            hist   = stats.get("history", [])
            mkt    = stats.get("market_min", 0)
            last   = hist[0].get("per_unit", 0) if hist else 0
            price  = mkt or last or stats.get("avg", 0)
            total_cost += price * amount

            prices_list = [e.get("per_unit", 0) for e in hist if e.get("per_unit")]
            trend, pct  = _calc_trend(prices_list) if len(prices_list) >= 3 else ("stable", 0.0)

            row = self._make_ingredient_row(iid, iname, amount, price, prices_list, trend, pct)
            ing_layout.addWidget(row)

        ing_layout.addStretch()
        scroll.setWidget(ing_widget)
        layout.addWidget(scroll, stretch=1)

        # Итого
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{config.BORDER_COLOR};")
        layout.addWidget(sep)

        total_row = QHBoxLayout()
        t1 = QLabel("Итого крафт:")
        t1.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:11px;")
        t2 = QLabel(_fmt(total_cost))
        t2.setStyleSheet(f"color:{config.TEXT_COLOR};font-size:13px;font-weight:600;")
        total_row.addWidget(t1)
        total_row.addStretch()
        total_row.addWidget(t2)
        layout.addLayout(total_row)

        return panel

    def _make_ingredient_row(
        self, item_id: str, name: str, amount: int,
        price: int, prices_list: list, trend: str, pct: float
    ) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background:{config.SURFACE2_COLOR};"
            f"border:0.5px solid {config.BORDER_COLOR}; border-radius:8px; }}"
        )
        hl = QHBoxLayout(row)
        hl.setContentsMargins(8, 6, 8, 6)
        hl.setSpacing(8)

        icon = ItemIconWidget(item_id, size=28)
        hl.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(1)

        name_row = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color:{config.TEXT_COLOR};font-size:12px;font-weight:600;")
        amt_lbl  = QLabel(f"×{amount}")
        amt_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:11px;")
        name_row.addWidget(name_lbl, stretch=1)
        name_row.addWidget(amt_lbl)
        info.addLayout(name_row)

        price_row = QHBoxLayout()
        price_lbl = QLabel(_fmt(price) + "/шт" if price else "нет данных")
        price_lbl.setStyleSheet(
            f"color:{config.ACCENT_COLOR if price else config.MUTED_COLOR};font-size:11px;"
        )
        price_row.addWidget(price_lbl)
        price_row.addStretch()

        if prices_list and len(prices_list) >= 2:
            spark = MiniSparkline(prices_list[-20:], trend, w=44, h=14)
            price_row.addWidget(spark)
            pct_color = (
                config.SUCCESS_COLOR if trend == "up"
                else config.DANGER_COLOR if trend == "down"
                else config.MUTED_COLOR
            )
            pct_sign  = "+" if pct >= 0 else ""
            pct_lbl   = QLabel(f"{pct_sign}{pct:.1f}%")
            pct_lbl.setStyleSheet(f"color:{pct_color};font-size:10px;")
            price_row.addWidget(pct_lbl)

        info.addLayout(price_row)

        # Предупреждение для мякоти
        if item_id in _MIDNIGHT_ITEMS:
            warn = QLabel("⚠ Пропадает после полуночи (МСК) — покупать с рук")
            warn.setStyleSheet(
                f"color:{config.WARNING_COLOR}; font-size:9px; background:transparent;"
            )
            warn.setWordWrap(True)
            info.addWidget(warn)

        hl.addLayout(info, stretch=1)
        return row

    def _make_right_panel(self) -> QWidget:
        """Правая панель: рынок + история продаж."""
        panel = QWidget()
        panel.setStyleSheet(f"background: {config.BG_COLOR};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Заголовок
        title = QLabel(f"РЫНОК · {self._item_name.upper()}")
        title.setStyleSheet(
            f"color:{config.MUTED_COLOR};font-size:10px;font-weight:600;letter-spacing:1px;"
        )
        layout.addWidget(title)

        # Метрики
        layout.addWidget(self._make_metrics())

        # График
        layout.addWidget(self._make_chart_block())

        # История продаж
        layout.addWidget(self._make_history_block())

        return panel

    def _make_metrics(self) -> QWidget:
        stats = self._prices.get(self._item_id, {})
        hist  = stats.get("history", [])

        mkt_min   = stats.get("market_min", 0)
        last_sale = hist[0].get("per_unit", 0) if hist else 0
        mkt_total = stats.get("market_total", 0)
        per_hour  = stats.get("per_hour", 0)

        prices_list = [e.get("per_unit", 0) for e in hist if e.get("per_unit")]
        trend, pct  = _calc_trend(prices_list) if len(prices_list) >= 4 else ("stable", 0.0)

        grid = QWidget()
        gl   = QGridLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(6)

        def _card(label: str, value: str, sub: str = "", color: str = "") -> QFrame:
            card = QFrame()
            # SURFACE2 для карточек метрик — чуть светлее фона, читается во всех темах
            card.setStyleSheet(
                f"QFrame {{ background:{config.SURFACE2_COLOR};"
                f"border:0.5px solid {config.BORDER_COLOR}; border-radius:8px; }}"
            )
            vl = QVBoxLayout(card)
            vl.setContentsMargins(8, 6, 8, 6)
            vl.setSpacing(1)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;background:transparent;")
            val = QLabel(value)
            val.setStyleSheet(
                f"color:{color or config.TEXT_COLOR};font-size:12px;font-weight:600;background:transparent;"
            )
            vl.addWidget(lbl)
            vl.addWidget(val)
            if sub:
                s = QLabel(sub)
                s.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;background:transparent;")
                vl.addWidget(s)
            return card

        # Тренд
        trend_color = (
            config.SUCCESS_COLOR if trend == "up"
            else config.DANGER_COLOR if trend == "down"
            else config.MUTED_COLOR
        )
        trend_sign  = "↑" if trend == "up" else "↓" if trend == "down" else "→"
        trend_str   = f"{trend_sign} {abs(pct):.1f}%"

        gl.addWidget(_card("Аукцион сейчас", _fmt(mkt_min) if mkt_min else "—", "/шт", config.ACCENT_COLOR), 0, 0)
        gl.addWidget(_card("Последняя сделка", _fmt(last_sale) if last_sale else "—", "/шт"), 0, 1)
        gl.addWidget(_card("Лотов активно", str(mkt_total) if mkt_total else "—", "на аукционе"), 0, 2)
        gl.addWidget(_card("Тренд 48 ч", trend_str, f"{per_hour:.0f} продаж/ч", trend_color), 0, 3)

        return grid

    def _make_chart_block(self) -> QWidget:
        stats       = self._prices.get(self._item_id, {})
        hist        = stats.get("history", [])
        prices_list = [e.get("per_unit", 0) for e in hist if e.get("per_unit")]

        block = QWidget()
        vl    = QVBoxLayout(block)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(4)

        header_row = QHBoxLayout()
        chart_lbl  = QLabel("График цен (последние 50 сделок)")
        chart_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:11px;")
        header_row.addWidget(chart_lbl)
        header_row.addStretch()

        if prices_list:
            mn_lbl = QLabel(f"мин {_fmt(min(prices_list))}")
            mx_lbl = QLabel(f"макс {_fmt(max(prices_list))}")
            mn_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;")
            mx_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;")
            header_row.addWidget(mn_lbl)
            header_row.addSpacing(8)
            header_row.addWidget(mx_lbl)
        vl.addLayout(header_row)

        chart_frame = QFrame()
        chart_frame.setStyleSheet(
            f"QFrame {{ background:{config.SURFACE_COLOR}; border-radius:8px; }}"
        )
        chart_frame.setFixedHeight(80)
        chart_fl = QVBoxLayout(chart_frame)
        chart_fl.setContentsMargins(6, 6, 6, 6)
        chart    = PriceChart(prices_list)
        chart_fl.addWidget(chart)
        vl.addWidget(chart_frame)

        return block

    def _make_history_block(self) -> QWidget:
        stats = self._prices.get(self._item_id, {})
        hist  = stats.get("history", [])

        block = QWidget()
        vl    = QVBoxLayout(block)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(4)

        title_row = QHBoxLayout()
        title_lbl = QLabel("ИСТОРИЯ ПРОДАЖ")
        title_lbl.setStyleSheet(
            f"color:{config.MUTED_COLOR};font-size:10px;font-weight:600;letter-spacing:1px;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        count_lbl = QLabel(f"{len(hist)} записей")
        count_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;")
        title_row.addWidget(count_lbl)
        vl.addLayout(title_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border:none;background:transparent;")

        table = QWidget()
        tl    = QVBoxLayout(table)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(2)

        # Шапка таблицы
        header = QWidget()
        header.setStyleSheet(
            f"background:{config.SURFACE2_COLOR};"
            f"border-bottom:1px solid {config.BORDER_COLOR}; border-radius:6px;"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 4, 8, 4)
        for text, w in [("Дата", 90), ("Кол-во", 60), ("Цена лота", 100), ("Цена/шт", 90)]:
            lbl = QLabel(text)
            lbl.setFixedWidth(w)
            lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;font-weight:600;")
            hl.addWidget(lbl)
        hl.addStretch()
        tl.addWidget(header)

        # Строки (чередующийся фон для читаемости)
        for idx_row, entry in enumerate(hist[:30]):
            t_str   = entry.get("time", "")
            amount  = entry.get("amount", 1)
            price   = entry.get("price", 0)
            per_unit = entry.get("per_unit", round(price / max(amount, 1)))
            try:
                dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                date_str = _fmt_dt(dt)
            except Exception:
                date_str = t_str[:16]

            row = QWidget()
            # Чередующийся фон строк — работает во всех темах
            if idx_row % 2 == 0:
                row.setStyleSheet(f"background:{config.SURFACE_COLOR}; border-radius:4px;")
            row_hl = QHBoxLayout(row)
            row_hl.setContentsMargins(8, 3, 8, 3)

            for text, w, color in [
                (date_str, 90, config.MUTED_COLOR),
                (f"×{amount}", 60, config.TEXT_COLOR),
                (_fmt(price), 100, config.TEXT_COLOR),
                (_fmt(per_unit), 90, config.ACCENT_COLOR),
            ]:
                lbl = QLabel(text)
                lbl.setFixedWidth(w)
                lbl.setStyleSheet(f"color:{color};font-size:11px;")
                row_hl.addWidget(lbl)
            row_hl.addStretch()
            tl.addWidget(row)

        tl.addStretch()
        scroll.setWidget(table)
        vl.addWidget(scroll, stretch=1)
        return block

    def _make_footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(36)
        footer.setStyleSheet(
            f"QFrame {{ background:{config.SURFACE_COLOR};"
            f"border-top:1px solid {config.BORDER_COLOR}; }}"
        )
        row = QHBoxLayout(footer)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(6)

        craft  = self._recipe.get("craft", {})
        stats  = self._prices.get(self._item_id, {})
        mkt    = stats.get("market_min", 0)
        result = craft.get("result_amount", 1)
        profit = self._calc_profit()

        if mkt and profit:
            # Продажа идёт поштучно: result_amount продаж по отдельности
            total_revenue = 0
            for _ in range(result):
                sale_price = mkt
                commission_per_item = round(sale_price * AUCTION_FEE)
                revenue_per_item = sale_price - commission_per_item
                total_revenue += revenue_per_item
            
            total_commission = round(mkt * result * AUCTION_FEE)
            total_cost = self._calc_craft_cost()
            
            formula = (
                f"{result}× ({_fmt(mkt)} − 5%) = {_fmt(total_revenue)}"
                f" − крафт {_fmt(total_cost)} = "
            )
            formula_lbl = QLabel(formula)
            formula_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:11px;")
            row.addWidget(formula_lbl)

            pc   = config.SUCCESS_COLOR if profit > 0 else config.DANGER_COLOR
            sign = "+" if profit > 0 else "−"
            pct  = (profit / max(total_cost, 1)) * 100
            profit_lbl = QLabel(f"{sign}{_fmt(abs(profit))} прибыли ({pct:+.1f}%)")
            profit_lbl.setStyleSheet(f"color:{pc};font-size:12px;font-weight:600;")
            row.addWidget(profit_lbl)

        row.addStretch()

        import calc_cache_manager as cache_mgr
        updated = cache_mgr.get_updated_at(self._item_id)
        upd_lbl = QLabel(f"обновлено {_fmt_dt(updated)}")
        upd_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;")
        row.addWidget(upd_lbl)

        return footer

    # ── Расчёты ────────────────────────────────────────────────────────────────

    def _calc_craft_cost(self) -> int:
        craft = self._recipe.get("craft", {})
        total = 0
        for ing in craft.get("ingredients", []):
            s      = self._prices.get(ing["id"], {})
            hist   = s.get("history", [])
            price  = s.get("market_min") or (hist[0].get("per_unit", 0) if hist else 0) or s.get("avg", 0)
            total += price * ing["amount"]
        return total

    def _calc_profit(self) -> int:
        craft         = self._recipe.get("craft", {})
        result_amount = craft.get("result_amount", 1)
        stats         = self._prices.get(self._item_id, {})
        mkt           = stats.get("market_min", 0)
        if not mkt:
            return 0
        # Продажа идёт поштучно: result_amount штук × цена за 1 шт
        total_revenue = 0
        for _ in range(result_amount):
            sale_price = mkt
            commission = round(sale_price * AUCTION_FEE)
            revenue_per_item = sale_price - commission
            total_revenue += revenue_per_item
        
        craft_cost = self._calc_craft_cost()
        return total_revenue - craft_cost

    def _refresh(self):
        """Запрашивает обновление цен через PriceSyncManager."""
        from api_v2.qt_bridge import PriceSyncManager

        # Блокируем кнопку на время обновления
        for btn in self.findChildren(QPushButton):
            if "Обновить" in btn.text():
                btn.setText("⏳ Загрузка...")
                btn.setEnabled(False)

        craft = self._recipe.get("craft", {})
        ids   = {self._item_id} | {ing["id"] for ing in craft.get("ingredients", [])}

        self._sync = PriceSyncManager(parent=self)

        def _on_ready(iid: str, s: dict):
            self._prices[iid] = s
            import calc_cache_manager as cache_mgr
            cache_mgr.set(iid, s)

        def _on_done():
            import calc_cache_manager as cache_mgr
            cache_mgr.save()
            self._safe_rebuild()
            self._sync.deleteLater()

        self._sync.price_updated.connect(_on_ready)
        self._sync.sync_finished.connect(_on_done)
        self._sync.sync_prices(list(ids), include_lots=True, force_refresh=True)

    def refresh_theme(self):
        """Вызывается при смене темы."""
        self._apply_style()
        self._safe_rebuild()

    def _safe_rebuild(self):
        """Пересобирает окно безопасно через смену centralWidget."""
        # Убираем все дочерние виджеты из layout
        lo = self.layout()
        if lo:
            while lo.count():
                item = lo.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()
            # Удаляем layout — назначаем временному виджету
            dummy = QWidget()
            dummy.setLayout(lo)
            dummy.deleteLater()

        # Пересоздаём через singleShot — даём Qt очистить очередь событий
        QTimer.singleShot(50, self._build)

    def _rebuild(self):
        """Обратная совместимость."""
        self._safe_rebuild()


# ─── Публичная функция открытия окна ──────────────────────────────────────────

def open_detail_window(
    item_id: str,
    item_name: str,
    recipe: dict,
    live_prices: dict,
    parent=None,
) -> Optional["CraftDetailWindow"]:
    """
    Открывает окно подробностей.
    Если окно для этого item_id уже открыто — фокусирует его.
    Если открыто 3 окна — фокусирует самое старое.
    """
    # Очищаем список от удалённых окон
    global _open_windows
    valid_windows = []
    for w in _open_windows:
        try:
            # Проверяем что окно живо (доступ к атрибуту не вызовет RuntimeError)
            _ = w.isVisible()
            valid_windows.append(w)
        except RuntimeError:
            # Окно было удалено C++ объектом
            pass
    _open_windows = valid_windows
    
    # Уже открыто для этого предмета?
    for win in _open_windows:
        if win._item_id == item_id:
            win.raise_()
            win.activateWindow()
            return win

    # Лимит 3 окна
    if len(_open_windows) >= _MAX_WINDOWS:
        oldest = _open_windows[0]
        oldest.raise_()
        oldest.activateWindow()
        return oldest

    win = CraftDetailWindow(item_id, item_name, recipe, live_prices, parent)
    _open_windows.append(win)
    win.show()
    return win
