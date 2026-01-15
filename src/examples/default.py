"""Default examples for general-purpose knowledge graph extraction."""

from __future__ import annotations

import langextract as lx

from .base import ExampleSet


class DefaultExamples(ExampleSet):
    """General-purpose examples for knowledge graph extraction.
    
    Includes examples for:
    - Employment relationships
    - Entity classification
    - Legal relationships
    """
    
    def get_examples(self) -> list[lx.data.ExampleData]:
        """Get default examples for langextract extraction.
        
        Returns:
            List of ExampleData with Triple schema attributes.
        """
        # Example 1: Employment relationships
        text1 = "John Smith works at Google Inc. as a senior software engineer."
        extractions1 = [
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="John Smith works at Google Inc.",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=31),
                attributes={
                    "head": "John Smith",
                    "relation": "works_at",
                    "tail": "Google Inc.",
                    "inference": "explicit",
                }
            ),
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="John Smith ... senior software engineer",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=61),
                attributes={
                    "head": "John Smith",
                    "relation": "has_position",
                    "tail": "senior software engineer",
                    "inference": "explicit",
                }
            )
        ]

        # Example 2: Entity classification
        text2 = "Sigma Corporation is a structured investment vehicle."
        extractions2 = [
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="Sigma Corporation is a structured investment vehicle",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=52),
                attributes={
                    "head": "Sigma Corporation",
                    "relation": "is_type",
                    "tail": "structured investment vehicle",
                    "inference": "explicit",
                }
            )
        ]

        # Example 3: Legal relationships
        text3 = "Sarah Johnson from Morrison & Foerster represents the plaintiff in the case."
        extractions3 = [
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="Sarah Johnson from Morrison & Foerster",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=38),
                attributes={
                    "head": "Sarah Johnson",
                    "relation": "works_at",
                    "tail": "Morrison & Foerster",
                    "inference": "explicit",
                }
            ),
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="Sarah Johnson ... represents the plaintiff",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=59),
                attributes={
                    "head": "Sarah Johnson",
                    "relation": "represents",
                    "tail": "plaintiff",
                    "inference": "explicit",
                }
            )
        ]

        return [
            lx.data.ExampleData(text=text1, extractions=extractions1),
            lx.data.ExampleData(text=text2, extractions=extractions2),
            lx.data.ExampleData(text=text3, extractions=extractions3),
        ]


__all__ = ["DefaultExamples"]
