from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QFrame

class ResizeHandle(QFrame):
    """A draggable handle for resizing widgets vertically."""
    dragged = Signal(int)  # Emits dy (delta y)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self.setCursor(Qt.CursorShape.SplitVCursor)
        self.setStyleSheet("""
            ResizeHandle {
                background-color: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-top: none;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            ResizeHandle:hover {
                background-color: #e2e8f0;
            }
        """)
        self._drag_start_y = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_y = event.globalPosition().y()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start_y is not None:
            current_y = event.globalPosition().y()
            dy = current_y - self._drag_start_y
            self.dragged.emit(int(dy))
            self._drag_start_y = current_y
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_y = None
            event.accept()


class ResizableTextEdit(QWidget):
    """A QTextEdit wrapper that allows vertical resizing via a bottom drag handle."""

    def __init__(self, text: str = "", height: int = 100, parent=None):
        super().__init__(parent)
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        self._edit = QTextEdit(text)
        self._edit.setFixedHeight(height)
        # Apply specific styling to the edit so it merges visually with handle
        self._edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e2e8f0;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                background-color: white;
                padding: 8px;
            }
        """)
        self._layout.addWidget(self._edit)
        
        self._handle = ResizeHandle()
        self._handle.dragged.connect(self._on_handle_dragged)
        self._layout.addWidget(self._handle)
        
    def _on_handle_dragged(self, dy: int):
        new_height = max(60, self._edit.height() + dy)
        self._edit.setFixedHeight(new_height)

    # ── Public API (Proxying QTextEdit) ──────────────────────────────────
    
    def toPlainText(self) -> str:
        return self._edit.toPlainText()
        
    def setPlainText(self, text: str) -> None:
        self._edit.setPlainText(text)
        
    def get_content_height(self) -> int:
        """Return the current height of the text edit area."""
        return self._edit.height()
