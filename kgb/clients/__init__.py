"""LLM client abstraction layer for knowledge graph extraction."""

from __future__ import annotations

from .base import BaseLLMClient, LLMClientError
from .config import ClientConfig, ClientType
from .factory import ClientFactory
from .providers import GeminiClient, OllamaClient, LMStudioClient

# Register all client types with the factory
ClientFactory.register("gemini", GeminiClient)
ClientFactory.register("ollama", OllamaClient)
ClientFactory.register("lmstudio", LMStudioClient)

__all__ = [
    "BaseLLMClient",
    "LLMClientError",
    "ClientConfig",
    "ClientType",
    "ClientFactory",
    "GeminiClient",
    "OllamaClient",
    "LMStudioClient",
]
