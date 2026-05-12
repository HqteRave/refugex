# ui/craft_filter.py  [v3.0]
import sys
import os

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QSpinBox, QWidget,
    QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QPoint
from craft_levels import SKILL_NAMES
import config


def _palette():
    """Возвращает палитру из текущей темы."""
    return {
        "ACCENT":        config.ACCENT_COLOR,
        "ACCENT_HOVER":  config.ACCENT_COLOR,
        "BORDER":        config.INPUT_BORDER,
        "BORDER_SOFT":   config.BORDER_COLOR,
        "TEXT":          config.TEXT_COLOR,
        "TEXT_MUTED":    config.MUTED_COLOR,
        "TEXT_SOFT":     config.MUTED_COLOR,
        "PANEL":         config.SURFACE_COLOR,
        "PANEL_2":       config.SURFACE_COLOR,
        "PANEL_3":       config.SURFACE2_COLOR,
        "DANGER":        config.DANGER_COLOR,
    }


_SKILL_ICONS = {
    "ammo":        "🔫",
    "pyro":        "💥",
    "armor":       "🛡",
    "engineering": "⚙️",
    "cooking":     "🍳",
    "brewing":     "🍺",
    "medicine":    "💊",
    "materials":   "⚗️",
}


# ── Хелперы ───────────────────────────────────────────────────────────────


def _chip(active: bool, *, subtle: bool = False) -> str:
    p = _palette()
    if active:
        return f"""
            QPushButton {{
                background: rgba(0,0,0,0.1);
                color: {p['TEXT']};
                border: 1px solid {p['ACCENT']};
                border-radius: 9px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {p['ACCENT_HOVER']};
            }}
        """
    bg = p["PANEL_3"] if subtle else "transparent"
    return f"""
        QPushButton {{
            background: {bg};
            color: {p['TEXT_MUTED']};
            border: 1px solid {p['BORDER']};
            border-radius: 9px;
            padding: 6px 12px;
            font-size: 11px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background: {p['PANEL_3']};
            color: {p['TEXT']};
            border: 1px solid {p['BORDER_SOFT']};
        }}
    """


def _mode_chip(active: bool) -> str:
    p = _palette()
    if active:
        return f"""
            QPushButton {{
                background: {p['PANEL_3']};
                color: {p['TEXT']};
                border: 1px solid {p['ACCENT']};
                border-radius: 10px;
                padding: 7px 14px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                border-color: {p['ACCENT_HOVER']};
            }}
        """
    return f"""
        QPushButton {{
            background: {p['PANEL_3']};
            color: {p['TEXT_MUTED']};
            border: 1px solid {p['BORDER']};
            border-radius: 10px;
            padding: 7px 14px;
            font-size: 11px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: {p['PANEL_2']};
            color: {p['TEXT']};
            border: 1px solid {p['BORDER_SOFT']};
        }}
    """


def _sep_h() -> QFrame:
    p = _palette()
    s = QFrame()
    s.setFrameShape(QFrame.Shape.HLine)
    s.setStyleSheet(f"background: {p['BORDER']}; max-height: 1px; border: none;")
    return s


def _section_label(text: str) -> QLabel:
    p = _palette()
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {p['TEXT_SOFT']}; font-size: 10px; font-weight: 700; "
        f"letter-spacing: 1px; text-transform: uppercase; background: transparent;"
    )
    return lbl


def _spin_style() -> str:
    p = _palette()
    return f"""
        QSpinBox#filterSpin {{
            background: {p['PANEL_3']};
            color: {p['TEXT']};
            border: 1px solid {p['BORDER']};
            border-radius: 8px;
            padding: 6px 8px;
            font-size: 11px;
            min-height: 30px;
        }}
        QSpinBox#filterSpin:hover {{
            border-color: {p['BORDER_SOFT']};
        }}
        QSpinBox#filterSpin:focus {{
            border-color: {p['ACCENT']};
            background: {p['PANEL_2']};
        }}
        QSpinBox#filterSpin::up-button,
        QSpinBox#filterSpin::down-button {{
            width: 16px;
            border: none;
            background: transparent;
        }}
    """


def _mini_step_btn() -> str:
    p = _palette()
    return f"""
        QPushButton {{
            background: {p['PANEL_3']};
            color: {p['TEXT']};
            border: 1px solid {p['BORDER_SOFT']};
            border-radius: 9px;
            min-width: 34px;
            min-height: 34px;
            max-width: 34px;
            max-height: 34px;
            font-size: 16px;
            font-weight: 700;
            padding: 0px;
        }}
        QPushButton:hover {{
            background: {p['PANEL_2']};
            border-color: {p['ACCENT']};
            color: {p['TEXT']};
        }}
    """


