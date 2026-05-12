# ui/liquidity_indicator.py
"""
Индикатор ликвидности (БЕЗ текста рядом)
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QPoint, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath
import config


class NeonTooltipWidget(QWidget):
    """
    Тултип в стиле приложения
    """
    
    def __init__(self, liquidity: str, sales_data: dict, parent=None):
        super().__init__(parent)
        self.liquidity = liquidity
        self.sales_data = sales_data
        self._parent_indicator = parent
        
        # Цвета
        self.colors = {
            'high': QColor(74, 222, 128),
            'medium': QColor(250, 204, 21),
            'low': QColor(248, 113, 113),
            'unknown': QColor(156, 163, 175)
        }
        self.color = self.colors.get(liquidity, self.colors['unknown'])
        
        # Настройки
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        
        # Данные
        self.per_5min = sales_data.get('per_5min', 0)
        self.per_10min = sales_data.get('per_10min', 0)
        self.per_30min = sales_data.get('per_30min', 0)
        self.per_hour = sales_data.get('per_hour', 0)
        self.count = sales_data.get('count', 0)
        
        self.liq_names = {
            'high': 'Высокая',
            'medium': 'Средняя',
            'low': 'Низкая',
            'unknown': 'Неизвестна'
        }
        
        self._calculate_size()
    
    def _calculate_size(self):
        """Вычисляем размер тултипа"""
        self.lines = [
            f"Ликвидность: {self.liq_names.get(self.liquidity, 'Неизвестна')}",
            f"Последние продажи по предмету",
            "",
            f"За 5 мин:  {self.per_5min} прод.",
            f"За 10 мин: {self.per_10min} прод.",
            f"За 30 мин: {self.per_30min} прод.",
            f"За 1 час:  {self.per_hour} прод.",
            "",
            f"Диапазон данных: {self.count} продаж"
        ]

        from PyQt6.QtGui import QFontMetrics
        max_width = 0
        for i, line in enumerate(self.lines):
            f = QFont("Segoe UI", 9 if i != 1 else 8)
            f.setBold(i == 0)
            max_width = max(max_width, QFontMetrics(f).horizontalAdvance(line))

        tooltip_w = max_width + 24
        tooltip_h = len(self.lines) * 16 + 12

        self.setFixedSize(tooltip_w, tooltip_h)
    
    def leaveEvent(self, event):
        """При уходе мыши - скрываем тултип"""
        self.hide()
        self.deleteLater()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        """Рисуем тултип"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(config.POPUP_BG))

        path = QPainterPath()
        path.addRoundedRect(rect, 6.0, 6.0)
        painter.drawPath(path)

        painter.setPen(QPen(QColor(config.BORDER_COLOR), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        y_offset = 14
        for i, line in enumerate(self.lines):
            if i == 0:
                # Первая строка — цвет ликвидности, жирный
                font = QFont("Segoe UI", 9)
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(self.color)
            elif i == 1:
                # Подзаголовок — muted
                font = QFont("Segoe UI", 8)
                font.setBold(False)
                painter.setFont(font)
                painter.setPen(QColor(config.MUTED_COLOR))
            elif line == "":
                y_offset += 16
                continue
            else:
                # Данные — обычный текст, чуть жирнее для читаемости
                font = QFont("Segoe UI", 9)
                font.setBold(False)
                painter.setFont(font)
                painter.setPen(QColor(config.TEXT_COLOR))

            painter.drawText(8, y_offset, line)
            y_offset += 16

        painter.end()


class StandardLiquidityIndicator(QWidget):
    """
    СТАНДАРТНЫЙ индикатор ликвидности (как в ItemCard)
    """
    
    ICON_COLORS = {
        'high': QColor(0, 220, 120),
        'medium': QColor(255, 200, 0),
        'low': QColor(255, 70, 100),
        'unknown': None
    }
    
    def __init__(self, liquidity: str, sales_data: dict, parent=None):
        super().__init__(parent)
        self.liquidity = liquidity
        self.sales_data = sales_data
        self._tooltip_widget = None
        self._is_hovered = False
        
        self.icon_color = self.ICON_COLORS.get(liquidity)
        
        self.setFixedSize(20, 20)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def enterEvent(self, event):
        """При наведении"""
        self._is_hovered = True
        QTimer.singleShot(200, self._show_custom_tooltip)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """При уходе"""
        self._is_hovered = False
        self._hide_tooltip()
        super().leaveEvent(event)
    
    def _hide_tooltip(self):
        """Скрыть тултип"""
        if self._tooltip_widget:
            self._tooltip_widget.hide()
            self._tooltip_widget.deleteLater()
            self._tooltip_widget = None
    
    def _show_custom_tooltip(self):
        """Показываем тултип"""
        if not self._is_hovered or self._tooltip_widget:
            return
        
        self._tooltip_widget = NeonTooltipWidget(self.liquidity, self.sales_data, self)
        
        global_pos = self.mapToGlobal(QPoint(self.width() + 10, -20))
        
        # Проверка границ экрана
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            tooltip_width = self._tooltip_widget.width()
            tooltip_height = self._tooltip_widget.height()
            
            if global_pos.x() + tooltip_width > screen_geometry.right():
                global_pos = self.mapToGlobal(QPoint(-tooltip_width - 10, -20))
            
            if global_pos.y() + tooltip_height > screen_geometry.bottom():
                global_pos.setY(screen_geometry.bottom() - tooltip_height - 10)
            
            if global_pos.y() < screen_geometry.top():
                global_pos.setY(screen_geometry.top() + 10)
            
            if global_pos.x() < screen_geometry.left():
                global_pos.setX(screen_geometry.right() - tooltip_width - 10)
        
        self._tooltip_widget.move(global_pos)
        self._tooltip_widget.show()
    
    def paintEvent(self, event):
        """Рисуем СТАНДАРТНЫЙ круг как в ItemCard"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        r = self.rect()
        cy = r.height() // 2
        cr = 7
        cx = r.width() // 2
        
        if self.icon_color:
            fill = QColor(self.icon_color)
            fill.setAlpha(210)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawEllipse(cx - cr, cy - cr, cr * 2, cr * 2)
            
            painter.setBrush(QColor(255, 255, 255, 55))
            painter.drawEllipse(cx - cr + 3, cy - cr + 3, cr - 2, cr - 2)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(80, 80, 105, 180))
            painter.drawEllipse(cx - cr, cy - cr, cr * 2, cr * 2)
            
            qfont = QFont("Segoe UI", 8)
            qfont.setBold(True)
            painter.setFont(qfont)
            painter.setPen(QColor(170, 170, 195))
            painter.drawText(
                cx - cr, cy - cr, cr * 2, cr * 2, 
                Qt.AlignmentFlag.AlignCenter, "?"
            )
        
        painter.end()


class LiquidityWithText(QWidget):
    """
    ПРОСТО индикатор БЕЗ текста (текст убран!)
    """
    
    def __init__(self, liquidity: str, sales_data: dict, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ТОЛЬКО индикатор, БЕЗ текста!
        self.indicator = StandardLiquidityIndicator(liquidity, sales_data)
        layout.addWidget(self.indicator)
