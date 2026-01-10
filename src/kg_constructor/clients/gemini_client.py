"""Gemini client using langextract for knowledge graph extraction."""

from __future__ import annotations

import os
from typing import Any

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
        """Extract knowledge graph triples using Gemini via langextract.

        Args:
            text: Input text to analyze
            prompt_description: Extraction instructions
            examples: Few-shot examples (list of lx.ExampleData)
            format_type: Pydantic model for structured output
            temperature: Sampling temperature
            max_tokens: Maximum tokens (not used by langextract)
            **kwargs: Additional langextract parameters

        Returns:
            List of extracted triples

        Raises:
            LLMClientError: If extraction fails
        """
        try:
            # Merge kwargs with instance settings
            langextract_kwargs = {
                "model_id": self.model_id,
                "api_key": self.api_key,
                "temperature": temperature,
                "max_workers": self.max_workers,
                "batch_length": self.batch_length,
                "max_char_buffer": self.max_char_buffer,
                "show_progress": self.show_progress,
                "use_schema_constraints": True,
                "fetch_urls": False,
            }
            langextract_kwargs.update(kwargs)

            # Perform extraction
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

    def get_model_name(self) -> str:
        """Return the Gemini model identifier."""
        return self.model_id

    def supports_structured_output(self) -> bool:
        """Gemini supports structured output via schema constraints."""
        return True


__all__ = ["GeminiClient"]
