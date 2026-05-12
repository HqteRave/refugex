import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSizePolicy,
    QApplication,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt,
    QPoint,
    QTimer,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QEasingCurve,
    QRectF,
    QRect,
    pyqtProperty,
)
from PyQt6.QtGui import (
    QPixmap,
    QCursor,
    QPainter,
    QColor,
    QPen,
    QLinearGradient,
    QFont,
    QPainterPath,
)
import config
from config import MUTED_COLOR
from craft_levels import SKILL_NAMES, STATION_NAMES
from id_aliases import resolve_craft_info
from ui.star_button import StarButton
from favorites_manager import get_favorites_manager

from app_paths import asset_path


# ─── Утилиты ──────────────────────────────────────────────────────────────────


def _fmt(v: int) -> str:
    return f"{v:,}".replace(",", " ") + " ₽"


def _icon_path(item_id: str, cat_key: str) -> str:
    return asset_path("assets", "icons", cat_key, f"{item_id}.png")


_TREND_THRESHOLD = 0.02


def _calc_trend(prices: list[float]) -> str:
    """Линейная регрессия МНК по последним ценам. Возвращает 'up'|'down'|'stable'."""
    n = len(prices)
    if n < 3:
        return "stable"
    mean_x = (n - 1) / 2
    mean_y = sum(prices) / n
    num = sum((i - mean_x) * (prices[i] - mean_y) for i in range(n))
    den = sum((i - mean_x) ** 2 for i in range(n))
    slope = num / den if den else 0.0
    slope_pct = (slope / mean_y) if mean_y else 0.0
    if slope_pct > _TREND_THRESHOLD:
        return "up"
    if slope_pct < -_TREND_THRESHOLD:
        return "down"
    return "stable"


class TrendArrow(QLabel):
    """Стрелка тренда: ↑ зелёная, ↓ красная, → серая."""

    _SYMBOLS = {"up": "↑", "down": "↓", "stable": "→"}
    _COLORS  = {
        "up": QColor(0, 200, 100),
        "down": QColor(233, 69, 96),
        "stable": None,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._trend = "stable"
        self.setFixedSize(22, 22)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply()

    def set_trend(self, trend: str):
        if trend != self._trend:
            self._trend = trend
            self._apply()

    def _apply(self):
        color = self._COLORS.get(self._trend)
        hex_color = color.name() if color else config.MUTED_COLOR
        self.setText(self._SYMBOLS.get(self._trend, "→"))
        self.setStyleSheet(
            f"color: {hex_color}; font-size: 16px; font-weight: bold; background: transparent;"
        )


# ─── Градиентный разделитель ──────────────────────────────────────────────────


class GradientLine(QFrame):
    def __init__(self, color: QColor | None = None, parent=None):
        super().__init__(parent)
        self._color = color or QColor(config.BORDER_COLOR)
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), 0)
        c = self._color
        grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 0))
        grad.setColorAt(0.2, QColor(c.red(), c.green(), c.blue(), 160))
        grad.setColorAt(0.5, QColor(c.red(), c.green(), c.blue(), 220))
        grad.setColorAt(0.8, QColor(c.red(), c.green(), c.blue(), 160))
        grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
        p.fillRect(0, 0, self.width(), 1, grad)
        p.end()


# ─── График продаж ────────────────────────────────────────────────────────────


