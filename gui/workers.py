"""QThread workers for two-stage PDF processing.

Stage 1: ExtractionWorker — PDF → JPEG images on disk (fast, no VLM).
Stage 2: OCRWorker — JPEG images → VLM → extracted text (slow).
"""

import logging
from pathlib import Path
from typing import List, Set, Tuple

from PySide6.QtCore import QThread, Signal

from core.image_utils import to_base64_data_uri
from core.page_cache import (
    cache_dir_for_pdf,
    extract_single_page,
    page_image_path,
)
from core.pdf_processor import PDFProcessor
from core.vlm_client import VLMClient

logger = logging.getLogger(__name__)


class ExtractionWorker(QThread):
    """Extract all PDF pages to cache folder as JPEG images.

    Fast operation (~50ms/page). Creates execution/cache/{stem}/page_NNN.jpg.
    Skips pages that already exist on disk (resume support).
    """

    page_extracted = Signal(int, int)      # page_num, total
    extraction_finished = Signal(str, int)  # cache_dir path, total pages

    def __init__(
        self,
        pdf_path: Path,
        dpi: int,
        max_pixels: int,
        jpeg_quality: int,
    ) -> None:
        super().__init__()
        self._pdf_path = pdf_path
        self._dpi = dpi
        self._max_pixels = max_pixels
        self._jpeg_quality = jpeg_quality
        self._cancelled = False

    def cancel(self) -> None:
        """Request cooperative cancellation."""
        self._cancelled = True

    def run(self) -> None:
        """Extract each page to the cache folder."""
        cache_dir = cache_dir_for_pdf(self._pdf_path)
        processor = PDFProcessor(dpi=self._dpi)
        total = processor.get_page_count(self._pdf_path)

        for page_num in range(1, total + 1):
            if self._cancelled:
                logger.info("Extraction cancelled at page %d", page_num)
                break

            output = page_image_path(cache_dir, page_num)
            if output.exists():
                logger.info("Skipping extraction for page %d (exists)", page_num)
            else:
                extract_single_page(
                    self._pdf_path, page_num, output,
                    dpi=self._dpi,
                    max_pixels=self._max_pixels,
                    jpeg_quality=self._jpeg_quality,
                )
            self.page_extracted.emit(page_num, total)

        self.extraction_finished.emit(str(cache_dir), total)


class OCRWorker(QThread):
    """Send cached page images to VLM for text extraction.

    Reads JPEG files from disk, converts to base64, sends to VLM API.
    """

    page_started = Signal(int, int)        # page_num, total
    page_completed = Signal(int, int, str)  # page_num, total, text
    page_error = Signal(int, str)          # page_num, error_msg
    processing_finished = Signal()

    def __init__(
        self,
        page_paths: List[Path],
        api_url: str,
        api_key: str,
        model_name: str,
        timeout: int,
        max_tokens: int,
        temperature: float,
        system_prompt: str,
        user_prompt: str,
        repeat_penalty: float = 1.0,
        presence_penalty: float = 0.0,
        enable_thinking: bool = False,
        skip_pages: Set[int] = None,
    ) -> None:
        super().__init__()
        self._page_paths = page_paths
        self._api_url = api_url
        self._api_key = api_key
        self._model_name = model_name
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._system_prompt = system_prompt
        self._user_prompt = user_prompt
        self._repeat_penalty = repeat_penalty
        self._presence_penalty = presence_penalty
        self._enable_thinking = enable_thinking
        self._skip_pages = skip_pages or set()
        self._cancelled = False

    def cancel(self) -> None:
        """Request cooperative cancellation. Current page finishes first."""
        self._cancelled = True

    def run(self) -> None:
        """Process each cached image through the VLM."""
        client = VLMClient(
            api_url=self._api_url,
            api_key=self._api_key,
            model_name=self._model_name,
            timeout=self._timeout,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            repeat_penalty=self._repeat_penalty,
            presence_penalty=self._presence_penalty,
            enable_thinking=self._enable_thinking,
        )

        try:
            self._process_pages(client)
        finally:
            self.processing_finished.emit()

    def _process_pages(self, client: VLMClient) -> None:
        """Core loop — read image from disk, send to VLM."""
        total = len(self._page_paths)

        for idx, page_path in enumerate(self._page_paths):
            page_num = idx + 1
            if self._cancelled:
                logger.info("OCR cancelled at page %d", page_num)
                break

            self.page_started.emit(page_num, total)

            if page_num in self._skip_pages:
                logger.info("Skipping OCR for page %d (already done)", page_num)
                # Emit empty/placeholder text so UI progresses
                self.page_completed.emit(page_num, total, "")
                continue

            try:
                text = self._ocr_single_page(client, page_path)
                self.page_completed.emit(page_num, total, text)
            except Exception as exc:
                logger.error("OCR page %d failed: %s", page_num, exc)
                self.page_error.emit(page_num, str(exc))

    def _ocr_single_page(self, client: VLMClient, page_path: Path) -> str:
        """Read JPEG from disk, convert to data URI, send to VLM."""
        jpeg_bytes = page_path.read_bytes()
        data_uri = to_base64_data_uri(jpeg_bytes)
        return client.process_image(
            data_uri,
            user_prompt=self._user_prompt,
            system_prompt=self._system_prompt,
        )
