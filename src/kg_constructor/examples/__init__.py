"""Examples module for langextract few-shot learning.

This module provides domain-specific examples for knowledge graph extraction.
Examples guide the LLM's extraction behavior by demonstrating expected output format.

Usage:
    from kg_constructor.examples import get_examples, LegalExamples, DefaultExamples
    
    # Get examples by domain name
    examples = get_examples("legal")
    
    # Or use directly
    legal_examples = LegalExamples().get_examples()
"""

from __future__ import annotations

from kg_constructor.examples.base import ExampleSet
from kg_constructor.examples.default import DefaultExamples
from kg_constructor.examples.domains.legal import LegalExamples

# Registry of available example sets
_EXAMPLE_REGISTRY: dict[str, type[ExampleSet]] = {
    "default": DefaultExamples,
    "legal": LegalExamples,
}


def get_examples(domain: str = "default") -> ExampleSet:
    """Get an example set by domain name.
    
    Args:
        domain: Domain identifier (default, legal, etc.)
        
    Returns:
        ExampleSet instance for the requested domain
        
    Raises:
        ValueError: If domain is not registered
    """
    if domain not in _EXAMPLE_REGISTRY:
        available = ", ".join(_EXAMPLE_REGISTRY.keys())
        raise ValueError(f"Unknown domain '{domain}'. Available: {available}")
    return _EXAMPLE_REGISTRY[domain]()


def register_examples(domain: str, example_class: type[ExampleSet]) -> None:
    """Register a custom example set.
    
    Args:
        domain: Domain identifier
        example_class: ExampleSet subclass
    """
    _EXAMPLE_REGISTRY[domain] = example_class


__all__ = [
    "ExampleSet",
    "DefaultExamples",
    "LegalExamples",
    "get_examples",
    "register_examples",
]
