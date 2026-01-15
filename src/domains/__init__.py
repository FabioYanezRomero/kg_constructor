"""Unified domain module for prompts and examples."""

from .base import KnowledgeDomain
from .models import DomainExamples, ExtractionMode, Triple, Extraction, ExtractionExample, AugmentationExample
from .registry import get_domain, register_domain, list_available_domains

# Import domains to trigger registration
from . import legal
from . import default

__all__ = [
    "KnowledgeDomain",
    "DomainExamples",
    "ExtractionMode",
    "Triple",
    "Extraction",
    "ExtractionExample",
    "AugmentationExample",
    "get_domain",
    "register_domain",
    "list_available_domains",
]
