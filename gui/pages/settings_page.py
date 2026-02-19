from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QLineEdit, QGroupBox, QScrollArea, QSpinBox, QDoubleSpinBox,
    QGridLayout, QTextEdit
)
from PySide6.QtCore import Signal
import logging

from core.config import Config

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """Application Settings Page — exposes all user-configurable Config fields."""

    home_requested = Signal()
    config_saved = Signal(Config)

    def __init__(self, config: Config):
        super().__init__()
        self._config = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QLabel("Settings")
        header.setObjectName("mainTitle")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.addWidget(self._build_api_group(config))
        content_layout.addWidget(self._build_model_group(config))
        content_layout.addWidget(self._build_processing_group(config))
        content_layout.addWidget(self._build_prompts_group(config))
        content_layout.addWidget(self._build_paths_group(config))
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        bottom_bar = QHBoxLayout()
        back_btn = QPushButton("← Back to Dashboard")
        back_btn.setObjectName("navLink")
        back_btn.clicked.connect(self.home_requested.emit)
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self._on_save)
        save_btn.setStyleSheet("background-color: #10b981;")
        bottom_bar.addWidget(back_btn)
        bottom_bar.addStretch()
        bottom_bar.addWidget(save_btn)
        layout.addLayout(bottom_bar)

    # ── Group builders ───────────────────────────────────────────────

    def _build_api_group(self, config: Config) -> QGroupBox:
        group = QGroupBox("API Connection")
        grid = QGridLayout(group)
        self._api_url_edit = QLineEdit(config.api_url)
        self._api_key_edit = QLineEdit(config.api_key)
        self._model_name_edit = QLineEdit(config.model_name)
        _add_rows(grid, [
            ("API URL:", self._api_url_edit),
            ("API Key:", self._api_key_edit),
            ("Model Name:", self._model_name_edit),
        ])
        return group

    def _build_model_group(self, config: Config) -> QGroupBox:
        group = QGroupBox("Model Parameters")
        grid = QGridLayout(group)
        self._temp_spin = _double_spin(0.0, 2.0, 0.1, config.temperature)
        self._repeat_spin = _double_spin(0.0, 2.0, 0.1, config.repeat_penalty)
        self._presence_spin = _double_spin(0.0, 2.0, 0.1, config.presence_penalty)
        self._max_tokens_spin = _int_spin(1, 32768, config.max_tokens)
        self._timeout_spin = _int_spin(10, 600, config.timeout)
        _add_rows(grid, [
            ("Temperature:", self._temp_spin),
            ("Repeat Penalty:", self._repeat_spin),
            ("Presence Penalty:", self._presence_spin),
            ("Max Tokens:", self._max_tokens_spin),
            ("Timeout (s):", self._timeout_spin),
        ])
        return group

    def _build_processing_group(self, config: Config) -> QGroupBox:
        group = QGroupBox("PDF Processing")
        grid = QGridLayout(group)
        self._dpi_spin = _int_spin(72, 600, config.pdf_dpi)
        self._pixels_spin = _int_spin(100_000, 10_000_000, config.max_image_pixels)
        self._quality_spin = _int_spin(1, 100, config.jpeg_quality)
        _add_rows(grid, [
            ("PDF DPI:", self._dpi_spin),
            ("Max Image Pixels:", self._pixels_spin),
            ("JPEG Quality:", self._quality_spin),
        ])
        return group

    def _build_prompts_group(self, config: Config) -> QGroupBox:
        group = QGroupBox("Prompts")
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel("System Prompt:"))
        self._system_prompt_edit = QTextEdit(config.system_prompt)
        self._system_prompt_edit.setFixedHeight(100)
        layout.addWidget(self._system_prompt_edit)
        layout.addWidget(QLabel("User Prompt:"))
        self._user_prompt_edit = QTextEdit(config.user_prompt)
        self._user_prompt_edit.setFixedHeight(60)
        layout.addWidget(self._user_prompt_edit)
        return group

    def _build_paths_group(self, config: Config) -> QGroupBox:
        group = QGroupBox("Paths")
        grid = QGridLayout(group)
        self._inbox_edit = QLineEdit(config.inbox_dir)
        self._outbox_edit = QLineEdit(config.outbox_dir)
        _add_rows(grid, [
            ("Inbox Dir:", self._inbox_edit),
            ("Outbox Dir:", self._outbox_edit),
        ])
        return group

    # ── Save ────────────────────────────────────────────────────────

    def _on_save(self) -> None:
        """Write all widget values back to config and emit saved signal."""
        self._config.api_url = self._api_url_edit.text()
        self._config.api_key = self._api_key_edit.text()
        self._config.model_name = self._model_name_edit.text()
        self._config.temperature = self._temp_spin.value()
        self._config.repeat_penalty = self._repeat_spin.value()
        self._config.presence_penalty = self._presence_spin.value()
        self._config.max_tokens = self._max_tokens_spin.value()
        self._config.timeout = self._timeout_spin.value()
        self._config.pdf_dpi = self._dpi_spin.value()
        self._config.max_image_pixels = self._pixels_spin.value()
        self._config.jpeg_quality = self._quality_spin.value()
        self._config.system_prompt = self._system_prompt_edit.toPlainText()
        self._config.user_prompt = self._user_prompt_edit.toPlainText()
        self._config.inbox_dir = self._inbox_edit.text()
        self._config.outbox_dir = self._outbox_edit.text()
        self.config_saved.emit(self._config)
        self.home_requested.emit()


# ── Module-level pure factory helpers ────────────────────────────────────────

def _add_rows(grid: QGridLayout, rows: list) -> None:
    """Populate a QGridLayout with (label_text, widget) pairs."""
    for row_idx, (label, widget) in enumerate(rows):
        grid.addWidget(QLabel(label), row_idx, 0)
        grid.addWidget(widget, row_idx, 1)


def _double_spin(
    min_val: float, max_val: float, step: float, value: float
) -> QDoubleSpinBox:
    """Create a configured QDoubleSpinBox."""
    spin = QDoubleSpinBox()
    spin.setRange(min_val, max_val)
    spin.setSingleStep(step)
    spin.setValue(value)
    return spin


def _int_spin(min_val: int, max_val: int, value: int) -> QSpinBox:
    """Create a configured QSpinBox."""
    spin = QSpinBox()
    spin.setRange(min_val, max_val)
    spin.setValue(value)
    return spin
