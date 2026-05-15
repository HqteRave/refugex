# ui/craft_calculator.py
"""
Калькулятор крафта для STALCRAFT.
- Кэш цен в calc_cache.json (мгновенная загрузка)
- Обновление по ПКМ или кнопке
- Дата обновления + предупреждение об устаревших данных
- Две цены продажи: последняя сделка и минимум аукциона
"""

import json
from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QGraphicsOpacityEffect, QMenu,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen, QPolygonF, QCursor, QAction

import config
import calc_cache_manager as cache_mgr
from ui.craft_detail_window import open_detail_window
from api_v2.qt_bridge import PriceSyncManager
from ui.liquidity_indicator import LiquidityWithText
from ui.star_button import StarButton
from favorites_manager import get_favorites_manager
from app_paths import asset_path
from non_tradeable_items import is_tradeable

_RECIPES_FILE = asset_path("recipes_calculator.json")
AUCTION_FEE   = 0.05
_TREND_THRESHOLD = 0.02


# ─── Утилиты ──────────────────────────────────────────────────────────────────

def _fmt(v: int) -> str:
    return f"{v:,} ₽".replace(",", " ")

def _calc_trend(prices: list[float]) -> tuple[str, float]:
    n = len(prices)
    if n < 3:
        return "stable", 0.0
    mean_x = (n - 1) / 2
    mean_y = sum(prices) / n
    num = sum((i - mean_x) * (prices[i] - mean_y) for i in range(n))
    den = sum((i - mean_x) ** 2 for i in range(n))
    slope = num / den if den else 0.0
    slope_pct = (slope / mean_y) if mean_y else 0.0
    if slope_pct > _TREND_THRESHOLD:
        return "up", slope_pct
    if slope_pct < -_TREND_THRESHOLD:
        return "down", slope_pct
    return "stable", slope_pct

def _calc_craft_change(current: float, history: list[float]) -> tuple[str, float]:
    """
    Сравнить текущую стоимость крафта с ценой час назад.
    Возвращает (color, pct_change):
      - 'red' если подорожали >3%
      - 'green' если подешевели >3%
      - 'gray' если стабильно (±3%)
    """
    if not history or len(history) < 2:
        return "gray", 0.0
    
    # История хранится от новых к старым, берём 12-й элемент (≈1 час назад, если интервал 5 мин)
    # Если меньше 12 элементов — берём последний доступный
    hour_ago_idx = min(12, len(history) - 1)
    price_hour_ago = history[hour_ago_idx]
    
    if price_hour_ago == 0:
        return "gray", 0.0
    
    pct_change = ((current - price_hour_ago) / price_hour_ago) * 100
    
    if pct_change > 3.0:
        return "red", pct_change
    elif pct_change < -3.0:
        return "green", pct_change
    else:
        return "gray", pct_change

def _fmt_date(dt: datetime | None) -> str:
    if not dt:
        return "нет данных"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone()
    return local.strftime("%d.%m %H:%M")

def _is_stale(dt: datetime | None) -> bool:
    if not dt:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() > 86400


# ─── Спарклайн ────────────────────────────────────────────────────────────────

class SparklineWidget(QWidget):
    def __init__(self, prices: list[float], trend: str, parent=None):
        super().__init__(parent)
        self._prices = prices
        self._trend  = trend
        self.setFixedSize(90, 36)

    def paintEvent(self, event):
        if not self._prices or len(self._prices) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color_map = {
            "up":     QColor(config.SUCCESS_COLOR),
            "down":   QColor(config.DANGER_COLOR),
            "stable": QColor(config.MUTED_COLOR),
        }
        color = color_map.get(self._trend, QColor(config.MUTED_COLOR))
        w, h, pad = 60, 36, 4
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
        pen = QPen(color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(path)
        last = _pt(len(prices) - 1, prices[-1])
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(last, 2.5, 2.5)

        ax, ay = 68, h / 2
        if self._trend == "up":
            pts = QPolygonF([QPointF(ax+7, ay+6), QPointF(ax+14, ay+6), QPointF(ax+10.5, ay-6)])
            p.setBrush(color); p.setPen(Qt.PenStyle.NoPen); p.drawPolygon(pts)
        elif self._trend == "down":
            pts = QPolygonF([QPointF(ax+7, ay-6), QPointF(ax+14, ay-6), QPointF(ax+10.5, ay+6)])
            p.setBrush(color); p.setPen(Qt.PenStyle.NoPen); p.drawPolygon(pts)
        else:
            p.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(ax+4, ay), QPointF(ax+16, ay))
            p.drawLine(QPointF(ax+12, ay-4), QPointF(ax+16, ay))
            p.drawLine(QPointF(ax+12, ay+4), QPointF(ax+16, ay))
        p.end()


# ─── Карточка крафта ──────────────────────────────────────────────────────────

