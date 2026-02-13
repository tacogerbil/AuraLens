"""QGraphicsView subclass with Ctrl+scroll zoom and click-drag pan."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QGraphicsView

_ZOOM_IN_FACTOR = 1.15
_ZOOM_OUT_FACTOR = 1.0 / _ZOOM_IN_FACTOR


class ZoomableGraphicsView(QGraphicsView):
    """Graphics view with Ctrl+scroll zoom and drag-to-pan."""

    def __init__(self) -> None:
        super().__init__()
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHints(
            self.renderHints()
            | self.renderHints().SmoothPixmapTransform
        )

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom on Ctrl+scroll, normal scroll otherwise."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = _ZOOM_IN_FACTOR if event.angleDelta().y() > 0 else _ZOOM_OUT_FACTOR
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def fit_to_width(self) -> None:
        """Scale view so the scene fits the viewport width."""
        scene = self.scene()
        if scene is None:
            return
        rect = scene.itemsBoundingRect()
        if rect.width() <= 0:
            return
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
