"""Prompt Tester Dialog for testing OCR prompts on single pages."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QGraphicsScene,
    QGraphicsPixmapItem,
)

from core.config import Config
from core.vlm_client import VLMClient, VLMError
from gui.zoomable_view import ZoomableGraphicsView

logger = logging.getLogger(__name__)


class PromptTester(QDialog):
    """Dialog to test system/user prompts on specific pages."""

    def __init__(self, config: Config, cache_dir: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = config
        self._cache_dir = cache_dir
        
        from core.workflow_orchestrator import WorkflowOrchestrator
        self._orchestrator = WorkflowOrchestrator(config)
        self._page_paths = self._orchestrator.get_page_paths_from_cache(cache_dir)
        
        self.setWindowTitle("Prompt Tester")
        self.resize(1200, 800)
        
        self._setup_ui()
        self._load_page(1)  # Load first page by default

    def _setup_ui(self) -> None:
        """Create the UI layout."""
        layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(20)
        layout.addWidget(splitter)
        
        # Left: Image Viewer (Zoomable)
        self._scene = QGraphicsScene()
        self._image_view = ZoomableGraphicsView()
        self._image_view.setScene(self._scene)
        splitter.addWidget(self._image_view)
        
        # Right: Controls & Output
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Page Selection
        page_layout = QHBoxLayout()
        page_layout.addWidget(QLabel("Page:"))
        self._page_spin = QSpinBox()
        self._page_spin.setRange(1, len(self._page_paths))
        self._page_spin.valueChanged.connect(self._load_page)
        page_layout.addWidget(self._page_spin)
        page_layout.addStretch()
        right_layout.addLayout(page_layout)
        
        # Prompts
        prompts_group = QGroupBox("Prompts")
        prompts_layout = QVBoxLayout(prompts_group)
        
        prompts_layout.addWidget(QLabel("System Prompt:"))
        self._system_prompt_edit = QTextEdit()
        self._system_prompt_edit.setPlainText(self._config.system_prompt)
        self._system_prompt_edit.setMaximumHeight(100)
        prompts_layout.addWidget(self._system_prompt_edit)
        
        prompts_layout.addWidget(QLabel("User Prompt:"))
        self._user_prompt_edit = QTextEdit()
        # Default to config user_prompt or fallback
        default_user_prompt = getattr(self._config, "user_prompt", "Extract text from this image.")
        self._user_prompt_edit.setPlainText(default_user_prompt) 
        self._user_prompt_edit.setMaximumHeight(60)
        prompts_layout.addWidget(self._user_prompt_edit)
        
        right_layout.addWidget(prompts_group)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self._run_btn = QPushButton("Run Test")
        self._run_btn.clicked.connect(self._run_test)
        btn_layout.addWidget(self._run_btn)
        right_layout.addLayout(btn_layout)
        
        # Output
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self._output_edit = QTextEdit()
        self._output_edit.setReadOnly(True)
        output_layout.addWidget(self._output_edit)
        right_layout.addWidget(output_group)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 400])

    def _load_page(self, page_num: int) -> None:
        """Load the image for the selected page."""
        if not self._page_paths:
            return
            
        path = self._page_paths[page_num - 1]
        pixmap = QPixmap(str(path))
        
        self._scene.clear()
        if not pixmap.isNull():
            self._scene.addPixmap(pixmap)
            self._image_view.fit_to_width()
        else:
            self._scene.addText("Failed to load image")

    def _run_test(self) -> None:
        """Run single-page OCR with current prompts."""
        page_num = self._page_spin.value()
        page_path = self._page_paths[page_num - 1]
        
        system_prompt = self._system_prompt_edit.toPlainText()
        user_prompt = self._user_prompt_edit.toPlainText()
        
        self._output_edit.setPlainText("Running...")
        self._run_btn.setEnabled(False)
        self.repaint()  # Force UI update
        
        # Run in a separate loop/thread ideally, but for a simple test dialog check
        # we'll try direct execution carefully, or use QTimer to unblock generic UI return
        # But VLMClient is synchronous requests. 
        # For responsiveness, we should use a worker, but since this is a "Test" dialog,
        # slight freeze is acceptable, OR we can process events.
        
        QTimer.singleShot(100, lambda: self._execute_vlm(page_path, system_prompt, user_prompt))

    def _execute_vlm(self, page_path: Path, system_prompt: str, user_prompt: str) -> None:
        """Execute VLM call."""
        from core.image_utils import to_base64_data_uri
        
        try:
            # Create client using centralized logic (MCCC: DRY)
            client = self._orchestrator.create_vlm_client()

            data_uri = to_base64_data_uri(page_path)
            
            text = client.process_image(
                image_data_uri=data_uri,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            self._output_edit.setPlainText(text)
            
        except Exception as e:
            self._output_edit.setPlainText(f"Error: {e}")
        finally:
            self._run_btn.setEnabled(True)
