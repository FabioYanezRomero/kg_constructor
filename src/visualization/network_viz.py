"""Interactive network visualization using Plotly.

Creates interactive HTML visualizations of knowledge graphs with
node/edge hover information and degree-based coloring.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import networkx as nx
import plotly.graph_objects as go


def visualize_graph(
    graph: nx.Graph | str | Path,
    output_path: Path | str | None = None,
    title: str | None = None,
    auto_open: bool = False
) -> go.Figure:
    """Visualize a graph with interactive Plotly.
    
    Args:
        graph: NetworkX graph or path to GraphML file
        output_path: Output HTML file path
        title: Optional title for the visualization
        auto_open: Whether to open in browser after saving
        
    Returns:
        Plotly Figure object
    """
    # Load graph if path provided
    if isinstance(graph, (str, Path)):
        graph_path = Path(graph)
        G = nx.read_graphml(str(graph_path))
        if title is None:
            title = graph_path.stem
        if output_path is None:
            output_path = graph_path.with_suffix(".html")
    else:
        G = graph
        if title is None:
            title = "Knowledge Graph"
    
    # Get layout positions
    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
    
    # ====================== EDGES ======================
    edge_traces = []
    
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_attrs = edge[2]
        
        # Build hover text
        hover_text = f"<b>Edge: {edge[0]} → {edge[1]}</b><br><br>"
        if edge_attrs:
            hover_text += "<b>Attributes:</b><br>"
            for key, value in edge_attrs.items():
                hover_text += f"<b>{key}:</b> {value}<br>"
        
        # Edge line
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode='lines',
            line=dict(width=2, color='#888'),
            hoverinfo='skip',
            showlegend=False
        ))
        
        # Hover marker at midpoint
        mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
        edge_traces.append(go.Scatter(
            x=[mid_x], y=[mid_y],
            mode='markers',
            marker=dict(size=20, color='rgba(0,0,0,0)', opacity=0),
            hovertext=[hover_text],
            hovertemplate='%{hovertext}<extra></extra>',
            showlegend=False
        ))
    
    # ====================== NODES ======================
    node_x, node_y, node_text, node_hover, node_colors = [], [], [], [], []
    
    for node, attrs in G.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(str(node))
        
        degree = G.degree(node)
        hover = f"<b>Node: {node}</b><br><br>"
        if attrs:
            hover += "<b>Attributes:</b><br>"
            for k, v in attrs.items():
                hover += f"<b>{k}:</b> {v}<br>"
        hover += f"<br><b>Connections:</b> {degree}"
        
        node_hover.append(hover)
        node_colors.append(degree)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        textfont=dict(size=10, color='black'),
        hovertemplate='%{hovertext}<extra></extra>',
        hovertext=node_hover,
        marker=dict(
            showscale=True,
            colorscale='Viridis',
            color=node_colors,
            size=20,
            colorbar=dict(thickness=15, title='Degree', xanchor='left'),
            line=dict(width=2, color='white')
        ),
        showlegend=False
    )
    
    # ====================== FIGURE ======================
    fig = go.Figure(data=edge_traces + [node_trace])
    
    fig.update_layout(
        title=dict(text=f'<b>{title}</b>', x=0.5, xanchor='center', font=dict(size=16)),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        annotations=[dict(
            text=f"Nodes: {G.number_of_nodes()} | Edges: {G.number_of_edges()}",
            showarrow=False, xref="paper", yref="paper", x=0.005, y=-0.002
        )],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        width=1200,
        height=800
    )
    
    # Save
    if output_path:
        fig.write_html(str(output_path), auto_open=auto_open)
        print(f"✓ Saved: {output_path} ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")
    
    return fig


def batch_visualize_graphs(
    input_dir: Path | str,
    output_dir: Path | str | None = None
) -> list[Path]:
    """Visualize all GraphML files in a directory.
    
    Args:
        input_dir: Directory containing .graphml files
        output_dir: Output directory for HTML files
        
    Returns:
        List of paths to created HTML files
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir / "visualizations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    graphml_files = list(input_dir.glob("*.graphml"))
    
    if not graphml_files:
        print(f"No .graphml files found in {input_dir}")
        return []
    
    print(f"Visualizing {len(graphml_files)} graphs...")
    
    html_files = []
    for graphml_file in graphml_files:
        output_path = output_dir / f"{graphml_file.stem}.html"
        try:
            visualize_graph(graphml_file, output_path)
            html_files.append(output_path)
        except Exception as e:
            print(f"✗ Error with {graphml_file.name}: {e}")
    
    print(f"\n✓ Saved {len(html_files)} visualizations to {output_dir}")
    return html_files


__all__ = ["visualize_graph", "batch_visualize_graphs"]