class CraftCard(QFrame):
    update_requested = pyqtSignal(str)  # item_id
    detail_requested  = pyqtSignal(str)  # item_id

    def __init__(self, item_data: dict, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self._hovered  = False
        self._updating = False
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.mouseDoubleClickEvent = lambda e: self.detail_requested.emit(self.item_data['id'])
        self._build()

    def set_updating(self, updating: bool):
        """Показывает/скрывает индикатор обновления."""
        self._updating = updating
        if hasattr(self, "_date_lbl"):
            if updating:
                self._date_lbl.setText("⏳ обновление...")
                self._date_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;background:transparent;")
                if hasattr(self, "_stale_lbl"):
                    self._stale_lbl.hide()
            else:
                self._refresh_date()

    def _refresh_date(self):
        """Обновляет дату и индикатор устаревания."""
        item_id   = self.item_data["id"]
        updated   = cache_mgr.get_updated_at(item_id)
        stale     = _is_stale(updated)
        date_str  = _fmt_date(updated)

        if hasattr(self, "_date_lbl"):
            self._date_lbl.setText(f"обновлено {date_str}")
            color = config.MUTED_COLOR
            self._date_lbl.setStyleSheet(f"color:{color};font-size:10px;background:transparent;")

        if hasattr(self, "_stale_lbl"):
            if stale and updated:
                self._stale_lbl.show()
            else:
                self._stale_lbl.hide()

    def refresh_prices(self, stats: dict):
        """Обновляет цены в карточке без пересоздания."""
        result_amount = self.item_data.get("result_amount", 1)
        craft_cost    = self.item_data.get("craft_cost", 0)

        last_sale = stats.get("last_sale", 0)
        # qt_bridge даёт "market_min", _calc_one сохраняет как "market_min_price"
        mkt_min   = stats.get("market_min", 0) or stats.get("market_min_price", 0)
        mhist     = stats.get("history", [])
        if not last_sale and mhist:
            last_sale = mhist[0].get("per_unit", 0)

        # Итог считается по аукциону
        auction_total = mkt_min * result_amount if mkt_min else 0
        commission    = round(auction_total * AUCTION_FEE)
        revenue       = auction_total - commission
        profit        = revenue - craft_cost

        if hasattr(self, "_mkt_min_lbl") and mkt_min:
            self._mkt_min_lbl.setText(_fmt(mkt_min * result_amount))
            if hasattr(self, "_mkt_min_sub"):
                self._mkt_min_sub.setText(f"= {_fmt(mkt_min)}/шт" if result_amount > 1 else "")

        if hasattr(self, "_last_sale_lbl") and last_sale:
            self._last_sale_lbl.setText(_fmt(last_sale * result_amount))
            if hasattr(self, "_last_sale_sub"):
                self._last_sale_sub.setText(f"= {_fmt(last_sale)}/шт" if result_amount > 1 else "")

        if hasattr(self, "_profit_lbl"):
            if profit > 0:
                self._profit_lbl.setText(f"+{_fmt(profit)}")
                self._profit_lbl.setStyleSheet(
                    f"color:{config.SUCCESS_COLOR};font-size:16px;font-weight:700;background:transparent;"
                )
            elif profit < 0:
                self._profit_lbl.setText(f"−{_fmt(abs(profit))}")
                self._profit_lbl.setStyleSheet(
                    f"color:{config.DANGER_COLOR};font-size:16px;font-weight:700;background:transparent;"
                )
            else:
                self._profit_lbl.setText("= 0 ₽")

        self._refresh_date()

    def enterEvent(self, event):
        self._hovered = True;  self.update();  super().enterEvent(event)
    def leaveEvent(self, event):
        self._hovered = False; self.update();  super().leaveEvent(event)

    def play_appear(self, delay: int = 0):
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        self._appear_effect = effect  # держим ссылку
        self._appear_anim = QPropertyAnimation(effect, b"opacity")
        self._appear_anim.setDuration(280)
        self._appear_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._appear_anim.setStartValue(0.0)
        self._appear_anim.setEndValue(1.0)
        self._appear_anim.finished.connect(self._on_appear_done)
        # Сохраняем timer чтобы он не удалился раньше времени
        self._appear_timer = QTimer(self)
        self._appear_timer.setSingleShot(True)
        self._appear_timer.timeout.connect(self._start_appear_anim)
        self._appear_timer.start(delay)

    def _start_appear_anim(self):
        try:
            if self._appear_anim:
                self._appear_anim.start()
        except RuntimeError:
            pass

    def _on_appear_done(self):
        try:
            self.setGraphicsEffect(None)
            self._appear_effect = None
            self._appear_anim  = None
        except RuntimeError:
            pass

    def paintEvent(self, event):
        fav_mgr = get_favorites_manager()
        is_fav  = fav_mgr.is_favorite(self.item_data["id"], 'craft')
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        radius = 12.0
        bg = QColor(config.SURFACE2_COLOR if self._hovered else config.SURFACE_COLOR)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), radius, radius)
        p.setPen(Qt.PenStyle.NoPen)
        p.fillPath(bg_path, bg)

        if is_fav:
            fc = QColor(config.FAV_BORDER)
            fr, fg, fb = fc.red(), fc.green(), fc.blue()
            for spread, alpha in [(6, 6), (4, 14), (2, 28)]:
                pen = QPen(QColor(fr, fg, fb, alpha), spread * 2)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                gp = QPainterPath()
                gp.addRoundedRect(r.x()+spread, r.y()+spread, r.width()-spread*2, r.height()-spread*2, radius, radius)
                p.drawPath(gp)
            pen = QPen(QColor(fr, fg, fb, 200), 1.8)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            bp = QPainterPath()
            bp.addRoundedRect(0.75, 0.75, r.width()-1.5, r.height()-1.5, radius, radius)
            p.drawPath(bp)

        if self._hovered:
            hc = QColor(config.HOVER_BORDER)
            hr, hg, hb = hc.red(), hc.green(), hc.blue()
            for spread, alpha in [(9, 4), (6, 9), (3.5, 18), (2, 35)]:
                pen = QPen(QColor(hr, hg, hb, alpha), spread * 2)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                gp = QPainterPath()
                gp.addRoundedRect(r.x()+spread, r.y()+spread, r.width()-spread*2, r.height()-spread*2, radius, radius)
                p.drawPath(gp)
            pen = QPen(QColor(hr, hg, hb, 130), 1.5)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            bp = QPainterPath()
            bp.addRoundedRect(0.75, 0.75, r.width()-1.5, r.height()-1.5, radius, radius)
            p.drawPath(bp)

        if not is_fav and not self._hovered:
            pen = QPen(QColor(config.BORDER_COLOR), 1)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            bp = QPainterPath()
            bp.addRoundedRect(0.5, 0.5, r.width()-1, r.height()-1, radius, radius)
            p.drawPath(bp)

        p.end()
        super().paintEvent(event)

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{background:{config.SURFACE2_COLOR};color:{config.TEXT_COLOR};
                    border:1px solid {config.FAINT_COLOR};border-radius:8px;padding:4px;}}
            QMenu::item {{padding:7px 18px;border-radius:5px;}}
            QMenu::item:selected {{background:{config.ACCENT_COLOR};color:#ffffff;}}
            QMenu::separator {{height:1px;background:{config.FAINT_COLOR};margin:3px 8px;}}
        """)

        refresh_act = QAction("↻  Обновить данные", self)
        refresh_act.triggered.connect(lambda: self.update_requested.emit(self.item_data["id"]))
        menu.addAction(refresh_act)

        menu.addSeparator()

        from favorites_manager import get_favorites_manager
        fav = get_favorites_manager()
        item_id = self.item_data["id"]
        if fav.is_favorite(item_id, "craft"):
            fav_act = QAction("★  Убрать из избранного", self)
            fav_act.triggered.connect(lambda: (fav.remove(item_id, "craft"), self.update()))
        else:
            fav_act = QAction("☆  Добавить в избранное", self)
            fav_act.triggered.connect(lambda: (fav.add(item_id, "craft"), self.update()))
        menu.addAction(fav_act)

        details_act = QAction("  Подробнее о предмете", self)
        details_act.triggered.connect(lambda: self.detail_requested.emit(self.item_data["id"]))
        menu.addAction(details_act)

        menu.exec(self.mapToGlobal(pos))

    def _build(self):
        self.setObjectName("craftCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        d             = self.item_data
        result_amount = d.get("result_amount", 1)
        craft_cost    = d["craft_cost"]
        craft_cost_pu = d.get("craft_cost_per_unit", craft_cost)
        market_price  = d["market_price"]
        mkt_after_fee = d["market_price_after_fee"]
        profit        = d["profit"]
        profit_pu     = d.get("profit_per_unit", profit)
        profit_pct    = d["profit_pct"]
        last_sale     = d.get("last_sale", 0)
        mkt_min_price = d.get("market_min_price", 0)
        mkt_trend     = d.get("market_trend", "stable")
        mkt_sparkline = d.get("market_sparkline", [])
        craft_trend   = d.get("craft_trend", "stable")
        craft_sparkline = d.get("craft_sparkline", [])
        is_multi      = result_amount > 1
        no_ing        = d.get("no_ingredient_data", False)
        no_mkt        = d.get("no_market_data", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)


        # ── Верхняя строка ────────────────────────────────────────────────────
        top_row = QHBoxLayout(); top_row.setSpacing(6)

        name_lbl = QLabel(d["name"])
        name_lbl.setStyleSheet(f"color:{config.TEXT_COLOR};font-size:13px;font-weight:600;background:transparent;")
        name_lbl.setMaximumWidth(260)
        top_row.addWidget(name_lbl, stretch=1)
        top_row.addStretch()

        # Категория убрана - показывается только в детальном окне

        layout.addLayout(top_row)

        def _muted(text):
            l = QLabel(text)
            l.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:9px;background:transparent;")
            return l

        # ── Средняя строка: Крафт → Продажа → Итог ───────────────────────────
        mid = QHBoxLayout()
        mid.setSpacing(8)

        # ── Блок 1: Крафт ─────────────────────────────────────────────────────
        cc = QVBoxLayout()
        cc.setSpacing(1)
        cc.addWidget(_muted("Крафт:"))
        if no_ing:
            craft_lbl = QLabel("нет данных")
            craft_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:12px;font-weight:600;background:transparent;")
            cc.addWidget(craft_lbl)
        else:
            # Основная стоимость крафта с цветовой индикацией
            craft_change_color = d.get("craft_change_color", "gray")
            craft_change_pct = d.get("craft_change_pct", 0.0)
            
            # Цвет и иконка в зависимости от изменения
            if craft_change_color == "red":
                color_hex = config.DANGER_COLOR
                icon = "↗"
            elif craft_change_color == "green":
                color_hex = config.SUCCESS_COLOR
                icon = "↘"
            else:
                color_hex = config.MUTED_COLOR
                icon = "—"
            
            craft_lbl = QLabel(f"{icon} {_fmt(craft_cost)}")
            craft_lbl.setStyleSheet(f"color:{color_hex};font-size:12px;font-weight:600;background:transparent;")
            cc.addWidget(craft_lbl)
            
            # Показываем процент изменения если не стабильно
            if abs(craft_change_pct) > 0.1:
                change_lbl = QLabel(f"{craft_change_pct:+.1f}% за час")
                change_lbl.setStyleSheet(f"color:{color_hex};font-size:8px;background:transparent;")
                cc.addWidget(change_lbl)
            
            if is_multi:
                cc.addWidget(_muted(f"= {_fmt(craft_cost_pu)}/шт"))
            if craft_sparkline:
                cc.addWidget(SparklineWidget(craft_sparkline[:15], craft_trend))
        mid.addLayout(cc, stretch=2)

        arr = QLabel("→")
        arr.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:13px;background:transparent;")
        arr.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        mid.addWidget(arr)

        # ── Блок 2: Продажа ───────────────────────────────────────────────────
        mc = QVBoxLayout()
        mc.setSpacing(1)
        mc.addWidget(_muted(f"Продажа ×{result_amount}:" if is_multi else "Продажа:"))

        if no_mkt:
            mc.addWidget(_muted("нет данных"))
        else:
            if mkt_min_price:
                self._mkt_min_lbl = QLabel(_fmt(mkt_min_price * result_amount))
                self._mkt_min_lbl.setStyleSheet(
                    f"color:{config.ACCENT_COLOR};font-size:12px;font-weight:600;background:transparent;"
                )
                mc.addWidget(self._mkt_min_lbl)
                mc.addWidget(_muted("аукцион"))
                if is_multi:
                    self._mkt_min_sub = _muted(f"= {_fmt(mkt_min_price)}/шт")
                    mc.addWidget(self._mkt_min_sub)
                else:
                    self._mkt_min_sub = _muted("")
            else:
                mc.addWidget(_muted("нет лотов"))

            if last_sale:
                mc.addSpacing(2)
                self._last_sale_lbl = QLabel(_fmt(last_sale * result_amount))
                self._last_sale_lbl.setStyleSheet(
                    f"color:{config.TEXT_COLOR};font-size:11px;font-weight:600;background:transparent;"
                )
                mc.addWidget(self._last_sale_lbl)
                mc.addWidget(_muted("последняя"))
                if is_multi:
                    self._last_sale_sub = _muted(f"= {_fmt(last_sale)}/шт")
                    mc.addWidget(self._last_sale_sub)
                else:
                    self._last_sale_sub = _muted("")

        if mkt_sparkline:
            mc.addWidget(SparklineWidget(mkt_sparkline[:15], mkt_trend))
        mid.addLayout(mc, stretch=2)

        arr2 = QLabel("→")
        arr2.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:13px;background:transparent;")
        arr2.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        mid.addWidget(arr2)

        # ── Блок 3: Итог с детализацией ───────────────────────────────────────
        rc = QVBoxLayout()
        rc.setSpacing(1)
        rc.addWidget(_muted("Итог:"))

        if no_mkt or no_ing:
            self._profit_lbl = QLabel("⚠️ нет данных")
            self._profit_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:11px;font-weight:700;background:transparent;")
            rc.addWidget(self._profit_lbl)
        else:
            if profit > 0:
                pc, pt = config.SUCCESS_COLOR, f"+{_fmt(profit)}"
            elif profit == 0:
                pc, pt = config.MUTED_COLOR, "= 0 ₽"
            else:
                pc, pt = config.DANGER_COLOR, f"−{_fmt(abs(profit))}"

            # Прибыль + количество штук (если >1)
            profit_row = QHBoxLayout()
            profit_row.setSpacing(4)
            profit_row.setContentsMargins(0, 0, 0, 0)
            
            self._profit_lbl = QLabel(pt)
            self._profit_lbl.setStyleSheet(f"color:{pc};font-size:13px;font-weight:700;background:transparent;")
            profit_row.addWidget(self._profit_lbl)
            
            if result_amount > 1:
                qty_lbl = QLabel(f"(за {result_amount} шт)")
                qty_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:9px;background:transparent;")
                profit_row.addWidget(qty_lbl)
            
            profit_row.addStretch()
            rc.addLayout(profit_row)

            pct_lbl = QLabel(f"{profit_pct:+.1f}%")
            pct_lbl.setStyleSheet(f"color:{pc};font-size:9px;background:transparent;")
            rc.addWidget(pct_lbl)

            if mkt_min_price:
                rc.addSpacing(3)
                auction_total = mkt_min_price * result_amount
                commission    = round(auction_total * AUCTION_FEE)
                revenue       = auction_total - commission
                for line in [
                    f"аукцион: {_fmt(auction_total)}",
                    f"−5%: −{_fmt(commission)}",
                    f"выручка: {_fmt(revenue)}",
                    f"−крафт: −{_fmt(craft_cost)}",
                ]:
                    lbl = QLabel(line)
                    lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:9px;background:transparent;")
                    rc.addWidget(lbl)

        mid.addLayout(rc, stretch=3)
        layout.addLayout(mid)

        # ── Нижняя строка: ликвидность + дата ────────────────────────────────
        bot = QHBoxLayout(); bot.setSpacing(8)

        per_hour = d.get("sales_data", {}).get("per_hour", 0)
        bot.addWidget(LiquidityWithText(d.get("liquidity", "unknown"), d.get("sales_data", {})))
        bot.addStretch()

        # Дата обновления
        updated   = cache_mgr.get_updated_at(d["id"])
        date_str  = _fmt_date(updated)
        stale     = _is_stale(updated)

        self._date_lbl = QLabel(f"обновлено {date_str}")
        self._date_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;background:transparent;")
        bot.addWidget(self._date_lbl)

        # Оранжевый ! если устарело
        self._stale_lbl = QLabel("!")
        self._stale_lbl.setStyleSheet(
            "color: #BA7517; background: #FAEEDA; border-radius: 9px;"
            "font-size: 11px; font-weight: 600; padding: 1px 5px;"
        )
        self._stale_lbl.setToolTip("Устаревшие данные (более 24 часов)")
        self._stale_lbl.setCursor(QCursor(Qt.CursorShape.WhatsThisCursor))
        if stale and updated:
            self._stale_lbl.show()
        else:
            self._stale_lbl.hide()
        bot.addWidget(self._stale_lbl)

        layout.addLayout(bot)


# ─── Калькулятор ──────────────────────────────────────────────────────────────

class CraftCalculator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("craftCalculator")

        self._all_items:       list = []
        self._filtered_items:  list = []
        self._visible_cards:   list = []
        self._card_index:      dict = {}   # item_id -> CraftCard
        self._batch_size = 50
        self._current_batch = 0

        self._live_prices:  dict = {}
        self._recipes:      dict = {}  # хранится для передачи в detail window
        self._refresh_timer: QTimer | None = None

        # Синхронизация через scapi
        self._sync = PriceSyncManager(parent=self)
        self._sync.price_updated.connect(self._on_price_ready)
        self._sync.sync_finished.connect(self._on_sync_finished)
        self._sync.error.connect(lambda msg: self._set_status(f"⚠ {msg}"))

        self._build()
        self._load_data()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(config.BG_COLOR))
        p.end()
        super().paintEvent(event)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._make_header())
        layout.addWidget(self._make_info_bar())

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("border: none;")
        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(14, 14, 14, 14)
        self._cards_layout.setSpacing(10)
        self._current_row_widget = None
        self._current_row_layout = None
        self._grid_col = 0

        self._scroll.setWidget(self._cards_widget)
        layout.addWidget(self._scroll, stretch=1)

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(f"QFrame{{background:{config.BG_COLOR};border-bottom:1px solid {config.BORDER_COLOR};}}")
        row = QHBoxLayout(header)
        row.setContentsMargins(18, 0, 18, 0)
        row.setSpacing(14)

        title = QLabel("Калькулятор крафта")
        title.setStyleSheet(f"color:{config.TEXT_COLOR};font-size:16px;font-weight:600;")
        row.addWidget(title)
        row.addStretch()

        sort_lbl = QLabel("Сортировка:")
        sort_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:12px;")
        row.addWidget(sort_lbl)

        self._sort_combo = QComboBox()
        self._sort_combo.addItems([
            "По выгоде (₽) ↓", "По выгоде (₽) ↑",
            "По выгоде (%) ↓", "По выгоде (%) ↑",
            "По цене ↓",       "По цене ↑",
            "По названию А-Я", "По названию Я-А",
        ])
        self._sort_combo.setFixedWidth(160)
        self._sort_combo.setStyleSheet(f"""
            QComboBox{{background:{config.INPUT_BG};border:1px solid {config.INPUT_BORDER};
                       border-radius:6px;padding:6px 12px;color:{config.TEXT_COLOR};font-size:12px;}}
            QComboBox:hover{{border-color:{config.ACCENT_COLOR};}}
            QComboBox::drop-down{{border:none;}}
            QComboBox QAbstractItemView{{background:{config.INPUT_BG};border:1px solid {config.ACCENT_COLOR};
                       selection-background-color:{config.ACCENT_COLOR};color:{config.TEXT_COLOR};}}
        """)
        self._sort_combo.currentIndexChanged.connect(self._apply_filters)
        row.addWidget(self._sort_combo)

        self._favorites_btn = QPushButton("⭐ Избранное")
        self._favorites_btn.setCheckable(True)
        self._favorites_btn.setFixedHeight(32)
        _fs = QColor(config.FAV_STAR)
        _r, _g, _b = _fs.red(), _fs.green(), _fs.blue()
        self._favorites_btn.setStyleSheet(f"""
            QPushButton{{background:{config.INPUT_BG};border:1px solid {config.INPUT_BORDER};
                         border-radius:6px;padding:0 16px;color:{config.MUTED_COLOR};font-size:12px;}}
            QPushButton:checked{{background:rgba({_r},{_g},{_b},0.25);color:{config.FAV_STAR};border-color:{config.FAV_STAR};}}
        """)
        self._favorites_btn.clicked.connect(self._apply_filters)
        row.addWidget(self._favorites_btn)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍  Поиск предмета...")
        self._search_box.setFixedWidth(260)
        self._search_box.setStyleSheet(f"""
            QLineEdit{{background:{config.INPUT_BG};border:1px solid {config.INPUT_BORDER};
                       border-radius:6px;padding:8px 12px;color:{config.TEXT_COLOR};font-size:12px;}}
            QLineEdit:focus{{border-color:{config.ACCENT_COLOR};}}
        """)
        self._search_box.textChanged.connect(self._apply_filters)
        row.addWidget(self._search_box)

        self._profit_filter = QPushButton("Только выгодные")
        self._profit_filter.setCheckable(True)
        self._profit_filter.setFixedHeight(32)
        self._profit_filter.setStyleSheet(f"""
            QPushButton{{background:{config.INPUT_BG};border:1px solid {config.INPUT_BORDER};
                         border-radius:6px;padding:0 16px;color:{config.MUTED_COLOR};font-size:12px;}}
            QPushButton:checked{{background:{config.ACCENT_COLOR};color:white;border-color:{config.ACCENT_COLOR};}}
        """)
        self._profit_filter.clicked.connect(self._apply_filters)
        row.addWidget(self._profit_filter)

        self._liquidity_filter = QPushButton("🟢 Высокая ликвидность")
        self._liquidity_filter.setCheckable(True)
        self._liquidity_filter.setFixedHeight(32)
        self._liquidity_filter.setStyleSheet(f"""
            QPushButton{{background:{config.INPUT_BG};border:1px solid {config.INPUT_BORDER};
                         border-radius:6px;padding:0 16px;color:{config.MUTED_COLOR};font-size:12px;}}
            QPushButton:checked{{background:{config.ACCENT_COLOR};color:white;border-color:{config.ACCENT_COLOR};}}
        """)
        self._liquidity_filter.clicked.connect(self._apply_filters)
        row.addWidget(self._liquidity_filter)

        self._refresh_btn = QPushButton("↻ Обновить всё")
        self._refresh_btn.setFixedHeight(32)
        self._refresh_btn.setStyleSheet(f"""
            QPushButton{{background:{config.INPUT_BG};border:1px solid {config.ACCENT_COLOR};
                         border-radius:6px;padding:0 14px;color:{config.ACCENT_COLOR};font-size:12px;}}
            QPushButton:hover{{background:{config.ACCENT_COLOR};color:white;}}
            QPushButton:disabled{{border-color:{config.INPUT_BORDER};color:{config.MUTED_COLOR};}}
        """)
        self._refresh_btn.clicked.connect(self._refresh_all)
        row.addWidget(self._refresh_btn)

        return header

    def _make_info_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(32)
        bar.setStyleSheet(f"QFrame{{background:{config.BG_COLOR};border-bottom:1px solid {config.BORDER_COLOR};}}")
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 0, 14, 0)

        self._count_lbl = QLabel("Загрузка...")
        self._count_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:11px;")
        self._filter_count_lbl = QLabel("")
        self._filter_count_lbl.setStyleSheet(f"color:{config.ACCENT_COLOR};font-size:11px;")
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color:{config.MUTED_COLOR};font-size:10px;font-style:italic;")

        row.addWidget(self._count_lbl)
        row.addWidget(QLabel("  ℹ️  Учтена комиссия 5% в итоге"))
        row.addStretch()
        row.addWidget(self._status_lbl)
        row.addSpacing(12)
        row.addWidget(self._filter_count_lbl)
        return bar

    def _set_status(self, text: str):
        self._status_lbl.setText(text)

    # ── Загрузка данных ───────────────────────────────────────────────────────

    def _load_data(self):
        """Загружает рецепты и заполняет калькулятор из кэша мгновенно."""
        try:
            with open(_RECIPES_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Фильтруем непродаваемые предметы
            self._recipes = {
                k: v for k, v in raw.items() 
                if v.get("craft") and is_tradeable(k)
            }
        except FileNotFoundError:
            self._count_lbl.setText("❌ recipes_calculator.json не найден!")
            return
        except Exception as e:
            self._count_lbl.setText(f"❌ Ошибка загрузки: {e}")
            return

        # Загружаем кэш
        cache_mgr.load()

        if cache_mgr.has_any():
            # Есть кэш — загружаем мгновенно
            self._set_status("из кэша")
            missing = self._load_from_cache()
            self._build_items_from_live()
            self._apply_filters()
            self._start_refresh_timer()

            # Догружаем через API то чего нет в кэше
            if missing:
                self._set_status(f"догружаю {len(missing)} предметов...")
                self._loaded  = [0]
                self._total   = len(missing)
                self._sync.sync_prices(list(missing), include_lots=True, force_refresh=False)
        else:
            # Первый запуск — нужно загрузить с API
            self._set_status("первая загрузка...")
            self._refresh_all()

    def _load_from_cache(self):
        """Заполняет _live_prices из calc_cache.json. Возвращает список ID без кэша."""
        self._live_prices.clear()
        missing_ids: set = set()

        for item_id in self._recipes:
            stats = cache_mgr.get_stats(item_id)
            if stats:
                self._live_prices[item_id] = stats
            else:
                missing_ids.add(item_id)

        for data in self._recipes.values():
            for ing in data["craft"]["ingredients"]:
                iid = ing["id"]
                if iid not in self._live_prices:
                    stats = cache_mgr.get_stats(iid)
                    if stats:
                        self._live_prices[iid] = stats
                    else:
                        missing_ids.add(iid)

        return missing_ids

    # ── Обновление ────────────────────────────────────────────────────────────

    def _refresh_all(self):
        """Принудительное обновление всех предметов через API."""
        if self._refresh_timer:
            self._refresh_timer.stop()

        all_ids: set = set(self._recipes.keys())
        for recipe in self._recipes.values():
            for ing in recipe["craft"]["ingredients"]:
                all_ids.add(ing["id"])

        self._live_prices.clear()
        total = len(all_ids)
        self._loaded = [0]
        self._total  = total
        self._count_lbl.setText(f"Загрузка с API... 0 / {total}")
        self._refresh_btn.setEnabled(False)

        self._sync.sync_prices(list(all_ids), include_lots=True, force_refresh=True)

    def _refresh_single(self, item_id: str):
        """Обновляет один предмет по запросу из ПКМ."""
        card = self._card_index.get(item_id)
        if card:
            card.set_updating(True)

        # Собираем item_id + все его ингредиенты
        ids_to_update = {item_id}
        recipe = self._recipes.get(item_id)
        if recipe:
            for ing in recipe["craft"]["ingredients"]:
                ids_to_update.add(ing["id"])

        # Временный синк для одного предмета
        single_sync = PriceSyncManager(parent=self)

        def _on_ready(iid: str, stats: dict):
            self._live_prices[iid] = stats
            cache_mgr.set(iid, stats)

        def _on_done():
            cache_mgr.save()
            # Пересчитываем только эту карточку
            self._rebuild_single_card(item_id)
            if card:
                card.set_updating(False)
            single_sync.deleteLater()

        single_sync.price_updated.connect(_on_ready)
        single_sync.sync_finished.connect(_on_done)
        single_sync.sync_prices(list(ids_to_update), include_lots=True, force_refresh=True)

    def _rebuild_single_card(self, item_id: str):
        """Пересчитывает и обновляет данные одной карточки."""
        card = self._card_index.get(item_id)
        if not card:
            return

        # Пересчитываем item_data
        new_items = self._calc_items_for([item_id])
        if not new_items:
            return

        new_data = new_items[0]

        # Обновляем item_data карточки
        card.item_data = new_data

        # Обновляем цены в карточке
        stats = self._live_prices.get(item_id, {})
        card.refresh_prices(stats)

    def _on_price_ready(self, item_id: str, stats: dict):
        self._live_prices[item_id] = stats
        cache_mgr.set(item_id, stats)
        if hasattr(self, "_loaded"):
            self._loaded[0] += 1
            self._count_lbl.setText(f"Загрузка с API... {self._loaded[0]} / {self._total}")

    def _on_sync_finished(self):
        cache_mgr.save()
        self._refresh_btn.setEnabled(True)
        self._set_status(f"обновлено {datetime.now().strftime('%H:%M:%S')}")
        self._build_items_from_live()
        self._apply_filters()
        self._start_refresh_timer()

    def _start_refresh_timer(self):
        if self._refresh_timer:
            self._refresh_timer.stop()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(300_000)  # 5 минут
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_all)
        self._refresh_timer.start()

    # ── Расчёт прибыльности ───────────────────────────────────────────────────

    def _calc_items_for(self, item_ids: list[str]) -> list[dict]:
        """Рассчитывает item_data для указанных item_id."""
        result = []
        for item_id in item_ids:
            data = self._recipes.get(item_id)
            if not data:
                continue
            item = self._calc_one(item_id, data)
            if item:
                result.append(item)
        return result

    def _calc_one(self, item_id: str, data: dict) -> dict | None:
        mkt           = self._live_prices.get(item_id, {})
        result_amount = data["craft"].get("result_amount", 1) or 1

        craft_cost  = 0
        no_ing_data = False
        ing_series  = []
        for ing in data["craft"]["ingredients"]:
            s     = self._live_prices.get(ing["id"], {})
            hist  = s.get("history", [])
            price = (hist[0]["per_unit"] if hist and hist[0].get("per_unit") else 0) or s.get("avg", 0)
            if not price:
                no_ing_data = True
            craft_cost += price * ing["amount"]
            ing_series.append([e["per_unit"] * ing["amount"] for e in hist if e.get("per_unit")])

        mhist     = mkt.get("history", [])
        last_sale = mkt.get("last_sale", 0) or (mhist[0].get("per_unit", 0) if mhist else 0)
        mkt_min   = mkt.get("market_min", 0)

        # Цена продажи: приоритет аукциону, fallback на последнюю сделку
        price_pu_for_display = mkt_min or last_sale or mkt.get("avg", 0)

        if not price_pu_for_display and craft_cost == 0:
            return None

        # Итог считается по аукциону (если есть), иначе по последней сделке
        auction_total  = mkt_min * result_amount if mkt_min else 0
        fallback_total = last_sale * result_amount if last_sale else 0
        sale_total     = auction_total or fallback_total

        commission     = round(sale_total * AUCTION_FEE)
        revenue        = sale_total - commission
        profit         = revenue - craft_cost
        profit_pu      = round((revenue / result_amount) - (craft_cost / result_amount)) if result_amount else profit
        profit_pct     = (profit / craft_cost * 100) if craft_cost > 0 else 0
        craft_pu       = round(craft_cost / result_amount) if craft_cost and result_amount else 0
        market_price   = sale_total
        mkt_after_fee  = revenue

        mkt_prices  = [e["per_unit"] for e in mhist if e.get("per_unit")]
        mkt_trend, _ = _calc_trend(mkt_prices)

        non_empty = [s for s in ing_series if s]
        if non_empty and min(len(s) for s in non_empty) >= 3:
            min_len      = min(len(s) for s in non_empty)
            craft_series = [sum(s[i] for s in ing_series if len(s) > i) for i in range(min_len)]
            craft_trend, _ = _calc_trend(craft_series)
            craft_sparkline = craft_series[-30:]
        else:
            craft_trend, craft_sparkline = "stable", []

        per_hour   = mkt.get("per_hour", 0)
        sales_data = {
            "per_5min":  int(per_hour / 12),
            "per_10min": int(per_hour / 6),
            "per_30min": int(per_hour / 2),
            "per_hour":  per_hour,
            "count":     mkt.get("count", 0),
        }
        
        # Расчёт изменения стоимости крафта за час
        craft_change_color, craft_change_pct = _calc_craft_change(craft_cost, craft_sparkline)

        return {
            "id":                            item_id,
            "item_id":                       item_id,
            "name":                          data["name"],
            "category":                      data["craft"].get("category", ""),
            "result_amount":                 result_amount,
            "craft_cost":                    craft_cost,
            "craft_cost_per_unit":           craft_pu,
            "market_price":                  market_price,
            "market_price_after_fee":        mkt_after_fee,
            "profit":                        profit,
            "profit_per_unit":               profit_pu,
            "profit_pct":                    profit_pct,
            "liquidity":                     mkt.get("liquidity", "unknown"),
            "sales_data":                    sales_data,
            "market_trend":                  mkt_trend,
            "market_sparkline":              mkt_prices[-30:],
            "craft_trend":                   craft_trend,
            "craft_sparkline":               craft_sparkline,
            "craft_change_color":            craft_change_color,
            "craft_change_pct":              craft_change_pct,
            "last_sale":                     last_sale,
            "market_min_price":              mkt_min,
            "no_market_data":                not price_pu_for_display,
            "no_ingredient_data":            no_ing_data,
        }

    def _build_items_from_live(self):
        self._all_items = []
        for item_id, data in self._recipes.items():
            item = self._calc_one(item_id, data)
            if item:
                self._all_items.append(item)

    # ── Фильтрация и сортировка ───────────────────────────────────────────────

    def _sort_items(self, items: list) -> list:
        idx  = self._sort_combo.currentIndex()
        keys = [
            lambda x: -x["profit"],
            lambda x:  x["profit"],
            lambda x: -x["profit_pct"],
            lambda x:  x["profit_pct"],
            lambda x: -x["market_price"],
            lambda x:  x["market_price"],
            lambda x:  x["name"],
            lambda x: -ord(x["name"][0]) if x["name"] else 0,
        ]
        return sorted(items, key=keys[idx] if idx < len(keys) else keys[0])

    def _apply_filters(self):
        search      = self._search_box.text().strip().lower()
        only_profit = self._profit_filter.isChecked()
        only_liq    = self._liquidity_filter.isChecked()
        only_fav    = self._favorites_btn.isChecked()
        fav_ids     = set(get_favorites_manager().get_all('craft')) if only_fav else set()

        filtered = [
            item for item in self._all_items
            if (not search       or search in item["name"].lower())
            and (not only_profit or item["profit"] > 0)
            and (not only_liq    or item["liquidity"] == "high")
            and (not only_fav    or item["item_id"] in fav_ids)
        ]
        self._filtered_items = self._sort_items(filtered)
        self._clear_cards()
        self._current_batch = 0
        self._load_next_batch()
        self._update_counts()

    def _clear_cards(self):
        # Удаляем все виджеты включая row-контейнеры и stretch
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._visible_cards.clear()
        self._card_index.clear()
        self._current_row_widget = None
        self._current_row_layout = None
        self._grid_col = 0

    def _load_next_batch(self):
        start = self._current_batch * self._batch_size
        batch = self._filtered_items[start: start + self._batch_size]
        if not batch:
            return
        for i, item in enumerate(batch):
            card = CraftCard(item)
            card.update_requested.connect(self._refresh_single)
            card.detail_requested.connect(self._open_detail)
            self._visible_cards.append(card)
            self._card_index[item["id"]] = card
            # Каждые 2 карточки — новая строка
            if self._grid_col == 0:
                self._current_row_widget = QWidget()
                self._current_row_layout = QHBoxLayout(self._current_row_widget)
                self._current_row_layout.setContentsMargins(0, 0, 0, 0)
                self._current_row_layout.setSpacing(10)
                self._current_row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                self._cards_layout.addWidget(self._current_row_widget)

            self._current_row_layout.addWidget(card, stretch=1)
            card.play_appear(delay=i * 25)
            self._grid_col += 1
            if self._grid_col >= 2:
                self._grid_col = 0
                self._current_row_widget = None
                self._current_row_layout = None
            # Если нечётное кол-во — последняя карточка занимает половину ширины,
            # добавляем пустой растяжитель для баланса
        # Если последняя строка нечётная — добавляем пустой виджет для баланса
        if self._grid_col == 1 and self._current_row_layout:
            spacer = QWidget()
            self._current_row_layout.addWidget(spacer, stretch=1)

        # Убираем старый stretch и добавляем новый в самый конец
        # чтобы карточки прижались к верху
        for i in range(self._cards_layout.count()):
            item = self._cards_layout.itemAt(i)
            if item and item.spacerItem():
                self._cards_layout.removeItem(item)
                break
        self._cards_layout.addStretch(1)

        self._current_batch += 1

    def _on_scroll(self, value):
        sb = self._scroll.verticalScrollBar()
        if value > sb.maximum() * 0.8 and len(self._visible_cards) < len(self._filtered_items):
            self._load_next_batch()

    def _open_detail(self, item_id: str):
        """Открывает окно подробностей для предмета."""
        recipe = self._recipes.get(item_id)
        if not recipe:
            return
        # Берём name из рецептов
        name = recipe.get("name", item_id)
        open_detail_window(
            item_id=item_id,
            item_name=name,
            recipe=recipe,
            live_prices=self._live_prices,
            parent=self,
        )

    def _update_counts(self):
        total      = len(self._all_items)
        profitable = sum(1 for x in self._all_items if x["profit"] > 0)
        filtered   = len(self._filtered_items)
        self._count_lbl.setText(f"Всего: {total}  •  Выгодных: {profitable}")
        self._filter_count_lbl.setText(f"Показано: {filtered}" if filtered != total else "")
