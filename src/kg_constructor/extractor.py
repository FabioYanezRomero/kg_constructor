"""Knowledge graph extraction using client abstraction layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import langextract as lx
from pydantic import BaseModel, Field

from kg_constructor.clients import BaseLLMClient, ClientConfig, create_client
from kg_constructor.examples import ExampleSet, get_examples


class Triple(BaseModel):
    """A single knowledge graph triple (head, relation, tail)."""

    head: str = Field(description="The source entity in the relationship")
    relation: str = Field(description="The relationship type connecting head to tail")
    tail: str = Field(description="The target entity in the relationship")
    inference: Literal["explicit", "contextual"] = Field(
        description="MUST be 'explicit' if directly stated, or 'contextual' if inferred for connectivity."
    )
    justification: str | None = Field(
        default=None,
        description="REQUIRED for 'contextual' triples. Explain the logical link between entities."
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
        prompt_path: Path | str | None = None,
        bridging_prompt_path: Path | str | None = None,
        examples: ExampleSet | str | None = None
    ) -> None:
        """Initialize the extractor.

        Args:
            client: Pre-configured client instance (takes precedence)
            client_config: Configuration for creating a client
            prompt_path: Path to prompt template file for initial extraction (default: prompts/default_prompt.txt)
            bridging_prompt_path: Path to prompt template for bridging/refinement (optional, uses hardcoded if not provided)
            examples: ExampleSet instance or domain name (e.g., 'legal', 'default'). If None, uses 'default'.

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

        # Set up examples
        if examples is None:
            self._example_set = get_examples("default")
        elif isinstance(examples, str):
            self._example_set = get_examples(examples)
        else:
            self._example_set = examples

        # Load prompt template for initial extraction
        if prompt_path is None:
            # Default to the generic prompt (now inside kg_constructor)
            prompt_path = Path(__file__).parent / "prompts" / "default_prompt.txt"
        else:
            prompt_path = Path(prompt_path)

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

        self.prompt_template = prompt_path.read_text(encoding="utf-8")

        # Load bridging prompt template (optional)
        self.bridging_prompt_template = None
        if bridging_prompt_path is not None:
            bridging_prompt_path = Path(bridging_prompt_path)
            if not bridging_prompt_path.exists():
                raise FileNotFoundError(f"Bridging prompt template not found: {bridging_prompt_path}")
            self.bridging_prompt_template = bridging_prompt_path.read_text(encoding="utf-8")

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
        """Create few-shot examples for langextract extraction.

        Returns:
            List of ExampleData with Triple schema attributes.
            Uses the configured example set.
        """
        return self._example_set.get_examples()

    def get_examples_as_dict(self) -> list[dict[str, Any]]:
        """Export few-shot examples in JSON-serializable format.

        Returns:
            List of example dictionaries for saving to examples.json
        """
        return self._example_set.get_examples_as_dict()

    def _get_extraction_prompt_description(self) -> str:
        """Get the prompt description for triple extraction.

        Returns:
            Detailed prompt description with Triple schema fields.
        """
        return """Extract knowledge graph triples (head, relation, tail) from the text.

Each extraction should include these attributes:
- head: The source entity in the relationship (person, organization, concept, etc.)
- relation: The relationship type connecting head to tail (e.g., works_at, filed_against, is_type, represents, etc.)
- tail: The target entity in the relationship
- inference: Whether the triple is "explicit" (directly stated in text) or "contextual" (inferred for connectivity)
- justification: Brief explanation for contextual triples (optional for explicit)

Focus on extracting meaningful relationships between entities. Use exact entity names from the text when possible."""

    def _normalize_triple(self, raw_triple: dict[str, Any]) -> dict[str, Any]:
        """Normalize a raw extraction to standard Triple format.

        Args:
            raw_triple: Raw triple dict from langextract extraction

        Returns:
            Normalized triple with standard fields
        """
        return {
            "head": raw_triple.get("head", ""),
            "relation": raw_triple.get("relation", ""),
            "tail": raw_triple.get("tail", ""),
            "inference": raw_triple.get("inference", "explicit"),
            "justification": raw_triple.get("justification"),
            # Source grounding (from langextract)
            "char_start": raw_triple.get("char_start"),
            "char_end": raw_triple.get("char_end"),
            "extraction_text": raw_triple.get("extraction_text"),
        }

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
            List of extracted triples as dictionaries with:
                - head, relation, tail, inference, justification (Triple schema)
                - char_start, char_end, extraction_text (source grounding)
        """
        # Prepare the prompt (inject text into template)
        record = {"text": text}
        if record_id:
            record["id"] = record_id

        prompt_text = self._prepare_prompt(record)
        # Create examples for langextract
        examples = self._create_examples()

        # Extract using the client
        raw_triples = self.client.extract(
            text=prompt_text,
            prompt_description=self._get_extraction_prompt_description(),
            examples=examples,
            format_type=Triple,  # Passed for compatibility, GeminiClient uses FormatType.JSON
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Normalize triples to standard format
        triples = [self._normalize_triple(t) for t in raw_triples]

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
            Tuple of (triples, metadata) where metadata includes:
                - connectivity info
                - bridging_triples: List of triples added during refinement
                - Each triple has iteration_source field (0=initial, 1,2...=bridging)
        """
        import networkx as nx

        # Step 1: Initial extraction
        triples = self.extract_from_text(text, record_id, temperature, max_tokens)
        
        # Mark initial triples with iteration_source = 0
        for triple in triples:
            triple["iteration_source"] = 0

        # Build graph and analyze connectivity
        G = self._build_graph_from_triples(triples)
        components = list(nx.weakly_connected_components(G))
        num_components = len(components)

        # Track all bridging triples for separate output
        all_bridging_triples: list[dict[str, Any]] = []

        metadata = {
            "initial_extraction": {
                "triples": len(triples),
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "disconnected_components": num_components,
            },
            "refinement_iterations": [],
            "bridging_triples": [],  # Will be populated with all bridging triples
        }

        # Step 2: Iterative refinement if needed
        iteration = 0
        while num_components > max_disconnected and iteration < max_iterations:
            # Format component information for the prompt
            component_info = self._format_components(components, G)

            # Create bridging prompt (use template if available, otherwise hardcoded)
            if self.bridging_prompt_template:
                # Use custom template with variable substitution
                bridging_prompt = self.bridging_prompt_template.replace(
                    "{num_components}", str(num_components)
                ).replace(
                    "{component_info}", component_info
                ).replace(
                    "{text}", text
                )
            else:
                # Use hardcoded default prompt
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

            # Extract bridging triples using unconstrained generation
            # (bypasses langextract source grounding to allow for better inference)
            bridging_triples = self.client.generate_json(
                text=bridging_prompt,
                prompt_description="Extract bridging triples to connect graph components. Infer relations if necessary.",
                format_type=Triple,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Normalize bridging triples
            bridging_triples = [self._normalize_triple(t) for t in bridging_triples]

            # Filter out duplicates
            existing_triples_set = {
                (t['head'], t['relation'], t['tail'])
                for t in triples
            }
            new_triples = [
                t for t in bridging_triples
                if (t['head'], t['relation'], t['tail']) not in existing_triples_set
            ]

            # Mark new triples with iteration_source
            current_iteration = iteration + 1
            for triple in new_triples:
                triple["iteration_source"] = current_iteration

            # Early stopping: if no new triples found, LLM cannot find more connections
            if len(new_triples) == 0:
                metadata["refinement_iterations"].append({
                    "iteration": current_iteration,
                    "new_triples": 0,
                    "total_triples": len(triples),
                    "disconnected_components": num_components,
                    "early_stop_reason": "no_new_triples_found"
                })
                break

            # Add to triples and track bridging triples separately
            triples.extend(new_triples)
            all_bridging_triples.extend(new_triples)
            
            G = self._build_graph_from_triples(triples)
            components = list(nx.weakly_connected_components(G))

            # Early stopping: if components didn't decrease, no progress made
            prev_num_components = num_components
            num_components = len(components)

            # Record iteration metadata
            metadata["refinement_iterations"].append({
                "iteration": current_iteration,
                "new_triples": len(new_triples),
                "total_triples": len(triples),
                "disconnected_components": num_components,
            })

            # Early stopping: if no improvement in connectivity
            if num_components >= prev_num_components:
                metadata["refinement_iterations"][-1]["early_stop_reason"] = "no_connectivity_improvement"
                break

            iteration += 1

        # Determine stopping reason
        stop_reason = None
        if num_components <= max_disconnected:
            stop_reason = "connectivity_goal_achieved"
        elif iteration >= max_iterations:
            stop_reason = "max_iterations_reached"
        elif metadata["refinement_iterations"] and "early_stop_reason" in metadata["refinement_iterations"][-1]:
            stop_reason = metadata["refinement_iterations"][-1]["early_stop_reason"]

        # Store bridging triples in metadata
        metadata["bridging_triples"] = all_bridging_triples

        # Final metadata
        metadata["final_state"] = {
            "total_triples": len(triples),
            "initial_triples": metadata["initial_extraction"]["triples"],
            "bridging_triples": len(all_bridging_triples),
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "disconnected_components": num_components,
            "is_connected": num_components == 1,
            "iterations_used": iteration,
            "stop_reason": stop_reason,
            "connectivity_improvement": metadata["initial_extraction"]["disconnected_components"] - num_components,
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
        # Increase visibility to the model: more components and more nodes per component
        for i, component in enumerate(components[:30], 1):  # Show up to 30 components
            nodes = list(component)[:10]  # Show up to 10 nodes per component
            node_str = ", ".join(nodes)
            if len(component) > 10:
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
