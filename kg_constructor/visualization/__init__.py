"""Graph visualization module.

Provides visualization tools for knowledge graphs:
- Network visualization (Plotly) - shows nodes and edges
- Entity highlighting (langextract) - highlights entities in source text
"""

from .network_viz import visualize_graph, batch_visualize_graphs
from .entity_viz import EntityVisualizer

__all__ = ["visualize_graph", "batch_visualize_graphs", "EntityVisualizer"]
