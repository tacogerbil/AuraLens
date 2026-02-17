"""Pure image transformation functions for VLM preprocessing."""

import base64
import io
import math
from typing import Tuple

from PIL import Image

# Disable DecompressionBombWarning for large images
Image.MAX_IMAGE_PIXELS = None


def calculate_scale_factor(
    width: int, height: int, max_pixels: int
) -> float:
    """Return downscale factor to fit within max_pixels. Always <= 1.0."""
    total = width * height
    if total <= max_pixels:
        return 1.0
    return math.sqrt(max_pixels / total)


def resize_for_vlm(
    image: Image.Image, max_pixels: int
) -> Image.Image:
    """Downscale image to fit within max_pixels using Lanczos. Never upscales."""
    width, height = image.size
    factor = calculate_scale_factor(width, height, max_pixels)
    if factor >= 1.0:
        return image

    new_w = max(1, int(width * factor))
    new_h = max(1, int(height * factor))
    return image.resize((new_w, new_h), Image.LANCZOS)


def convert_rgba_to_rgb(image: Image.Image) -> Image.Image:
    """Composite RGBA onto white background, returning RGB."""
    if image.mode != "RGBA":
        return image.convert("RGB") if image.mode != "RGB" else image

    background = Image.new("RGB", image.size, (255, 255, 255))
    background.paste(image, mask=image.split()[3])
    return background


def encode_to_jpeg(image: Image.Image, quality: int = 90) -> bytes:
    """Encode PIL Image to JPEG bytes. Handles RGBA → RGB conversion."""
    rgb_image = convert_rgba_to_rgb(image)
    buffer = io.BytesIO()
    rgb_image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def to_base64_data_uri(jpeg_bytes: bytes) -> str:
    """Wrap JPEG bytes as a base64 data URI for VLM payloads."""
    encoded = base64.b64encode(jpeg_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def prepare_image_for_vlm(
    image: Image.Image,
    max_pixels: int = 1_806_336,  # MiniCPM-V 4.5 max (1344x1344)
    jpeg_quality: int = 90,
) -> str:
    """Full pipeline: resize → encode → base64 data URI."""
    resized = resize_for_vlm(image, max_pixels)
    jpeg_bytes = encode_to_jpeg(resized, quality=jpeg_quality)
    return to_base64_data_uri(jpeg_bytes)
