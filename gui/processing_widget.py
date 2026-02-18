"""Progress display widget for PDF processing — no business logic."""

import time

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt


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
        main_layout = QVBoxLayout(self)
        main_layout.addStretch()

        # Center Card
        from gui.components.card import Card
        self._card = Card(title="Processing Status")
        self._card.setFixedWidth(400) # Fixed width for cleaner look
        
        card_layout = QVBoxLayout()
        card_layout.setSpacing(15)

        # Stage indicator
        self._stage_label = QLabel("")
        self._stage_label.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        self._stage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._stage_label)

        self._title_label = QLabel("Ready")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet("border: none; color: palette(text);")
        self._title_label.setWordWrap(True)
        card_layout.addWidget(self._title_label)

        self._page_label = QLabel("")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setStyleSheet("border: none; color: palette(midlight);")
        card_layout.addWidget(self._page_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        card_layout.addWidget(self._progress_bar)

        bottom_row = QHBoxLayout()
        self._eta_label = QLabel("")
        self._eta_label.setStyleSheet("border: none;")
        bottom_row.addWidget(self._eta_label)
        bottom_row.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        bottom_row.addWidget(self._cancel_btn)

        card_layout.addLayout(bottom_row)
        
        self._card.add_layout(card_layout)
        
        # Add Card to Main Layout (Centered)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self._card)
        row.addStretch()
        
        main_layout.addLayout(row)
        main_layout.addStretch()

    def start(self, filename: str, total_pages: int) -> None:
        """Reset all widgets for a new processing run."""
        self._start_time = time.time()
        self._total_pages = total_pages
        self._title_label.setText(f"Processing: {filename}")
        self._page_label.setText(f"Page 0 of {total_pages}")
        self._progress_bar.setValue(0)
        self._eta_label.setText("Calculating...")
        self._cancel_btn.setEnabled(True)

    def set_stage(self, stage_text: str) -> None:
        """Set the current processing stage."""
        self._stage_label.setText(stage_text)

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
