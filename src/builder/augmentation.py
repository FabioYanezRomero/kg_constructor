"""Augmentation logic for improving graph connectivity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx
from ..clients import BaseLLMClient
from ..domains import KnowledgeDomain, Triple, InferenceType
from .extraction import extract_from_text, _prepare_prompt


def _build_graph_from_triples(triples: list[Triple]) -> nx.DiGraph:
    """Build NetworkX graph from Triple objects for analysis."""
    G = nx.DiGraph()
    for t in triples:
        if t.head and t.tail:
            G.add_edge(t.head, t.tail, relation=t.relation)
    return G


def _format_components(components: list[set], G: nx.DiGraph) -> str:
    """Format disconnected components for the augmentation prompt."""
    formatted = []
    for i, nodes in enumerate(components, 1):
        node_list = ", ".join(list(nodes)[:10])
        if len(nodes) > 10:
            node_list += "..."
        formatted.append(f"Component {i}: [{node_list}]")
    return "\n".join(formatted)


def extract_connected_graph(
    client: BaseLLMClient,
    domain: KnowledgeDomain,
    text: str,
    record_id: str | None = None,
    initial_triples: list[Triple] | list[dict[str, Any]] | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    max_disconnected: int = 3,
    max_iterations: int = 2,
    augmentation_strategy: str = "connectivity",
    prompt_override: str | None = None,
    augmentation_prompt_override: str | None = None
) -> tuple[list[Triple], dict[str, Any]]:
    """Extract triples with iterative connectivity improvement.

    Preserves partial results if an augmentation iteration fails.

    Args:
        client: LLM client
        domain: Knowledge domain
        text: Input text
        record_id: Record ID
        initial_triples: Optional existing triples to start from (will be validated)
        temperature: Sampling temperature
        max_tokens: Max tokens
        max_disconnected: Target max number of components
        max_iterations: Max iterations for augmentation
        augmentation_strategy: Strategy name
        prompt_override: Extraction prompt override
        augmentation_prompt_override: Augmentation prompt override

    Returns:
        Tuple of (all_triples, metadata)
    """
    # 1. Initial Extraction (if needed) and validation
    if initial_triples:
        validated_triples = []
        for t in initial_triples:
            if isinstance(t, Triple):
                validated_triples.append(t)
            else:
                try:
                    validated_triples.append(Triple(**t))
                except Exception as e:
                    print(f"Warning: Skipping invalid initial triple: {e}")
        all_triples = validated_triples
    else:
        all_triples = extract_from_text(
            client, domain, text, record_id, temperature, max_tokens, prompt_override
        )

    augmentation_component = domain.get_augmentation(augmentation_strategy)
    aug_prompt_template = augmentation_prompt_override or augmentation_component.prompt
    aug_examples = [_format_example_for_client(ex) for ex in augmentation_component.examples]

    iterations_data = []
    error_occurred = False

    # 2. Iterative Augmentation
    for i in range(max_iterations):
        try:
            G = _build_graph_from_triples(all_triples)
            components = list(nx.weakly_connected_components(G))
            
            if len(components) <= max_disconnected:
                break

            # Prepare augmentation prompt
            comp_text = _format_components(components, G)
            
            # Serialize current triples for prompt (as dicts)
            current_triples_dicts = [t.model_dump() for t in all_triples]
            
            record = {
                "text": text,
                "current_triples": current_triples_dicts,
                "disconnected_components": comp_text
            }
            
            prompt_text = _prepare_prompt(aug_prompt_template, record)
            
            # Call LLM for bridge triples
            new_triples_raw = client.extract(
                text=prompt_text,
                prompt_description=f"Identify missing relationships to connect the following disconnected components: {comp_text}",
                examples=aug_examples,
                format_type=Triple,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            new_triples = []
            for t_raw in new_triples_raw:
                # Use Triple model to normalize then update inference type
                try:
                    # langextract/clients might return dicts.
                    # We want to force inference=CONTEXTUAL for augmented triples.
                    t_dict = t_raw if isinstance(t_raw, dict) else t_raw.model_dump()
                    t_dict["inference"] = InferenceType.CONTEXTUAL
                    new_triples.append(Triple(**t_dict))
                except Exception as e:
                    print(f"Warning: Skipping invalid augmented triple: {e}")
            
            all_triples.extend(new_triples)
            iterations_data.append({
                "iteration": i + 1,
                "components_before": len(components),
                "new_triples_count": len(new_triples),
                "status": "success"
            })
            
        except Exception as e:
            print(f"Error during augmentation iteration {i+1}: {e}")
            iterations_data.append({
                "iteration": i + 1,
                "status": "failed",
                "error": str(e)
            })
            error_occurred = True
            break # Exit loop but return what we have

    final_G = _build_graph_from_triples(all_triples)
    final_components = list(nx.weakly_connected_components(final_G))

    metadata = {
        "iterations": iterations_data, 
        "final_components": len(final_components),
        "partial_result": error_occurred
    }

    return all_triples, metadata


def _format_example_for_client(raw_ex: dict[str, Any]) -> Any:
    """Helper to convert raw dict to langextract ExampleData.
    
    Handles both extraction (text/extractions) and augmentation (input/output) formats.
    """
    import langextract as lx
    
    # 1. Standard Extraction Example
    if "text" in raw_ex and "extractions" in raw_ex:
        return lx.data.ExampleData(**raw_ex)
    
    # 2. Augmentation Example (input/output)
    if "input" in raw_ex and "output" in raw_ex:
        # Convert the complex input to a string representation for the LLM
        # This matches how the real prompt is constructed in extract_connected_graph
        input_data = raw_ex["input"]
        
        # If input is a dict (from JSON), we can format it.
        # Otherwise if it's already a string, use it.
        if isinstance(input_data, dict):
            # We want something like: 
            # Text: ... 
            # Disconnected Components: ...
            text_part = f"Text: {input_data.get('text', '')}"
            comp_part = ""
            if "components" in input_data:
                # Format components manually for the example text
                comps = input_data["components"]
                comp_list = []
                for i, c in enumerate(comps, 1):
                    entities = c.get("entities", []) if isinstance(c, dict) else c
                    comp_list.append(f"Component {i}: [{', '.join(entities)}]")
                comp_part = "\nDisconnected Components:\n" + "\n".join(comp_list)
            example_text = text_part + comp_part
        else:
            example_text = str(input_data)

        # Output to extractions
        # langextract expects extractions to be raw dicts or lx.data.ExtractionData
        return lx.data.ExampleData(
            text=example_text,
            extractions=[{"attributes": t} for t in raw_ex["output"]]
        )
    
    # Fallback/Unknown format
    return lx.data.ExampleData(text=str(raw_ex), extractions=[])
