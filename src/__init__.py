"""Knowledge graph constructor package."""

from __future__ import annotations

from typing import Any

__all__ = [
    # Unified API
    "KnowledgeGraphExtractor",
    "ExtractionPipeline",
    "EntityVisualizer",
    "ClientConfig",
    "ClientFactory",
    # Client types
    "GeminiClient",
    "OllamaClient",
    "LMStudioClient",
    # Examples
    "ExampleSet",
    "DefaultExamples",
    "LegalExamples",
    "get_examples",
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


def ClientFactory(*args: Any, **kwargs: Any) -> Any:
    """Client factory class for creating LLM clients."""
    from .clients import ClientFactory as _impl

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


def EntityVisualizer(*args: Any, **kwargs: Any) -> Any:
    """Create an entity visualizer for highlighting entities in text."""
    from .visualizer import EntityVisualizer as _impl

    return _impl(*args, **kwargs)


def ExampleSet(*args: Any, **kwargs: Any) -> Any:
    """Base class for example sets."""
    from .examples import ExampleSet as _impl

    return _impl(*args, **kwargs)


def DefaultExamples(*args: Any, **kwargs: Any) -> Any:
    """Get default examples for general-purpose extraction."""
    from .examples import DefaultExamples as _impl

    return _impl(*args, **kwargs)


def LegalExamples(*args: Any, **kwargs: Any) -> Any:
    """Get legal domain examples."""
    from .examples import LegalExamples as _impl

    return _impl(*args, **kwargs)


def get_examples(*args: Any, **kwargs: Any) -> Any:
    """Get examples by domain name (default, legal, etc.)."""
    from .examples import get_examples as _impl

    return _impl(*args, **kwargs)
