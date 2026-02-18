from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt

class DimmerOverlay(QWidget):
    """
    A semi-transparent overlay to dim the parent window content.
    Used to create modal focus separation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False) # Catch clicks? Or let them pass? 
        # Usually a modal dimmer blocks interaction with background.
        
        self.hide()
        
        # Determine background color based on theme eventually, but black semi-transparent is standard.
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 100)) # 40% opacity black
        self.setPalette(pal)
        
    def show_dimmer(self):
        """Show and resize to cover parent."""
        if self.parentWidget():
            self.resize(self.parentWidget().size())
            self.raise_()
            self.show()
            
    def hide_dimmer(self):
        self.hide()
        
    # Ensure it stays resized with parent
    # The parent (MainWindow) needs to call resize on this, 
    # OR we install an event filter. 
    # For simplicity, we'll handle resizing in the MainWindow resizeEvent.
