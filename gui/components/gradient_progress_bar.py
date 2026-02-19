from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QBrush
from PySide6.QtWidgets import QProgressBar

class GradientProgressBar(QProgressBar):
    """
    Custom QProgressBar that draws a fixed gradient across its full width,
    'revealing' it as progress increases.
    
    This avoids the default behavior where the gradient is stretched to fit
    the current progress width.
    """
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        
        # 1. Draw Background
        # Hardcoded to match AuraLens UI theme (#f1f5f9)
        bg_color = QColor("#f1f5f9") 
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 4, 4)

        # 2. Calculate Progress Width
        val = self.value()
        max_val = self.maximum()
        min_val = self.minimum()
        
        if max_val <= min_val:
            return
            
        range_val = max_val - min_val
        percent = (val - min_val) / range_val
        width = rect.width() * percent
        
        # Clamp width
        width = max(0, min(width, rect.width()))
        
        if width <= 0:
            return

        # 3. Define Gradient (Fixed to Full Widget Width)
        # Red -> Orange -> Yellow -> Lime -> Green
        gradient = QLinearGradient(0, 0, rect.width(), 0)
        gradient.setColorAt(0.00, QColor("#ef4444"))   # Red
        gradient.setColorAt(0.25, QColor("#f97316"))   # Orange
        gradient.setColorAt(0.50, QColor("#eab308"))   # Yellow
        gradient.setColorAt(0.75, QColor("#84cc16"))   # Lime
        gradient.setColorAt(1.00, QColor("#22c55e"))   # Green

        # 4. Draw Progress Chunk
        # Using the gradient brush with default coordinates maps 0..width to the gradient
        painter.setBrush(QBrush(gradient))
        
        chunk_rect = QRectF(0, 0, width, rect.height())
        painter.drawRoundedRect(chunk_rect, 4, 4)
