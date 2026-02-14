"""Inbox monitoring and auto-processing coordinator.

Manages PDF queue and auto-processing workflow.
"""

import logging
from collections import deque
from pathlib import Path
from typing import Deque, Optional

from PySide6.QtCore import QObject, Signal

from core.config import Config
from core.config_validator import ConfigValidator

logger = logging.getLogger(__name__)


class InboxCoordinator(QObject):
    """Coordinates inbox queue and auto-processing."""

    # Signals
    pdf_queued = Signal(Path, int)  # pdf_path, queue_size
    processing_requested = Signal(Path)  # pdf_path to process
    status_updated = Signal(str)  # status message

    def __init__(self, config: Config, parent: QObject = None) -> None:
        """Initialize inbox coordinator.

        Args:
            config: Application configuration
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self._config = config
        self._queue: Deque[Path] = deque()
        self._is_processing = False

    def queue_pdf(self, pdf_path: Path) -> None:
        """Add PDF to processing queue.

        Args:
            pdf_path: Path to PDF file
        """
        self._queue.append(pdf_path)
        queue_size = len(self._queue)
        logger.info("Inbox: queued %s (%d in queue)", pdf_path.name, queue_size)

        self.pdf_queued.emit(pdf_path, queue_size)
        self.status_updated.emit(
            f"Inbox: {pdf_path.name} queued ({queue_size} pending)"
        )

    def process_next_if_ready(self, is_processing: bool) -> None:
        """Process next queued PDF if system is idle and ready.

        Args:
            is_processing: Whether system is currently processing
        """
        self._is_processing = is_processing

        if self._is_processing or not self._queue:
            return

        if not self._can_auto_process():
            self.status_updated.emit(
                "Inbox: waiting — configure model and API first"
            )
            return

        pdf_path = self._queue.popleft()
        if not pdf_path.exists():
            logger.warning("Inbox: file vanished: %s", pdf_path)
            self.process_next_if_ready(is_processing=False)
            return

        logger.info("Inbox: starting auto-process for %s", pdf_path.name)
        self.processing_requested.emit(pdf_path)
        self.status_updated.emit(f"Auto-processing: {pdf_path.name}")

    def get_queue_size(self) -> int:
        """Get current queue size.

        Returns:
            Number of PDFs in queue
        """
        return len(self._queue)

    def _can_auto_process(self) -> bool:
        """Check if config is sufficient for auto-processing.

        Returns:
            True if config has required fields
        """
        return ConfigValidator.can_auto_process(self._config)