def _action_btn(primary: bool = False, danger: bool = False) -> str:
    p = _palette()
    if danger:
        return f"""
            QPushButton {{
                background: transparent;
                color: {p['DANGER']};
                border: 1px solid {config.DANGER_COLOR}38;
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {config.DANGER_COLOR}15;
                border-color: {p['DANGER']};
            }}
        """
    if primary:
        return f"""
            QPushButton {{
                background: {p['ACCENT']};
                color: {config.BG_COLOR};
                border: 1px solid {p['ACCENT']};
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {p['ACCENT_HOVER']};
            }}
        """
    return f"""
        QPushButton {{
            background: {p['PANEL_3']};
            color: {p['TEXT']};
            border: 1px solid {p['BORDER']};
            border-radius: 10px;
            padding: 8px 14px;
            font-size: 11px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: {p['PANEL_2']};
            border-color: {p['BORDER_SOFT']};
        }}
    """


# ── Попап ─────────────────────────────────────────────────────────────────


class FilterPopup(QFrame):
    """v3.0 — современный единый стиль, тот же функционал."""

    def __init__(self, on_change, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("filterPopup")

        self._on_change = on_change
        self._mode = "all"
        self._active_skills: set = set()
        self._active_levels: set = set()
        self._spins:       dict[str, QSpinBox]    = {}
        self._mode_btns:   dict[str, QPushButton] = {}
        self._skill_btns:  dict[str, QPushButton] = {}
        self._level_btns:  dict[int, QPushButton] = {}

        self._build()
        self._apply_popup_style()

    # ── Построение ────────────────────────────────────────────────────────

    def _apply_popup_style(self):
        p = _palette()
        self.setStyleSheet(f"""
            QFrame#filterPopup {{
                background: {p['PANEL']};
                border: 1px solid {p['BORDER_SOFT']};
                border-radius: 16px;
            }}
        """)
        if hasattr(self, '_scroll'):
            self._scroll.setStyleSheet(f"""
                QScrollArea {{ border: none; background: transparent; }}
                QScrollBar:vertical {{
                    background: {p['PANEL']}; width: 8px; border-radius: 4px;
                    margin: 8px 4px 8px 0;
                }}
                QScrollBar::handle:vertical {{
                    background: {p['BORDER_SOFT']}; border-radius: 4px; min-height: 28px;
                }}
                QScrollBar::handle:vertical:hover {{ background: {p['ACCENT']}; }}
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {{ height: 0px; }}
            """)
        if hasattr(self, '_title_lbl'):
            self._title_lbl.setStyleSheet(
                f"font-size: 13px; font-weight: 700; color: {p['TEXT']}; background: transparent;"
            )
        if hasattr(self, '_subtitle_lbl'):
            self._subtitle_lbl.setStyleSheet(
                f"font-size: 10px; color: {p['TEXT_SOFT']}; background: transparent;"
            )
        if hasattr(self, '_hint_lbl'):
            self._hint_lbl.setStyleSheet(
                f"color: {p['TEXT_SOFT']}; font-size: 10px; background: transparent;"
            )
        if hasattr(self, '_levels_wrap'):
            self._levels_wrap.setStyleSheet(f"""
                QFrame {{
                    background: {p['PANEL_2']};
                    border: 1px solid {p['BORDER_SOFT']};
                    border-radius: 14px;
                }}
            """)
        for lbl in getattr(self, '_skill_name_lbls', []):
            lbl.setStyleSheet(
                f"color: {p['TEXT']}; font-size: 12px; font-weight: 500; background: transparent;"
            )
        for lbl in getattr(self, '_dots_lbls', []):
            lbl.setStyleSheet(
                f"color: {p['TEXT_SOFT']}; font-size: 13px; font-weight: 600; letter-spacing: 1px; background: transparent;"
            )
        for btn in getattr(self, '_step_btns', []):
            btn.setStyleSheet(_mini_step_btn())
        for spin in self._spins.values():
            spin.setStyleSheet(_spin_style())

    def refresh_style(self):
        self._apply_popup_style()
        self._refresh_mode_btns()
        self._refresh_skill_btns()
        self._refresh_level_btns()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(self._scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        root = QVBoxLayout(content)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # Header card
        head = QFrame()
        head.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                border-radius: 0px;
            }
        """)
        head_l = QVBoxLayout(head)
        head_l.setContentsMargins(14, 12, 14, 12)
        head_l.setSpacing(4)

        self._title_lbl = QLabel("⚙ Фильтры крафта")
        self._title_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: #e0e0e0; background: transparent;"
        )
        self._subtitle_lbl = QLabel("Фильтр для удобства поиска!")
        self._subtitle_lbl.setStyleSheet(
            f"font-size: 10px; color: #666680; background: transparent;"
        )
        self._subtitle_lbl.setWordWrap(True)
        head_l.addWidget(self._title_lbl)
        head_l.addWidget(self._subtitle_lbl)
        root.addWidget(head)

        # Режим показа
        root.addWidget(_section_label("ПОКАЗАТЬ"))
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        for text, key in [
            ("Все", "all"),
            ("Только крафт", "craft"),
            ("Без крафта", "nocraft"),
            ("🎯 Мои навыки", "mine"),
        ]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet(_mode_chip(key == self._mode))
            btn.clicked.connect(lambda _, k=key: self._set_mode(k))
            self._mode_btns[key] = btn
            mode_row.addWidget(btn)
        mode_row.addStretch()
        root.addLayout(mode_row)

        root.addWidget(_sep_h())

        # Навыки
        root.addWidget(_section_label("НАВЫК КРАФТА"))
        skill_grid = QGridLayout()
        skill_grid.setSpacing(8)
        cols = 3
        for i, key in enumerate(SKILL_NAMES.keys()):
            icon = _SKILL_ICONS.get(key, "")
            name = SKILL_NAMES[key]
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumHeight(34)
            btn.setStyleSheet(_chip(False))
            btn.clicked.connect(lambda _, k=key: self._toggle_skill(k))
            self._skill_btns[key] = btn
            skill_grid.addWidget(btn, i // cols, i % cols)
        root.addLayout(skill_grid)

        root.addWidget(_sep_h())

        # Уровни
        root.addWidget(_section_label("УРОВЕНЬ КРАФТА"))
        lvl_row = QHBoxLayout()
        lvl_row.setSpacing(8)
        for lvl in range(1, 6):
            dots = "●" * lvl + "○" * (5 - lvl)
            btn = QPushButton(f"ур.{lvl}  {dots}")
            btn.setCheckable(True)
            btn.setMinimumHeight(34)
            btn.setStyleSheet(_chip(False, subtle=True))
            btn.clicked.connect(lambda _, l=lvl: self._toggle_level(l))
            self._level_btns[lvl] = btn
            lvl_row.addWidget(btn)
        lvl_row.addStretch()
        root.addLayout(lvl_row)

        root.addWidget(_sep_h())

        # Мои уровни
        root.addWidget(_section_label("МОИ УРОВНИ НАВЫКОВ"))
        self._hint_lbl = QLabel("Режим «Мои навыки» показывает только то, что ты уже можешь крафтить.")
        self._hint_lbl.setStyleSheet("color: #666680; font-size: 10px; background: transparent;")
        self._hint_lbl.setWordWrap(True)
        root.addWidget(self._hint_lbl)

        self._levels_wrap = QFrame()
        self._levels_wrap.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 1px solid #1e1e40;
                border-radius: 14px;
            }
        """)
        levels_layout = QVBoxLayout(self._levels_wrap)
        levels_layout.setContentsMargins(12, 12, 12, 12)
        levels_layout.setSpacing(8)

        self._skill_name_lbls = []
        self._dots_lbls = []
        self._step_btns = []

        for key, name in SKILL_NAMES.items():
            icon = _SKILL_ICONS.get(key, "")

            row = QHBoxLayout()
            row.setSpacing(8)

            lbl = QLabel(f"{icon} {name}")
            lbl.setStyleSheet(
                "color: #e0e0e0; font-size: 12px; font-weight: 500; background: transparent;"
            )
            lbl.setFixedWidth(150)
            self._skill_name_lbls.append(lbl)
            row.addWidget(lbl)

            down_btn = QPushButton("−")
            down_btn.setFixedSize(34, 34)
            down_btn.setStyleSheet(_mini_step_btn())
            self._step_btns.append(down_btn)

            spin = QSpinBox()
            spin.setRange(0, 5)
            spin.setValue(0)
            spin.setFixedWidth(60)
            spin.setObjectName("filterSpin")
            spin.setSpecialValueText("—")
            spin.setStyleSheet(_spin_style())
            self._spins[key] = spin

            up_btn = QPushButton("+")
            up_btn.setFixedSize(34, 34)
            up_btn.setStyleSheet(_mini_step_btn())
            self._step_btns.append(up_btn)

            dots_lbl = QLabel("○ ○ ○ ○ ○")
            dots_lbl.setStyleSheet(
                "color: #666680; font-size: 13px; font-weight: 600; letter-spacing: 1px; background: transparent;"
            )
            dots_lbl.setFixedWidth(96)
            dots_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._dots_lbls.append(dots_lbl)

            down_btn.clicked.connect(lambda _, s=spin: s.setValue(max(0, s.value() - 1)))
            up_btn.clicked.connect(lambda _, s=spin: s.setValue(min(5, s.value() + 1)))

            spin.valueChanged.connect(self._emit)
            def _make_dots_updater(dl):
                def _update(v):
                    p = _palette()
                    dl.setText(
                        f'<font color="{p["ACCENT"]}">{"● " * v}</font>'
                        f'<font color="{p["TEXT_SOFT"]}">{"○ " * (5 - v)}</font>'
                    )
                return _update
            spin.valueChanged.connect(_make_dots_updater(dots_lbl))

            row.addWidget(down_btn)
            row.addWidget(spin)
            row.addWidget(up_btn)
            row.addWidget(dots_lbl)
            row.addStretch()
            levels_layout.addLayout(row)

        root.addWidget(self._levels_wrap)

        root.addWidget(_sep_h())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        reset_btn = QPushButton("✕ Сбросить")
        reset_btn.setObjectName("filterResetBtn")
        reset_btn.setStyleSheet(_action_btn(danger=True))
        reset_btn.clicked.connect(self.reset)

        close_btn = QPushButton("Готово")
        close_btn.setObjectName("filterApplyBtn")
        close_btn.setStyleSheet(_action_btn(primary=True))
        close_btn.clicked.connect(self.hide)

        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        root.addStretch()
        self._scroll.setWidget(content)

    # ── Логика ────────────────────────────────────────────────────────────

    def _set_mode(self, mode: str):
        self._mode = mode
        if mode == "nocraft":
            self._active_skills.clear()
            self._active_levels.clear()
            self._refresh_skill_btns()
            self._refresh_level_btns()
        self._refresh_mode_btns()
        self._emit()

    def _toggle_skill(self, key: str):
        if key in self._active_skills:
            self._active_skills.discard(key)
        else:
            self._active_skills.add(key)
        self._refresh_skill_btns()
        if self._active_skills and self._mode not in ("craft", "mine"):
            self._set_mode("craft")
            return
        self._emit()

    def _toggle_level(self, lvl: int):
        if lvl in self._active_levels:
            self._active_levels.discard(lvl)
        else:
            self._active_levels.add(lvl)
        self._refresh_level_btns()
        if self._active_levels and self._mode not in ("craft", "mine"):
            self._set_mode("craft")
            return
        self._emit()

    def _refresh_mode_btns(self):
        for key, btn in self._mode_btns.items():
            btn.setChecked(key == self._mode)
            btn.setStyleSheet(_mode_chip(key == self._mode))

    def _refresh_skill_btns(self):
        for key, btn in self._skill_btns.items():
            active = key in self._active_skills
            btn.setChecked(active)
            btn.setStyleSheet(_chip(active))

    def _refresh_level_btns(self):
        for lvl, btn in self._level_btns.items():
            active = lvl in self._active_levels
            btn.setChecked(active)
            btn.setStyleSheet(_chip(active, subtle=True))

    def _emit(self):
        if self._on_change:
            self._on_change()

    # ── Публичный API ─────────────────────────────────────────────────────

    def reset(self):
        self._mode = "all"
        self._active_skills.clear()
        self._active_levels.clear()
        for spin in self._spins.values():
            spin.setValue(0)
        self._refresh_mode_btns()
        self._refresh_skill_btns()
        self._refresh_level_btns()
        self._emit()

    def show_near(self, btn: QWidget):
        win = btn.window()
        win_tl = win.mapToGlobal(QPoint(0, 0))
        win_w = win.width()
        win_h = win.height()

        btn_global = btn.mapToGlobal(QPoint(0, btn.height() + 6))

        max_w = int(win_w * 0.72)
        popup_w = max(460, min(max_w, 760))

        available_h = (win_tl.y() + win_h) - btn_global.y() - 12
        popup_h = max(240, min(available_h, 720))

        self.setFixedWidth(popup_w)
        self.setFixedHeight(popup_h)

        x = btn_global.x()
        if x + popup_w > win_tl.x() + win_w - 8:
            x = win_tl.x() + win_w - popup_w - 8
        if x < win_tl.x() + 8:
            x = win_tl.x() + 8

        self.move(x, btn_global.y())
        self.show()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def active_skills(self) -> set:
        return self._active_skills

    @property
    def active_levels(self) -> set:
        return self._active_levels

    def get_my_level(self, skill: str) -> int:
        s = self._spins.get(skill)
        return s.value() if s else 0

    def has_any_my_level(self) -> bool:
        return any(s.value() > 0 for s in self._spins.values())

    def matches(self, card) -> bool:
        craftable = getattr(card, "is_craftable", False)

        if self._mode == "mine":
            if not craftable:
                return False
            if not self.has_any_my_level():
                return True
            my = self.get_my_level(getattr(card, "craft_skill", ""))
            if my == 0:
                return True
            return getattr(card, "craft_level", 0) <= my

        if self._mode == "nocraft" and craftable:
            return False
        if self._mode == "craft" and not craftable:
            return False
        if not craftable:
            return True
        if self._active_skills and getattr(card, "craft_skill", "") not in self._active_skills:
            return False
        if self._active_levels and getattr(card, "craft_level", 0) not in self._active_levels:
            return False
        return True


