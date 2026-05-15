import sys
import traceback
import first_run

first_run.init()

from settings import configure_logging

configure_logging()

from app_paths import app_path, asset_path


def _install_crash_handler():
    import datetime, os

    log_path = app_path("crash.log")

    def _handler(exc_type, exc_value, exc_tb):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = (
            f"\n{'='*60}\n"
            f"[{timestamp}]\n"
            f"{''.join(traceback.format_exception(exc_type, exc_value, exc_tb))}"
        )
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _handler

    # Ограничиваем размер лога — оставляем последние 500 строк
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > 500:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.writelines(lines[-500:])
        except Exception:
            pass


_install_crash_handler()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(asset_path("assets", "app_icon.ico")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
