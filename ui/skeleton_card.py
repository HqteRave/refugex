"""
Скелетон-карточка с shimmer-анимацией для отображения во время загрузки категории.
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath
import config


class _ShimmerBar(QWidget):
    """Серый прямоугольник с бегущим светлым бликом."""

    def __init__(self, w: int, h: int, radius: int = 4, parent=None):
        super().__init__(parent)
        self.setFixedSize(w, h)
        self._radius = radius
        self._phase = 0.0

    @pyqtProperty(float)
    def phase(self):
        return self._phase

    @phase.setter
    def phase(self, v: float):
        self._phase = v
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        base = QColor(config.SURFACE2_COLOR)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        p.fillPath(path, base)

        # Блик — линейный градиент бегущий слева направо
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(max(0.0, self._phase - 0.25), QColor(255, 255, 255, 0))
        grad.setColorAt(self._phase, QColor(255, 255, 255, 28))
        grad.setColorAt(min(1.0, self._phase + 0.25), QColor(255, 255, 255, 0))
        p.fillPath(path, grad)
        p.end()


class SkeletonCard(QFrame):
    """Заглушка-карточка, повторяющая размеры ItemCard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("skeletonCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._bars: list[_ShimmerBar] = []
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 10)
        outer.setSpacing(10)

        # Верхняя строка: иконка + правая часть
        top = QHBoxLayout()
        top.setSpacing(14)

        icon_bar = _ShimmerBar(72, 72, radius=10)
        self._bars.append(icon_bar)
        top.addWidget(icon_bar)

        right = QVBoxLayout()
        right.setSpacing(8)

        name_bar = _ShimmerBar(200, 14, radius=4)
        self._bars.append(name_bar)
        right.addWidget(name_bar)

        sub_bar = _ShimmerBar(120, 10, radius=4)
        self._bars.append(sub_bar)
        right.addWidget(sub_bar)

        prices_row = QHBoxLayout()
        prices_row.setSpacing(16)
        for _ in range(3):
            col_bar = _ShimmerBar(70, 32, radius=4)
            self._bars.append(col_bar)
            prices_row.addWidget(col_bar)
        prices_row.addStretch()
        right.addLayout(prices_row)

        liq_bar = _ShimmerBar(90, 12, radius=4)
        self._bars.append(liq_bar)
        right.addWidget(liq_bar)

        top.addLayout(right, stretch=1)
        outer.addLayout(top)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        path = QPainterPath()
        path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 12.0, 12.0)
        p.setPen(Qt.PenStyle.NoPen)
        p.fillPath(path, QColor(config.SURFACE_COLOR))
        p.end()
        super().paintEvent(event)

    def set_phase(self, phase: float):
        for bar in self._bars:
            bar.phase = phase


class SkeletonOverlay:
    """
    Управляет группой SkeletonCard в layout.
    Показывает N заглушек с анимацией, затем убирает.
    """

    def __init__(self, layout, count: int = 8):
        self._layout = layout
        self._cards: list[SkeletonCard] = []
        self._anim: QPropertyAnimation | None = None
        self._phase_val = 0.0
        self._timer: QTimer | None = None

        for _ in range(count):
            card = SkeletonCard()
            self._cards.append(card)
            self._layout.insertWidget(self._layout.count() - 1, card)

        self._start_animation()

    def _start_animation(self):
        self._timer = QTimer()
        self._timer.setInterval(16)  # ~60 fps
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._phase_val = (self._phase_val + 0.012) % 1.25
        phase = min(self._phase_val, 1.0)
        for card in self._cards:
            card.set_phase(phase)

    def remove(self):
        if self._timer:
            self._timer.stop()
            self._timer = None
        for card in self._cards:
            self._layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
