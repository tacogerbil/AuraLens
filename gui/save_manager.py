"""File save operations manager.

Handles saving processed text in multiple formats (txt, md, epub).
"""

import logging
from pathlib import Path
from typing import List

from core.book_assembler import BookAssembler
from core.config import Config

logger = logging.getLogger(__name__)


class SaveManager:
    """Manages all file save operations."""

    def __init__(self, config: Config) -> None:
        """Initialize save manager with configuration.

        Args:
            config: Application configuration
        """
        self._config = config
        self._assembler = BookAssembler()

    def get_default_save_dir(self, pdf_path: Path = None) -> str:
        """Get default directory for save dialog.

        Args:
            pdf_path: Optional PDF path to use as fallback

        Returns:
            Directory path as string
        """
        if self._config.outbox_dir:
            return self._config.outbox_dir
        if pdf_path:
            return str(pdf_path.parent)
        return ""

    def save_as_format(
        self,
        texts: List[str],
        path: Path,
        chosen_filter: str
    ) -> None:
        """Save texts in the chosen format.

        Args:
            texts: List of page texts
            path: Output file path
            chosen_filter: Qt file filter string
        """
        title = path.stem

        if path.suffix == ".epub" or "EPUB" in chosen_filter:
            self._assembler.save_as_epub(texts, path, title=title)
        elif path.suffix == ".md" or "Markdown" in chosen_filter:
            self._assembler.save_as_markdown(texts, path)
        else:
            self._assembler.save_to_file(texts, path)

        logger.info("Saved: %s (%d pages)", path.name, len(texts))

    def auto_save_to_outbox(
        self,
        texts: List[str],
        pdf_path: Path
    ) -> None:
        """Auto-save to outbox directory (inbox mode).

        Args:
            texts: List of page texts
            pdf_path: Original PDF path
        """
        if not texts:
            return

        output_path = self._get_auto_save_path(pdf_path)
        self._assembler.save_to_file(texts, output_path)
        logger.info("Auto-saved: %s", output_path)

    def save_incremental(
        self,
        texts: List[str],
        pdf_path: Path
    ) -> None:
        """Save incremental progress.

        Args:
            texts: List of page texts (may include empty slots)
            pdf_path: Original PDF path
        """
        if not pdf_path:
            return

        try:
            output_path = self._get_auto_save_path(pdf_path)
            self._assembler.save_to_file(texts, output_path)
        except Exception as e:
            logger.error("Incremental save failed: %s", e)

    def _get_auto_save_path(self, pdf_path: Path) -> Path:
        """Get path for auto-save operations.

        Args:
            pdf_path: Original PDF path

        Returns:
            Path for auto-save file
        """
        outbox = self._config.outbox_dir.strip()
        if not outbox:
            outbox = str(pdf_path.parent)

        return Path(outbox) / f"{pdf_path.stem}.txt"
