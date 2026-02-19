from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLabel, QFrame

from core.config import Config
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLabel, QFrame, QTextEdit

from core.config import Config

class PromptEditorWidget(QWidget):
    """
    Reusable widget containing System Prompt and User Prompt editors.
    Uses ResizableTextEdit for adjustable geometry.
    """

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Vertical splitter for System / User prompts
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)

        # System Prompt Section
        self._system_container = self._build_prompt_panel(
            "System Prompt:",
            self._config.system_prompt,
            self._config.system_prompt_height,
            "_system_edit"
        )
        splitter.addWidget(self._system_container)

        # User Prompt Section
        self._user_container = self._build_prompt_panel(
            "User Prompt:",
            self._config.user_prompt,
            self._config.user_prompt_height,
            "_user_edit"
        )
        splitter.addWidget(self._user_container)
        
        # Set initial sizes based on content/defaults
        splitter.setSizes([self._config.system_prompt_height, self._config.user_prompt_height])
        splitter.splitterMoved.connect(self._on_splitter_moved)

        layout.addWidget(splitter)

    def _build_prompt_panel(self, label: str, text: str, height: int, attr_name: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)
        
        lbl = QLabel(label)
        lbl.setStyleSheet("font-weight: bold; color: #334155;")
        layout.addWidget(lbl)
        
        editor = QTextEdit()
        editor.setPlainText(text)
        
        # Connect signals for real-time config updates (shared state)
        editor.textChanged.connect(self._sync_to_config)
        
        layout.addWidget(editor)
        
        setattr(self, attr_name, editor)
        return container

    def _on_splitter_moved(self, pos: int, index: int):
        """Update config height values when splitter acts."""
        # sizes() returns [height1, height2]
        # self.sender() is the QSplitter
        splitter: QSplitter = self.sender()
        sizes = splitter.sizes()
        if len(sizes) == 2:
            self._config.system_prompt_height = sizes[0]
            self._config.user_prompt_height = sizes[1]

    def _sync_to_config(self):
        """Update config object with current values immediately."""
        if hasattr(self, "_system_edit"):
             self._config.system_prompt = self._system_edit.toPlainText()
        if hasattr(self, "_user_edit"):
             self._config.user_prompt = self._user_edit.toPlainText()

    def get_system_prompt(self) -> str:
        return self._system_edit.toPlainText()

    def get_user_prompt(self) -> str:
        return self._user_edit.toPlainText()
