"""Augmentation strategies for iterative graph refinement.

This module provides:
- Strategy Protocol for extensibility
- Registry pattern for strategy dispatch
- Built-in connectivity strategy
"""

from __future__ import annotations

from typing import Any, Protocol, Callable, TYPE_CHECKING

import networkx as nx

from ..clients import BaseLLMClient
from ..domains import KnowledgeDomain, Triple, InferenceType
from .extraction import extract_from_text, _prepare_prompt

if TYPE_CHECKING:
    import langextract as lx


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
        input_data = raw_ex["input"]
        
        if isinstance(input_data, dict):
            text_part = f"Text: {input_data.get('text', '')}"
            comp_part = ""
            if "components" in input_data:
                comps = input_data["components"]
                comp_list = []
                for i, c in enumerate(comps, 1):
                    entities = c.get("entities", []) if isinstance(c, dict) else c
                    comp_list.append(f"Component {i}: [{', '.join(entities)}]")
                comp_part = "\nDisconnected Components:\n" + "\n".join(comp_list)
            example_text = text_part + comp_part
        else:
            example_text = str(input_data)

        return lx.data.ExampleData(
            text=example_text,
            extractions=[{"attributes": t} for t in raw_ex["output"]]
        )
    
    # Fallback/Unknown format
    return lx.data.ExampleData(text=str(raw_ex), extractions=[])


# =============================================================================
# Built-in Connectivity Strategy
# =============================================================================

def _format_components(components: list[set], G: nx.DiGraph) -> str:
    """Format disconnected components for the augmentation prompt."""
    formatted = []
    for i, nodes in enumerate(components, 1):
        node_list = ", ".join(list(nodes)[:10])
        if len(nodes) > 10:
            node_list += "..."
        formatted.append(f"Component {i}: [{node_list}]")
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
    aug_examples = [_format_example_for_client(ex) for ex in augmentation_component.examples]
    
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
            comp_text = _format_components(components, G)
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
                prompt_description=f"Identify missing relationships to connect: {comp_text}",
                examples=aug_examples,
                format_type=Triple,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            new_triples = []
            for t_raw in new_triples_raw:
                try:
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
            break

    final_G = _build_graph_from_triples(all_triples)
    final_components = list(nx.weakly_connected_components(final_G))

    metadata = {
        "strategy": "connectivity",
        "iterations": iterations_data, 
        "final_components": len(final_components),
        "partial_result": error_occurred
    }

    return all_triples, metadata


# =============================================================================
# Main Orchestrator (Backward Compatible)
# =============================================================================

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
    # 1. Initial Extraction (if needed)
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
        triples = validated_triples
    else:
        triples = extract_from_text(
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

    return strategy_fn(
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


__all__ = [
    "AugmentationStrategy",
    "register_strategy",
    "list_strategies",
    "STRATEGIES",
    "connectivity_strategy",
    "extract_connected_graph",
]
