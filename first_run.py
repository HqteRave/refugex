"""
Инициализация при первом запуске:
- Создаёт %APPDATA%\\SC-CraftX\\
- Копирует credentials.json из bundle (если ещё нет)
- Мигрирует старые файлы рядом с EXE → %APPDATA%\\SC-CraftX\\
"""
import os
import shutil
import sys
from app_paths import APPDATA_DIR, BUNDLE_DIR

_MIGRATE_FILES = ['credentials.json', 'config.json', 'favorites.json', 'cache.db']


def _exe_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def init():
    exe_dir = _exe_dir()

    # 1. Мигрируем файлы рядом с EXE → %APPDATA% (если они там лежат)
    for name in _MIGRATE_FILES:
        src = os.path.join(exe_dir, name)
        dst = os.path.join(APPDATA_DIR, name)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.move(src, dst)

    # 2. Если credentials.json всё ещё нет — копируем из bundle
    cred_dst = os.path.join(APPDATA_DIR, 'credentials.json')
    if not os.path.exists(cred_dst):
        cred_bundle = os.path.join(BUNDLE_DIR, 'credentials.json')
        if os.path.exists(cred_bundle):
            shutil.copy2(cred_bundle, cred_dst)

    # 3. Создаём пустой favorites.json если нет
    fav_dst = os.path.join(APPDATA_DIR, 'favorites.json')
    if not os.path.exists(fav_dst):
        import json
        with open(fav_dst, 'w', encoding='utf-8') as f:
            json.dump({'auction': [], 'craft': []}, f)
