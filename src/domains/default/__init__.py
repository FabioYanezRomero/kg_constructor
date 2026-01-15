"""Default knowledge domain implementation."""

from __future__ import annotations

from ..base import KnowledgeDomain
from ..registry import register_domain


class DefaultDomain(KnowledgeDomain):
    """Default domain for general-purpose knowledge graph extraction."""
    pass


# Register the domain
register_domain("default", DefaultDomain)


__all__ = ["DefaultDomain"]
