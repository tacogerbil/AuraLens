from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, 
    QLineEdit, QCheckBox, QGroupBox, QScrollArea, QSpinBox
)
from PySide6.QtCore import Qt, Signal
import logging

from core.config import Config

logger = logging.getLogger(__name__)

class SettingsPage(QWidget):
    """
    Application Settings Page (converted from PreferencesDialog).
    """
    
    home_requested = Signal()
    config_saved = Signal(Config)

    def __init__(self, config: Config):
        super().__init__()
        self._config = config
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Settings")
        header.setObjectName("mainTitle") # Reuse style
        layout.addWidget(header)
        
        # Valid Content Card
        content_card = QFrame()
        content_card.setStyleSheet("background: white; border-radius: 16px;")
        card_layout = QVBoxLayout(content_card)
        card_layout.setContentsMargins(30,30,30,30)
        
        # 1. API Keys
        api_group = QGroupBox("API Keys")
        api_layout = QGridLayout(api_group)
        
        api_layout.addWidget(QLabel("API Key:"), 0, 0)
        self._api_key_edit = QLineEdit(config.api_key)
        api_layout.addWidget(self._api_key_edit, 0, 1)
        
        card_layout.addWidget(api_group)
        
        # 2. Paths
        path_group = QGroupBox("Paths")
        path_layout = QGridLayout(path_group)
        
        path_layout.addWidget(QLabel("Inbox Dir:"), 0, 0)
        self._inbox_edit = QLineEdit(config.inbox_dir)
        path_layout.addWidget(self._inbox_edit, 0, 1)
        
        path_layout.addWidget(QLabel("Outbox Dir:"), 1, 0)
        self._outbox_edit = QLineEdit(config.outbox_dir)
        path_layout.addWidget(self._outbox_edit, 1, 1)
        
        card_layout.addWidget(path_group)
        
        # 3. Model Params
        model_group = QGroupBox("Model Parameters")
        model_layout = QGridLayout(model_group)
        
        model_layout.addWidget(QLabel("Temperature:"), 0, 0)
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 1.0)
        self._temp_spin.setSingleStep(0.1)
        self._temp_spin.setValue(config.temperature)
        model_layout.addWidget(self._temp_spin, 0, 1)
        
        card_layout.addWidget(model_group)
        card_layout.addStretch()
        
        layout.addWidget(content_card)
        
        # Bottom Bar
        bottom_bar = QHBoxLayout()
        back_btn = QPushButton("← Back to Dashboard")
        back_btn.clicked.connect(self.home_requested.emit)
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self._on_save)
        # Style specific for save
        save_btn.setStyleSheet("background-color: #10b981;") 
        
        bottom_bar.addWidget(back_btn)
        bottom_bar.addStretch()
        bottom_bar.addWidget(save_btn)
        
        layout.addLayout(bottom_bar)

    def _on_save(self):
        """Update config object and emit saved signal."""
        self._config.api_key = self._api_key_edit.text()
        self._config.inbox_dir = self._inbox_edit.text()
        self._config.outbox_dir = self._outbox_edit.text()
        self._config.temperature = self._temp_spin.value()
        
        self.config_saved.emit(self._config)
        self.home_requested.emit()

from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout # Lazy import fix
