"""Registry for knowledge domains.

This module provides a central registry for domain classes,
enabling dynamic discovery and instantiation by name.

Usage:
    # Decorator-based registration (preferred)
    @domain("mydomain")
    class MyDomain(KnowledgeDomain):
        pass
    
    # Manual registration (alternative)
    register_domain("mydomain", MyDomain)
    
    # Retrieval
    my_domain = get_domain("mydomain", extraction_mode="open")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeVar

if TYPE_CHECKING:
    from .base import KnowledgeDomain


_DOMAIN_REGISTRY: dict[str, type[KnowledgeDomain]] = {}

T = TypeVar("T", bound="KnowledgeDomain")


def domain(name: str) -> Callable[[type[T]], type[T]]:
    """Decorator to register a domain class.
    
    Usage:
        @domain("legal")
        class LegalDomain(KnowledgeDomain):
            pass
    
    Args:
        name: The name to register the domain under.
        
    Returns:
        A decorator that registers the class and returns it unchanged.
    """
    def decorator(cls: type[T]) -> type[T]:
        register_domain(name, cls)
        return cls
    return decorator


def register_domain(name: str, domain_class: type[KnowledgeDomain]) -> None:
    """Register a new knowledge domain.
    
    Args:
        name: The name to register the domain under.
        domain_class: The domain class to register.
    """
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


__all__ = ["domain", "register_domain", "get_domain", "list_available_domains"]
