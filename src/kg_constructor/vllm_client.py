from __future__ import annotations

"""HTTP client for interacting with a vLLM OpenAI-compatible server."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


class VLLMClientError(RuntimeError):
    """Raised when the vLLM server returns an error response."""


@dataclass
class VLLMClient:
    """Client for issuing completion requests to a vLLM server."""

    base_url: str
    timeout: int = 120
    api_key: Optional[str] = None

    def generate(
        self,
        prompt: str,
        model: str,
        params: Dict[str, Any] | None = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": self._build_messages(prompt, system_prompt),
        }
        if params:
            payload.update({key: value for key, value in params.items() if value is not None})

        endpoint = self._compose_url("/v1/chat/completions")
        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=self.timeout,
                headers=self._headers(),
            )
        except requests.RequestException as exc:  # pragma: no cover - network errors
            raise VLLMClientError(f"Failed to reach vLLM server at {endpoint}: {exc}") from exc

        if response.status_code != requests.codes.ok:
            raise VLLMClientError(
                f"vLLM generation failed with status {response.status_code}: {response.text}"
            )

        body = response.json()
        choices = body.get("choices")
        if not choices:
            raise VLLMClientError("Unexpected vLLM response: missing choices")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise VLLMClientError("Unexpected vLLM response: missing message field")
        content = message.get("content")
        if not isinstance(content, str):
            raise VLLMClientError("Unexpected vLLM response: missing content field")
        return content

    def _compose_url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def _build_messages(prompt: str, system_prompt: Optional[str]) -> list[Dict[str, str]]:
        messages: list[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages


__all__ = ["VLLMClient", "VLLMClientError"]
