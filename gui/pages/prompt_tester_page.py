import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QGraphicsScene,
    QFrame
)

from core.config import Config
from gui.workers import VLMWorker
from gui.zoomable_view import ZoomableGraphicsView

logger = logging.getLogger(__name__)


class PromptTesterPage(QWidget):
    """
    Prompt Testing Page (Converted from Dialog).
    Designed to fit within the main StackedWidget.
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
        self._load_page(1)

    def _setup_ui(self) -> None:
        """Create the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_layout = QHBoxLayout()
        back_btn = QPushButton("← Back to Dashboard")
        back_btn.clicked.connect(self.home_requested.emit)
        header_layout.addWidget(back_btn)

        title = QLabel("Prompt Tester")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Splitter (Image | Controls)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Image viewer
        self._scene = QGraphicsScene()
        self._image_view = ZoomableGraphicsView()
        self._image_view.setScene(self._scene)
        image_frame = QFrame()
        image_frame.setStyleSheet("background: white; border-radius: 16px;")
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.addWidget(self._image_view)
        splitter.addWidget(image_frame)

        # Right: Controls & output
        right_panel = QFrame()
        right_panel.setStyleSheet("background: white; border-radius: 16px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)

        page_layout = QHBoxLayout()
        page_layout.addWidget(QLabel("Page:"))
        self._page_spin = QSpinBox()
        if self._page_paths:
            self._page_spin.setRange(1, len(self._page_paths))
        else:
            self._page_spin.setRange(0, 0)
            self._image_view.hide()
        self._page_spin.valueChanged.connect(self._load_page)
        page_layout.addWidget(self._page_spin)
        page_layout.addStretch()
        right_layout.addLayout(page_layout)

        right_layout.addWidget(QLabel("System Prompt:"))
        self._system_prompt_edit = QTextEdit()
        self._system_prompt_edit.setPlainText(self._config.system_prompt)
        self._system_prompt_edit.setMaximumHeight(100)
        right_layout.addWidget(self._system_prompt_edit)

        right_layout.addWidget(QLabel("User Prompt:"))
        self._user_prompt_edit = QTextEdit()
        self._user_prompt_edit.setPlainText(
            getattr(self._config, "user_prompt", "Extract text from this image.")
        )
        self._user_prompt_edit.setMaximumHeight(60)
        right_layout.addWidget(self._user_prompt_edit)

        self._run_btn = QPushButton("Run Test")
        self._run_btn.clicked.connect(self._run_test)
        self._run_btn.setStyleSheet(
            "background-color: #10b981; color: white; font-weight: bold; padding: 10px;"
        )
        right_layout.addWidget(self._run_btn)

        right_layout.addWidget(QLabel("Output:"))
        self._output_edit = QTextEdit()
        self._output_edit.setReadOnly(True)
        right_layout.addWidget(self._output_edit)

        splitter.addWidget(right_panel)
        splitter.setSizes([600, 400])
        splitter.setHandleWidth(10)
        main_layout.addWidget(splitter)

    def _load_page(self, page_num: int) -> None:
        """Load the image for the selected page."""
        if not self._page_paths:
            return
        path = self._page_paths[page_num - 1]
        pixmap = QPixmap(str(path))
        self._scene.clear()
        if not pixmap.isNull():
            self._scene.addPixmap(pixmap)
        else:
            self._scene.addText("Failed to load image")

    def _run_test(self) -> None:
        """Launch VLMWorker to process the current page off-thread."""
        if not self._page_paths:
            return

        page_num = self._page_spin.value()
        page_path = self._page_paths[page_num - 1]
        system_prompt = self._system_prompt_edit.toPlainText()
        user_prompt = self._user_prompt_edit.toPlainText()

        self._output_edit.setPlainText("Running...")
        self._run_btn.setEnabled(False)

        params = self._orchestrator.get_ocr_params()
        self._worker = VLMWorker(
            page_path=page_path,
            api_url=params["api_url"],
            api_key=params["api_key"],
            model_name=params["model_name"],
            timeout=params["timeout"],
            max_tokens=params["max_tokens"],
            temperature=params["temperature"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(lambda: self._run_btn.setEnabled(True))
        self._worker.start()

    def _on_result(self, text: str) -> None:
        self._output_edit.setPlainText(text)

    def _on_error(self, msg: str) -> None:
        self._output_edit.setPlainText(f"Error: {msg}")
