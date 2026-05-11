"""Pathology knowledge domain implementation."""

from __future__ import annotations

from ..base import KnowledgeDomain
from ..registry import domain


@domain("pathology")
class PathologyDomain(KnowledgeDomain):
    """Pathology domain for histopathology and clinical pathology report extraction.

    Resources are loaded from the pathology domain root:
    - extraction/prompt_open.md
    - extraction/prompt_constrained.md
    - extraction/examples.json
    - augmentation/connectivity/prompt.md
    - augmentation/connectivity/examples.json
    - schema.json
    """
    pass


__all__ = ["PathologyDomain"]
