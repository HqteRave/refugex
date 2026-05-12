"""
examples/pyqt6_example.py — Пример интеграции api_v2 с PyQt6

Демонстрирует:
  - Загрузку цен при клике на кнопку
  - Автоматическое обновление по таймеру
  - Отображение прогресса
  - Обработку ошибок
"""

import sys
from pathlib import Path

# Добавляем родительскую папку в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QTextEdit, QProgressBar, QCheckBox
)
from PyQt6.QtCore import Qt

from api_v2 import AutoSyncManager, PriceStats, SyncProgress
from settings_v2 import Settings, configure_logging


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("SC-CraftX — Пример API v2")
        self.setMinimumSize(800, 600)
        
        # Список предметов для синхронизации
        self.item_ids = [
            "pistol-pm",
            "rifle-akm",
            "ammo-9x18-pm",
            "ammo-5-45x39-ps",
            "detector-echo"
        ]
        
        # Создаём менеджер синхронизации
        self.sync_manager = AutoSyncManager(
            item_ids=self.item_ids,
            interval_seconds=Settings.SYNC_INTERVAL
        )
        
        # Подключаем сигналы
        self.sync_manager.price_updated.connect(self.on_price_updated)
        self.sync_manager.sync_progress.connect(self.on_progress)
        self.sync_manager.sync_started.connect(self.on_sync_started)
        self.sync_manager.sync_finished.connect(self.on_sync_finished)
        self.sync_manager.error.connect(self.on_error)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Создание интерфейса"""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        
        # Заголовок
        title = QLabel("SC-CraftX — Тестирование API v2")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Кнопка ручной синхронизации
        self.btn_sync = QPushButton("Синхронизировать цены")
        self.btn_sync.clicked.connect(self.manual_sync)
        layout.addWidget(self.btn_sync)
        
        # Чекбокс для автообновления
        self.chk_auto = QCheckBox("Автоматическое обновление")
        self.chk_auto.toggled.connect(self.toggle_auto_sync)
        layout.addWidget(self.chk_auto)
        
        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Статус
        self.lbl_status = QLabel("Готов к работе")
        self.lbl_status.setStyleSheet("color: #666;")
        layout.addWidget(self.lbl_status)
        
        # Лог
        log_label = QLabel("Лог обновлений:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # Кнопка очистки
        btn_clear = QPushButton("Очистить лог")
        btn_clear.clicked.connect(self.log_text.clear)
        layout.addWidget(btn_clear)
    
    def manual_sync(self):
        """Ручная синхронизация"""
        self.log("Запуск ручной синхронизации...")
        self.sync_manager.sync_prices(self.item_ids, include_lots=True)
    
    def toggle_auto_sync(self, checked: bool):
        """Вкл/выкл автообновления"""
        if checked:
            self.log(f"Автообновление включено (интервал: {Settings.SYNC_INTERVAL}s)")
            self.sync_manager.start_auto_sync(include_lots=True)
        else:
            self.log("Автообновление отключено")
            self.sync_manager.stop_auto_sync()
    
    # ═══════════════════════════════════════════════════════════════════════
    # Обработчики сигналов
    # ═══════════════════════════════════════════════════════════════════════
    
    def on_price_updated(self, item_id: str, stats: PriceStats):
        """Обновление цены предмета"""
        msg = (
            f"<b>{item_id}</b>: "
            f"Средняя цена: <span style='color: green;'>{stats.avg_price:,}</span> ₽ | "
            f"Сделок: {stats.count} | "
            f"Ликвидность: {stats.liquidity}"
        )
        
        if stats.market_total_lots > 0:
            msg += f" | Лотов: {stats.market_total_lots}"
        
        self.log(msg)
    
    def on_progress(self, progress: SyncProgress):
        """Обновление прогресса"""
        self.progress.setVisible(True)
        self.progress.setMaximum(progress.total_items)
        self.progress.setValue(progress.completed_items)
        
        if progress.current_item:
            self.lbl_status.setText(f"Обработка: {progress.current_item}...")
    
    def on_sync_started(self):
        """Начало синхронизации"""
        self.btn_sync.setEnabled(False)
        self.lbl_status.setText("Синхронизация...")
        self.log("<i>Синхронизация началась...</i>")
    
    def on_sync_finished(self):
        """Завершение синхронизации"""
        self.btn_sync.setEnabled(True)
        self.progress.setVisible(False)
        self.lbl_status.setText("Готов к работе")
        self.log("<i style='color: green;'>Синхронизация завершена!</i>")
    
    def on_error(self, message: str):
        """Ошибка"""
        self.log(f"<span style='color: red;'>ОШИБКА: {message}</span>")
    
    def log(self, message: str):
        """Добавить запись в лог"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def closeEvent(self, event):
        """Очистка при закрытии"""
        self.sync_manager.cleanup()
        event.accept()


def main():
    """Точка входа"""
    # Настройка логирования
    configure_logging()
    
    # Проверка настроек
    errors = Settings.validate()
    if errors:
        print("ОШИБКИ КОНФИГУРАЦИИ:")
        for err in errors:
            print(f"  - {err}")
        print("\nСоздай .env файл на основе .env.example!")
        sys.exit(1)
    
    # Запуск приложения
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
