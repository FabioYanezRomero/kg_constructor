"""Entity and relation extraction using langextract library."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import langextract as lx
from pydantic import BaseModel, Field


class Triple(BaseModel):
    """A single knowledge graph triple (head, relation, tail)."""

    head: str = Field(description="The source entity in the relationship")
    relation: str = Field(description="The relationship type connecting head to tail")
    tail: str = Field(description="The target entity in the relationship")
    inference: str = Field(
        description="Whether the triple is 'explicit' (directly stated) or 'contextual' (inferred for connectivity)"
    )
    justification: str | None = Field(
        default=None,
        description="Explanation for contextual triples (required when inference='contextual')"
    )


@dataclass
class ExtractionConfig:
    """Configuration for langextract-based extraction."""

    model_id: str = "gemini-2.0-flash-exp"
    api_key: str | None = None
    temperature: float = 0.0
    max_workers: int = 10
    batch_length: int = 10
    max_char_buffer: int = 8000
    use_schema_constraints: bool = True
    show_progress: bool = True


class LangExtractExtractor:
    """Extracts entities and relations from legal text using langextract."""

    def __init__(self, config: ExtractionConfig | None = None) -> None:
        """Initialize the extractor with optional configuration.

        Args:
            config: Extraction configuration. If None, uses defaults.
        """
        self.config = config or ExtractionConfig()

    def _get_extraction_prompt(self) -> str:
        """Get the prompt description for entity/relation extraction."""
        return """Extract all explicit knowledge graph triples (head, relation, tail) from the legal case background text.

Extraction Rules:
- Identify entities and relations explicitly stated in the background facts
- Prefer splitting complex phrases into smaller meaningful entities when this increases graph coverage
- Every explicit triple must be labeled with "inference": "explicit"

Connectivity Rules:
- Build a directed graph with the explicit triples, but check connectivity as undirected
- If the graph is disconnected, add the minimum number of auxiliary bridging triples to connect all components
- Bridging triples must:
  - Stay faithful to the context (e.g., introduce an "event" node implied in the background)
  - Include "inference": "contextual" and a short "justification" (1-2 phrases)
  - Avoid external knowledge beyond the provided background

The text to analyze is in the 'text' field of the input record."""

    def _create_examples(self) -> list[dict[str, Any]]:
        """Create few-shot examples to guide extraction."""
        # Example from UKSC-2009-0019
        example_text = """H is a three year old child whose parents separated before his birth. From the date of his birth until very recently, H has lived with his maternal grandmother, GB. H's mother, GLB, lived with her mother and H intermittently at GB's home from the time he was born until July 2006. She left GB's home then and has not returned. In November 2006, GB was granted, by consent, a residence order in respect of H."""

        example_triples = [
            {
                "head": "H",
                "relation": "is",
                "tail": "three-year-old child",
                "inference": "explicit"
            },
            {
                "head": "H",
                "relation": "parents separated",
                "tail": "before his birth",
                "inference": "explicit"
            },
            {
                "head": "GB",
                "relation": "is",
                "tail": "maternal grandmother of H",
                "inference": "explicit"
            },
            {
                "head": "GLB",
                "relation": "is",
                "tail": "mother of H",
                "inference": "explicit"
            },
            {
                "head": "H",
                "relation": "lived with",
                "tail": "GB (from birth until very recently)",
                "inference": "explicit"
            },
            {
                "head": "GB",
                "relation": "was granted",
                "tail": "residence order in respect of H (by consent, November 2006)",
                "inference": "explicit"
            }
        ]

        return [
            lx.ExampleData(
                input_text=example_text,
                expected_output=example_triples
            )
        ]

    def extract_from_text(self, text: str, record_id: str | None = None) -> list[dict[str, Any]]:
        """Extract triples from a single text document.

        Args:
            text: The legal case background text to analyze
            record_id: Optional identifier for the record (for logging)

        Returns:
            List of extracted triples as dictionaries
        """
        prompt = self._get_extraction_prompt()
        examples = self._create_examples()

        # Prepare input document
        input_doc = {"text": text}
        input_str = json.dumps(input_doc, ensure_ascii=False)

        # Extract using langextract
        result = lx.extract(
            text_or_documents=input_str,
            prompt_description=prompt,
            examples=examples,
            format_type=Triple,
            model_id=self.config.model_id,
            api_key=self.config.api_key,
            temperature=self.config.temperature,
            max_workers=self.config.max_workers,
            batch_length=self.config.batch_length,
            max_char_buffer=self.config.max_char_buffer,
            use_schema_constraints=self.config.use_schema_constraints,
            show_progress=self.config.show_progress,
            fetch_urls=False
        )

        # Extract triples from result
        triples = []
        if hasattr(result, 'extractions'):
            for extraction in result.extractions:
                if hasattr(extraction, 'data') and extraction.data:
                    triple_dict = extraction.data.model_dump()
                    triples.append(triple_dict)

        return triples

    def extract_from_dataset_record(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract triples from a dataset record containing a 'text' field.

        Args:
            record: Dataset record with at least a 'text' field

        Returns:
            List of extracted triples as dictionaries
        """
        text = record.get("text", "")
        if not text:
            raise ValueError("Record must contain a non-empty 'text' field")

        record_id = record.get("id", None)
        return self.extract_from_text(text, record_id)

    def extract_from_csv(
        self,
        csv_path: Path,
        text_column: str = "background",
        id_column: str = "id",
        limit: int | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        """Extract triples from all records in a CSV file.

        Args:
            csv_path: Path to CSV file
            text_column: Name of column containing text to analyze
            id_column: Name of column containing record IDs
            limit: Optional limit on number of records to process

        Returns:
            Dictionary mapping record IDs to lists of triples
        """
        import pandas as pd

        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        if limit:
            df = df.head(limit)

        results = {}
        for _, row in df.iterrows():
            record_id = str(row[id_column])
            text = str(row[text_column])

            if not text or text == "nan":
                continue

            try:
                triples = self.extract_from_text(text, record_id)
                results[record_id] = triples
            except Exception as e:
                print(f"Error processing record {record_id}: {e}")
                results[record_id] = []

        return results


__all__ = [
    "Triple",
    "ExtractionConfig",
    "LangExtractExtractor",
]
