"""Knowledge graph constructor package.

Primary interface is the CLI:
    python -m src extract --input data.jsonl --domain legal
    python -m src augment connectivity --input data.jsonl --domain legal
    python -m src convert --input outputs/extracted_json
    python -m src visualize --input outputs/graphml
"""

from __future__ import annotations

from typing import Any

__all__ = [
    # Core builder
    "extract_from_text",
    "extract_connected_graph",
    # Clients
    "ClientConfig",
    "ClientFactory",
    # Visualization
    "EntityVisualizer",
    # Domains
    "get_domain",
    "KnowledgeDomain",
    "ExtractionMode",
    # Data loading
    "load_records",
    # Converters
    "json_to_graphml",
]


def extract_from_text(*args: Any, **kwargs: Any) -> Any:
    """Extract triples from text."""
    from .builder import extract_from_text as _impl
    return _impl(*args, **kwargs)


def extract_connected_graph(*args: Any, **kwargs: Any) -> Any:
    """Extract and augment graph connectivity."""
    from .builder import extract_connected_graph as _impl
    return _impl(*args, **kwargs)


def ClientConfig(*args: Any, **kwargs: Any) -> Any:
    """Create a client configuration."""
    from .clients import ClientConfig as _impl
    return _impl(*args, **kwargs)


def ClientFactory(*args: Any, **kwargs: Any) -> Any:
    """Client factory for creating LLM clients."""
    from .clients import ClientFactory as _impl
    return _impl(*args, **kwargs)


def EntityVisualizer(*args: Any, **kwargs: Any) -> Any:
    """Create an entity visualizer for highlighting entities in text."""
    from .visualization import EntityVisualizer as _impl
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


def load_records(*args: Any, **kwargs: Any) -> Any:
    """Load records from JSONL/JSON/CSV file."""
    from .datasets import load_records as _impl
    return _impl(*args, **kwargs)


def json_to_graphml(*args: Any, **kwargs: Any) -> Any:
    """Convert triples to GraphML format."""
    from .converters import json_to_graphml as _impl
    return _impl(*args, **kwargs)
