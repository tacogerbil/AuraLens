"""Assemble extracted page texts into a complete book output."""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

DEFAULT_SEPARATOR = "\n\n--- Page {n} ---\n\n"


class BookAssembler:
    """Join page texts with configurable separators."""

    def __init__(self, page_separator: str = DEFAULT_SEPARATOR) -> None:
        self._separator = page_separator

    def assemble(self, page_texts: List[str]) -> str:
        """Combine page texts into a single string with separators."""
        if not page_texts:
            return ""

        if len(page_texts) == 1:
            return page_texts[0]

        parts: List[str] = []
        for i, text in enumerate(page_texts):
            if i > 0:
                parts.append(self._separator.replace("{n}", str(i + 1)))
            parts.append(text)

        return "".join(parts)

    def save_to_file(self, page_texts: List[str], output_path: Path) -> None:
        """Assemble and write to file. I/O boundary."""
        content = self.assemble(page_texts)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        logger.info(
            "Saved %d pages (%d chars) to %s",
            len(page_texts),
            len(content),
            output_path,
        )
