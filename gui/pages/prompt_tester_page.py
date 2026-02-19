"""Prompt Tester Page — split viewer, nav bar, gradient progress, resizable prompts."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.config import Config
from gui.workers import VLMWorker
from gui.zoomable_view import ZoomableGraphicsView

logger = logging.getLogger(__name__)

_GRADIENT_BAR_STYLE = """
    QProgressBar {
        border: 1px solid #e2e8f0;
        border-radius: 5px;
        background-color: #f1f5f9;
        text-align: center;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0    #ef4444,
            stop:0.33 #f97316,
            stop:0.66 #eab308,
            stop:1    #22c55e);
        border-radius: 4px;
    }
"""


class PromptTesterPage(QWidget):
    """
    Prompt Testing Page.

    Layout (top → bottom):
      - Header: back button + title
      - Split viewer: PDF image (left 50%) | OCR output (right 50%)
      - Nav bar: ← [page#] → [Run Test]
      - Gradient progress bar (hidden when idle)
      - Resizable prompts: System Prompt / User Prompt (vertical splitter)
    """

    home_requested = Signal()

    def __init__(self, config: Config, cache_dir: Path):
        super().__init__()
        self._config = config
        self._cache_dir = cache_dir
        self._worker: Optional[VLMWorker] = None

        from core.workflow_orchestrator import WorkflowOrchestrator
        self._orchestrator = WorkflowOrchestrator(config)
        self._page_paths = self._orchestrator.get_page_paths_from_cache(cache_dir)

        self._setup_ui()
        if self._page_paths:
            self._load_page(1)

    # ── UI Construction ──────────────────────────────────────────────

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(8)

        main_layout.addLayout(self._build_header())

        # Outer vertical splitter: top = viewer+nav, bottom = prompts
        outer = QSplitter(Qt.Orientation.Vertical)
        outer.setHandleWidth(8)
        outer.setChildrenCollapsible(False)
        outer.addWidget(self._build_viewer_section())
        outer.addWidget(self._build_prompts_section())
        outer.setSizes([600, 300])

        main_layout.addWidget(outer)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        back_btn = QPushButton("← Back to Dashboard")
        back_btn.clicked.connect(self.home_requested.emit)
        row.addWidget(back_btn)
        title = QLabel("Prompt Tester")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        row.addWidget(title)
        row.addStretch()
        return row

    def _build_viewer_section(self) -> QWidget:
        """PDF image | OCR output split, plus nav bar and progress bar."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 50/50 horizontal split
        view_split = QSplitter(Qt.Orientation.Horizontal)
        view_split.setHandleWidth(8)
        view_split.setChildrenCollapsible(False)
        view_split.addWidget(self._build_image_panel())
        view_split.addWidget(self._build_output_panel())
        view_split.setSizes([500, 500])
        layout.addWidget(view_split)

        layout.addLayout(self._build_nav_bar())

        self._progress_bar = _make_gradient_bar()
        self._progress_bar.setFixedHeight(12)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        return widget

    def _build_image_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background: white; border-radius: 12px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        self._scene = QGraphicsScene()
        self._image_view = ZoomableGraphicsView()
        self._image_view.setScene(self._scene)
        layout.addWidget(self._image_view)
        return frame

    def _build_output_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background: white; border-radius: 12px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        lbl = QLabel("OCR Output")
        lbl.setStyleSheet("font-weight: bold; color: #334155;")
        layout.addWidget(lbl)
        self._output_edit = QTextEdit()
        self._output_edit.setReadOnly(True)
        layout.addWidget(self._output_edit)
        return frame

    def _build_nav_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self._prev_btn = QPushButton("←")
        self._prev_btn.setFixedWidth(40)
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(self._on_prev)
        row.addWidget(self._prev_btn)

        self._page_spin = QSpinBox()
        self._page_spin.setFixedWidth(70)
        total = len(self._page_paths) if self._page_paths else 0
        self._page_spin.setRange(1 if total else 0, max(total, 1))
        self._page_spin.valueChanged.connect(self._load_page)
        row.addWidget(self._page_spin)

        self._total_label = QLabel(f"/ {total}")
        self._total_label.setStyleSheet("color: #64748b;")
        row.addWidget(self._total_label)

        self._next_btn = QPushButton("→")
        self._next_btn.setFixedWidth(40)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._on_next)
        row.addWidget(self._next_btn)

        row.addStretch()

        self._run_btn = QPushButton("Run Test")
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_btn.clicked.connect(self._run_test)
        self._run_btn.setStyleSheet(
            "background-color: #10b981; color: white; font-weight: bold; padding: 8px 20px;"
        )
        row.addWidget(self._run_btn)

        return row

    def _build_prompts_section(self) -> QWidget:
        """Vertically resizable System Prompt / User Prompt panels."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_prompt_panel(
            "System Prompt:", self._config.system_prompt, "_system_prompt_edit"
        ))
        splitter.addWidget(self._build_prompt_panel(
            "User Prompt:",
            getattr(self._config, "user_prompt", "Extract text from this image."),
            "_user_prompt_edit",
        ))
        splitter.setSizes([200, 100])

        layout.addWidget(splitter)
        return widget

    def _build_prompt_panel(self, label: str, text: str, attr: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(QLabel(label))
        edit = QTextEdit()
        edit.setPlainText(text)
        edit.setMinimumHeight(40)
        layout.addWidget(edit)
        setattr(self, attr, edit)
        return widget

    # ── Navigation ───────────────────────────────────────────────────

    def _on_prev(self) -> None:
        if self._page_spin.value() > 1:
            self._page_spin.setValue(self._page_spin.value() - 1)

    def _on_next(self) -> None:
        total = len(self._page_paths) if self._page_paths else 0
        if self._page_spin.value() < total:
            self._page_spin.setValue(self._page_spin.value() + 1)

    def _load_page(self, page_num: int) -> None:
        if not self._page_paths:
            return
        path = self._page_paths[page_num - 1]
        pixmap = QPixmap(str(path))
        self._scene.clear()
        if not pixmap.isNull():
            self._scene.addPixmap(pixmap)
        else:
            self._scene.addText("Failed to load image")
        total = len(self._page_paths)
        self._prev_btn.setEnabled(page_num > 1)
        self._next_btn.setEnabled(page_num < total)

    # ── Run Test ─────────────────────────────────────────────────────

    def _run_test(self) -> None:
        if not self._page_paths:
            return
        page_num = self._page_spin.value()
        page_path = self._page_paths[page_num - 1]

        self._output_edit.setPlainText("Running...")
        self._run_btn.setEnabled(False)
        self._progress_bar.setRange(0, 0)  # indeterminate pulsing
        self._progress_bar.show()

        params = self._orchestrator.get_ocr_params()
        self._worker = VLMWorker(
            page_path=page_path,
            api_url=params["api_url"],
            api_key=params["api_key"],
            model_name=params["model_name"],
            timeout=params["timeout"],
            max_tokens=params["max_tokens"],
            temperature=params["temperature"],
            system_prompt=self._system_prompt_edit.toPlainText(),
            user_prompt=self._user_prompt_edit.toPlainText(),
        )
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_result(self, text: str) -> None:
        self._output_edit.setPlainText(text)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)

    def _on_error(self, msg: str) -> None:
        self._output_edit.setPlainText(f"Error: {msg}")
        self._progress_bar.hide()

    def _on_worker_done(self) -> None:
        self._run_btn.setEnabled(True)


# ── Module helpers ────────────────────────────────────────────────────────────

def _make_gradient_bar() -> QProgressBar:
    """Create a styled red→orange→yellow→green QProgressBar."""
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(0)
    bar.setTextVisible(False)
    bar.setStyleSheet(_GRADIENT_BAR_STYLE)
    return bar
