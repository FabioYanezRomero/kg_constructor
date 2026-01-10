"""Knowledge graph extraction using client abstraction layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import langextract as lx
from pydantic import BaseModel, Field

from kg_constructor.clients import BaseLLMClient, ClientConfig, create_client


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


class KnowledgeGraphExtractor:
    """Extracts knowledge graphs from text using configurable LLM clients.

    This class provides a unified interface for extracting entities and relations
    from text using different LLM backends (Gemini, Ollama, LM Studio) via the
    client abstraction layer.
    """

    def __init__(
        self,
        client: BaseLLMClient | None = None,
        client_config: ClientConfig | None = None,
        prompt_path: Path | str | None = None
    ) -> None:
        """Initialize the extractor.

        Args:
            client: Pre-configured client instance (takes precedence)
            client_config: Configuration for creating a client
            prompt_path: Path to prompt template file (default: prompts/default_prompt.txt)

        Raises:
            ValueError: If neither client nor client_config is provided
        """
        # Set up client
        if client is not None:
            self.client = client
        elif client_config is not None:
            self.client = create_client(client_config)
        else:
            # Default to Gemini
            self.client = create_client(ClientConfig(client_type="gemini"))

        # Load prompt template
        if prompt_path is None:
            # Default to the generic prompt
            prompt_path = Path(__file__).parent.parent / "prompts" / "default_prompt.txt"
        else:
            prompt_path = Path(prompt_path)

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

        self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def _prepare_prompt(self, record: dict[str, Any]) -> str:
        """Prepare the extraction prompt from template.

        Args:
            record: Dataset record to inject into template

        Returns:
            Formatted prompt string
        """
        # Replace template variables
        prompt = self.prompt_template.replace(
            "{{record_json}}",
            json.dumps(record, ensure_ascii=False, indent=2)
        )
        return prompt

    def _create_examples(self) -> list[lx.ExampleData]:
        """Create few-shot examples for extraction.

        Returns:
            List of ExampleData objects for langextract
        """
        # Example from legal domain
        example_text = """H is a three year old child whose parents separated before his birth.
        From the date of his birth until very recently, H has lived with his maternal
        grandmother, GB. H's mother, GLB, lived with her mother and H intermittently
        at GB's home from the time he was born until July 2006."""

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
            }
        ]

        return [
            lx.ExampleData(
                input_text=example_text,
                expected_output=example_triples
            )
        ]

    def extract_from_text(
        self,
        text: str,
        record_id: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None
    ) -> list[dict[str, Any]]:
        """Extract triples from a single text.

        Args:
            text: The text to analyze
            record_id: Optional identifier for logging
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            List of extracted triples as dictionaries
        """
        # Prepare the prompt (inject text into template)
        record = {"text": text}
        if record_id:
            record["id"] = record_id

        prompt_text = self._prepare_prompt(record)
        examples = self._create_examples()

        # Extract using the client
        triples = self.client.extract(
            text=prompt_text,
            prompt_description="Extract knowledge graph triples from the text",
            examples=examples,
            format_type=Triple,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return triples

    def extract_from_record(
        self,
        record: dict[str, Any],
        text_field: str = "text",
        temperature: float = 0.0,
        max_tokens: int | None = None
    ) -> list[dict[str, Any]]:
        """Extract triples from a dataset record.

        Args:
            record: Dataset record (must contain text_field)
            text_field: Name of field containing text to analyze
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            List of extracted triples

        Raises:
            ValueError: If text_field not found in record
        """
        if text_field not in record:
            raise ValueError(f"Record missing required field: {text_field}")

        text = record[text_field]
        record_id = record.get("id", None)

        return self.extract_from_text(text, record_id, temperature, max_tokens)

    def extract_from_csv(
        self,
        csv_path: Path,
        text_column: str = "background",
        id_column: str = "id",
        limit: int | None = None,
        temperature: float = 0.0
    ) -> dict[str, list[dict[str, Any]]]:
        """Extract triples from all records in a CSV file.

        Args:
            csv_path: Path to CSV file
            text_column: Name of column containing text
            id_column: Name of column containing record IDs
            limit: Optional limit on number of records
            temperature: Sampling temperature

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
                record = {"text": text, "id": record_id}
                triples = self.extract_from_record(record, text_field="text", temperature=temperature)
                results[record_id] = triples
            except Exception as e:
                print(f"Error processing record {record_id}: {e}")
                results[record_id] = []

        return results

    def get_model_name(self) -> str:
        """Get the name of the model being used.

        Returns:
            Model identifier string
        """
        return self.client.get_model_name()


__all__ = [
    "Triple",
    "KnowledgeGraphExtractor",
]
