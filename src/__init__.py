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
    # Domain Pattern
    "get_domain",
    "KnowledgeDomain",
    "ExtractionMode",
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


def EntityVisualizer(*args: Any, **kwargs: Any) -> Any:
    """Create an entity visualizer for highlighting entities in text."""
    from .visualizer import EntityVisualizer as _impl

    return _impl(*args, **kwargs)


def get_domain(*args: Any, **kwargs: Any) -> Any:
    """Get a knowledge domain by name."""
    from .domains import get_domain as _impl
    return _impl(*args, **kwargs)


def KnowledgeDomain(*args: Any, **kwargs: Any) -> Any:
    """Base class for knowledge domains."""
    from .domains import KnowledgeDomain as _impl
    return _impl


def ExtractionMode(*args: Any, **kwargs: Any) -> Any:
    """Enum for extraction modes."""
    from .domains import ExtractionMode as _impl
    return _impl
