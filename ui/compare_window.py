"""
Окно сравнения предметов (до 3 штук).
Открывается через ПКМ → «Добавить к сравнению» на карточке ItemCard.
"""
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QFont
import config


MAX_COMPARE = 3
_REFRESH_INTERVAL = 60  # секунды между автообновлениями


class _RefreshWorker(QObject):
    """Запрашивает свежие данные для всех предметов в фоновом потоке."""
    finished = pyqtSignal(list)  # [(name, item_id, stats), ...]

    def __init__(self, items: list):
        super().__init__()
        self._items = items

    def run(self):
        from api.stalcraft import get_price_history, calculate_price_stats
        result = []
        for name, item_id, _old_stats in self._items:
            history = get_price_history(item_id)
            stats = calculate_price_stats(history) if history else _old_stats
            result.append((name, item_id, stats))
        self.finished.emit(result)


def _fmt(v: int) -> str:
    return f"{v:,}".replace(",", " ") + " ₽"


class _Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(1)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(config.BORDER_COLOR))
        p.end()


class _StatRow(QWidget):
    """Одна строка сравнения: метка + N значений."""

    def __init__(self, label: str, values: list[str], highlights: list[str] | None = None):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(0)

        lbl = QLabel(label)
        lbl.setFixedWidth(110)
        lbl.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 11px;")
        row.addWidget(lbl)

        for i, val in enumerate(values):
            cell = QLabel(val)
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            color = config.TEXT_COLOR
            if highlights and i < len(highlights):
                color = highlights[i]
            cell.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
            row.addWidget(cell)

            if i < len(values) - 1:
                row.addWidget(_Divider())


class _ItemColumn(QFrame):
    """Колонка одного предмета в окне сравнения."""

    def __init__(self, name: str, item_id: str, stats: dict | None, parent=None):
        super().__init__(parent)
        self.setObjectName("compareCol")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        name_lbl = QLabel(name)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(
            f"color: {config.TEXT_COLOR}; font-size: 13px; font-weight: 700;"
        )
        layout.addWidget(name_lbl)

        id_lbl = QLabel(item_id)
        id_lbl.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 10px;")
        layout.addWidget(id_lbl)

        layout.addSpacing(6)

        if stats and stats.get("count", 0) > 0:
            for label, val in [
                ("Мин. цена", _fmt(stats["min"])),
                ("Сред. цена", _fmt(stats["avg"])),
                ("Макс. цена", _fmt(stats["max"])),
                ("Продаж всего", str(stats["count"])),
                ("За час", str(stats.get("per_hour", 0))),
                ("За 24 ч", str(stats.get("per_day", 0))),
            ]:
                row = QHBoxLayout()
                row.setSpacing(6)
                lbl = QLabel(label + ":")
                lbl.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 11px;")
                lbl.setFixedWidth(95)
                val_lbl = QLabel(val)
                val_lbl.setStyleSheet(
                    f"color: {config.TEXT_COLOR}; font-size: 12px; font-weight: 600;"
                )
                row.addWidget(lbl)
                row.addWidget(val_lbl)
                row.addStretch()
                layout.addLayout(row)

            liq_map = {
                "high": ("Высокая", config.SUCCESS_COLOR),
                "medium": ("Средняя", config.WARNING_COLOR),
                "low": ("Низкая", config.DANGER_COLOR),
                "unknown": ("Нет данных", config.MUTED_COLOR),
            }
            liq_text, liq_color = liq_map.get(
                stats.get("liquidity", "unknown"),
                ("Нет данных", config.MUTED_COLOR),
            )
            liq_row = QHBoxLayout()
            liq_lbl = QLabel("Ликвидность:")
            liq_lbl.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 11px;")
            liq_lbl.setFixedWidth(95)
            liq_val = QLabel(liq_text)
            liq_val.setStyleSheet(f"color: {liq_color}; font-size: 12px; font-weight: 700;")
            liq_row.addWidget(liq_lbl)
            liq_row.addWidget(liq_val)
            liq_row.addStretch()
            layout.addLayout(liq_row)
        else:
            no_data = QLabel("Нет данных о ценах")
            no_data.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 12px;")
            layout.addWidget(no_data)

        layout.addStretch()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8.0, 8.0)
        p.setPen(QColor(config.BORDER_COLOR))
        p.setBrush(QColor(config.SURFACE_COLOR))
        p.drawPath(path)
        p.end()


