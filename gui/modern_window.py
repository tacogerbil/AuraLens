"""Modern Frameless Window with Native Resizing behavior."""

from PySide6.QtCore import Qt, QPoint, QEvent, QSize
from PySide6.QtGui import QMouseEvent, QCursor, QWindow
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QApplication,
    QFrame
)

from gui.theme_manager import ThemeManager

class TitleBar(QFrame):
    """Custom Title Bar for ModernWindow."""

    def __init__(self, parent=None, title="AuraLens"):
        super().__init__(parent)
        self.setFixedHeight(32)
        
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(10, 0, 0, 0)
        self._layout.setSpacing(0)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self._layout.addWidget(self._title_label)
        self._layout.addStretch()

        # Window Controls
        self._min_btn = self._create_btn("-", self.window().showMinimized)
        self._max_btn = self._create_btn("□", self._toggle_max)
        self._close_btn = self._create_btn("✕", self.window().close)
        
        # Determine strict colours for buttons to ensure visibility
        self._close_btn.setObjectName("closeBtn") # For specific styling if needed

        self._layout.addWidget(self._min_btn)
        self._layout.addWidget(self._max_btn)
        self._layout.addWidget(self._close_btn)

    def _create_btn(self, text, slot):
        btn = QPushButton(text)
        btn.setFixedSize(45, 32)
        btn.setFlat(True)
        btn.clicked.connect(slot)
        btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 0px;
                background-color: transparent;
                font-family: 'Segoe UI Symbol', sans-serif; 
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton#closeBtn:hover {
                background-color: #e81123;
                color: white;
            }
        """)
        return btn

    def _toggle_max(self):
        if self.window().isMaximized():
            self.window().showNormal()
        else:
            self.window().showMaximized()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().windowHandle().startSystemMove()

class ModernWindow(QMainWindow):
    """Base class for modern frameless windows."""

    RESIZE_MARGIN = 6  # Pixels around the edge to trigger resize

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main container to act as the "Window" background
        self._container = QWidget()
        self._container.setObjectName("ModernWindowContainer")
        self.setCentralWidget(self._container)
        
        # Custom Layout
        self._main_layout = QVBoxLayout(self._container)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Title Bar
        self._title_bar = TitleBar(self, title="AuraLens")
        self._main_layout.addWidget(self._title_bar)

        # Content Area (Subclasses typically add to this or replace central widget logic)
        self._content_area = QWidget()
        self._main_layout.addWidget(self._content_area)
        
        # Apply initial theme
        ThemeManager.apply_theme(QApplication.instance(), ThemeManager.get_current_theme())
        self._update_styles()

    def setWindowTitle(self, title: str):
        super().setWindowTitle(title)
        if hasattr(self, '_title_bar'):
             self._title_bar._title_label.setText(title)

    def _update_styles(self):
        """Set container style to match theme window color."""
        # This ensures the rounded corners or border exists if we wanted
        # For now, just robust background
        pass 

    # ── Geometry & Resizing ─────────────────────────────────────────

    def _check_edges(self, pos: QPoint):
        """Determine which edge the mouse is on."""
        edges = Qt.Edge(0)
        rect = self.rect()
        m = self.RESIZE_MARGIN

        # Logic for corner detection
        on_left = pos.x() < m
        on_right = pos.x() > rect.width() - m
        on_top = pos.y() < m
        on_bottom = pos.y() > rect.height() - m

        if on_top: edges |= Qt.Edge.TopEdge
        if on_bottom: edges |= Qt.Edge.BottomEdge
        if on_left: edges |= Qt.Edge.LeftEdge
        if on_right: edges |= Qt.Edge.RightEdge

        return edges

    def _update_cursor(self, edges: Qt.Edge):
        """Update cursor shape based on edges."""
        if edges == (Qt.Edge.TopEdge | Qt.Edge.LeftEdge) or edges == (Qt.Edge.BottomEdge | Qt.Edge.RightEdge):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges == (Qt.Edge.TopEdge | Qt.Edge.RightEdge) or edges == (Qt.Edge.BottomEdge | Qt.Edge.LeftEdge):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._check_edges(event.position().toPoint())
            if edges:
                self.windowHandle().startSystemResize(edges)
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Update cursor when hovering edges (even if not pressed)
        edges = self._check_edges(event.position().toPoint())
        self._update_cursor(edges)
        super().mouseMoveEvent(event)
