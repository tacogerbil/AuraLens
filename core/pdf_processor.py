"""PDF to PIL Image extraction using pdf2image (poppler)."""

import gc
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PageInfo:
    """Metadata and image for a single extracted PDF page."""

    page_num: int
    total_pages: int
    image: Image.Image


class PDFProcessor:
    """Extract pages from PDFs as PIL Images, one at a time."""

    def __init__(self, dpi: int = 150) -> None:
        self._dpi = dpi

    def get_page_count(self, pdf_path: Path) -> int:
        """Return total page count using poppler's pdfinfo."""
        info = pdfinfo_from_path(str(pdf_path))
        count: int = info.get("Pages", 0)
        logger.info("PDF %s has %d pages", pdf_path.name, count)
        return count

    def extract_page(self, pdf_path: Path, page_num: int) -> Image.Image:
        """Extract a single page as a PIL Image. Pages are 1-indexed."""
        images = convert_from_path(
            str(pdf_path),
            first_page=page_num,
            last_page=page_num,
            fmt="jpeg",
            dpi=self._dpi,
        )
        if not images:
            raise ValueError(f"No image returned for page {page_num}")
        return images[0]

    def iter_pages(self, pdf_path: Path) -> Generator[PageInfo, None, None]:
        """Yield PageInfo for each page, freeing memory after each."""
        self._validate_path(pdf_path)
        total = self.get_page_count(pdf_path)

        for page_num in range(1, total + 1):
            logger.info("Extracting page %d/%d from %s", page_num, total, pdf_path.name)
            image = self.extract_page(pdf_path, page_num)
            yield PageInfo(page_num=page_num, total_pages=total, image=image)

            del image
            gc.collect()

    @staticmethod
    def _validate_path(pdf_path: Path) -> None:
        """Raise FileNotFoundError if path doesn't exist."""
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
