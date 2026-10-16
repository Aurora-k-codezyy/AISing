import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from aising_client.api import ApiClient
from aising_client.branding import fetch_branding
from aising_client.logging_config import setup_logging
from aising_client.task_patch import apply_task_patches
from aising_client.ui.main_window import MainWindow
from aising_client.ui.window_chrome import DarkTitleBarController, enable_windows_dark_mode


def main() -> int:
    setup_logging()
    enable_windows_dark_mode()
    apply_task_patches()
    app = QApplication(sys.argv)
    if hasattr(app, "styleHints") and hasattr(app.styleHints(), "setColorScheme"):
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    title_bar_controller = DarkTitleBarController(app)
    app.installEventFilter(title_bar_controller)
    branding = fetch_branding(ApiClient())
    app.setApplicationName(branding.app_name)
    app.setApplicationDisplayName(branding.display_name)
    if branding.icon_path.exists():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(branding.icon_path)))
    window = MainWindow(branding=branding)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

