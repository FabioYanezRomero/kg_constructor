"""Pydantic models for domain data validation."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExtractionMode(str, Enum):
    """Modes for graph extraction."""
    OPEN = "open"
    CONSTRAINED = "constrained"


class InferenceType(str, Enum):
    """Types of inference for triples."""
    EXPLICIT = "explicit"
    CONTEXTUAL = "contextual"


class Triple(BaseModel):
    """A single knowledge graph triple (head, relation, tail)."""
    head: str = Field(description="The source entity in the relationship (person, organization, concept, etc.)")
    relation: str = Field(description="The relationship type connecting head to tail (e.g., works_at, filed_against, is_type, represents, etc.)")
    tail: str = Field(description="The target entity in the relationship")
    inference: InferenceType = Field(
        default=InferenceType.EXPLICIT,
        description="MUST be 'explicit' if directly stated, or 'contextual' if inferred for connectivity."
    )
    justification: Optional[str] = Field(
        default=None,
        description="Brief explanation for 'contextual' triples (optional for explicit)."
    )


class Extraction(BaseModel):
    """A grounded extraction from text."""
    extraction_class: str = "Triple"
    extraction_text: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    attributes: Triple


class ExtractionExample(BaseModel):
    """Few-shot example for extraction."""
    text: str
    extractions: list[Extraction]


class Component(BaseModel):
    """A disconnected component in a graph."""
    entities: list[str]


class AugmentationInput(BaseModel):
    """Input for augmentation/bridging."""
    text: str
    components: list[Component]


class AugmentationExample(BaseModel):
    """Few-shot example for augmentation."""
    input: AugmentationInput
    output: list[Triple]


class DomainSchema(BaseModel):
    """Schema defining allowed entity and relation types for a domain."""
    entity_types: list[str] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)


class DomainExamples(BaseModel):
    """Collection of examples for a domain."""
    extraction: list[ExtractionExample] = Field(default_factory=list)
    augmentation: list[AugmentationExample] = Field(default_factory=list)


__all__ = [
    "ExtractionMode",
    "InferenceType",
    "Triple",
    "Extraction",
    "ExtractionExample",
    "AugmentationExample",
    "DomainSchema",
    "DomainExamples",
]
