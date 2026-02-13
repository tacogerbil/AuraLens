"""AuraLens entry point — composition root, no business logic."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.config import load_config
from gui.main_window import MainWindow


def main() -> None:
    """Launch the AuraLens application."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AuraLens")
    app.setOrganizationName("AuraLens")
    app.setApplicationVersion("0.1.0")

    config = load_config()
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
