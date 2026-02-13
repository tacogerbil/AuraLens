"""QFileSystemWatcher adapter for inbox monitoring.

Watches a configured directory for new PDF files.
Uses QFileSystemWatcher for event-driven detection, plus a fallback
QTimer poll for network drives where inotify doesn't work.
"""

import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, Signal

from core.inbox_watcher import InboxScanner

logger = logging.getLogger(__name__)

_POLL_INTERVAL_MS = 5_000  # 5-second fallback poll


class InboxMonitor(QObject):
    """Watch inbox_dir and emit signals when new PDFs appear.

    Signals:
        pdf_detected(Path): Emitted once per new PDF file found.
    """

    pdf_detected = Signal(object)  # Path (Signal doesn't support Path directly)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._scanner = InboxScanner()
        self._inbox_dir: Optional[Path] = None
        self._enabled = False

        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_directory_changed)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_poll)

    @property
    def is_enabled(self) -> bool:
        """Whether monitoring is currently active."""
        return self._enabled

    @property
    def inbox_dir(self) -> Optional[Path]:
        """Currently watched directory, or None."""
        return self._inbox_dir

    def start(self, inbox_dir: str) -> None:
        """Begin watching the given directory for new PDFs.

        If inbox_dir is empty or invalid, monitoring stays disabled.
        """
        self.stop()

        if not inbox_dir.strip():
            logger.debug("InboxMonitor: empty path, not starting")
            return

        path = Path(inbox_dir)
        if not path.is_dir():
            logger.warning("InboxMonitor: directory does not exist: %s", path)
            return

        self._inbox_dir = path
        self._scanner.reset()
        self._enabled = True

        self._watcher.addPath(str(path))
        self._timer.start(_POLL_INTERVAL_MS)

        # Initial scan to pick up files already present
        self._emit_new_files()

        logger.info("InboxMonitor started: %s", path)

    def stop(self) -> None:
        """Stop watching. Clears all state."""
        if self._inbox_dir and str(self._inbox_dir) in self._watcher.directories():
            self._watcher.removePath(str(self._inbox_dir))

        self._timer.stop()
        self._enabled = False
        self._inbox_dir = None
        self._scanner.reset()
        logger.debug("InboxMonitor stopped")

    def update_path(self, new_inbox_dir: str) -> None:
        """Change the watched directory. Restarts monitoring if non-empty."""
        self.stop()
        if new_inbox_dir.strip():
            self.start(new_inbox_dir)

    # ── Internal ─────────────────────────────────────────────────────

    def _on_directory_changed(self, _path: str) -> None:
        """QFileSystemWatcher callback — directory contents changed."""
        self._emit_new_files()

    def _on_poll(self) -> None:
        """Fallback timer poll for network drives."""
        if self._enabled and self._inbox_dir:
            self._emit_new_files()

    def _emit_new_files(self) -> None:
        """Scan and emit signal for each new PDF."""
        if not self._inbox_dir:
            return

        new_files: List[Path] = self._scanner.scan(self._inbox_dir)
        for pdf_path in new_files:
            logger.info("New PDF detected: %s", pdf_path.name)
            self.pdf_detected.emit(pdf_path)
