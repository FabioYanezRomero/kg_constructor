"""Legal knowledge domain implementation."""

from __future__ import annotations

from ..base import KnowledgeDomain
from ..registry import register_domain


class LegalDomain(KnowledgeDomain):
    """Legal domain for knowledge graph extraction.
    
    This class now uses automatic root resolution and grouped API 
    inherited from KnowledgeDomain.
    """
    pass


# Register the domain
register_domain("legal", LegalDomain)


__all__ = ["LegalDomain"]
