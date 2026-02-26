"""Knowledge Graph dynamic unified pipeline module.

Enables dynamically chained logic executions across processing contexts.
"""

from .context import PipelineContext
from .step import PipelineStep, register_step, get_step, list_available_steps
from .runner import PipelineRunner

# Explicitly load implementations to trigger their @register_step decorators.
# These will register the steps in the registry upon importing the `pipeline` module.
from .steps import extraction, augmentation, export, converter, visualization

__all__ = [
    "PipelineContext",
    "PipelineStep",
    "register_step",
    "get_step",
    "list_available_steps",
    "PipelineRunner"
]
