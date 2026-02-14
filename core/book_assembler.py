"""Assemble extracted page texts into a complete book output.

Supports plain text, Markdown, and EPUB formats.
"""


import logging
import re
from pathlib import Path
from typing import List, Set

from ebooklib import epub

logger = logging.getLogger(__name__)

DEFAULT_SEPARATOR = "\n\n--- Page {n} ---\n\n"
_PAGE_PATTERN = re.compile(r"--- Page (\d+) ---")



class BookAssembler:
    """Join page texts with configurable separators."""

    def __init__(self, page_separator: str = DEFAULT_SEPARATOR) -> None:
        self._separator = page_separator

    def get_completed_pages(self, output_path: Path) -> Set[int]:
        """Scan file for page separators to identify completed pages."""
        if not output_path.exists():
            return set()

        try:
            content = output_path.read_text(encoding="utf-8")
            # Pattern matches standard separator: --- Page 123 ---
            # We assume user hasn't manually messed with the file too much
            found = _PAGE_PATTERN.findall(content)
            return {int(p) for p in found}
        except Exception as e:
            logger.warning("Failed to scan completed pages in %s: %s", output_path, e)
            return set()

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
        """Assemble and write to .txt file. I/O boundary."""
        content = self.assemble(page_texts)
        self._atomic_write(output_path, content)
        logger.info(
            "Saved %d pages (%d chars) to %s",
            len(page_texts),
            len(content),
            output_path,
        )

    def assemble_markdown(self, page_texts: List[str]) -> str:
        """Combine page texts with Markdown horizontal rules as separators."""
        if not page_texts:
            return ""
        return "\n\n---\n\n".join(page_texts)

    def save_as_markdown(
        self, page_texts: List[str], output_path: Path
    ) -> None:
        """Save as .md with horizontal rule page breaks."""
        content = self.assemble_markdown(page_texts)
        self._atomic_write(output_path, content)
        logger.info("Saved Markdown: %d pages to %s", len(page_texts), output_path)

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write to temp file and rename to ensure atomic update."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(path)
        except OSError:
            # Fallback if rename fails (e.g. file locked on Windows)
            # We try direct write which might truncate if it crashes, but better than nothing
            logger.warning("Atomic rename failed for %s, falling back to direct write", path)
            path.write_text(content, encoding="utf-8")

    def save_as_epub(
        self,
        page_texts: List[str],
        output_path: Path,
        title: str = "Untitled",
        author: str = "AuraLens",
    ) -> None:
        """Save as .epub with one chapter per page. Text only, no images."""
        book = epub.EpubBook()
        book.set_identifier("auralens-" + title.replace(" ", "-").lower())
        book.set_title(title)
        book.set_language("en")
        book.add_author(author)

        chapters = self._build_epub_chapters(page_texts)
        for chapter in chapters:
            book.add_item(chapter)

        book.toc = chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav"] + chapters

        output_path.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(output_path), book)
        logger.info("Saved EPUB: %d chapters to %s", len(chapters), output_path)

    @staticmethod
    def _build_epub_chapters(page_texts: List[str]) -> List[epub.EpubHtml]:
        """Create one EpubHtml chapter per page."""
        chapters: List[epub.EpubHtml] = []
        for i, text in enumerate(page_texts):
            page_num = i + 1
            chapter = epub.EpubHtml(
                title=f"Page {page_num}",
                file_name=f"page_{page_num:03d}.xhtml",
                lang="en",
            )
            escaped = text.replace("&", "&amp;").replace("<", "&lt;")
            paragraphs = escaped.split("\n\n")
            html_body = "".join(f"<p>{p}</p>" for p in paragraphs if p.strip())
            chapter.content = f"<h2>Page {page_num}</h2>{html_body}"
            chapters.append(chapter)
        return chapters
