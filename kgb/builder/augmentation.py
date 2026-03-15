"""Augmentation strategies for iterative graph refinement.

This module provides:
- Strategy Protocol for extensibility
- Registry pattern for strategy dispatch
- Built-in connectivity strategy
"""

from __future__ import annotations

from typing import Any, Protocol, Callable

import networkx as nx

from ..clients import BaseLLMClient
from ..domains import KnowledgeDomain, Triple, InferenceType
from .extraction import (
    _build_schema_guidance,
    _collect_schema_constraints,
    _render_prompt_template,
    _validate_triples_against_schema,
    _warn_on_schema_validation,
    extract_triples,
)

# =============================================================================
# Strategy Protocol & Registry
# =============================================================================

class AugmentationStrategy(Protocol):
    """Protocol for augmentation strategies.
    
    Strategy-specific parameters (e.g., max_iterations, max_disconnected)
    are passed via **kwargs and handled by each strategy individually.
    """
    def __call__(
        self,
        client: BaseLLMClient,
        domain: KnowledgeDomain,
        text: str,
        triples: list[Triple],
        **kwargs: Any
    ) -> tuple[list[Triple], dict[str, Any]]:
        """Execute the strategy.
        
        Args:
            client: LLM client for generation
            domain: Knowledge domain with prompts/examples
            text: Original source text
            triples: Current list of triples
            **kwargs: Strategy-specific parameters
            
        Returns:
            Tuple of (refined_triples, metadata)
        """
        ...


STRATEGIES: dict[str, AugmentationStrategy] = {}


def register_strategy(name: str) -> Callable[[AugmentationStrategy], AugmentationStrategy]:
    """Decorator for registering augmentation strategies.
    
    Usage:
        @register_strategy("my_strategy")
        def my_strategy(client, domain, text, triples, **kwargs):
            ...
            return refined_triples, metadata
    """
    def decorator(fn: AugmentationStrategy) -> AugmentationStrategy:
        STRATEGIES[name] = fn
        return fn
    return decorator


def list_strategies() -> list[str]:
    """List all registered augmentation strategies."""
    return list(STRATEGIES.keys())


# =============================================================================
# Shared Utilities
# =============================================================================

def _build_graph_from_triples(triples: list[Triple]) -> nx.DiGraph:
    """Build NetworkX graph from Triple objects for analysis."""
    G = nx.DiGraph()
    for t in triples:
        if t.head and t.tail:
            G.add_edge(t.head, t.tail, relation=t.relation)
    return G


# =============================================================================
# Built-in Connectivity Strategy
# =============================================================================

def _format_components(components: list[set], G: nx.DiGraph, triples: list) -> str:
    """Format disconnected components with their triples for the augmentation prompt.
    
    Args:
        components: List of sets of node names (from nx.weakly_connected_components)
        G: The NetworkX graph
        triples: List of Triple objects
        
    Returns:
        Formatted string showing each component with its entities and triples
    """
    formatted = []
    
    for i, nodes in enumerate(components, 1):
        # Get entities in this component
        node_list = list(nodes)[:15]  # Limit to 15 entities for readability
        truncated = len(nodes) > 15
        
        # Find triples that belong to this component (both head and tail in this component)
        component_triples = []
        for t in triples:
            head = getattr(t, 'head', t.get('head', '')) if isinstance(t, dict) else t.head
            tail = getattr(t, 'tail', t.get('tail', '')) if isinstance(t, dict) else t.tail
            if head in nodes or tail in nodes:
                relation = getattr(t, 'relation', t.get('relation', '')) if isinstance(t, dict) else t.relation
                component_triples.append(f"  ({head}) --[{relation}]--> ({tail})")
        
        # Format component output
        entity_str = ", ".join(node_list)
        if truncated:
            entity_str += f"... (+{len(nodes) - 15} more)"
        
        comp_output = f"Component {i}:\n"
        comp_output += f"  Entities: [{entity_str}]\n"
        comp_output += f"  Triples ({len(component_triples)}):\n"
        
        # Limit triples shown per component
        for triple_str in component_triples[:10]:
            comp_output += f"    {triple_str}\n"
        if len(component_triples) > 10:
            comp_output += f"    ... (+{len(component_triples) - 10} more triples)\n"
        
        formatted.append(comp_output)
    
    return "\n".join(formatted)


