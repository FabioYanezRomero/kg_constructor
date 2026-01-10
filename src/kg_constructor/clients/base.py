"""Base client interface for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMClientError(RuntimeError):
    """Base exception for LLM client errors."""


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients.

    All client implementations must inherit from this class and implement
    the extract method for knowledge graph extraction.
    """

    @abstractmethod
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
        """Extract structured information from text.

        Args:
            text: The input text to extract information from
            prompt_description: Instructions for what to extract
            examples: Optional list of few-shot examples
            format_type: Optional Pydantic model for structured output
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            List of extracted triples as dictionaries

        Raises:
            LLMClientError: If extraction fails
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier being used.

        Returns:
            Model name/identifier string
        """
        pass

    @abstractmethod
    def supports_structured_output(self) -> bool:
        """Check if this client supports structured output via schema.

        Returns:
            True if structured output is supported, False otherwise
        """
        pass


__all__ = ["BaseLLMClient", "LLMClientError"]
