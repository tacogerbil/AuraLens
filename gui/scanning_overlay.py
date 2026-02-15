"""Retro-style scanning progress overlay widget."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ScanningOverlay(QWidget):
    """Retro-style 'SCANNING...' progress overlay with animated bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._progress = 0.0  # 0.0 to 1.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.setInterval(50)  # 20 FPS
        
        self.hide()

    def start(self) -> None:
        """Show overlay and start progress animation."""
        self._progress = 0.0
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self) -> None:
        """Hide overlay and stop animation."""
        self._timer.stop()
        self.hide()

    def _animate(self) -> None:
        """Increment progress and loop."""
        self._progress += 0.02  # 2% per frame
        if self._progress >= 1.0:
            self._progress = 0.0
        self.update()

    def paintEvent(self, event) -> None:
        """Draw retro progress bar with red-to-green gradient."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 180))

        # Retro font for "SCANNING..."
        font = QFont("Courier New", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        
        text_rect = self.rect()
        text_rect.setHeight(100)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "SCANNING...")

        # Progress bar dimensions
        bar_width = 400
        bar_height = 40
        bar_x = (self.width() - bar_width) // 2
        bar_y = (self.height() // 2) + 20

        # Outer border (retro style)
        painter.setPen(QPen(QColor(200, 200, 200), 3))
        painter.drawRect(bar_x - 5, bar_y - 5, bar_width + 10, bar_height + 10)

        # Inner background
        painter.fillRect(bar_x, bar_y, bar_width, bar_height, QColor(40, 40, 40))

        # Progress fill with red-to-green gradient
        fill_width = int(bar_width * self._progress)
        if fill_width > 0:
            # Calculate color based on progress (red -> yellow -> green)
            if self._progress < 0.5:
                # Red to yellow
                r = 255
                g = int(255 * (self._progress * 2))
                b = 0
            else:
                # Yellow to green
                r = int(255 * (2 - self._progress * 2))
                g = 255
                b = 0
            
            # Draw filled bars (retro segmented look)
            segment_width = 20
            gap = 2
            num_segments = fill_width // (segment_width + gap)
            
            for i in range(num_segments):
                seg_x = bar_x + i * (segment_width + gap)
                painter.fillRect(
                    seg_x, bar_y, segment_width, bar_height,
                    QColor(r, g, b)
                )
