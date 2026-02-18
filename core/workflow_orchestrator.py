"""Pure orchestration logic for PDF processing workflow.

Coordinates extraction → OCR → save pipeline without Qt dependencies.
"""

import logging
from pathlib import Path
from typing import List, Set

from core.book_assembler import BookAssembler
from core.config import Config
from core.page_cache import cache_dir_for_pdf, list_cached_pages

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Coordinates PDF processing workflow stages."""

    def __init__(self, config: Config) -> None:
        """Initialize orchestrator with configuration.

        Args:
            config: Application configuration
        """
        self._config = config

    def get_cache_dir_for_pdf(self, pdf_path: Path) -> Path:
        """Get cache directory for a PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Path to cache directory
        """
        return cache_dir_for_pdf(pdf_path)

    def get_extraction_params(self) -> dict:
        """Get parameters for extraction worker.

        Returns:
            Dictionary of extraction parameters
        """
        return {
            "dpi": self._config.pdf_dpi,
            "max_pixels": self._config.max_image_pixels,
            "jpeg_quality": self._config.jpeg_quality,
        }

    def get_ocr_params(self) -> dict:
        """Get parameters for OCR worker.

        Returns:
            Dictionary of OCR parameters
        """
        model_name = self._config.model_name
        enable_thinking = self._get_minicpm_thinking(model_name)
        max_tokens = self._config.max_tokens

        if enable_thinking:
            thinking_budget = self._get_thinking_budget(model_name)
            max_tokens += thinking_budget

        return {
            "api_url": self._config.api_url,
            "api_key": self._config.api_key,
            "model_name": model_name,
            "timeout": self._config.timeout,
            "max_tokens": max_tokens,
            "temperature": self._config.temperature,
            "system_prompt": self._config.system_prompt,
            "user_prompt": self._config.user_prompt,  # Now configurable from settings
            "repeat_penalty": self._config.repeat_penalty,
            "presence_penalty": self._config.presence_penalty,
            "enable_thinking": enable_thinking,
        }

    def create_vlm_client(self, overrides: dict = None) -> "VLMClient":
        """Create a configured VLMClient instance.

        Args:
            overrides: Optional dictionary of parameters to override defaults.
                       Useful for testing prompts without changing global config.

        Returns:
            Configured VLMClient instance.
        """
        from core.vlm_client import VLMClient

        params = self.get_ocr_params()
        if overrides:
            params.update(overrides)

        # Remove 'system_prompt' and 'user_prompt' from init params
        # as VLMClient.__init__ doesn't take them (they go to process_image)
        # BUT get_ocr_params returns them.
        # We need to filter them out for __init__, OR update VLMClient to take them?
        # VLMClient __init__ signature:
        # (api_url, api_key, model_name, timeout, max_tokens, temperature, repeat_penalty, presence_penalty, enable_thinking)
        # It does NOT take prompts in init.
        
        init_params = {
            k: v for k, v in params.items()
            if k in [
                "api_url", "api_key", "model_name", "timeout", "max_tokens",
                "temperature", "repeat_penalty", "presence_penalty", "enable_thinking"
            ]
        }
        
        return VLMClient(**init_params)

    def _get_minicpm_thinking(self, model_name: str) -> bool:
        """Check if deep thinking is enabled for this model."""
        settings = self._config.minicpm_settings.get(model_name, {})
        return settings.get("enable_thinking", False)

    def _get_thinking_budget(self, model_name: str) -> int:
        """Get thinking token budget for this model (default 4096)."""
        settings = self._config.minicpm_settings.get(model_name, {})
        return settings.get("thinking_budget", 4096)

    def is_fully_cached(self, cache_dir: Path) -> bool:
        """Check if all pages have both images and text in cache.
        
        Args:
            cache_dir: Cache directory to check
            
        Returns:
            True if cache is complete (all pages have images and text),
            False otherwise (empty cache, missing images, or missing text)
        """
        from core.page_cache import page_text_path, get_page_number
        
        page_images = list_cached_pages(cache_dir)
        if not page_images:
            return False
        
        # Verify all pages have corresponding text files
        for image_path in page_images:
            page_num = get_page_number(image_path.name)
            if page_num == -1:
                continue
                
            text_file = page_text_path(cache_dir, page_num)
            # Relaxed check: if text file exists (even if empty), it's considered valid
            if not text_file.exists():
                return False
        
        logger.info(
            "Cache complete: %d pages with images and text in %s",
            len(page_images),
            cache_dir
        )
        return True

    def calculate_resume_pages(
        self, cache_dir: Path
    ) -> Set[int]:
        """Calculate which pages to skip during OCR resume.

        Args:
            cache_dir: Cache directory containing page files

        Returns:
            Set of page numbers already completed
        """
        from core.page_cache import page_text_path, get_page_number
        
        completed = set()
        page_images = list_cached_pages(cache_dir)
        
        for image_path in page_images:
            page_num = get_page_number(image_path.name)
            if page_num == -1:
                continue
                
            text_file = page_text_path(cache_dir, page_num)
            if text_file.exists():
                completed.add(page_num)
        
        if completed:
            logger.info(
                "Resume: skipping %d pages with existing text: %s",
                len(completed),
                sorted(completed)
            )
        return completed

    def get_page_paths_from_cache(self, cache_dir: Path) -> List[Path]:
        """Get list of cached page image paths.

        Args:
            cache_dir: Cache directory path

        Returns:
            List of page image paths
        """
        return list_cached_pages(cache_dir)

    def get_incremental_save_path(
        self, pdf_path: Path
    ) -> Path:
        """Determine where to save incremental output.

        Args:
            pdf_path: Original PDF path

        Returns:
            Path for incremental save file
        """
        outbox = self._config.outbox_dir.strip()
        if not outbox:
            outbox = str(pdf_path.parent)

        return Path(outbox) / f"{pdf_path.stem}.txt"
