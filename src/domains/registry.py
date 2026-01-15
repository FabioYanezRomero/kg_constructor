"""Registry for knowledge domains."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import KnowledgeDomain


_DOMAIN_REGISTRY: dict[str, type[KnowledgeDomain]] = {}


def register_domain(name: str, domain_class: type[KnowledgeDomain]) -> None:
    """Register a new knowledge domain."""
    _DOMAIN_REGISTRY[name] = domain_class


def get_domain(name: str, **kwargs) -> KnowledgeDomain:
    """Get a domain instance by name.
    
    Args:
        name: Domain name (e.g., "legal")
        **kwargs: Arguments to pass to the domain constructor (e.g., extraction_mode)
        
    Returns:
        KnowledgeDomain instance
        
    Raises:
        ValueError: If domain is not registered
    """
    if name not in _DOMAIN_REGISTRY:
        available = ", ".join(_DOMAIN_REGISTRY.keys())
        raise ValueError(f"Unknown domain '{name}'. Available: {available}")
    return _DOMAIN_REGISTRY[name](**kwargs)


def list_available_domains() -> list[str]:
    """List all registered domain names."""
    return list(_DOMAIN_REGISTRY.keys())


__all__ = ["register_domain", "get_domain", "list_available_domains"]
