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

    def _create_examples(self) -> list[Any]:
        """Create few-shot examples for extraction.

        Returns:
            List of ExampleData with embedded Triple models
        """
        # Example text
        text1 = "John Smith works at Google Inc. as a senior software engineer."

        # Create Extraction objects with Triple models embedded
        # Note: For Pydantic structured extraction, we don't use the data field
        # Instead, we create simple text-based extractions
        extractions1 = [
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="John Smith works_at Google Inc.",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=len(text1))
            ),
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="John Smith has_position senior software engineer",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=len(text1))
            )
        ]

        text2 = "Sigma Corporation is a structured investment vehicle."
        extractions2 = [
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="Sigma Corporation is_type structured investment vehicle",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=len(text2))
            )
        ]

        return [
            lx.data.ExampleData(text=text1, extractions=extractions1),
            lx.data.ExampleData(text=text2, extractions=extractions2)
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
        # Create examples for langextract
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

    def extract_connected_graph(
        self,
        text: str,
        record_id: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        max_disconnected: int = 3,
        max_iterations: int = 2
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Extract triples with iterative connectivity improvement.

        This method performs a two-step extraction:
        1. Initial extraction of explicit and contextual triples
        2. Iterative refinement to reduce disconnected components

        Args:
            text: The text to analyze
            record_id: Optional identifier for logging
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            max_disconnected: Maximum acceptable disconnected components
            max_iterations: Maximum refinement iterations

        Returns:
            Tuple of (triples, metadata) where metadata includes connectivity info
        """
        import networkx as nx

        # Step 1: Initial extraction
        triples = self.extract_from_text(text, record_id, temperature, max_tokens)

        # Build graph and analyze connectivity
        G = self._build_graph_from_triples(triples)
        components = list(nx.weakly_connected_components(G))
        num_components = len(components)

        metadata = {
            "initial_extraction": {
                "triples": len(triples),
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "disconnected_components": num_components,
            },
            "refinement_iterations": []
        }

        # Step 2: Iterative refinement if needed
        iteration = 0
        while num_components > max_disconnected and iteration < max_iterations:
            # Format component information for the prompt
            component_info = self._format_components(components, G)

            # Create bridging prompt
            bridging_prompt = f"""
The previously extracted knowledge graph has {num_components} disconnected components.

Disconnected Components:
{component_info}

Original Text:
{text}

Task: Find EXPLICIT relationships in the text that connect these components,
or infer MINIMAL contextual triples necessary for connectivity. Focus on:
1. Shared entities between components
2. Implicit relationships stated in the text
3. Temporal or causal connections
4. Hierarchical relationships (part-of, type-of)

Extract ONLY the bridging triples needed to connect components.
Do not re-extract existing triples.
"""

            # Extract bridging triples
            bridging_triples = self.client.extract(
                text=bridging_prompt,
                prompt_description="Extract bridging triples to connect graph components",
                examples=self._create_examples(),
                format_type=Triple,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Filter out duplicates
            existing_triples_set = {
                (t['head'], t['relation'], t['tail'])
                for t in triples
            }
            new_triples = [
                t for t in bridging_triples
                if (t['head'], t['relation'], t['tail']) not in existing_triples_set
            ]

            # Add to triples and rebuild graph
            triples.extend(new_triples)
            G = self._build_graph_from_triples(triples)
            components = list(nx.weakly_connected_components(G))
            num_components = len(components)

            # Record iteration metadata
            metadata["refinement_iterations"].append({
                "iteration": iteration + 1,
                "new_triples": len(new_triples),
                "total_triples": len(triples),
                "disconnected_components": num_components,
            })

            iteration += 1

        # Final metadata
        metadata["final_state"] = {
            "total_triples": len(triples),
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "disconnected_components": num_components,
            "is_connected": num_components == 1,
            "iterations_used": iteration,
        }

        return triples, metadata

    def _build_graph_from_triples(self, triples: list[dict[str, Any]]):
        """Build NetworkX graph from triples."""
        import networkx as nx

        G = nx.DiGraph()
        for triple in triples:
            head = triple.get('head', '')
            tail = triple.get('tail', '')
            relation = triple.get('relation', '')
            if head and tail:
                G.add_edge(head, tail, relation=relation)
        return G

    def _format_components(
        self,
        components: list[set],
        G
    ) -> str:
        """Format disconnected components for prompt."""
        component_strs = []
        for i, component in enumerate(components[:10], 1):  # Limit to 10 components
            nodes = list(component)[:5]  # Limit to 5 nodes per component
            node_str = ", ".join(nodes)
            if len(component) > 5:
                node_str += f" ... ({len(component)} total nodes)"
            component_strs.append(f"Component {i}: {node_str}")

        return "\n".join(component_strs)

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
