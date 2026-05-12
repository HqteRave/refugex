import os
import sys


def _bundle_dir() -> str:
    """Временная папка с ресурсами PyInstaller (sys._MEIPASS) или папка проекта."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _appdata_dir() -> str:
    """%APPDATA%\\SC-CraftX — папка пользовательских данных."""
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    path = os.path.join(base, 'SC-CraftX')
    os.makedirs(path, exist_ok=True)
    return path


BUNDLE_DIR = _bundle_dir()
APPDATA_DIR = _appdata_dir()


def asset_path(*parts: str) -> str:
    """Read-only ресурс внутри EXE (assets, json-данные рецептов)."""
    return os.path.join(BUNDLE_DIR, *parts)


def app_path(*parts: str) -> str:
    """Записываемый пользовательский файл в %APPDATA%\\SC-CraftX\\."""
    return os.path.join(APPDATA_DIR, *parts)
