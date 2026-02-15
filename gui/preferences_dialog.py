"""Preferences dialog — all user-configurable settings in a tabbed layout."""

from typing import Optional

import requests
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import Config


class PreferencesDialog(QDialog):
    """Modal dialog for editing all AuraLens settings."""

    def __init__(self, config: Config, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(550)

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._build_api_tab()
        self._build_processing_tab()
        self._build_folders_tab()
        self._build_prompt_section(layout)
        self._build_button_bar(layout)
        self._populate_from_config(config)

    # ── Tab builders ────────────────────────────────────────────────

    def _build_api_tab(self) -> None:
        """API connection settings tab."""
        tab = QWidget()
        form = QVBoxLayout(tab)

        self._api_url = self._add_line_edit(form, "API URL:")
        self._api_key = self._add_line_edit(form, "API Key:")
        self._model_name = self._add_line_edit(form, "Model Name:")

        self._temperature = QDoubleSpinBox()
        self._temperature.setRange(0.0, 2.0)
        self._temperature.setSingleStep(0.1)
        self._temperature.setDecimals(1)
        form.addWidget(QLabel("Temperature:"))
        form.addWidget(self._temperature)

        self._repeat_penalty = QDoubleSpinBox()
        self._repeat_penalty.setRange(1.0, 2.0)
        self._repeat_penalty.setSingleStep(0.1)
        self._repeat_penalty.setDecimals(1)
        self._repeat_penalty.setToolTip(
            "Penalize repeated sequences (1.0=none, 1.2=moderate, 1.5=strong)"
        )
        form.addWidget(QLabel("Repeat Penalty:"))
        form.addWidget(self._repeat_penalty)

        self._presence_penalty = QDoubleSpinBox()
        self._presence_penalty.setRange(0.0, 2.0)
        self._presence_penalty.setSingleStep(0.1)
        self._presence_penalty.setDecimals(1)
        self._presence_penalty.setToolTip(
            "Penalize already-seen tokens (0.0=none, 0.5=moderate, 1.0=strong)"
        )
        form.addWidget(QLabel("Presence Penalty:"))
        form.addWidget(self._presence_penalty)

        self._timeout = self._add_spinbox(form, "Timeout (s):", 1, 600)
        self._max_tokens = self._add_spinbox(form, "Max Tokens:", 1, 32768)

        form.addStretch()
        self._tabs.addTab(tab, "API")

    def _build_processing_tab(self) -> None:
        """Image processing settings tab."""
        tab = QWidget()
        form = QVBoxLayout(tab)

        self._pdf_dpi = self._add_spinbox(form, "PDF DPI:", 72, 600)
        self._max_image_pixels = self._add_spinbox(
            form, "Max Image Pixels:", 10000, 10_000_000
        )
        self._jpeg_quality = self._add_spinbox(form, "JPEG Quality:", 1, 100)

        form.addStretch()
        self._tabs.addTab(tab, "Processing")

    def _build_folders_tab(self) -> None:
        """Inbox/outbox folder settings tab."""
        tab = QWidget()
        form = QVBoxLayout(tab)

        self._inbox_dir, self._inbox_browse = self._add_folder_row(
            form, "Inbox Folder:"
        )
        self._outbox_dir, self._outbox_browse = self._add_folder_row(
            form, "Outbox Folder:"
        )

        form.addStretch()
        self._tabs.addTab(tab, "Folders")

    def _build_prompt_section(self, parent_layout: QVBoxLayout) -> None:
        """System prompt editor below the tabs."""
        parent_layout.addWidget(QLabel("System Prompt:"))
        self._system_prompt = QPlainTextEdit()
        self._system_prompt.setMaximumHeight(120)
        parent_layout.addWidget(self._system_prompt)

    def _build_button_bar(self, parent_layout: QVBoxLayout) -> None:
        """OK/Cancel buttons and Test Connection."""
        bar = QHBoxLayout()

        self._test_btn = QPushButton("Test Connection")
        self._test_btn.clicked.connect(self._test_connection)
        bar.addWidget(self._test_btn)

        bar.addStretch()

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        bar.addWidget(self._button_box)

        parent_layout.addLayout(bar)

    # ── Widget helpers ──────────────────────────────────────────────

    @staticmethod
    def _add_line_edit(layout: QVBoxLayout, label: str) -> QLineEdit:
        """Add a labeled QLineEdit to the layout."""
        layout.addWidget(QLabel(label))
        edit = QLineEdit()
        layout.addWidget(edit)
        return edit

    @staticmethod
    def _add_spinbox(
        layout: QVBoxLayout, label: str, min_val: int, max_val: int
    ) -> QSpinBox:
        """Add a labeled QSpinBox to the layout."""
        layout.addWidget(QLabel(label))
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        layout.addWidget(spin)
        return spin

    def _add_folder_row(
        self, layout: QVBoxLayout, label: str
    ) -> tuple[QLineEdit, QPushButton]:
        """Add a labeled line edit with a Browse button."""
        layout.addWidget(QLabel(label))
        row = QHBoxLayout()
        edit = QLineEdit()
        row.addWidget(edit)
        btn = QPushButton("Browse...")
        btn.clicked.connect(lambda: self._browse_folder(edit))
        row.addWidget(btn)
        layout.addLayout(row)
        return edit, btn

    # ── Populate / Extract ──────────────────────────────────────────

    def _populate_from_config(self, config: Config) -> None:
        """Fill all widgets from a Config instance."""
        self._api_url.setText(config.api_url)
        self._api_key.setText(config.api_key)
        self._model_name.setText(config.model_name)
        self._temperature.setValue(config.temperature)
        self._repeat_penalty.setValue(config.repeat_penalty)
        self._presence_penalty.setValue(config.presence_penalty)
        self._timeout.setValue(config.timeout)
        self._max_tokens.setValue(config.max_tokens)
        self._pdf_dpi.setValue(config.pdf_dpi)
        self._max_image_pixels.setValue(config.max_image_pixels)
        self._jpeg_quality.setValue(config.jpeg_quality)
        self._inbox_dir.setText(config.inbox_dir)
        self._outbox_dir.setText(config.outbox_dir)
        self._system_prompt.setPlainText(config.system_prompt)

    def get_config(self) -> Config:
        """Read all widget values back into a Config dataclass."""
        return Config(
            api_url=self._api_url.text(),
            api_key=self._api_key.text(),
            model_name=self._model_name.text(),
            temperature=self._temperature.value(),
            repeat_penalty=self._repeat_penalty.value(),
            presence_penalty=self._presence_penalty.value(),
            timeout=self._timeout.value(),
            max_tokens=self._max_tokens.value(),
            pdf_dpi=self._pdf_dpi.value(),
            max_image_pixels=self._max_image_pixels.value(),
            jpeg_quality=self._jpeg_quality.value(),
            inbox_dir=self._inbox_dir.text(),
            outbox_dir=self._outbox_dir.text(),
            system_prompt=self._system_prompt.toPlainText(),
        )

    # ── Slots ───────────────────────────────────────────────────────

    def _browse_folder(self, target: QLineEdit) -> None:
        """Open a folder picker and set the target line edit."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            target.setText(folder)

    def _test_connection(self) -> None:
        """Send a minimal request to the configured API URL."""
        url = self._api_url.text().strip()
        key = self._api_key.text().strip()
        if not url:
            QMessageBox.warning(self, "Test Connection", "API URL is empty.")
            return

        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"

        payload = {
            "model": self._model_name.text().strip() or "test",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            QMessageBox.information(
                self, "Test Connection", "Connection successful!"
            )
        except requests.Timeout:
            QMessageBox.critical(
                self,
                "Test Connection",
                f"Connection timed out after {self._timeout.value()} seconds.\n\n"
                "Check your network connection and Firewall settings.",
            )
        except requests.ConnectionError:
            QMessageBox.critical(
                self,
                "Test Connection",
                "Could not connect to the server.\n\n"
                "1. Check the API URL (IP and Port).\n"
                "2. Ensure OpenWebUI is running.\n"
                "3. Check if the server is reachable (Ping/Firewall).",
            )
        except requests.RequestException as err:
            msg = f"Connection failed:\n{err}"
            if err.response is not None:
                try:
                    data = err.response.json()
                    # Common OpenWebUI/OpenAI error fields
                    detail = (
                        data.get("detail")
                        or data.get("error", {}).get("message")
                        or data.get("message")
                    )
                    if detail:
                        msg = f"Server Error:\n{detail}"
                except Exception:
                    # Not JSON or parsing failed
                    pass

            QMessageBox.critical(self, "Test Connection", msg)

    def run(self) -> bool:
        """Show dialog modally and return True if accepted."""
        result = super().exec()
        return result == QDialog.DialogCode.Accepted
