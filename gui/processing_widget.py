"""Progress display widget for PDF processing — no business logic."""

import time

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def format_eta(seconds: float) -> str:
    """Format seconds into a human-readable ETA string."""
    if seconds < 60:
        return "< 1 min"
    minutes = int(seconds / 60)
    if minutes < 60:
        return f"~{minutes} min"
    hours = minutes // 60
    remaining_min = minutes % 60
    if remaining_min == 0:
        return f"~{hours} hr"
    return f"~{hours} hr {remaining_min} min"


class ProcessingWidget(QWidget):
    """Displays processing progress with ETA and cancel button.

    Pure display widget — receives updates via public methods,
    emits cancel_requested when user clicks Cancel.
    """

    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._start_time: float = 0.0
        self._total_pages: int = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the progress display layout."""
        layout = QVBoxLayout(self)
        layout.addStretch()

        self._title_label = QLabel("Ready")
        layout.addWidget(self._title_label)

        self._page_label = QLabel("")
        layout.addWidget(self._page_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        bottom_row = QHBoxLayout()
        self._eta_label = QLabel("")
        bottom_row.addWidget(self._eta_label)
        bottom_row.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        bottom_row.addWidget(self._cancel_btn)

        layout.addLayout(bottom_row)
        layout.addStretch()

    def start(self, filename: str, total_pages: int) -> None:
        """Reset all widgets for a new processing run."""
        self._start_time = time.time()
        self._total_pages = total_pages
        self._title_label.setText(f"Processing: {filename}")
        self._page_label.setText(f"Page 0 of {total_pages}")
        self._progress_bar.setValue(0)
        self._eta_label.setText("Calculating...")
        self._cancel_btn.setEnabled(True)

    def update_page(self, page_num: int, total: int) -> None:
        """Update progress bar, page label, and ETA."""
        self._total_pages = total
        self._page_label.setText(f"Page {page_num} of {total}")

        percent = int((page_num / total) * 100) if total > 0 else 0
        self._progress_bar.setValue(percent)

        self._update_eta(page_num, total)

    def finish(self) -> None:
        """Set progress to 100% and disable cancel."""
        self._progress_bar.setValue(100)
        self._page_label.setText(f"Page {self._total_pages} of {self._total_pages}")
        self._eta_label.setText("Complete")
        self._cancel_btn.setEnabled(False)

    def _update_eta(self, pages_done: int, total: int) -> None:
        """Recalculate and display ETA based on elapsed time."""
        if pages_done <= 0:
            self._eta_label.setText("Calculating...")
            return

        elapsed = time.time() - self._start_time
        avg_per_page = elapsed / pages_done
        remaining_pages = total - pages_done

        if remaining_pages <= 0:
            self._eta_label.setText("Almost done...")
            return

        eta_seconds = avg_per_page * remaining_pages
        self._eta_label.setText(f"ETA: {format_eta(eta_seconds)}")
