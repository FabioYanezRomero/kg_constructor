"""Knowledge graph constructor package."""

from __future__ import annotations

from typing import Any

__all__ = [
    # Unified API
    "KnowledgeGraphExtractor",
    "ExtractionPipeline",
    "ClientConfig",
    "create_client",
    # Client types
    "GeminiClient",
    "OllamaClient",
    "LMStudioClient",
]


def KnowledgeGraphExtractor(*args: Any, **kwargs: Any) -> Any:
    """Create a knowledge graph extractor with configurable client."""
    from .extractor import KnowledgeGraphExtractor as _impl

    return _impl(*args, **kwargs)


def ExtractionPipeline(*args: Any, **kwargs: Any) -> Any:
    """Create an extraction pipeline with configurable client."""
    from .extraction_pipeline import ExtractionPipeline as _impl

    return _impl(*args, **kwargs)


def ClientConfig(*args: Any, **kwargs: Any) -> Any:
    """Create a client configuration."""
    from .clients import ClientConfig as _impl

    return _impl(*args, **kwargs)


def create_client(*args: Any, **kwargs: Any) -> Any:
    """Create an LLM client from configuration."""
    from .clients import create_client as _impl

    return _impl(*args, **kwargs)


def GeminiClient(*args: Any, **kwargs: Any) -> Any:
    """Create a Gemini API client."""
    from .clients import GeminiClient as _impl

    return _impl(*args, **kwargs)


def OllamaClient(*args: Any, **kwargs: Any) -> Any:
    """Create an Ollama client."""
    from .clients import OllamaClient as _impl

    return _impl(*args, **kwargs)


def LMStudioClient(*args: Any, **kwargs: Any) -> Any:
    """Create an LM Studio client."""
    from .clients import LMStudioClient as _impl

    return _impl(*args, **kwargs)