class CompareWindow(QDialog):
    """Диалог сравнения предметов. Глобальный синглтон через get()."""

    _instance: "CompareWindow | None" = None
    # [(name, item_id, stats)]
    _items: list = []

    @classmethod
    def get(cls, parent=None) -> "CompareWindow":
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = CompareWindow(parent)
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Сравнение предметов")
        self.setMinimumSize(600, 400)
        self.resize(900, 500)
        self._refreshing = False
        self._seconds_since_refresh = 0

        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(1000)
        self._auto_timer.timeout.connect(self._on_tick)
        self._auto_timer.start()

        self._apply_stylesheet()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Заголовок
        title_row = QHBoxLayout()
        title = QLabel("⚖ Сравнение предметов")
        title.setStyleSheet(
            f"color: {config.TEXT_COLOR}; font-size: 16px; font-weight: 700;"
        )

        self._refresh_btn = QPushButton("↻ Обновить")
        self._refresh_btn.setFixedWidth(100)
        self._refresh_btn.clicked.connect(self._manual_refresh)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 10px;")

        clear_btn = QPushButton("Очистить")
        clear_btn.setFixedWidth(90)
        clear_btn.clicked.connect(self._clear_all)

        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self._status_lbl)
        title_row.addSpacing(8)
        title_row.addWidget(self._refresh_btn)
        title_row.addSpacing(4)
        title_row.addWidget(clear_btn)
        layout.addLayout(title_row)

        hint = QLabel(f"Добавьте до {MAX_COMPARE} предметов через ПКМ → «Добавить к сравнению»")
        hint.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 11px;")
        layout.addWidget(hint)

        # Область колонок
        self._cols_widget = QWidget()
        self._cols_layout = QHBoxLayout(self._cols_widget)
        self._cols_layout.setContentsMargins(0, 0, 0, 0)
        self._cols_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll.setWidget(self._cols_widget)
        layout.addWidget(scroll, stretch=1)

        self._refresh_columns()

    def _refresh_columns(self):
        # Очищаем колонки
        while self._cols_layout.count():
            item = self._cols_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not CompareWindow._items:
            placeholder = QLabel("Нет предметов для сравнения.\nПКМ по карточке → «Добавить к сравнению»")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(f"color: {config.MUTED_COLOR}; font-size: 13px;")
            self._cols_layout.addWidget(placeholder)
            return

        for name, item_id, stats in CompareWindow._items:
            wrapper = QWidget()
            wrapper.setMinimumWidth(220)
            wl = QVBoxLayout(wrapper)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(4)

            # Кнопка удаления конкретного предмета
            remove_btn = QPushButton("✕ Убрать")
            remove_btn.setFixedHeight(24)
            remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {config.MUTED_COLOR};
                    border: 1px solid {config.BORDER_COLOR};
                    border-radius: 4px;
                    font-size: 10px;
                    padding: 0 8px;
                }}
                QPushButton:hover {{
                    color: #ffffff;
                    background: {config.DANGER_COLOR};
                    border-color: {config.DANGER_COLOR};
                }}
            """)
            remove_btn.clicked.connect(lambda _, iid=item_id: self._remove_item(iid))
            wl.addWidget(remove_btn)

            col = _ItemColumn(name, item_id, stats)
            wl.addWidget(col)
            self._cols_layout.addWidget(wrapper)

        self._cols_layout.addStretch()

    def _on_tick(self):
        """Вызывается каждую секунду: обновляет счётчик и запускает автообновление."""
        if not CompareWindow._items:
            self._status_lbl.setText("")
            return
        self._seconds_since_refresh += 1
        remaining = _REFRESH_INTERVAL - self._seconds_since_refresh
        if remaining > 0:
            self._status_lbl.setText(f"Обновление через {remaining} с")
        else:
            self._start_refresh()

    def _manual_refresh(self):
        if not self._refreshing and CompareWindow._items:
            self._seconds_since_refresh = 0
            self._start_refresh()

    def _start_refresh(self):
        if self._refreshing or not CompareWindow._items:
            return
        self._refreshing = True
        self._refresh_btn.setEnabled(False)
        self._status_lbl.setText("Обновление...")

        worker = _RefreshWorker(list(CompareWindow._items))
        worker.finished.connect(self._on_refresh_done)
        t = threading.Thread(target=worker.run, daemon=True)
        t.start()
        self._worker = worker  # держим ссылку чтобы сигнал дошёл

    def _on_refresh_done(self, new_items: list):
        CompareWindow._items = new_items
        self._refreshing = False
        self._seconds_since_refresh = 0
        self._refresh_btn.setEnabled(True)
        self._status_lbl.setText(f"Обновлено только что")
        self._refresh_columns()

    def _remove_item(self, item_id: str):
        CompareWindow._items = [(n, i, s) for n, i, s in CompareWindow._items if i != item_id]
        self._refresh_columns()

    def _clear_all(self):
        CompareWindow._items.clear()
        self._refresh_columns()

    def closeEvent(self, event):
        self._auto_timer.stop()
        CompareWindow._items.clear()
        super().closeEvent(event)

    def _apply_stylesheet(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: {config.BG_COLOR};
            }}
            QPushButton {{
                background: {config.SURFACE2_COLOR};
                color: {config.TEXT_COLOR};
                border: 1px solid {config.BORDER_COLOR};
                border-radius: 6px;
                padding: 5px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {config.ACCENT_COLOR};
                color: #ffffff;
                border-color: {config.ACCENT_COLOR};
            }}
        """)

    def refresh_theme(self):
        """Вызывается при смене темы в главном окне."""
        self._apply_stylesheet()
        self._refresh_columns()

    @classmethod
    def add_item(cls, name: str, item_id: str, stats: dict | None, parent=None):
        """Добавляет предмет в сравнение и открывает окно."""
        # Убираем дубликат если уже есть
        cls._items = [(n, i, s) for n, i, s in cls._items if i != item_id]
        if len(cls._items) >= MAX_COMPARE:
            cls._items.pop(0)
        cls._items.append((name, item_id, stats))

        win = cls.get(parent)
        win._refresh_columns()
        win.show()
        win.raise_()
        win.activateWindow()
        # Сразу обновляем данные при добавлении предмета
        win._seconds_since_refresh = 0
        QTimer.singleShot(300, win._start_refresh)
