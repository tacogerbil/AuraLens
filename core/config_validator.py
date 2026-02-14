"""Configuration validation logic.

Consolidates validation checks previously duplicated in MainWindow.
"""

from typing import Optional, Tuple

from core.config import Config


class ConfigValidator:
    """Pure validation logic for configuration objects."""

    @staticmethod
    def validate_for_ocr(config: Config) -> Tuple[bool, Optional[str]]:
        """Validate that config has required fields for OCR processing.

        Args:
            config: Configuration object to validate

        Returns:
            Tuple of (is_valid, error_message).
            If valid, error_message is None.
            If invalid, error_message describes the problem.
        """
        if not config.model_name.strip():
            return False, "Model name is not set. Open Settings to configure it."

        if not config.api_url.strip():
            return False, "API URL is not set. Open Settings to configure it."

        return True, None

    @staticmethod
    def can_auto_process(config: Config) -> bool:
        """Check if config is sufficient for automatic processing.

        Args:
            config: Configuration object to check

        Returns:
            True if config has minimum required fields for auto-processing.
        """
        is_valid, _ = ConfigValidator.validate_for_ocr(config)
        return is_valid
