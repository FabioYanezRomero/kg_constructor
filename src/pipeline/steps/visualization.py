"""Visualization pipeline steps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...visualization.network_viz import visualize_graph
from ...visualization.entity_viz import EntityVisualizer
from ..context import PipelineContext
from ..step import register_step


@register_step("visualize-network")
class VisualizeNetworkStep:
    """Pipeline step for interactive Plotly network visualizations."""
    
    def __init__(
        self, 
        output_dir: Path | str, 
        dark_mode: bool = False, 
        layout: str = "spring"
    ):
        """Initialize the network visualization step.
        
        Args:
            output_dir: Directory to save the output HTML.
            dark_mode: Whether to employ the premium dark scheme.
            layout: Visualization layout method.
        """
        self.output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
        self.dark_mode = dark_mode
        self.layout = layout

    def process(self, context: PipelineContext, **kwargs: Any) -> PipelineContext:
        """Generate network visualizations utilizing context triples.
        
        Args:
            context: The pipeline context containing triples for visualization.
            **kwargs: Unused.
            
        Returns:
            PipelineContext updated with visual HTML output artifacts.
        """
        if not context.triples:
            context.metadata["visualize_network_skipped"] = "True"
            return context

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / f"{context.record_id}.html"
            
            # Visualize directly utilizing the triples sequence and the title inference
            visualize_graph(
                graph=context.triples,
                output_path=output_path,
                title=f"Knowledge Graph: {context.record_id}",
                dark_mode=self.dark_mode,
                layout=self.layout
            )
            context.artifacts["network_viz_path"] = str(output_path)
        except Exception as e:
            context.errors.append(f"Network Visualization failed: {str(e)}")
            
        return context


@register_step("visualize-extraction")
class VisualizeExtractionStep:
    """Pipeline step for rendering extracted text segments directly inside the document."""
    
    def __init__(
        self, 
        output_dir: Path | str, 
        animation_speed: float = 1.0, 
        group_by: str = "entity_type"
    ):
        """Initialize the document visualizer engine.
        
        Args:
            output_dir: Destination path wrapper.
            animation_speed: Render CSS speed configuration.
            group_by: 'entity_type' or 'relation' classification mode.
        """
        self.output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
        self.animation_speed = animation_speed
        self.group_by = group_by

    def process(self, context: PipelineContext, **kwargs: Any) -> PipelineContext:
        """Embed rendering attributes directly against the document layout.
        
        Args:
            context: The executing pipeline Context object instance.
            **kwargs: Unused.
            
        Returns:
            PipelineContext with linked entity-mapped visualization documents.
        """
        if not context.text or not context.triples:
            context.metadata["visualize_extraction_skipped"] = "True (missing text or triples)"
            return context

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / f"{context.record_id}.html"
            
            visualizer = EntityVisualizer(animation_speed=self.animation_speed)
            visualizer.save_visualization(
                text=context.text,
                triples=context.triples,
                output_path=output_path,
                document_id=context.record_id,
                group_by=self.group_by
            )
            
            context.artifacts["extraction_viz_path"] = str(output_path)
        except Exception as e:
            context.errors.append(f"Extraction Visualization failed: {str(e)}")
            
        return context

__all__ = ["VisualizeNetworkStep", "VisualizeExtractionStep"]
