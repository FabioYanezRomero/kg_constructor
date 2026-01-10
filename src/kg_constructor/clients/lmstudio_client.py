"""LM Studio client using langextract for knowledge graph extraction."""

from __future__ import annotations

from typing import Any

import langextract as lx
from langextract.providers.openai import OpenAILanguageModel

from .base import BaseLLMClient, LLMClientError


class LMStudioClient(BaseLLMClient):
    """Client for LM Studio local models via langextract.

    LM Studio provides an OpenAI-compatible API, so we use langextract's
    OpenAI provider with a custom base URL.
    """

    def __init__(
        self,
        model_id: str = "local-model",
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        max_workers: int = 5,
        batch_length: int = 5,
        max_char_buffer: int = 8000,
        show_progress: bool = True,
        timeout: int = 120
    ) -> None:
        """Initialize LM Studio client.

        Args:
            model_id: Model identifier (use the model name from LM Studio)
            base_url: LM Studio server URL (default: http://localhost:1234/v1)
            api_key: API key (LM Studio uses "lm-studio" by default)
            max_workers: Maximum parallel workers (keep lower for local models)
            batch_length: Number of chunks per batch (keep lower for local)
            max_char_buffer: Maximum characters for inference
            show_progress: Whether to show progress bar
            timeout: Request timeout in seconds
        """
        self.model_id = model_id
        self.base_url = base_url
        self.api_key = api_key
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
        """Extract knowledge graph triples using LM Studio via langextract.

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
            # Create OpenAI-compatible language model for LM Studio
            lmstudio_model = OpenAILanguageModel(
                model_id=self.model_id,
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )

            # Prepare langextract kwargs
            langextract_kwargs = {
                "model": lmstudio_model,
                "temperature": temperature,
                "max_workers": self.max_workers,
                "batch_length": self.batch_length,
                "max_char_buffer": self.max_char_buffer,
                "show_progress": self.show_progress,
                "use_schema_constraints": False,  # LM Studio may not support schema
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
            raise LLMClientError(f"LM Studio extraction failed: {e}") from e

    def get_model_name(self) -> str:
        """Return the LM Studio model identifier."""
        return f"lmstudio/{self.model_id}"

    def supports_structured_output(self) -> bool:
        """LM Studio generally doesn't support native structured output."""
        return False


__all__ = ["LMStudioClient"]
