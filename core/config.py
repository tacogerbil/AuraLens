"""JSON-backed application settings for AuraLens."""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are an OCR assistant. Extract ALL text from this image exactly as it appears. "
    "Preserve paragraph breaks, line breaks, and formatting. "
    "Do not add commentary, interpretation, or markdown formatting. "
    "Output only the raw extracted text."
)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONFIG_PATH = CONFIG_DIR / "settings.json"


@dataclass
class Config:
    """All user-configurable settings with sensible defaults."""

    api_url: str = "http://localhost:3000/api/chat/completions"
    api_key: str = ""
    model_name: str = ""
    temperature: float = 0.0
    repeat_penalty: float = 1.2  # Penalize repetition (1.0=none, >1.0=penalty)
    presence_penalty: float = 0.5  # Penalize already-seen tokens (0.0-2.0)
    pdf_dpi: int = 150
    max_image_pixels: int = 1_003_520
    jpeg_quality: int = 90
    timeout: int = 120
    max_tokens: int = 4096
    inbox_dir: str = ""
    outbox_dir: str = ""
    system_prompt: str = field(default=DEFAULT_SYSTEM_PROMPT)
    
    # Window geometry persistence
    window_width: int = 1600
    window_height: int = 1000
    window_x: int = -1  # -1 means center on screen
    window_y: int = -1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to a plain dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dict, ignoring unknown keys."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load config from JSON file. Returns defaults if file missing."""
    if not path.exists():
        logger.info("No config file at %s, using defaults", path)
        return Config()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        logger.info("Loaded config from %s", path)
        return Config.from_dict(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Corrupt config at %s: %s — using defaults", path, exc)
        return Config()


def save_config(config: Config, path: Path = CONFIG_PATH) -> None:
    """Write config to JSON file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Saved config to %s", path)
