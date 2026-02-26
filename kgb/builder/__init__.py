"""Knowledge Graph Builder module.

This module provides the core engines for constructing a knowledge graph:
- Extraction: Converting raw text into initial triples.
- Augmentation: Iteratively refining the graph via registered strategies.

Extensibility:
- Use `@register_strategy` to add new augmentation strategies.
- Use `list_strategies()` to discover available strategies.
"""

from .extraction import extract_from_text
from .augmentation import (
    extract_connected_graph,
    AugmentationStrategy,
    register_strategy,
    list_strategies,
    STRATEGIES,
)

__all__ = [
    "extract_from_text",
    "extract_connected_graph",
    "AugmentationStrategy",
    "register_strategy",
    "list_strategies",
    "STRATEGIES",
]
