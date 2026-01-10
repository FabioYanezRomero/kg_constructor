"""Gemini client using langextract for knowledge graph extraction."""

from __future__ import annotations

import json
import os
from typing import Any

import requests
import langextract as lx

from .base import BaseLLMClient, LLMClientError


class GeminiClient(BaseLLMClient):
    """Client for Google Gemini models via langextract.

    This client uses the langextract library to interact with Gemini models
    for structured knowledge graph extraction.
    """

    def __init__(
        self,
        model_id: str = "gemini-2.0-flash-exp",
        api_key: str | None = None,
        max_workers: int = 10,
        batch_length: int = 10,
        max_char_buffer: int = 8000,
        show_progress: bool = True
    ) -> None:
        """Initialize Gemini client.

        Args:
            model_id: Gemini model identifier (e.g., "gemini-2.0-flash-exp")
            api_key: Google API key (or use LANGEXTRACT_API_KEY/GOOGLE_API_KEY env var)
            max_workers: Maximum parallel workers for concurrent processing
            batch_length: Number of text chunks processed per batch
            max_char_buffer: Maximum characters for inference
            show_progress: Whether to show progress bar
        """
        self.model_id = model_id
        self.api_key = api_key or os.getenv("LANGEXTRACT_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.max_workers = max_workers
        self.batch_length = batch_length
        self.max_char_buffer = max_char_buffer
        self.show_progress = show_progress

        if not self.api_key:
            raise LLMClientError(
                "No API key provided. Set api_key parameter or LANGEXTRACT_API_KEY/GOOGLE_API_KEY env var"
            )

    def extract(
        self,
        text: str,
        prompt_description: str,
        examples: list[Any] | None = None,
        format_type: type | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Extract knowledge graph triples using Gemini.

        When format_type is a Pydantic model, uses Google Generative AI SDK directly
        to avoid langextract's example system incompatibility with Pydantic models.

        Args:
            text: Input text to analyze
            prompt_description: Extraction instructions
            examples: Few-shot examples (not used with Pydantic models)
            format_type: Pydantic model for structured output
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Returns:
            List of extracted triples

        Raises:
            LLMClientError: If extraction fails
        """
        try:
            # When using Pydantic models, bypass langextract and use SDK directly
            # This avoids the incompatibility with langextract's example system
            if format_type is not None:
                return self._extract_with_pydantic(
                    text=text,
                    prompt_description=prompt_description,
                    format_type=format_type,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            # For non-Pydantic extraction, use langextract
            langextract_kwargs = {
                "model_id": self.model_id,
                "api_key": self.api_key,
                "temperature": temperature,
                "max_workers": self.max_workers,
                "batch_length": self.batch_length,
                "max_char_buffer": self.max_char_buffer,
                "show_progress": self.show_progress,
                "use_schema_constraints": False,
                "fetch_urls": False,
            }
            langextract_kwargs.update(kwargs)

            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt_description,
                examples=examples or [],
                format_type=format_type,
                **langextract_kwargs
            )

            # Extract triples from result
            triples = []
            if hasattr(result, 'extractions'):
                for extraction in result.extractions:
                    if hasattr(extraction, 'data') and extraction.data:
                        triple_dict = extraction.data.model_dump()
                        triples.append(triple_dict)

            return triples

        except Exception as e:
            raise LLMClientError(f"Gemini extraction failed: {e}") from e

    def _extract_with_pydantic(
        self,
        text: str,
        prompt_description: str,
        format_type: type,
        temperature: float,
        max_tokens: int | None
    ) -> list[dict[str, Any]]:
        """Extract using Gemini API directly via HTTP.

        This bypasses langextract to avoid Pydantic/example incompatibility issues.
        """
        try:
            # Get the Pydantic schema
            schema_json = format_type.model_json_schema()

            # Build the enhanced prompt with schema
            full_prompt = f"""{prompt_description}

{text}

Return a JSON array of objects matching this schema:
{json.dumps(schema_json, indent=2)}

Important: Return ONLY a valid JSON array, no markdown, no explanations."""

            # Call Gemini API directly
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"

            payload = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens or 8192,
                    "responseMimeType": "application/json"
                }
            }

            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()

            # Extract text from response
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        result_text = parts[0]["text"].strip()

                        # Parse JSON
                        parsed = json.loads(result_text)

                        # Handle both array and single object responses
                        if isinstance(parsed, list):
                            return parsed
                        elif isinstance(parsed, dict):
                            return [parsed]

            return []

        except Exception as e:
            raise LLMClientError(f"Pydantic extraction failed: {e}") from e

    def get_model_name(self) -> str:
        """Return the Gemini model identifier."""
        return self.model_id

    def supports_structured_output(self) -> bool:
        """Gemini supports structured output via schema constraints."""
        return True


__all__ = ["GeminiClient"]
