"""Image review screen shown between extraction and OCR."""

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ImageReviewWidget(QWidget):
    """Tells user images are extracted and ready for optional editing."""

    continue_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._cache_dir: Path = Path()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the review screen layout."""
        layout = QVBoxLayout(self)
        layout.addStretch()

        self._info_label = QLabel("No pages extracted yet.")
        layout.addWidget(self._info_label)

        self._folder_label = QLabel("")
        self._folder_label.setTextInteractionFlags(
            self._folder_label.textInteractionFlags()
            | self._folder_label.textInteractionFlags().TextSelectableByMouse
        )
        layout.addWidget(self._folder_label)

        self._instructions_label = QLabel(
            "Review and edit the page images if needed.\n"
            "Open the folder in your file manager to make changes."
        )
        layout.addWidget(self._instructions_label)

        self._build_button_row(layout)
        layout.addStretch()

    def _build_button_row(self, parent_layout: QVBoxLayout) -> None:
        """Add Open Folder and Continue buttons."""
        row = QHBoxLayout()

        self._open_btn = QPushButton("Open Folder")
        self._open_btn.clicked.connect(self._open_folder)
        row.addWidget(self._open_btn)

        row.addStretch()

        self._continue_btn = QPushButton("Continue to OCR")
        self._continue_btn.clicked.connect(self.continue_requested.emit)
        row.addWidget(self._continue_btn)

        parent_layout.addLayout(row)

    def show_ready(self, cache_dir: Path, page_count: int) -> None:
        """Update labels with extraction results."""
        self._cache_dir = cache_dir
        self._info_label.setText(
            f"Extracted {page_count} pages to:"
        )
        self._folder_label.setText(str(cache_dir))

    def _open_folder(self) -> None:
        """Open the cache folder in the system file manager."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._cache_dir)))
