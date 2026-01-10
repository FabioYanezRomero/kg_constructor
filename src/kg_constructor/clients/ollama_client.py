"""Ollama client using langextract for knowledge graph extraction."""

from __future__ import annotations

from typing import Any

import langextract as lx
from langextract.providers.ollama import OllamaLanguageModel

from .base import BaseLLMClient, LLMClientError


class OllamaClient(BaseLLMClient):
    """Client for Ollama local models via langextract.

    This client uses langextract's Ollama provider to interact with
    locally hosted models for knowledge graph extraction.
    """

    def __init__(
        self,
        model_id: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        max_workers: int = 5,
        batch_length: int = 5,
        max_char_buffer: int = 8000,
        show_progress: bool = True,
        timeout: int = 120
    ) -> None:
        """Initialize Ollama client.

        Args:
            model_id: Ollama model name (e.g., "llama3.1", "mistral", "phi3")
            base_url: Ollama server URL
            max_workers: Maximum parallel workers (keep lower for local models)
            batch_length: Number of chunks per batch (keep lower for local)
            max_char_buffer: Maximum characters for inference
            show_progress: Whether to show progress bar
            timeout: Request timeout in seconds
        """
        self.model_id = model_id
        self.base_url = base_url
        self.max_workers = max_workers
        self.batch_length = batch_length
        self.max_char_buffer = max_char_buffer
        self.show_progress = show_progress
        self.timeout = timeout

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
        """Extract knowledge graph triples using Ollama via langextract.

        Args:
            text: Input text to analyze
            prompt_description: Extraction instructions
            examples: Few-shot examples (list of lx.ExampleData)
            format_type: Pydantic model for structured output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional langextract parameters

        Returns:
            List of extracted triples

        Raises:
            LLMClientError: If extraction fails
        """
        try:
            # Create Ollama language model
            ollama_model = OllamaLanguageModel(
                model_id=self.model_id,
                base_url=self.base_url,
                timeout=self.timeout
            )

            # Prepare langextract kwargs
            langextract_kwargs = {
                "model": ollama_model,
                "temperature": temperature,
                "max_workers": self.max_workers,
                "batch_length": self.batch_length,
                "max_char_buffer": self.max_char_buffer,
                "show_progress": self.show_progress,
                "use_schema_constraints": False,  # Ollama may not support schema
                "fence_output": True,  # Expect JSON in code fences
                "fetch_urls": False,
            }

            if max_tokens:
                langextract_kwargs["language_model_params"] = {"max_tokens": max_tokens}

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
            raise LLMClientError(f"Ollama extraction failed: {e}") from e

    def get_model_name(self) -> str:
        """Return the Ollama model identifier."""
        return f"ollama/{self.model_id}"

    def supports_structured_output(self) -> bool:
        """Ollama generally doesn't support native structured output."""
        return False


__all__ = ["OllamaClient"]
