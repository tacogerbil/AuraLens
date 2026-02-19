import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
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
    QGroupBox,
    QGraphicsScene,
    QFrame
)

from core.config import Config
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
        
        # Determine page paths
        from core.workflow_orchestrator import WorkflowOrchestrator
        self._orchestrator = WorkflowOrchestrator(config)
        self._page_paths = self._orchestrator.get_page_paths_from_cache(cache_dir)
        
        self._setup_ui()
        self._load_page(1)

    def _setup_ui(self) -> None:
        """Create the UI layout matching reference 'OCRProcessingPage' style."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Header with Back button
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
        
        # Left Panel (Image Viewer)
        self._scene = QGraphicsScene()
        self._image_view = ZoomableGraphicsView()
        self._image_view.setScene(self._scene)
        # Wrap in visible frame for style
        image_frame = QFrame()
        image_frame.setStyleSheet("background: white; border-radius: 16px;")
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(0,0,0,0)
        image_layout.addWidget(self._image_view)
        
        splitter.addWidget(image_frame)
        
        # Right Panel (Controls & Output)
        right_panel = QFrame()
        right_panel.setStyleSheet("background: white; border-radius: 16px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20,20,20,20)
        
        # Page Selection
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
        
        # Prompts
        right_layout.addWidget(QLabel("System Prompt:"))
        self._system_prompt_edit = QTextEdit()
        self._system_prompt_edit.setPlainText(self._config.system_prompt)
        self._system_prompt_edit.setMaximumHeight(100)
        right_layout.addWidget(self._system_prompt_edit)
        
        right_layout.addWidget(QLabel("User Prompt:"))
        self._user_prompt_edit = QTextEdit()
        default_user_prompt = getattr(self._config, "user_prompt", "Extract text from this image.")
        self._user_prompt_edit.setPlainText(default_user_prompt) 
        self._user_prompt_edit.setMaximumHeight(60)
        right_layout.addWidget(self._user_prompt_edit)
        
        # Run Button
        self._run_btn = QPushButton("Run Test")
        self._run_btn.clicked.connect(self._run_test)
        self._run_btn.setStyleSheet("background-color: #10b981; color: white; font-weight: bold; padding: 10px;")
        right_layout.addWidget(self._run_btn)
        
        # Output
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
            # self._image_view.fit_to_width() # Need to ensure view is ready
        else:
            self._scene.addText("Failed to load image")

    def _run_test(self) -> None:
        """Run single-page OCR with current prompts."""
        if not self._page_paths:
             return
             
        page_num = self._page_spin.value()
        page_path = self._page_paths[page_num - 1]
        
        system_prompt = self._system_prompt_edit.toPlainText()
        user_prompt = self._user_prompt_edit.toPlainText()
        
        self._output_edit.setPlainText("Running...")
        self._run_btn.setEnabled(False)
        self.repaint() 
        
        QTimer.singleShot(100, lambda: self._execute_vlm(page_path, system_prompt, user_prompt))

    def _execute_vlm(self, page_path: Path, system_prompt: str, user_prompt: str) -> None:
        """Execute VLM call."""
        from core.image_utils import to_base64_data_uri
        
        try:
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
