"""Connectivity augmentation pipeline step."""

from __future__ import annotations

from typing import Any

from ...builder import extract_connected_graph
from ...clients import BaseLLMClient
from ...domains import KnowledgeDomain

from ..context import PipelineContext
from ..step import register_step


@register_step("augment")
class AugmentationStep:
    """Pipeline step for refining extracted knowledge graphs."""
    
    def __init__(
        self, 
        client: BaseLLMClient, 
        domain: KnowledgeDomain, 
        strategy: str = "connectivity",
        max_disconnected: int = 3,
        max_iterations: int = 2,
        temperature: float = 0.0,
        augmentation_prompt_override: str | None = None
    ):
        """Initialize the augmentation step.
        
        Args:
            client: Instantiated LLM client to use.
            domain: Knowledge domain defining the augmentation prompt context.
            strategy: The augmentation strategy to employ (default: connectivity).
            max_disconnected: Constraint parameter for connectivity tracking.
            max_iterations: Max retry attempts parameter.
            temperature: LLM temperature setting.
            augmentation_prompt_override: Optional custom prompt text.
        """
        self.client = client
        self.domain = domain
        self.strategy = strategy
        self.max_disconnected = max_disconnected
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.augmentation_prompt_override = augmentation_prompt_override

    def process(self, context: PipelineContext, **kwargs: Any) -> PipelineContext:
        """Execute augmentation to connect graph components via inference.
        
        Args:
            context: The pipeline context with existing triples to refine.
            **kwargs: Unused.
            
        Returns:
            PipelineContext with refined graph triples.
        """
        if not context.triples:
            context.metadata["augmentation_skipped"] = "True (no initial triples found)"
            return context

        try:
            triples, metadata = extract_connected_graph(
                client=self.client,
                domain=self.domain,
                text=context.text,
                record_id=context.record_id,
                initial_triples=context.triples,
                temperature=self.temperature,
                max_disconnected=self.max_disconnected,
                max_iterations=self.max_iterations,
                augmentation_strategy=self.strategy,
                augmentation_prompt_override=self.augmentation_prompt_override
            )
            # Override former triples state with augmented ones
            context.triples = triples
            
            # Store metadata
            context.metadata["augmentation_" + self.strategy] = metadata
            
        except Exception as e:
            context.errors.append(f"Augmentation '{self.strategy}' failed: {str(e)}")
            
        return context

__all__ = ["AugmentationStep"]