# ── Панель — одна кнопка ──────────────────────────────────────────────────


class CraftFilterBar(QFrame):
    """v3.0 — более современная панель, тот же функционал."""

    def __init__(self, on_change=None, parent=None):
        super().__init__(parent)
        self.setObjectName("craftFilterBar")
        self.setFixedHeight(48)
        self._on_change = on_change
        self._popup = FilterPopup(on_change=self._on_popup_change, parent=None)
        self._build()
        self.refresh_style()

    def refresh_style(self):
        p = _palette()
        self.setStyleSheet(f"""
            QFrame#craftFilterBar {{
                background: transparent;
                border-bottom: 1px solid {p['BORDER_SOFT']};
            }}
        """)
        if hasattr(self, '_mode_lbl'):
            self._mode_lbl.setStyleSheet(f"color: {p['TEXT']}; font-size: 11px; font-weight: 500;")
        if hasattr(self, '_tags_lbl'):
            self._tags_lbl.setStyleSheet(f"color: {p['TEXT_SOFT']}; font-size: 11px;")
        if hasattr(self, '_filter_btn'):
            self._filter_btn.setStyleSheet(_action_btn(primary=False))
        if hasattr(self, '_reset_btn'):
            self._reset_btn.setStyleSheet(_action_btn(danger=True))
        if hasattr(self, '_popup'):
            self._popup.refresh_style()

    def _build(self):
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(10)

        self._mode_lbl = QLabel("Все предметы")
        row.addWidget(self._mode_lbl)

        self._tags_lbl = QLabel("")
        row.addWidget(self._tags_lbl)

        row.addStretch()

        self._filter_btn = QPushButton("⚙ Фильтры")
        self._filter_btn.setObjectName("advFilterBtn")
        self._filter_btn.setFixedHeight(32)
        self._filter_btn.setCheckable(True)
        self._filter_btn.clicked.connect(self._toggle_popup)
        row.addWidget(self._filter_btn)

        self._reset_btn = QPushButton("✕")
        self._reset_btn.setFixedSize(32, 32)
        self._reset_btn.setToolTip("Сбросить все фильтры")
        self._reset_btn.clicked.connect(self.reset)
        row.addWidget(self._reset_btn)

    def _toggle_popup(self):
        if self._popup.isVisible():
            self._popup.hide()
            self._filter_btn.setChecked(False)
        else:
            self._popup.show_near(self._filter_btn)
            self._filter_btn.setChecked(True)

    def _on_popup_change(self):
        self._update_labels()
        if self._on_change:
            self._on_change()

    def _update_labels(self):
        mode_names = {
            "all": "Все предметы",
            "craft": "Только крафт",
            "nocraft": "Без крафта",
            "mine": "🎯 Мои навыки",
        }
        self._mode_lbl.setText(mode_names.get(self._popup.mode, ""))

        tags = []
        for k in self._popup.active_skills:
            icon = _SKILL_ICONS.get(k, "")
            p = _palette()
            tags.append(f'<font color="{p["ACCENT"]}">{icon}</font>')
        for lvl in sorted(self._popup.active_levels):
            p = _palette()
            tags.append(f'<font color="{p["ACCENT_HOVER"]}">ур.{lvl}</font>')
        self._tags_lbl.setText("  ".join(tags))

    def reset(self):
        self._popup.reset()
        self._filter_btn.setChecked(False)
        self._update_labels()

    def matches(self, card) -> bool:
        return self._popup.matches(card)
