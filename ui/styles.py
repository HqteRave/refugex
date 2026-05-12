import theme_manager as _tm


def build_style() -> str:
    t = _tm.get_theme()
    BG          = t["BG_COLOR"]
    SURFACE     = t["SURFACE_COLOR"]
    SURFACE2    = t["SURFACE2_COLOR"]
    SIDEBAR     = t["SIDEBAR_COLOR"]
    HEADER      = t["HEADER_COLOR"]
    ACCENT      = t["ACCENT_COLOR"]
    TEXT        = t["TEXT_COLOR"]
    MUTED       = t["MUTED_COLOR"]
    SUCCESS     = t["SUCCESS_COLOR"]
    WARNING     = t["WARNING_COLOR"]
    DANGER      = t["DANGER_COLOR"]
    BORDER      = t["BORDER_COLOR"]
    INPUT_BG    = t["INPUT_BG"]
    INPUT_BDR   = t["INPUT_BORDER"]
    HOVER_BG    = t["HOVER_BG"]
    SUBCAT_HVR  = t["SUBCAT_HOVER"]
    HISTORY_BG  = t["HISTORY_BG"]
    FILTER_BG   = t["FILTER_BG"]
    POPUP_BG    = t["POPUP_BG"]

    return f"""
QMainWindow, QWidget, QFrame, QScrollArea, QAbstractScrollArea {{
    background: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
    margin: 0;
    padding: 0;
    outline: none;
}}
*:focus {{
    outline: none;
}}
QScrollArea > QWidget > QWidget {{
    background: {BG};
}}
QWidget#craftCalculator {{
    background: {BG};
}}
QWidget#craftCardsWidget {{
    background: {BG};
}}

/* ── Шапка ── */
QFrame#header {{
    background: {HEADER};
    border-bottom: 1px solid {BORDER};
    margin: 0;
    padding: 0;
}}
QLabel#headerTitle {{
    background: transparent;
}}
QLabel#headerSub {{
    color: {MUTED};
    font-size: 12px;
    background: transparent;
}}
QLabel#headerVer {{
    color: {MUTED};
    font-size: 11px;
    background: transparent;
    padding-right: 4px;
}}

/* ── Сайдбар ── */
QFrame#sidebar {{
    background: {SIDEBAR};
    border-right: 1px solid {BORDER};
    min-width: 220px;
    max-width: 220px;
    margin: 0;
    padding: 0;
}}
QFrame#sidebar QWidget {{
    background: {SIDEBAR};
}}
QFrame#sidebar QScrollArea {{
    background: {SIDEBAR};
    border: none;
}}
QFrame#sidebar QScrollArea > QWidget > QWidget {{
    background: {SIDEBAR};
}}

/* ── Кнопки категорий ── */
QPushButton#catBtn {{
    background: transparent;
    color: {TEXT};
    border: none;
    border-radius: 8px;
    text-align: left;
}}
QPushButton#catBtn:hover {{
    background: {HOVER_BG};
}}
QPushButton#catBtn[active="true"] {{
    background: rgba(233,69,96,0.18);
    color: {ACCENT};
}}

/* ── Кнопка Калькулятора ── */
QPushButton#calculatorBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(233,69,96,0.20),
                                stop:1 rgba(233,69,96,0.12));
    color: {TEXT};
    border: 1px solid rgba(233,69,96,0.25);
    border-radius: 8px;
    text-align: left;
    margin: 4px 0;
}}
QPushButton#calculatorBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(233,69,96,0.28),
                                stop:1 rgba(233,69,96,0.18));
    border: 1px solid rgba(233,69,96,0.35);
}}
QPushButton#calculatorBtn[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(233,69,96,0.35),
                                stop:1 rgba(233,69,96,0.25));
    border: 1px solid rgba(233,69,96,0.50);
    color: {ACCENT};
}}

/* ── Кнопки подкатегорий ── */
QPushButton#subcatBtn {{
    background: transparent;
    color: {MUTED};
    border: none;
    border-radius: 6px;
    text-align: left;
}}
QPushButton#subcatBtn:hover {{
    background: {SUBCAT_HVR};
    color: {TEXT};
}}
QPushButton#subcatBtn[active="true"] {{
    background: rgba(233,69,96,0.10);
    color: {ACCENT};
}}

/* ── Скроллбар ── */
QScrollBar:vertical {{
    background: {BG};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {INPUT_BDR};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ── Карточка ── */
QFrame#itemCard {{
    background: {SURFACE};
    border-radius: 12px;
    border: 1px solid {BORDER};
}}
QFrame#itemCard:hover {{
    border: 1px solid {ACCENT};
    background: {SURFACE2};
}}
QFrame#itemCard:hover QFrame {{
    border: none;
}}
QFrame#itemCard:hover QFrame#historyPanel {{
    border: none;
    background: {HISTORY_BG};
}}
QFrame#itemCard QWidget,
QFrame#itemCard QLabel {{
    background: transparent;
}}

QLabel#itemName {{
    color: {TEXT};
    font-size: 14px;
    font-weight: bold;
    background: transparent;
}}
QLabel#itemId {{
    color: {MUTED};
    font-size: 10px;
    background: transparent;
}}
QLabel#priceLabel {{
    color: {MUTED};
    font-size: 10px;
    letter-spacing: 1px;
    background: transparent;
}}
QLabel#priceMin, QLabel#priceMax {{
    color: {MUTED};
    font-size: 12px;
    background: transparent;
}}
QLabel#priceAvg {{
    color: {TEXT};
    font-size: 14px;
    font-weight: bold;
    background: transparent;
}}

/* ── Ликвидность ── */
QLabel#liqHigh {{
    color: {SUCCESS};
    font-weight: bold;
    font-size: 12px;
    background: transparent;
}}
QLabel#liqMed {{
    color: {WARNING};
    font-weight: bold;
    font-size: 12px;
    background: transparent;
}}
QLabel#liqLow {{
    color: {DANGER};
    font-weight: bold;
    font-size: 12px;
    background: transparent;
}}
QLabel#liqNone {{
    color: {MUTED};
    font-size: 12px;
    background: transparent;
}}

/* ── История продаж ── */
QFrame#historyPanel {{
    background: {HISTORY_BG};
    border-radius: 8px;
    border: none;
}}
QFrame#historyPanel QWidget,
QFrame#historyPanel QFrame,
QFrame#historyPanel QLabel {{
    background: {HISTORY_BG};
    border: none;
}}

/* ── Таблица ── */
QTableWidget {{
    background: transparent;
    color: {TEXT};
    border: none;
    gridline-color: {BORDER};
    font-size: 11px;
}}
QTableWidget::item {{
    padding: 4px 8px;
    background: transparent;
}}
QTableWidget::item:alternate {{
    background: {SURFACE};
}}
QHeaderView::section {{
    background: {SURFACE};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 5px 8px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}

/* ── Поиск ── */
QLineEdit#searchBox {{
    background: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {INPUT_BDR};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
}}
QLineEdit#searchBox:focus {{
    border: 1px solid {ACCENT};
    background: {SURFACE2};
}}

/* ── Кнопка истории ── */
QPushButton#historyBtn {{
    background: transparent;
    color: {MUTED};
    border: 1px solid {INPUT_BDR};
    border-radius: 5px;
    padding: 3px 10px;
    font-size: 11px;
    min-width: 100px;
}}
QPushButton#historyBtn:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
    background: rgba(233, 69, 96, 0.08);
}}
QPushButton#historyBtn:pressed {{
    background: rgba(233, 69, 96, 0.15);
}}

/* ── Счётчик обновления ── */
QLabel#refreshLbl {{
    color: {MUTED};
    font-size: 11px;
    background: transparent;
}}

/* ── Панель фильтров ── */
QWidget#craftFilterBar {{
    background: {FILTER_BG};
    border-bottom: 1px solid {BORDER};
}}

QComboBox#filterCombo {{
    background: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {INPUT_BDR};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    min-width: 130px;
}}
QComboBox#filterCombo:hover {{
    border-color: {ACCENT};
}}
QComboBox#filterCombo::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox#filterCombo QAbstractItemView {{
    background: {SURFACE2};
    color: {TEXT};
    border: 1px solid {INPUT_BDR};
    selection-background-color: rgba(233, 69, 96, 0.18);
    selection-color: {ACCENT};
    outline: none;
}}

/* ── Кнопка "⚙ Фильтры" ── */
QPushButton#advFilterBtn {{
    background: {INPUT_BG};
    color: {MUTED};
    border: 1px solid {INPUT_BDR};
    border-radius: 6px;
    padding: 4px 14px;
    font-size: 12px;
}}
QPushButton#advFilterBtn:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
    background: rgba(233, 69, 96, 0.08);
}}
QPushButton#advFilterBtn:pressed {{
    background: rgba(233, 69, 96, 0.15);
}}
QPushButton#advFilterBtn:checked {{
    border-color: {ACCENT};
    color: {ACCENT};
    background: rgba(233, 69, 96, 0.12);
}}

/* ── Всплывающее окно фильтров ── */
QWidget#filterPopup {{
    background: {POPUP_BG};
    border: 1px solid {ACCENT};
    border-radius: 10px;
}}
QWidget#filterPopup QLabel {{
    background: transparent;
    color: {MUTED};
    font-size: 11px;
}}

/* SpinBox в попапе */
QSpinBox#filterSpin {{
    background: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {INPUT_BDR};
    border-radius: 5px;
    padding: 3px 6px;
    font-size: 12px;
}}
QSpinBox#filterSpin:focus {{
    border-color: {ACCENT};
}}
QSpinBox#filterSpin::up-button, QSpinBox#filterSpin::down-button {{
    background: {HOVER_BG};
    border: none;
    width: 16px;
}}
QSpinBox#filterSpin::up-button:hover, QSpinBox#filterSpin::down-button:hover {{
    background: {ACCENT};
}}

/* Чекбоксы в попапе */
QCheckBox#filterCheck {{
    color: {TEXT};
    font-size: 12px;
    background: transparent;
    spacing: 8px;
}}
QCheckBox#filterCheck::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {INPUT_BDR};
    background: {INPUT_BG};
}}
QCheckBox#filterCheck::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox#filterCheck::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url(none);
}}

/* Кнопки в попапе */
QPushButton#filterResetBtn {{
    background: transparent;
    color: {MUTED};
    border: 1px solid {INPUT_BDR};
    border-radius: 5px;
    padding: 4px 14px;
    font-size: 12px;
}}
QPushButton#filterResetBtn:hover {{
    border-color: {MUTED};
    color: {TEXT};
}}

QPushButton#filterApplyBtn {{
    background: rgba(233, 69, 96, 0.15);
    color: {ACCENT};
    border: 1px solid {ACCENT};
    border-radius: 5px;
    padding: 4px 18px;
    font-size: 12px;
    font-weight: bold;
}}
QPushButton#filterApplyBtn:hover {{
    background: rgba(233, 69, 96, 0.28);
}}
QPushButton#filterApplyBtn:pressed {{
    background: rgba(233, 69, 96, 0.40);
}}

/* ── Кнопка темы ── */
QPushButton#themeBtn {{
    background: {INPUT_BG};
    color: {MUTED};
    border: 1px solid {INPUT_BDR};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
}}
QPushButton#themeBtn:hover {{
    border-color: {ACCENT};
    color: {TEXT};
}}
"""


# Обратная совместимость — модуль всё ещё экспортирует GLOBAL_STYLE
GLOBAL_STYLE = build_style()