class PriceChart(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("priceChart")
        self.setMinimumHeight(220)
        self.setMaximumHeight(220)
        self.setMinimumWidth(400)

        self._data = []
        self._hover_index = -1
        self.setMouseTracking(True)

        self.setStyleSheet("""
            QFrame#priceChart {
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }
        """)

    def update_data(self, history: list):
        """Обновление данных графика"""
        self._data = history[::-1]  # Разворачиваем, чтобы старые были слева
        self._hover_index = -1
        self.update()

    def mouseMoveEvent(self, event):
        if not self._data:
            return

        pos = event.pos()
        margin = 40
        padding = 20

        chart_width = self.width() - margin - padding * 2
        chart_height = self.height() - margin - padding * 2

        # Проверяем, находится ли курсор в области графика
        if (
            pos.x() < padding + margin
            or pos.x() > self.width() - padding
            or pos.y() < padding
            or pos.y() > self.height() - padding - margin
        ):
            self._hover_index = -1
            self.update()
            return

        # Находим ближайшую точку
        if len(self._data) > 1:
            step = chart_width / (len(self._data) - 1)
            index = round((pos.x() - padding - margin) / step)
            if 0 <= index < len(self._data):
                self._hover_index = index
                self.update()

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 8.0, 8.0)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(config.HISTORY_BG))
        p.drawPath(path)
        p.setPen(QPen(QColor(config.BORDER_COLOR), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()

        super().paintEvent(event)

        if not self._data:
            self._draw_empty_state()
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 40
        padding = 20

        w = self.width() - margin - padding * 2
        h = self.height() - margin - padding * 2

        # Извлекаем цены
        prices = [entry.get("per_unit", 0) for entry in self._data]
        if not prices:
            return

        min_price = min(prices)
        max_price = max(prices)

        # Добавляем 10% padding по вертикали — иначе маленькие колебания
        # выглядят как огромные скачки (ось растягивается от min до max)
        spread = max_price - min_price if max_price != min_price else max_price * 0.1 or 1
        padding_pct = 0.10
        min_price = max(0, min_price - spread * padding_pct)
        max_price = max_price + spread * padding_pct
        price_range = max_price - min_price

        # Рисуем сетку
        self._draw_grid(p, padding, margin, w, h, min_price, max_price)

        # Рисуем линию графика
        self._draw_line(p, padding, margin, w, h, prices, min_price, price_range)

        # Рисуем точки
        self._draw_points(p, padding, margin, w, h, prices, min_price, price_range)

        # Рисуем подсказку при наведении
        if self._hover_index >= 0:
            self._draw_tooltip(p, padding, margin, w, h, prices, min_price, price_range)

        p.end()

    def _draw_empty_state(self):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont("Segoe UI", 11)
        p.setFont(font)
        p.setPen(QColor(config.MUTED_COLOR))

        text = "Нет данных для отображения"
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
        p.end()

    def _draw_grid(self, p, padding, margin, w, h, min_price, max_price):
        """Рисуем фоновую сетку"""
        p.setPen(QPen(QColor(config.BORDER_COLOR), 1))

        for i in range(5):
            y = padding + i * (h / 4)
            p.drawLine(padding + margin, int(y), padding + margin + w, int(y))

            price = max_price - (i * (max_price - min_price) / 4)
            label = f"{int(price):,}".replace(",", " ")

            font = QFont("Segoe UI", 8)
            p.setFont(font)
            p.setPen(QColor(config.MUTED_COLOR))

            rect = QRect(padding, int(y) - 10, margin - 5, 20)
            p.drawText(
                rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label
            )

    def _draw_line(self, p, padding, margin, w, h, prices, min_price, price_range):
        """Рисуем линию графика"""
        if len(prices) < 2:
            return

        # Градиент для линии
        path = QPainterPath()
        step = w / (len(prices) - 1)

        for i, price in enumerate(prices):
            x = padding + margin + i * step
            y = padding + h - ((price - min_price) / price_range) * h

            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        ac = QColor(config.CHART_COLOR)
        pen = QPen(ac, 2)
        p.setPen(pen)
        p.drawPath(path)

        fill_path = QPainterPath(path)
        fill_path.lineTo(padding + margin + w, padding + h)
        fill_path.lineTo(padding + margin, padding + h)
        fill_path.closeSubpath()

        gradient = QLinearGradient(0, padding, 0, padding + h)
        gradient.setColorAt(0, QColor(ac.red(), ac.green(), ac.blue(), 40))
        gradient.setColorAt(1, QColor(ac.red(), ac.green(), ac.blue(), 5))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(gradient)
        p.drawPath(fill_path)

    def _draw_points(self, p, padding, margin, w, h, prices, min_price, price_range):
        """Рисуем точки на графике"""
        step = w / (len(prices) - 1) if len(prices) > 1 else 0
        ac = QColor(config.CHART_COLOR)

        for i, price in enumerate(prices):
            x = padding + margin + i * step
            y = padding + h - ((price - min_price) / price_range) * h

            if i == self._hover_index:
                p.setPen(QPen(ac, 2))
                p.setBrush(QColor(ac.red(), ac.green(), ac.blue(), 200))
                p.drawEllipse(QPoint(int(x), int(y)), 6, 6)
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(ac.red(), ac.green(), ac.blue(), 180))
                p.drawEllipse(QPoint(int(x), int(y)), 4, 4)

            p.setBrush(QColor(255, 255, 255, 60))
            p.drawEllipse(QPoint(int(x), int(y)), 2, 2)

    def _draw_tooltip(self, p, padding, margin, w, h, prices, min_price, price_range):
        """Рисуем всплывающую подсказку"""
        if self._hover_index < 0 or self._hover_index >= len(self._data):
            return

        entry = self._data[self._hover_index]
        price = prices[self._hover_index]

        step = w / (len(prices) - 1) if len(prices) > 1 else 0
        x = padding + margin + self._hover_index * step
        y = padding + h - ((price - min_price) / price_range) * h

        # Форматируем время с точностью до минуты
        time_str = entry.get("time", "")
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            formatted_time = dt.strftime("%d.%m.%Y %H:%M")
        except:
            formatted_time = time_str[:16].replace("T", " ")

        amount = entry.get("amount", 1)
        per_unit = entry.get("per_unit", price)
        lot_price = entry.get("price", per_unit * amount)

        # Цена/шт — то что отображается на графике
        price_str = f"{int(per_unit):,}".replace(",", " ") + " ₽/шт"
        lot_str   = f"{int(lot_price):,}".replace(",", " ") + " ₽ (лот)"

        lines = [formatted_time, price_str, lot_str, f"× {amount} шт"]

        # Размеры тултипа
        font = QFont("Segoe UI", 9)
        p.setFont(font)

        max_width = 0
        for line in lines:
            metrics = p.fontMetrics()
            max_width = max(max_width, metrics.horizontalAdvance(line))

        tooltip_w = max_width + 16
        tooltip_h = 74  # 4 строки

        # Позиционирование
        tooltip_x = int(x) - tooltip_w // 2
        tooltip_y = int(y) - tooltip_h - 15

        # Корректировка, чтобы не выходил за границы
        if tooltip_x < padding:
            tooltip_x = padding
        if tooltip_x + tooltip_w > self.width() - padding:
            tooltip_x = self.width() - padding - tooltip_w
        if tooltip_y < padding:
            tooltip_y = int(y) + 15

        # Рисуем фон тултипа
        tooltip_rect = QRectF(
            float(tooltip_x), float(tooltip_y), float(tooltip_w), float(tooltip_h)
        )

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(config.POPUP_BG))

        path = QPainterPath()
        path.addRoundedRect(tooltip_rect, 6.0, 6.0)
        p.drawPath(path)

        p.setPen(QPen(QColor(config.BORDER_COLOR), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        p.setPen(QColor(config.TEXT_COLOR))
        y_offset = tooltip_y + 14

        for line in lines:
            p.drawText(tooltip_x + 8, y_offset, line)
            y_offset += 16


# ─── Кастомный тултип ─────────────────────────────────────────────────────────


class FadeTooltip(QFrame):
    _instance = None

    @classmethod
    def get(cls) -> "FadeTooltip":
        if cls._instance is None:
            cls._instance = FadeTooltip()
        return cls._instance

    def __init__(self):
        super().__init__(
            None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setObjectName("fadeTooltip")
        self._refresh_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setWordWrap(True)
        self._label.setMinimumWidth(250)
        self._label.setContentsMargins(0, 0, 0, 0)
        self._label.setMargin(0)
        layout.addWidget(self._label)

        self._target_opacity = 1.0
        self._anim_opacity = QPropertyAnimation(self, b"windowOpacity")
        self._anim_opacity.setDuration(200)
        self._anim_opacity.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_pos = QPropertyAnimation(self, b"pos")
        self._anim_pos.setDuration(200)
        self._anim_pos.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(self._anim_opacity)
        self._anim_group.addAnimation(self._anim_pos)

        # для fade-out используем только opacity
        self._anim_fade_out = QPropertyAnimation(self, b"windowOpacity")
        self._anim_fade_out.setDuration(160)
        self._anim_fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_fade_out.finished.connect(self._on_fade_done)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

    def _refresh_style(self):
        self.setStyleSheet(f"""
            QFrame#fadeTooltip {{
                background-color: {config.POPUP_BG};
                border: 1px solid {config.BORDER_COLOR};
                border-radius: 12px;
            }}
            QFrame#fadeTooltip QLabel {{
                color: {config.TEXT_COLOR};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                font-weight: 500;
                line-height: 1.1em;
                background: transparent;
            }}
        """)

    def show_at(self, pos: QPoint, text: str):
        self._refresh_style()
        compact_text = text.replace("<p", '<div style="margin:0; padding:0;"')
        compact_text = compact_text.replace("</p>", "</div>")
        compact_text = compact_text.replace("<br><br>", "<br>")
        self._label.setText(compact_text)
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        x, y = pos.x() + 14, pos.y() + 14
        if x + self.width() > screen.right() - 10:
            x = pos.x() - self.width() - 8
        if y + self.height() > screen.bottom() - 10:
            y = pos.y() - self.height() - 8

        target = QPoint(x, y)
        start = QPoint(x, y + 8)   # стартуем на 8px ниже

        self._anim_group.stop()
        self._anim_fade_out.stop()

        self.move(start)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self._anim_opacity.setStartValue(0.0)
        self._anim_opacity.setEndValue(self._target_opacity)
        self._anim_pos.setStartValue(start)
        self._anim_pos.setEndValue(target)
        self._anim_group.start()

        self._hide_timer.start(6000)

    def _fade_out(self):
        self._anim_group.stop()
        self._anim_fade_out.stop()
        self._anim_fade_out.setStartValue(self.windowOpacity())
        self._anim_fade_out.setEndValue(0.0)
        self._anim_fade_out.start()

    def _on_fade_done(self):
        if self.windowOpacity() == 0.0:
            self.hide()

    def hide_now(self):
        self._hide_timer.stop()
        self._anim_group.stop()
        self._anim_fade_out.stop()
        self.hide()


# ─── LiqLabel — свечение через QPainter ──────────────────────────────────────


class LiqLabel(QLabel):
    GLOW_COLORS = {
        "liqHigh": ("Высокая", QColor(0, 220, 120), QColor(0, 180, 90, 80)),
        "liqMed": ("Средняя", QColor(255, 200, 0), QColor(200, 150, 0, 80)),
        "liqLow": ("Низкая", QColor(255, 70, 100), QColor(200, 30, 60, 80)),
        "liqNone": ("Нет данных", QColor(100, 100, 125), QColor(0, 0, 0, 0)),
    }
    ICON_COLORS = {
        "liqHigh": QColor(0, 220, 120),
        "liqMed": QColor(255, 200, 0),
        "liqLow": QColor(255, 70, 100),
        "liqNone": None,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._obj_name = "liqNone"
        self._hovered = False
        self._stats = {}
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumWidth(110)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def set_status(self, obj_name: str):
        self._obj_name = obj_name
        text, _, _ = self.GLOW_COLORS.get(obj_name, self.GLOW_COLORS["liqNone"])
        self.setText(text)
        self.setObjectName(obj_name)
        self._hovered = False
        self.update()

    def set_tooltip(self, text: str):
        # сохраняем для обратной совместимости, но не используем напрямую
        pass

    def set_stats(self, stats: dict):
        self._stats = stats

    def _build_tooltip_html(self) -> str:
        s = self._stats
        if not s:
            return ""
        _bg   = config.POPUP_BG
        _brd  = config.BORDER_COLOR
        _txt  = config.TEXT_COLOR
        _mute = config.MUTED_COLOR
        _acc  = config.ACCENT_COLOR
        count      = s.get("count", 0)
        per_minute = s.get("per_minute", 0)
        per_5min   = s.get("per_5min", 0)
        per_hour   = s.get("per_hour", 0)
        per_day    = s.get("per_day", 0)
        span       = s.get("span", "")
        avg_price  = s.get("avg", 0)
        return (
            f"<div style='background-color:{_bg}; border:1px solid {_brd}; padding:10px 12px; border-radius:10px;'>"
            f"<b style='color:{_txt};font-size:12px;'>📊 Ликвидность: {count} сделок</b><br>"
            f"<span style='color:{_mute};font-size:10px;'>Последние продажи по предмету</span><br><br>"
            f"<table style='border-collapse:collapse;font-size:11px;'>"
            f"<tr><td style='padding:0 10px 2px 0;color:{_mute};'>За 1 мин:</td>"
            f"<td style='padding:0 0 2px 0;color:{_txt};font-weight:600;'>{per_minute} прод.</td></tr>"
            f"<tr><td style='padding:0 10px 2px 0;color:{_mute};'>За 5 мин:</td>"
            f"<td style='padding:0 0 2px 0;color:{_txt};font-weight:600;'>{per_5min} прод.</td></tr>"
            f"<tr><td style='padding:0 10px 2px 0;color:{_mute};'>За час:</td>"
            f"<td style='padding:0 0 2px 0;color:{_txt};font-weight:600;'>{per_hour} прод.</td></tr>"
            f"<tr><td style='padding:0 10px 4px 0;color:{_mute};'>За 24 ч:</td>"
            f"<td style='padding:0 0 4px 0;color:{_txt};font-weight:600;'>{per_day} прод.</td></tr>"
            f"</table>"
            f"<div style='margin-top:4px;color:{_mute};font-size:10px;'>Диапазон данных: "
            f"<span style='color:{_txt};font-weight:600;'>{span if span else 'н/д'}</span></div>"
            f"<div style='margin-top:2px;color:{_mute};font-size:10px;'>Сред. цена/шт: "
            f"<span style='color:{_acc};font-weight:700;'>{avg_price:,} ₽</span></div>"
            f"</div>"
        ).replace(",", " ")

    def paintEvent(self, event):
        _, color, glow_color = self.GLOW_COLORS.get(
            self._obj_name, self.GLOW_COLORS["liqNone"]
        )
        icon_color = self.ICON_COLORS.get(self._obj_name)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        r = self.rect()
        cy = r.height() // 2
        cr = 7
        cx = cr + 3

        if icon_color:
            fill = QColor(icon_color)
            fill.setAlpha(210)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawEllipse(cx - cr, cy - cr, cr * 2, cr * 2)
            p.setBrush(QColor(255, 255, 255, 55))
            p.drawEllipse(cx - cr + 3, cy - cr + 3, cr - 2, cr - 2)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(80, 80, 105, 180))
            p.drawEllipse(cx - cr, cy - cr, cr * 2, cr * 2)
            qfont = QFont("Segoe UI", 8)
            qfont.setBold(True)
            p.setFont(qfont)
            p.setPen(QColor(170, 170, 195))
            p.drawText(
                cx - cr, cy - cr, cr * 2, cr * 2, Qt.AlignmentFlag.AlignCenter, "?"
            )

        font = QFont("Segoe UI", 9)
        font.setBold(True)
        p.setFont(font)

        text_x = cx + cr + 6
        align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        text_rect = r.adjusted(text_x, 0, 0, 0)

        if self._hovered and glow_color.alpha() > 0:
            for radius, alpha in ((4, 18), (2, 35), (1, 55)):
                g = QColor(glow_color)
                g.setAlpha(alpha)
                p.setPen(g)
                for dx in (-radius, 0, radius):
                    for dy in (-radius, 0, radius):
                        if dx == 0 and dy == 0:
                            continue
                        p.drawText(
                            text_rect.adjusted(dx, dy, dx, dy), align, self.text()
                        )

        p.setPen(color)
        p.drawText(text_rect, align, self.text())
        p.end()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        html = self._build_tooltip_html()
        if html:
            FadeTooltip.get().show_at(QCursor.pos(), html)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        FadeTooltip.get().hide_now()
        super().leaveEvent(event)


_LEVEL_COLORS = {
    1: ("#152015", "#4caf50"),
    2: ("#101d28", "#2196f3"),
    3: ("#222010", "#ffc107"),
    4: ("#22140c", "#ff9800"),
    5: ("#200c16", "#e9455f"),
}

_SKILL_ICONS = {
    "ammo": "🔫",
    "pyro": "💥",
    "armor": "🛡️",
    "engineering": "⚙️",
    "cooking": "🍳",
    "brewing": "🍺",
    "medicine": "💊",
    "materials": "⚗️",
}

_STATION_ICONS = {
    "workbench": "🔧",
    "lab": "🔬",
    "kitchen": "🍴",
    "stove": "🔥",
}


class CraftBadge(QFrame):

    def __init__(self, item_id: str, parent=None):
        super().__init__(parent)
        self._craft = resolve_craft_info(item_id)
        self._build()

    @property
    def craft(self) -> dict | None:
        return self._craft

    def refresh(self):
        if not self._craft:
            return
        level = self._craft["level"]
        accent = config.BADGE_COLOR
        if hasattr(self, '_bar_widget'):
            self._bar_widget.update()
        if hasattr(self, '_dots_lbl'):
            filled = f'<font color="{accent}">{"●" * level}</font>'
            empty = f'<font color="{config.FAINT_COLOR}">{"●" * (5 - level)}</font>'
            self._dots_lbl.setText(filled + empty)
        if hasattr(self, '_skill_lbl'):
            self._skill_lbl.setStyleSheet(
                f"color: {config.TEXT_COLOR}; font-size: 11px; font-weight: 600;"
                "letter-spacing: 0.3px;"
            )
        if hasattr(self, '_station_lbl'):
            self._station_lbl.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 11px;")

    def _build(self):
        if not self._craft:
            self.hide()
            return

        skill = self._craft["skill"]
        level = self._craft["level"]
        station = self._craft["station"]

        self.setStyleSheet("""
            QFrame { background: transparent; border: none; }
            QFrame QLabel { background: transparent; }
        """)
        self.setFixedHeight(24)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 10, 0)
        row.setSpacing(6)

        # QWidget (не QFrame) чтобы родительский stylesheet не перекрывал paintEvent
        from PyQt6.QtWidgets import QWidget as _QWidget
        class _Bar(_QWidget):
            def paintEvent(self_, ev):
                p = QPainter(self_)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(QRectF(self_.rect()), 2.0, 2.0)
                p.fillPath(path, QColor(config.BADGE_COLOR))
                p.end()

        self._bar_widget = _Bar()
        self._bar_widget.setFixedSize(3, 16)
        row.addWidget(self._bar_widget)
        row.addSpacing(2)

        icon = _SKILL_ICONS.get(skill, "·")
        sname = SKILL_NAMES.get(skill, skill)
        self._skill_lbl = QLabel(f"{icon} {sname}")
        self._skill_lbl.setStyleSheet(
            f"color: {config.TEXT_COLOR}; font-size: 11px; font-weight: 600;"
            "letter-spacing: 0.3px;"
        )

        accent = config.BADGE_COLOR
        filled = f'<font color="{accent}">{"●" * level}</font>'
        empty = f'<font color="{config.FAINT_COLOR}">{"●" * (5 - level)}</font>'
        self._dots_lbl = QLabel()
        self._dots_lbl.setText(filled + empty)
        self._dots_lbl.setStyleSheet("font-size: 11px; letter-spacing: 1px;")

        row.addWidget(self._skill_lbl)
        row.addSpacing(4)
        row.addWidget(self._dots_lbl)
        row.addStretch()

        st_icon = _STATION_ICONS.get(station, "·")
        st_name = STATION_NAMES.get(station, station)
        self._station_lbl = QLabel(f"{st_icon} {st_name}")
        self._station_lbl.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 11px;")
        row.addWidget(self._station_lbl)


class RoundedIcon(QLabel):
    SIZE = 72
    RADII = 10
    
    _icon_cache = {}

    def __init__(self, item_id: str, cat_key: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._load(item_id, cat_key)

    def _load(self, item_id: str, cat_key: str):
        cache_key = f"{cat_key}:{item_id}"
        
        if cache_key in self._icon_cache:
            self.setPixmap(self._icon_cache[cache_key])
            return
        
        path = _icon_path(item_id, cat_key)
        if os.path.exists(path):
            raw = QPixmap(path).scaled(
                self.SIZE,
                self.SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            rounded = QPixmap(raw.size())
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path_obj = QPainterPath()
            path_obj.addRoundedRect(
                0, 0, raw.width(), raw.height(), self.RADII, self.RADII
            )
            painter.setClipPath(path_obj)
            painter.drawPixmap(0, 0, raw)
            painter.end()
            
            self._icon_cache[cache_key] = rounded
            self.setPixmap(rounded)
        else:
            self.setText("?")
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setStyleSheet(
                f"background: {config.SURFACE_COLOR}; border-radius: 10px;"
                f"color: {config.MUTED_COLOR}; font-size: 24px;"
            )


class ItemCard(QFrame):
    def __init__(self, item: dict, cat_key: str, is_best: bool = False):
        super().__init__()
        self.item_name = item["name"]
        self.item_id = item["item_id"]
        self.cat_key = cat_key
        self._history = []
        self._hist_visible = False

        craft = resolve_craft_info(self.item_id)
        self.craft_skill = craft["skill"] if craft else None
        self.craft_level = craft["level"] if craft else None
        self.craft_station = craft["station"] if craft else None
        self.is_craftable = craft is not None
        self.is_best = is_best

        self.setObjectName("itemCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._hovered = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

        self._favorites = get_favorites_manager()

        # Flash-анимация при изменении цены
        self._flash_alpha_val = 0
        self._flash_color = QColor(0, 200, 100)  # зелёный по умолчанию
        self._flash_anim = QPropertyAnimation(self, b"flashAlpha")
        self._flash_anim.setDuration(1200)
        self._flash_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._last_avg = None

        self._build()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def play_appear(self, delay: int = 0):
        """Fade-in + сдвиг снизу при появлении карточки."""
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)

        self._appear_effect = effect
        self._appear_anim = QPropertyAnimation(effect, b"opacity")
        self._appear_anim.setDuration(280)
        self._appear_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._appear_anim.setStartValue(0.0)
        self._appear_anim.setEndValue(1.0)
        self._appear_anim.finished.connect(self._on_appear_done)

        QTimer.singleShot(delay, self._appear_anim.start)

    def _on_appear_done(self):
        self.setGraphicsEffect(None)
        self._appear_effect = None

    @pyqtProperty(int)
    def flashAlpha(self):
        return self._flash_alpha_val

    @flashAlpha.setter
    def flashAlpha(self, value):
        self._flash_alpha_val = value
        self.update()

    def paintEvent(self, event):
        from config import SURFACE_COLOR, SURFACE2_COLOR

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        radius = 12.0

        bg = QColor(SURFACE2_COLOR if self._hovered else SURFACE_COLOR)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), radius, radius)
        p.setPen(Qt.PenStyle.NoPen)
        p.fillPath(bg_path, bg)

        if self._hovered:
            hc = QColor(config.HOVER_BORDER)
            hr, hg, hb = hc.red(), hc.green(), hc.blue()
            for spread, alpha in [(9, 4), (6, 9), (3.5, 18), (2, 35)]:
                pen = QPen(QColor(hr, hg, hb, alpha), spread * 2)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                gp = QPainterPath()
                gp.addRoundedRect(
                    r.x() + spread, r.y() + spread,
                    r.width() - spread * 2, r.height() - spread * 2,
                    radius, radius,
                )
                p.drawPath(gp)
            pen = QPen(QColor(hr, hg, hb, 130), 1.5)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            bp = QPainterPath()
            bp.addRoundedRect(0.75, 0.75, r.width() - 1.5, r.height() - 1.5, radius, radius)
            p.drawPath(bp)

        if self._favorites.is_favorite(self.item_id):
            fc = QColor(config.FAV_BORDER)
            fr, fg, fb = fc.red(), fc.green(), fc.blue()
            for spread, alpha in [(6, 6), (4, 14), (2, 28)]:
                pen = QPen(QColor(fr, fg, fb, alpha), spread * 2)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                gp = QPainterPath()
                gp.addRoundedRect(
                    r.x() + spread, r.y() + spread,
                    r.width() - spread * 2, r.height() - spread * 2,
                    radius, radius,
                )
                p.drawPath(gp)
            pen = QPen(QColor(fr, fg, fb, 200), 1.8)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            bp = QPainterPath()
            bp.addRoundedRect(0.75, 0.75, r.width() - 1.5, r.height() - 1.5, radius, radius)
            p.drawPath(bp)
        elif not self._hovered:
            pen = QPen(QColor(config.BORDER_COLOR), 1)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            bp = QPainterPath()
            bp.addRoundedRect(0.5, 0.5, r.width() - 1, r.height() - 1, radius, radius)
            p.drawPath(bp)

        # Flash-подсветка при изменении цены
        if self._flash_alpha_val > 0:
            fc = QColor(self._flash_color)
            # Слабый фон (~8% от alpha анимации)
            fc.setAlpha(int(self._flash_alpha_val * 0.08))
            flash_path = QPainterPath()
            flash_path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), radius, radius)
            p.setPen(Qt.PenStyle.NoPen)
            p.fillPath(flash_path, fc)
            # Левая полоска 3px
            fc.setAlpha(self._flash_alpha_val)
            bar_path = QPainterPath()
            bar_path.addRoundedRect(r.x(), r.y() + 8, 3, r.height() - 16, 1.5, 1.5)
            p.fillPath(bar_path, fc)

        p.end()
        super().paintEvent(event)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 10)
        outer.setSpacing(0)

        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(RoundedIcon(self.item_id, self.cat_key))

        right = QVBoxLayout()
        right.setSpacing(5)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_lbl = QLabel(self.item_name)
        name_lbl.setObjectName("itemName")

        id_lbl = QLabel(self.item_id)
        id_lbl.setObjectName("itemId")
        id_lbl.setToolTip("ID предмета (в API)")
        id_lbl.setCursor(QCursor(Qt.CursorShape.IBeamCursor))

        name_row.addWidget(name_lbl, stretch=1)

        self._star_btn = StarButton(self.item_id, fav_type='auction')
        self._star_btn.toggled.connect(self._on_star_clicked)
        name_row.addWidget(self._star_btn)

        name_row.addWidget(id_lbl)
        right.addLayout(name_row)

        right.addWidget(GradientLine())

        prices_row = QHBoxLayout()
        prices_row.setSpacing(0)
        self._min_lbl = self._price_col(prices_row, "МИН", bold=False)
        self._avg_lbl = self._price_col(prices_row, "СРЕД", bold=True)
        self._max_lbl = self._price_col(prices_row, "МАКС", bold=False)
        self._market_lbl = self._price_col(prices_row, "РЫНОК ▸", bold=False, accent=True)
        right.addLayout(prices_row)

        bot_row = QHBoxLayout()
        bot_row.setSpacing(0)

        liq_prefix = QLabel("Ликвидность: ")
        liq_prefix.setObjectName("priceLabel")

        self._liq_lbl = LiqLabel()
        self._liq_lbl.set_status("liqNone")
        self._liq_lbl.setText("⏳ Загрузка...")

        self._cnt_lbl = QLabel("")
        self._cnt_lbl.setObjectName("itemId")

        self._hist_btn = QPushButton("▶ История")
        self._hist_btn.setObjectName("historyBtn")
        self._hist_btn.setFixedWidth(100)
        self._hist_btn.clicked.connect(self._toggle_history)

        self._trend_arrow = TrendArrow()

        bot_row.addWidget(liq_prefix)
        bot_row.addWidget(self._liq_lbl)
        bot_row.addSpacing(8)
        bot_row.addWidget(self._trend_arrow)
        bot_row.addSpacing(8)
        bot_row.addWidget(self._cnt_lbl)
        bot_row.addStretch()
        bot_row.addWidget(self._hist_btn)
        right.addLayout(bot_row)

        top.addLayout(right, stretch=1)
        outer.addLayout(top)

        self._craft_badge = CraftBadge(self.item_id)
        if self.is_craftable:
            outer.addSpacing(6)
            outer.addWidget(self._craft_badge)

        outer.addSpacing(8)
        outer.addWidget(self._build_history_panel())

    def _build_history_panel(self) -> QFrame:
        self._history_frame = QFrame()
        self._history_frame.setObjectName("historyPanel")
        self._history_frame.setMaximumHeight(0)
        self._history_frame.setMinimumHeight(0)

        self._history_anim = QPropertyAnimation(self._history_frame, b"maximumHeight")
        self._history_anim.setDuration(220)
        self._history_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._history_expanded_h = 310

        layout = QVBoxLayout(self._history_frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("📋  История продаж (последние 50 сделок)")
        title.setStyleSheet(f"color: {MUTED_COLOR}; font-size: 11px;")
        layout.addWidget(title)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)

        self._chart = PriceChart()
        content_layout.addWidget(self._chart, stretch=2)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Дата", "Кол-во", "Цена лота", "Цена/шт"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setMaximumHeight(220)
        content_layout.addWidget(self._table, stretch=1)

        layout.addLayout(content_layout)

        return self._history_frame

    def _price_col(self, layout: QHBoxLayout, label: str, bold: bool = False, accent: bool = False) -> QLabel:
        col = QVBoxLayout()
        col.setSpacing(2)

        lbl = QLabel(label)
        lbl.setObjectName("priceLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if accent:
            lbl.setStyleSheet(f"color: {config.ACCENT_COLOR}; font-size: 10px; font-weight: 600;")

        val = QLabel("⏳")
        if accent:
            val.setObjectName("priceAccent")
            val.setStyleSheet(f"color: {config.ACCENT_COLOR}; font-size: 13px; font-weight: 700;")
        else:
            val.setObjectName("priceAvg" if bold else "priceMin")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        col.addWidget(lbl)
        col.addWidget(val)
        layout.addLayout(col)
        return val

    def refresh_theme(self):
        if hasattr(self, '_craft_badge') and self.is_craftable:
            self._craft_badge.refresh()

    def update_prices(self, stats: dict):
        if stats["count"] == 0:
            self._min_lbl.setText("—")
            self._avg_lbl.setText("Нет данных")
            self._max_lbl.setText("—")
            self._market_lbl.setText("—")
            self._liq_lbl.set_status("liqNone")
            self._liq_lbl.set_tooltip("Нет данных о продажах")
            return

        new_avg = stats["avg"]

        # Запускаем flash только при обновлении (не при первой загрузке)
        if self._last_avg is not None and new_avg != self._last_avg:
            if new_avg > self._last_avg:
                self._flash_color = QColor(0, 200, 100)   # зелёный — цена выросла
            else:
                self._flash_color = QColor(233, 69, 96)   # красный — цена упала
            self._flash_anim.stop()
            self._flash_anim.setStartValue(220)
            self._flash_anim.setEndValue(0)
            self._flash_anim.start()

        self._last_avg = new_avg

        self._min_lbl.setText(_fmt(stats["min"]))
        self._avg_lbl.setText(_fmt(stats["avg"]))
        self._max_lbl.setText(_fmt(stats["max"]))
        self._cnt_lbl.setText(f"{stats['count']} сделок")
        market_min = stats.get("market_min", 0)
        self._market_lbl.setText(_fmt(market_min) if market_min else "—")
        self._history = stats.get("history", [])

        _liq_map = {
            "high": "liqHigh",
            "medium": "liqMed",
            "low": "liqLow",
            "unknown": "liqNone",
        }
        self._liq_lbl.set_status(_liq_map.get(stats["liquidity"], "liqNone"))
        self._liq_lbl.set_stats(stats)

        # Тренд по последним 5 ценам
        history = stats.get("history", [])
        if history:
            prices = [e.get("per_unit", 0) for e in history[:5]]
            self._trend_arrow.set_trend(_calc_trend(prices))

        if self._hist_visible:
            self._fill_table()

    def _toggle_history(self):
        self._hist_visible = not self._hist_visible
        self._hist_btn.setText("▼ История" if self._hist_visible else "▶ История")

        self._history_anim.stop()
        if self._hist_visible:
            self._history_frame.setMaximumHeight(0)
            self._history_frame.show()
            self._history_anim.setStartValue(0)
            self._history_anim.setEndValue(self._history_expanded_h)
            self._fill_table()
        else:
            self._history_anim.setStartValue(self._history_frame.height())
            self._history_anim.setEndValue(0)
            self._history_anim.finished.connect(self._on_history_collapsed)
        self._history_anim.start()

    def _on_history_collapsed(self):
        try:
            self._history_anim.finished.disconnect(self._on_history_collapsed)
        except Exception:
            pass
        self._history_frame.hide()

    def update_market(self, market_min: int, market_total: int = 0):
        """Обновляет только колонку РЫНОК ▸ без перерисовки всей карточки."""
        self._market_lbl.setText(_fmt(market_min) if market_min else "—")

    def _fill_table(self):
        # Обновляем график
        self._chart.update_data(self._history)

        # Обновляем таблицу
        self._table.setRowCount(0)
        for entry in self._history:
            row = self._table.rowCount()
            self._table.insertRow(row)
            t = entry.get("time", "")[:16].replace("T", " ")
            amount = entry.get("amount", 1)
            price = entry.get("price", 0)
            per_unit = entry.get("per_unit", price)
            self._table.setItem(row, 0, QTableWidgetItem(t))
            self._table.setItem(row, 1, QTableWidgetItem(f"× {amount}"))
            self._table.setItem(row, 2, QTableWidgetItem(_fmt(price)))
            self._table.setItem(row, 3, QTableWidgetItem(_fmt(per_unit)))

    def _on_star_clicked(self, is_favorite: bool):
        """Обработка клика по звёздочке (звёздочка сама сохраняет в FavoritesManager)"""
        self.update()

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        from ui.compare_window import CompareWindow, MAX_COMPARE

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
                padding: 7px 18px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background: {config.ACCENT_COLOR};
                color: #ffffff;
            }}
            QMenu::item:disabled {{
                color: {config.MUTED_COLOR};
            }}
        """)

        already_in = any(i == self.item_id for _, i, _ in CompareWindow._items)
        count = len(CompareWindow._items)

        if already_in:
            act = QAction("✓ Уже в сравнении", self)
            act.setEnabled(False)
        elif count >= MAX_COMPARE:
            act = QAction(f"⚖ Сравнение заполнено ({MAX_COMPARE}/{MAX_COMPARE})", self)
            act.setEnabled(False)
        else:
            act = QAction(f"⚖ Добавить к сравнению ({count + 1}/{MAX_COMPARE})", self)
            stats = self._build_stats_snapshot()
            act.triggered.connect(lambda: CompareWindow.add_item(
                self.item_name, self.item_id, stats, self.window()
            ))

        menu.addAction(act)
        menu.exec(event.globalPos())

    def _build_stats_snapshot(self) -> dict | None:
        """Возвращает текущий снапшот статистики для окна сравнения."""
        if not hasattr(self, '_liq_lbl') or not self._liq_lbl._stats:
            return None
        return dict(self._liq_lbl._stats)
