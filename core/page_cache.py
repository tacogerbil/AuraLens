"""Cache folder management for extracted PDF page images."""

import logging
import re
from pathlib import Path
from typing import List

from core.image_utils import encode_to_jpeg, resize_for_vlm
from core.pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

_CACHE_ROOT = Path(__file__).resolve().parent.parent / "cache"
_PAGE_PATTERN = re.compile(r"^page_(\d{3})\.jpg$")


def cache_dir_for_pdf(pdf_path: Path) -> Path:
    """Return execution/cache/{stem}/ for the given PDF."""
    return _CACHE_ROOT / pdf_path.stem


def page_image_path(cache_dir: Path, page_num: int) -> Path:
    """Return path for page_NNN.jpg (1-indexed, zero-padded to 3 digits)."""
    return cache_dir / f"page_{page_num:03d}.jpg"


def page_text_path(cache_dir: Path, page_num: int) -> Path:
    """Return path for page_NNN.txt (1-indexed, zero-padded to 3 digits)."""
    return cache_dir / f"page_{page_num:03d}.txt"


def save_page_text(cache_dir: Path, page_num: int, text: str) -> None:
    """Save OCR text for a single page to cache."""
    text_path = page_text_path(cache_dir, page_num)
    text_path.write_text(text, encoding="utf-8")
    logger.debug("Saved page %d text to %s", page_num, text_path)


def load_page_text(cache_dir: Path, page_num: int) -> str:
    """Load OCR text for a single page from cache.
    
    Returns empty string if file doesn't exist.
    """
    text_path = page_text_path(cache_dir, page_num)
    if not text_path.exists():
        return ""
    return text_path.read_text(encoding="utf-8")


def list_cached_page_texts(cache_dir: Path) -> List[str]:
    """Load all page texts in order, returning empty strings for missing pages."""
    page_images = list_cached_pages(cache_dir)
    texts = []
    for i, _ in enumerate(page_images, start=1):
        texts.append(load_page_text(cache_dir, i))
    return texts



def list_cached_pages(cache_dir: Path) -> List[Path]:
    """Return sorted list of page_NNN.jpg files in cache dir."""
    if not cache_dir.is_dir():
        return []

    matches = [
        p for p in sorted(cache_dir.iterdir())
        if _PAGE_PATTERN.match(p.name)
    ]
    return matches


def extract_single_page(
    pdf_path: Path,
    page_num: int,
    output_path: Path,
    dpi: int,
    max_pixels: int,
    jpeg_quality: int,
) -> None:
    """Extract one page from PDF, resize for VLM, save as JPEG.

    Skips if output_path already exists (resume support).
    """
    if output_path.exists():
        logger.debug("Page %d already cached at %s", page_num, output_path)
        return

    processor = PDFProcessor(dpi=dpi)
    image = processor.extract_page(pdf_path, page_num)
    resized = resize_for_vlm(image, max_pixels)
    jpeg_bytes = encode_to_jpeg(resized, quality=jpeg_quality)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(jpeg_bytes)
    logger.info("Cached page %d to %s", page_num, output_path)
