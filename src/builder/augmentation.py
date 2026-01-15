"""Augmentation logic for improving graph connectivity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx
from ..clients import BaseLLMClient
from ..domains import KnowledgeDomain, Triple
from .extraction import extract_from_text, _normalize_triple, _prepare_prompt


def _build_graph_from_triples(triples: list[dict[str, Any]]) -> nx.DiGraph:
    """Build NetworkX graph from triples for analysis."""
    G = nx.DiGraph()
    for t in triples:
        head, tail = t.get("head"), t.get("tail")
        if head and tail:
            G.add_edge(head, tail, relation=t.get("relation"))
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
    initial_triples: list[dict[str, Any]] | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    max_disconnected: int = 3,
    max_iterations: int = 2,
    augmentation_strategy: str = "connectivity",
    prompt_override: str | None = None,
    augmentation_prompt_override: str | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract triples with iterative connectivity improvement.

    Args:
        client: LLM client
        domain: Knowledge domain
        text: Input text
        record_id: Record ID
        initial_triples: Optional existing triples to start from
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
    # 1. Initial Extraction (if needed)
    all_triples = initial_triples or extract_from_text(
        client, domain, text, record_id, temperature, max_tokens, prompt_override
    )

    augmentation_component = domain.get_augmentation(augmentation_strategy)
    aug_prompt_template = augmentation_prompt_override or augmentation_component.prompt
    aug_examples = [lx_data_example(ex) for ex in augmentation_component.examples]

    iterations_data = []

    # 2. Iterative Augmentation
    for i in range(max_iterations):
        G = _build_graph_from_triples(all_triples)
        components = list(nx.weakly_connected_components(G))
        
        if len(components) <= max_disconnected:
            break

        # Prepare augmentation prompt
        comp_text = _format_components(components, G)
        record = {
            "text": text,
            "current_triples": all_triples,
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
        
        new_triples = [_normalize_triple(t) for t in new_triples_raw]
        for nt in new_triples:
            nt["inference"] = "augmented"
        
        all_triples.extend(new_triples)
        iterations_data.append({
            "iteration": i + 1,
            "components_before": len(components),
            "new_triples_count": len(new_triples)
        })

    return all_triples, {"iterations": iterations_data, "final_components": len(components)}


def lx_data_example(raw_ex: dict[str, Any]) -> Any:
    """Helper to convert raw dict to langextract ExampleData."""
    import langextract as lx
    return lx.data.ExampleData(**raw_ex)
