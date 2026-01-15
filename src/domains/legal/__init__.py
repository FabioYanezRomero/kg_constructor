"""Legal knowledge domain implementation."""

from __future__ import annotations

from ..base import KnowledgeDomain
from ..registry import domain


@domain("legal")
class LegalDomain(KnowledgeDomain):
    """Legal domain for knowledge graph extraction.
    
    This class uses automatic root resolution and grouped API 
    inherited from KnowledgeDomain. Resources are loaded from:
    - extraction/prompt_open.txt or extraction/prompt_constrained.txt
    - extraction/examples.json
    - augmentation/prompt.txt
    - augmentation/examples.json
    - schema.json
    """
    pass


__all__ = ["LegalDomain"]
