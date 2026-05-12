import theme_manager as _tm

API_BASE_URL    = "https://eapi.stalcraft.net"
REGION          = "ru"
APP_NAME        = "SC-CraftX"
APP_VERSION     = "0.1.0"


def _refresh():
    """Обновляет все цветовые константы из текущей темы. Вызывается при смене темы."""
    import sys
    m = sys.modules[__name__]
    t = _tm.get_theme()
    for k, v in t.items():
        if k != "name":
            setattr(m, k, v)


# Инициализируем при первом импорте
_refresh()
