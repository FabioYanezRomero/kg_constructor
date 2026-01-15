"""Unified domain module for prompts and examples.

This module provides the Unified Domain Pattern for managing
knowledge domain resources (prompts, examples, schemas).

Usage:
    from src.domains import get_domain, domain, KnowledgeDomain
    
    # Get a registered domain
    legal = get_domain("legal", extraction_mode="open")
    
    # Create a new domain with decorator
    @domain("custom")
    class CustomDomain(KnowledgeDomain):
        pass
"""

from .base import KnowledgeDomain, DomainComponent, DomainLike, DomainResourceError
from .models import DomainExamples, ExtractionMode, Triple, Extraction, ExtractionExample, AugmentationExample, DomainSchema
from .registry import domain, get_domain, register_domain, list_available_domains

# Import domains to trigger registration
from . import legal
from . import default

__all__ = [
    # Base classes and protocols
    "KnowledgeDomain",
    "DomainComponent",
    "DomainLike",
    "DomainResourceError",
    # Models
    "DomainExamples",
    "DomainSchema",
    "ExtractionMode",
    "Triple",
    "Extraction",
    "ExtractionExample",
    "AugmentationExample",
    # Registry
    "domain",
    "get_domain",
    "register_domain",
    "list_available_domains",
]
