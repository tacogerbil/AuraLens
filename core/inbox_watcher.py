"""Pure-logic inbox scanner — detects new PDF files in a directory.

No Qt imports. The GUI adapter (gui/inbox_monitor.py) wraps this
with QFileSystemWatcher for event-driven file detection.
"""

import logging
from pathlib import Path
from typing import List, Set

logger = logging.getLogger(__name__)

_PDF_GLOB = "*.pdf"


class InboxScanner:
    """Track PDF files in a directory and identify new arrivals.

    Maintains a set of 'seen' file paths. Each call to scan()
    returns only files not previously seen.
    """

    def __init__(self) -> None:
        self._seen: Set[Path] = set()

    @property
    def seen_count(self) -> int:
        """Number of files already seen."""
        return len(self._seen)

    def scan(self, inbox_dir: Path) -> List[Path]:
        """Return PDF files in inbox_dir that haven't been seen yet.

        Resolves paths to avoid symlink/case duplicates.
        Returns sorted by name for deterministic ordering.
        """
        if not inbox_dir.is_dir():
            logger.warning("Inbox directory does not exist: %s", inbox_dir)
            return []

        current = {p.resolve() for p in inbox_dir.glob(_PDF_GLOB) if p.is_file()}
        new_files = sorted(current - self._seen)
        self._seen.update(new_files)

        if new_files:
            logger.info(
                "Found %d new PDF(s) in %s", len(new_files), inbox_dir,
            )

        return new_files

    def mark_seen(self, path: Path) -> None:
        """Manually mark a file as seen (e.g. already processed)."""
        self._seen.add(path.resolve())

    def reset(self) -> None:
        """Clear all seen state. Next scan returns everything."""
        self._seen.clear()
        logger.debug("InboxScanner reset — seen set cleared")
