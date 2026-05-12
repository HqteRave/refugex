import json
import os
from themes import THEMES, DEFAULT_THEME
from app_paths import app_path

_CONFIG_FILE = app_path("config.json")

_current_theme_key = DEFAULT_THEME


def _load_config() -> dict:
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(data: dict):
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init():
    global _current_theme_key
    cfg = _load_config()
    key = cfg.get("theme", DEFAULT_THEME)
    if key in THEMES:
        _current_theme_key = key


def get_theme() -> dict:
    return THEMES[_current_theme_key]


def get_theme_key() -> str:
    return _current_theme_key


def set_theme(key: str):
    global _current_theme_key
    if key not in THEMES:
        return
    _current_theme_key = key
    cfg = _load_config()
    cfg["theme"] = key
    _save_config(cfg)


def get(var: str) -> str:
    return get_theme().get(var, "")
