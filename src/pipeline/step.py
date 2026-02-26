"""Protocol and Registry for pipeline steps."""

from __future__ import annotations

from typing import Any, Protocol, Callable

from .context import PipelineContext


class PipelineStep(Protocol):
    """Protocol that all knowledge graph pipeline steps must implement.
    
    A step takes a PipelineContext, performs some action (extraction, translation, saving), 
    modifies and returns the context.
    """
    
    def process(self, context: PipelineContext, **kwargs: Any) -> PipelineContext:
        """Process the context and return the updated context.
        
        Args:
            context: The current state of the document in the pipeline.
            **kwargs: Engine-specific implementation details (clients, paths, parameters)
                      injected by the Orchestrator or the step instance itself.
                      
        Returns:
            The modified PipelineContext.
        """
        ...


# Central registry for pipeline steps
_STEP_REGISTRY: dict[str, PipelineStep] = {}


def register_step(name: str) -> Callable[[PipelineStep], PipelineStep]:
    """Decorator to register a new pipeline step.
    
    Usage:
        @register_step("extract")
        class ExtractionStep:
            def process(self, context: PipelineContext, **kwargs: Any) -> PipelineContext:
                ...
    
    Args:
        name: The name to register the step under.
        
    Returns:
        A decorator that registers the class and returns it unchanged.
    """
    def decorator(fn: PipelineStep) -> PipelineStep:
        if name in _STEP_REGISTRY:
            raise ValueError(f"Pipeline step '{name}' is already registered.")
        _STEP_REGISTRY[name] = fn
        return fn
    return decorator


def get_step(name: str) -> PipelineStep:
    """Retrieve a registered pipeline step class/factory by its name.
    
    Args:
        name: The name of the registered step.
        
    Returns:
        The step class or factory function.
        
    Raises:
        ValueError: If the step is not registered.
    """
    if name not in _STEP_REGISTRY:
        available = ", ".join(_STEP_REGISTRY.keys())
        raise ValueError(f"Unknown pipeline step '{name}'. Available: {available}")
    return _STEP_REGISTRY[name]


def list_available_steps() -> list[str]:
    """Get a list of all registered pipeline steps."""
    return list(_STEP_REGISTRY.keys())


__all__ = ["PipelineStep", "register_step", "get_step", "list_available_steps"]
