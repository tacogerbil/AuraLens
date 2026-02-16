"""VLM API client for OpenWebUI chat/completions with vision support."""

import logging
import re
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

RETRY_BACKOFF_SECONDS = 5.0
MAX_RETRIES = 1

_THINKING_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_thinking_tags(text: str) -> str:
    """Remove <think>...</think> blocks from VLM response."""
    return _THINKING_PATTERN.sub("", text).strip()


# --- Exceptions ---


class VLMError(Exception):
    """Base exception for VLM client errors."""


class VLMAuthError(VLMError):
    """Raised on 401/403 authentication failures."""


class VLMModelNotFoundError(VLMError):
    """Raised on 404 — model not found or wrong endpoint."""


class VLMTimeoutError(VLMError):
    """Raised when the VLM request times out after retries."""


# --- Client ---


class VLMClient:
    """Stateless VLM API client. All config injected via constructor."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model_name: str,
        timeout: int = 120,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        repeat_penalty: float = 1.0,
        presence_penalty: float = 0.0,
        enable_thinking: bool = False,
    ) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._model_name = model_name
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._repeat_penalty = repeat_penalty
        self._presence_penalty = presence_penalty
        self._enable_thinking = enable_thinking

    def process_image(
        self,
        image_data_uri: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send image + prompts to VLM, return extracted text.

        Stateless: Constructs a fresh messages array for every request.
        
        Args:
            image_data_uri: Base64 data URI of the image.
            user_prompt: Specific instruction for this image (User role).
            system_prompt: Optional global instruction (System role).

        Returns:
            Extracted text content.
        
        Raises:
            VLMAuthError: On 401/403.
            VLMModelNotFoundError: On 404.
            VLMTimeoutError: If retries exhausted.
            VLMError: On other failures.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1 + MAX_RETRIES):
            try:
                response_json = self._send_request(
                    image_data_uri, user_prompt, system_prompt
                )
                return self._extract_text(response_json)
            except (VLMAuthError, VLMModelNotFoundError):
                raise
            except VLMTimeoutError as exc:
                last_error = exc
                if not self._should_retry(attempt):
                    break
                logger.warning("Timeout on attempt %d, retrying...", attempt + 1)
                time.sleep(RETRY_BACKOFF_SECONDS)
            except VLMError as exc:
                last_error = exc
                if not self._should_retry(attempt):
                    break
                logger.warning("Error on attempt %d: %s, retrying...", attempt + 1, exc)
                time.sleep(RETRY_BACKOFF_SECONDS)

        raise VLMError(f"VLM request failed after {1 + MAX_RETRIES} attempts: {last_error}")

    def _build_headers(self) -> Dict[str, str]:
        """Construct HTTP headers with auth token."""
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _build_payload(
        self,
        image_data_uri: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct OpenAI-compatible multimodal chat payload.
        
        Structure:
        - System message (optional)
        - User message (text + image)
        """
        messages: List[Dict[str, Any]] = []

        # 1. System Message (Optional)
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 2. User Message (Text + Image)
        content: List[Dict[str, Any]] = [
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {"url": image_data_uri},
            },
        ]
        messages.append({"role": "user", "content": content})

        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        
        # Add penalties only if non-default
        if self._repeat_penalty != 1.0:
            payload["repeat_penalty"] = self._repeat_penalty
        if self._presence_penalty != 0.0:
            payload["presence_penalty"] = self._presence_penalty
        if self._enable_thinking:
            payload["enable_thinking"] = True

        return payload

    def _send_request(
        self,
        image_data_uri: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute HTTP POST to VLM API. Raises typed exceptions on failure."""
        headers = self._build_headers()
        payload = self._build_payload(image_data_uri, user_prompt, system_prompt)

        try:
            response = requests.post(
                self._api_url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise VLMTimeoutError(f"Request timed out after {self._timeout}s") from exc
        except requests.exceptions.ConnectionError as exc:
            raise VLMError(f"Connection failed: {exc}") from exc

        self._check_status(response)
        return response.json()

    def _check_status(self, response: requests.Response) -> None:
        """Map HTTP status codes to typed exceptions."""
        code = response.status_code
        if code in (401, 403):
            raise VLMAuthError(f"Authentication failed (HTTP {code})")
        if code == 404:
            raise VLMModelNotFoundError(
                f"Model or endpoint not found (HTTP 404): {self._api_url}"
            )
        if code >= 500:
            raise VLMError(f"Server error (HTTP {code}): {response.text[:200]}")
        if code >= 400:
            raise VLMError(f"Client error (HTTP {code}): {response.text[:200]}")

    def _extract_text(self, response_json: Dict[str, Any]) -> str:
        """Parse text content from OpenAI chat/completions response."""
        try:
            content = response_json["choices"][0]["message"]["content"]
            return strip_thinking_tags(content)
        except (KeyError, IndexError, TypeError) as exc:
            raise VLMError(
                f"Unexpected response format: {list(response_json.keys())}"
            ) from exc

    @staticmethod
    def _should_retry(attempt: int) -> bool:
        """Return True if more retry attempts remain."""
        return attempt < MAX_RETRIES
