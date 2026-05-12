# ui/star_button.py
"""
Кнопка-звёздочка для избранного
Поддерживает два типа: 'auction' (аукцион) и 'craft' (калькулятор)
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, pyqtProperty, QSize
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen
from favorites_manager import get_favorites_manager
import config


class StarButton(QPushButton):
    """
    Кнопка-звёздочка для добавления в избранное
    Автоматически синхронизируется с FavoritesManager
    """
    
    # Сигнал при клике (отправляет новое состояние: True = в избранном)
    toggled = pyqtSignal(bool)
    
    def __init__(self, item_id: str, fav_type: str = 'auction', parent=None):
        """
        item_id: ID предмета
        fav_type: 'auction' (аукцион) или 'craft' (калькулятор)
        """
        super().__init__(parent)
        self._item_id = item_id
        self._fav_type = fav_type
        self._favorites_mgr = get_favorites_manager()
        self._hover = False
        self._glow_intensity = 0.0
        
        # Загружаем текущее состояние из менеджера
        self._is_favorite = self._favorites_mgr.is_favorite(item_id, fav_type)
        
        # Настройки
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        
        # Анимация свечения
        self._setup_animation()
    
    def _setup_animation(self):
        """Анимация при наведении"""
        self.animation = QPropertyAnimation(self, b"glow_intensity")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
    
    @pyqtProperty(float)
    def glow_intensity(self):
        return self._glow_intensity
    
    @glow_intensity.setter
    def glow_intensity(self, value):
        self._glow_intensity = value
        self.update()
    
    def set_favorite(self, is_favorite: bool):
        """Установить состояние вручную"""
        self._is_favorite = is_favorite
        self.update()
    
    def is_favorite(self) -> bool:
        """Получить текущее состояние"""
        return self._is_favorite
    
    def enterEvent(self, event):
        """При наведении - свечение"""
        self._hover = True
        self.animation.stop()
        self.animation.setStartValue(self._glow_intensity)
        self.animation.setEndValue(1.0)
        self.animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """При уходе - убрать свечение"""
        self._hover = False
        self.animation.stop()
        self.animation.setStartValue(self._glow_intensity)
        self.animation.setEndValue(0.0)
        self.animation.start()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """При клике - переключить и сохранить в FavoritesManager"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Переключаем состояние через FavoritesManager
            new_state = self._favorites_mgr.toggle(self._item_id, self._fav_type)
            self._is_favorite = new_state
            self.toggled.emit(self._is_favorite)
            self.update()
        super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """Рисуем звёздочку"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        size = 10  # Размер звезды
        
        # Цвета — читаем из текущей темы
        fav_c = QColor(config.FAV_STAR)
        muted_c = QColor(config.MUTED_COLOR)
        if self._is_favorite:
            fill_color = fav_c
            outline_color = QColor(fav_c.red(), fav_c.green(), fav_c.blue()).darker(120)
        else:
            fill_color = QColor(muted_c.red(), muted_c.green(), muted_c.blue(), 130)
            outline_color = QColor(muted_c.red(), muted_c.green(), muted_c.blue(), 180)

        # Свечение при наведении
        if self._glow_intensity > 0:
            glow_radius = size + 4 * self._glow_intensity
            painter.setPen(Qt.PenStyle.NoPen)

            glow_color = QColor(fav_c.red(), fav_c.green(), fav_c.blue()) if self._is_favorite else QColor(muted_c.red(), muted_c.green(), muted_c.blue())
            glow_color.setAlphaF(0.3 * self._glow_intensity)
            
            painter.setBrush(glow_color)
            painter.drawEllipse(
                int(center_x - glow_radius),
                int(center_y - glow_radius),
                int(glow_radius * 2),
                int(glow_radius * 2)
            )
        
        # Рисуем звезду (5 лучей)
        path = QPainterPath()
        
        import math
        points = []
        for i in range(5):
            # Внешние точки
            angle = math.pi / 2 + (2 * math.pi * i / 5)
            x = center_x + size * math.cos(angle)
            y = center_y - size * math.sin(angle)
            points.append((x, y))
            
            # Внутренние точки
            angle = math.pi / 2 + (2 * math.pi * i / 5) + (math.pi / 5)
            x = center_x + (size * 0.4) * math.cos(angle)
            y = center_y - (size * 0.4) * math.sin(angle)
            points.append((x, y))
        
        # Строим путь звезды
        path.moveTo(points[0][0], points[0][1])
        for i in range(1, len(points)):
            path.lineTo(points[i][0], points[i][1])
        path.closeSubpath()
        
        # Заливка
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill_color)
        painter.drawPath(path)
        
        # Обводка
        pen = QPen(outline_color, 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        
        painter.end()
