"""Pipeline orchestrator for executing sequences of steps."""

from __future__ import annotations

from typing import Sequence
from .context import PipelineContext
from .step import PipelineStep

import concurrent.futures
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn


class PipelineRunner:
    """Executes a dynamically configured sequence of pipeline steps over multiple contexts."""
    
    def __init__(self, steps: Sequence[PipelineStep]):
        """Initialize the pipeline with a specific logical sequence of steps.
        
        Args:
            steps: The instantiated sequence of steps to execute sequentially per document.
        """
        self.steps = steps

    def execute_single(self, context: PipelineContext) -> PipelineContext:
        """Run a single context sequentially through the pipeline sequence.
        
        Args:
            context: The initialized data context for a single document.
            
        Returns:
            The final context after all steps have executed.
        """
        for step in self.steps:
            try:
                context = step.process(context)
            except Exception as e:
                context.errors.append(f"Error in {step.__class__.__name__}: {str(e)}")
            
            # Fast fail if a critical error occurs
            if context.errors:
                break
        
        return context

    def execute_batch(
        self, 
        contexts: list[PipelineContext], 
        max_workers: int | None = None,
        show_progress: bool = True
    ) -> list[PipelineContext]:
        """Execute the pipeline concurrently across multiple contexts.
        
        Args:
            contexts: A list of PipelineContext records.
            max_workers: Size of the ThreadPoolExecutor. None = Python default.
            show_progress: Provide rich progress tracking in the terminal.
            
        Returns:
            List of fully processed PipelineContexts.
        """
        results = []
        
        if show_progress:
            # Setup Rich Progress Bars
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                
                task_id = progress.add_task("Running Pipeline...", total=len(contexts))
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_ctx = {
                        executor.submit(self.execute_single, ctx): ctx 
                        for ctx in contexts
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_ctx):
                        results.append(future.result())
                        progress.advance(task_id)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(self.execute_single, contexts))
            
        return results

__all__ = ["PipelineRunner"]
