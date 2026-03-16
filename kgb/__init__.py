"""Knowledge graph constructor package.

Primary interface is the CLI:
    kgb extract --input data.jsonl --domain legal
    kgb augment connectivity --input data.jsonl --domain legal
    kgb convert --input outputs/extracted_json
    kgb visualize --input outputs/graphml
"""

from __future__ import annotations

from typing import Any

__all__ = [
    # Core builder
    "extract_triples",
    "extract_from_text",
    "augment_triples",
    "extract_connected_graph",
    # Clients
    "ClientConfig",
    "ClientFactory",
    # Visualization
    "TextVisualizer",
    "EntityVisualizer",
    "render_graph",
    "batch_render_graphs",
    # Domains
    "get_domain",
    "KnowledgeDomain",
    "ExtractionMode",
    # Data loading
    "load_records",
    # Converters
    "json_to_graphml",
]


def extract_triples(*args: Any, **kwargs: Any) -> Any:
    """Extract triples from text."""
    from .builder import extract_triples as _impl
    return _impl(*args, **kwargs)


def extract_from_text(*args: Any, **kwargs: Any) -> Any:
    """Extract triples from text."""
    from .builder import extract_from_text as _impl
    return _impl(*args, **kwargs)


def augment_triples(*args: Any, **kwargs: Any) -> Any:
    """Augment triples using a builder strategy."""
    from .builder import augment_triples as _impl
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


def TextVisualizer(*args: Any, **kwargs: Any) -> Any:
    """Create a text visualizer for highlighting triples in source text."""
    from .visualization import TextVisualizer as _impl
    return _impl(*args, **kwargs)


def EntityVisualizer(*args: Any, **kwargs: Any) -> Any:
    """Backward-compatible alias for the text visualizer."""
    from .visualization import EntityVisualizer as _impl
    return _impl(*args, **kwargs)


def render_graph(*args: Any, **kwargs: Any) -> Any:
    """Render an interactive graph visualization."""
    from .visualization import render_graph as _impl
    return _impl(*args, **kwargs)


def batch_render_graphs(*args: Any, **kwargs: Any) -> Any:
    """Render graph visualizations for all GraphML files in a directory."""
    from .visualization import batch_render_graphs as _impl
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
    from .io.readers import load_records as _impl
    return _impl(*args, **kwargs)


def json_to_graphml(*args: Any, **kwargs: Any) -> Any:
    """Convert triples to GraphML format."""
    from .io.writers import json_to_graphml as _impl
    return _impl(*args, **kwargs)
