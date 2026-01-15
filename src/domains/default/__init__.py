"""Default knowledge domain implementation."""

from __future__ import annotations

from ..base import KnowledgeDomain
from ..registry import domain


@domain("default")
class DefaultDomain(KnowledgeDomain):
    """Default domain for general-purpose knowledge graph extraction.
    
    This is the fallback domain used when no specific domain is specified.
    Resources are loaded from:
    - extraction/prompt_open.txt or extraction/prompt_constrained.txt
    - extraction/examples.json
    - augmentation/prompt.txt
    - augmentation/examples.json
    """
    pass


__all__ = ["DefaultDomain"]
