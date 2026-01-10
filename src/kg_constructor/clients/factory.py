"""Factory for creating LLM clients based on configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .base import BaseLLMClient, LLMClientError
from .gemini_client import GeminiClient
from .lmstudio_client import LMStudioClient
from .ollama_client import OllamaClient

ClientType = Literal["gemini", "ollama", "lmstudio"]


@dataclass
class ClientConfig:
    """Configuration for creating an LLM client.

    This class encapsulates all parameters needed to instantiate
    any supported LLM client type.
    """

    # Client type selection
    client_type: ClientType = "gemini"

    # Common parameters (all clients)
    model_id: str = "gemini-2.0-flash"
    temperature: float = 0.0
    max_workers: int = 10
    max_char_buffer: int = 8000
    show_progress: bool = True

    # Langextract-specific parameters
    extraction_passes: int = 1  # Number of extraction passes (higher = better recall)
    batch_length: int = 10  # For Ollama/LMStudio clients

    # API-based clients (Gemini)
    api_key: str | None = None

    # Local server-based clients (Ollama, LM Studio)
    base_url: str | None = None
    timeout: int = 120

    # Provider-specific defaults
    def __post_init__(self) -> None:
        """Set provider-specific defaults if not provided."""
        if self.client_type == "ollama":
            if not self.base_url:
                self.base_url = "http://localhost:11434"
            if self.model_id == "gemini-2.0-flash-exp":
                self.model_id = "llama3.1"
            # Lower defaults for local models
            if self.max_workers == 10:
                self.max_workers = 5
            if self.batch_length == 10:
                self.batch_length = 5

        elif self.client_type == "lmstudio":
            if not self.base_url:
                self.base_url = "http://localhost:1234/v1"
            if not self.api_key:
                self.api_key = "lm-studio"
            if self.model_id == "gemini-2.0-flash-exp":
                self.model_id = "local-model"
            # Lower defaults for local models
            if self.max_workers == 10:
                self.max_workers = 5
            if self.batch_length == 10:
                self.batch_length = 5


def create_client(config: ClientConfig) -> BaseLLMClient:
    """Factory function to create an LLM client based on configuration.

    Args:
        config: Client configuration specifying type and parameters

    Returns:
        Instantiated client matching the requested type

    Raises:
        LLMClientError: If client type is unsupported or configuration is invalid

    Examples:
        >>> # Create Gemini client
        >>> config = ClientConfig(client_type="gemini", api_key="your-key")
        >>> client = create_client(config)

        >>> # Create Ollama client
        >>> config = ClientConfig(
        ...     client_type="ollama",
        ...     model_id="llama3.1",
        ...     base_url="http://localhost:11434"
        ... )
        >>> client = create_client(config)

        >>> # Create LM Studio client
        >>> config = ClientConfig(
        ...     client_type="lmstudio",
        ...     model_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        ...     base_url="http://localhost:1234/v1"
        ... )
        >>> client = create_client(config)
    """
    if config.client_type == "gemini":
        return GeminiClient(
            model_id=config.model_id,
            api_key=config.api_key,
            max_workers=config.max_workers,
            max_char_buffer=config.max_char_buffer,
            extraction_passes=config.extraction_passes,
            show_progress=config.show_progress,
            temperature=config.temperature,
        )

    elif config.client_type == "ollama":
        if not config.base_url:
            raise LLMClientError("Ollama client requires base_url")

        return OllamaClient(
            model_id=config.model_id,
            base_url=config.base_url,
            max_workers=config.max_workers,
            batch_length=config.batch_length,
            max_char_buffer=config.max_char_buffer,
            show_progress=config.show_progress,
            timeout=config.timeout
        )

    elif config.client_type == "lmstudio":
        if not config.base_url:
            raise LLMClientError("LM Studio client requires base_url")

        return LMStudioClient(
            model_id=config.model_id,
            base_url=config.base_url,
            api_key=config.api_key or "lm-studio",
            max_workers=config.max_workers,
            batch_length=config.batch_length,
            max_char_buffer=config.max_char_buffer,
            show_progress=config.show_progress,
            timeout=config.timeout
        )

    else:
        raise LLMClientError(
            f"Unsupported client type: {config.client_type}. "
            f"Supported types: gemini, ollama, lmstudio"
        )


__all__ = ["ClientConfig", "create_client", "ClientType"]
