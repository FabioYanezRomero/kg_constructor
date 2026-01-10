"""Base class for example sets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import langextract as lx


class ExampleSet(ABC):
    """Abstract base class for few-shot example sets.
    
    Subclasses define domain-specific examples that guide LLM extraction behavior.
    Examples demonstrate the expected Triple format (head, relation, tail, inference).
    """
    
    @abstractmethod
    def get_examples(self) -> list[lx.data.ExampleData]:
        """Get examples as langextract ExampleData objects.
        
        Returns:
            List of ExampleData with text and extractions
        """
        pass
    
    def get_examples_as_dict(self) -> list[dict[str, Any]]:
        """Export examples in JSON-serializable format.
        
        Returns:
            List of example dictionaries for saving to examples.json
        """
        examples = self.get_examples()
        result = []
        for example in examples:
            example_dict = {
                "text": example.text,
                "extractions": []
            }
            for extraction in example.extractions:
                ext_dict = {
                    "extraction_class": extraction.extraction_class,
                    "extraction_text": extraction.extraction_text,
                }
                if extraction.char_interval:
                    ext_dict["char_start"] = extraction.char_interval.start_pos
                    ext_dict["char_end"] = extraction.char_interval.end_pos
                if extraction.attributes:
                    ext_dict["attributes"] = extraction.attributes
                example_dict["extractions"].append(ext_dict)
            result.append(example_dict)
        return result
    
    def _create_extraction(
        self,
        text: str,
        extraction_text: str,
        start_pos: int,
        end_pos: int,
        head: str,
        relation: str,
        tail: str,
        inference: str = "explicit",
        justification: str | None = None
    ) -> lx.data.Extraction:
        """Helper to create an Extraction object.
        
        Args:
            text: Full text (for reference)
            extraction_text: The extracted text span
            start_pos: Character start position
            end_pos: Character end position
            head: Source entity
            relation: Relationship type
            tail: Target entity
            inference: "explicit" or "contextual"
            justification: Explanation for contextual triples
            
        Returns:
            langextract Extraction object
        """
        attributes = {
            "head": head,
            "relation": relation,
            "tail": tail,
            "inference": inference,
        }
        if justification:
            attributes["justification"] = justification
            
        return lx.data.Extraction(
            extraction_class="Triple",
            extraction_text=extraction_text,
            char_interval=lx.data.CharInterval(start_pos=start_pos, end_pos=end_pos),
            attributes=attributes
        )


__all__ = ["ExampleSet"]