@register_strategy("connectivity")
def connectivity_strategy(
    client: BaseLLMClient,
    domain: KnowledgeDomain,
    text: str,
    triples: list[Triple],
    *,
    max_disconnected: int = 3,
    max_iterations: int = 2,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    augmentation_prompt_override: str | None = None,
    **kwargs: Any
) -> tuple[list[Triple], dict[str, Any]]:
    """Connectivity augmentation: Reduce disconnected graph components.
    
    Iteratively prompts the LLM to find bridging relationships between
    disconnected components until the target is reached or max iterations.
    
    Args:
        client: LLM client
        domain: Knowledge domain
        text: Source text
        triples: Initial triples
        max_disconnected: Target max number of components (default: 3)
        max_iterations: Max refinement iterations (default: 2)
        temperature: Sampling temperature
        max_tokens: Max tokens for LLM
        augmentation_prompt_override: Override the default prompt
        
    Returns:
        Tuple of (all_triples, metadata)
    """
    augmentation_component = domain.get_augmentation("connectivity")
    aug_prompt_template = augmentation_prompt_override or augmentation_component.prompt
    constraints = _collect_schema_constraints(domain, augmentation_component.examples)
    
    all_triples = list(triples)  # Copy to avoid mutating input
    iterations_data = []
    error_occurred = False

    for i in range(max_iterations):
        try:
            G = _build_graph_from_triples(all_triples)
            components = list(nx.weakly_connected_components(G))
            
            if len(components) <= max_disconnected:
                break

            # Prepare augmentation prompt
            comp_text = _format_components(components, G, all_triples)
            current_triples_dicts = [t.model_dump() for t in all_triples]
            
            record = {
                "text": text,
                "current_triples": current_triples_dicts,
                "disconnected_components": comp_text
            }
            
            final_prompt = _render_prompt_template(
                aug_prompt_template,
                record,
                schema_guidance=_build_schema_guidance(constraints),
            )
            
            # Call LLM for bridge triples using augment (NOT extract)
            # Augmentation generates NEW bridging triples that don't need source grounding
            # The extract() method uses langextract's grounding which fails for augmentation
            new_triples_raw = client.augment(
                text=final_prompt,
                prompt_description=f"Generate bridging triples to connect disconnected components",
                format_type=Triple,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            new_triples = []
            normalized_new_triples_raw: list[dict[str, Any]] = []
            for t_raw in new_triples_raw:
                try:
                    t_dict = t_raw if isinstance(t_raw, dict) else t_raw.model_dump()
                    t_dict["inference"] = InferenceType.CONTEXTUAL
                    new_triples.append(Triple(**t_dict))
                    normalized_new_triples_raw.append(t_dict)
                except Exception as e:
                    print(f"Warning: Skipping invalid augmented triple: {e}")

            validated_new_triples, validation_summary = _validate_triples_against_schema(
                new_triples,
                constraints,
                raw_triples=normalized_new_triples_raw,
            )
            _warn_on_schema_validation("augmentation", validation_summary)

            all_triples.extend(validated_new_triples)
            iterations_data.append({
                "iteration": i + 1,
                "components_before": len(components),
                "new_triples_count": len(validated_new_triples),
                "status": "success",
                "schema_validation": validation_summary,
            })
            
        except Exception as e:
            print(f"Error during augmentation iteration {i+1}: {e}")
            iterations_data.append({
                "iteration": i + 1,
                "status": "failed",
                "error": str(e)
            })
            error_occurred = True
            break

    final_G = _build_graph_from_triples(all_triples)
    final_components = list(nx.weakly_connected_components(final_G))

    metadata = {
        "strategy": "connectivity",
        "iterations": iterations_data, 
        "final_components": len(final_components),
        "partial_result": error_occurred,
        "schema_constraints_applied": constraints.enforce,
        "allowed_entity_types": list(constraints.entity_types),
        "allowed_relation_types": list(constraints.relation_types),
    }

    return all_triples, metadata


# =============================================================================
# Main Orchestrator (Backward Compatible)
# =============================================================================

def augment_triples(
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
    """Extract triples with iterative improvement via a registered strategy.

    This function orchestrates:
    1. Initial extraction (if no triples provided)
    2. Triple validation
    3. Strategy dispatch

    Args:
        client: LLM client
        domain: Knowledge domain
        text: Input text
        record_id: Record ID
        initial_triples: Optional existing triples to start from
        temperature: Sampling temperature
        max_tokens: Max tokens
        max_disconnected: Target max components (passed to strategy)
        max_iterations: Max iterations (passed to strategy)
        augmentation_strategy: Strategy name (default: "connectivity")
        prompt_override: Extraction prompt override
        augmentation_prompt_override: Augmentation prompt override

    Returns:
        Tuple of (all_triples, metadata)
        
    Raises:
        ValueError: If the strategy is not registered
    """
    initial_schema_validation: dict[str, Any] | None = None

    # 1. Initial Extraction (if needed)
    if initial_triples:
        validated_triples = []
        raw_validated_triples: list[dict[str, Any]] = []
        for t in initial_triples:
            if isinstance(t, Triple):
                validated_triples.append(t)
                raw_validated_triples.append(t.model_dump())
            else:
                try:
                    triple = Triple(**t)
                    validated_triples.append(triple)
                    raw_validated_triples.append(t)
                except Exception as e:
                    print(f"Warning: Skipping invalid initial triple: {e}")
        extraction_constraints = _collect_schema_constraints(domain, domain.extraction.examples)
        triples, validation_summary = _validate_triples_against_schema(
            validated_triples,
            extraction_constraints,
            raw_triples=raw_validated_triples,
        )
        initial_schema_validation = validation_summary
        _warn_on_schema_validation("augmentation bootstrap", validation_summary)
    else:
        triples = extract_triples(
            client, domain, text, record_id, temperature, max_tokens, prompt_override
        )

    # 2. Strategy Dispatch
    strategy_fn = STRATEGIES.get(augmentation_strategy)
    if not strategy_fn:
        available = ", ".join(list_strategies())
        raise ValueError(
            f"Unknown augmentation strategy: '{augmentation_strategy}'. "
            f"Available: [{available}]"
        )

    triples, metadata = strategy_fn(
        client=client,
        domain=domain,
        text=text,
        triples=triples,
        max_disconnected=max_disconnected,
        max_iterations=max_iterations,
        temperature=temperature,
        max_tokens=max_tokens,
        augmentation_prompt_override=augmentation_prompt_override
    )
    if initial_schema_validation is not None:
        metadata["initial_schema_validation"] = initial_schema_validation
    return triples, metadata


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
    """Backward-compatible alias for ``augment_triples``."""
    return augment_triples(
        client=client,
        domain=domain,
        text=text,
        record_id=record_id,
        initial_triples=initial_triples,
        temperature=temperature,
        max_tokens=max_tokens,
        max_disconnected=max_disconnected,
        max_iterations=max_iterations,
        augmentation_strategy=augmentation_strategy,
        prompt_override=prompt_override,
        augmentation_prompt_override=augmentation_prompt_override,
    )


__all__ = [
    "AugmentationStrategy",
    "register_strategy",
    "list_strategies",
    "STRATEGIES",
    "connectivity_strategy",
    "augment_triples",
    "extract_connected_graph",
]
