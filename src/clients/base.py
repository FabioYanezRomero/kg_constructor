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
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Extract structured information from text with source grounding.

        Args:
            text: The input text
            prompt_description: Instructions for extraction
            examples: Few-shot examples
            format_type: Pydantic model for schema
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            List of dictionaries with source grounding
        """
        pass

    @abstractmethod
    def generate_json(
        self,
        text: str,
        prompt_description: str,
        format_type: type,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Generate structured JSON items directly from text.

        Unlike extract(), this method should NOT attempt to ground extractions
        in the source text (i.e., no char positions required). This is useful
        for high-level inference and bridging.

        Args:
            text: The input text
            prompt_description: Instructions for generation
            format_type: Pydantic model for schema enforcement
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            List of dictionaries matching the schema
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

    @classmethod
    @abstractmethod
    def from_config(cls, config: "ClientConfig") -> "BaseLLMClient":
        """Create a client instance from a ClientConfig.

        Each client subclass must implement this method to handle its
        specific configuration parameters.

        Args:
            config: ClientConfig instance with client parameters

        Returns:
            Configured client instance
        """
        pass


# Forward reference for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .config import ClientConfig


__all__ = ["BaseLLMClient", "LLMClientError"]
