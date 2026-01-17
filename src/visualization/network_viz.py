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


from ..domains import Triple


def visualize_graph(
    graph: nx.Graph | str | Path | list[Triple] | list[dict[str, Any]],
    output_path: Path | str | None = None,
    title: str | None = None,
    dark_mode: bool = False,
    layout: str = "spring",
    auto_open: bool = False
) -> go.Figure:
    """Visualize a graph with interactive Plotly.
    
    Args:
        graph: NetworkX graph, path to GraphML, or list of triples
        output_path: Output HTML file path
        title: Optional title for the visualization
        dark_mode: Whether to use dark mode theme
        layout: Layout algorithm ('spring', 'circular', 'kamada_kawai', 'shell')
        auto_open: Whether to open in browser after saving
        
    Returns:
        Plotly Figure object
    """
    # 1. Load or Build Graph
    if isinstance(graph, (str, Path)):
        graph_path = Path(graph)
        G = nx.read_graphml(str(graph_path))
        if title is None:
            title = graph_path.stem
        if output_path is None:
            output_path = graph_path.with_suffix(".html")
    elif isinstance(graph, list):
        # Build from triples
        G = nx.DiGraph()
        for t in graph:
            if isinstance(t, Triple):
                G.add_edge(t.head, t.tail, relation=t.relation, inference=str(t.inference))
            else:
                G.add_edge(t.get("head"), t.get("tail"), **{k: v for k, v in t.items() if k not in ["head", "tail"]})
        if title is None:
            title = "Extracted Knowledge Graph"
    else:
        G = graph
        if title is None:
            title = "Knowledge Graph"
    
    # 2. Calculate Layout
    if layout == "circular":
        pos = nx.circular_layout(G)
    elif layout == "kamada_kawai":
        pos = nx.kamada_kawai_layout(G)
    elif layout == "shell":
        pos = nx.shell_layout(G)
    else:
        pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
    
    # 3. Theme Configuration
    theme = {
        "bg": "#0f172a" if dark_mode else "white",
        "text": "#f1f5f9" if dark_mode else "#1e293b",
        "grid": "#334155" if dark_mode else "#e2e8f0",
        "edge": "#475569" if dark_mode else "#94a3b8",
        "node_line": "#1e293b" if dark_mode else "white",
        "colorscale": "Turbo" # Premium multi-color scale
    }
    
    # 4. Build Traces
    edge_traces = []
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_attrs = edge[2]
        
        # Build hover text
        hover_text = f"<b>{edge[0]} → {edge[1]}</b><br><br>"
        if edge_attrs:
            for key, value in edge_attrs.items():
                hover_text += f"<b>{key}:</b> {value}<br>"
        
        # Line style (dashed for augmented if present)
        is_augmented = edge_attrs.get("inference") == "contextual"
        line_style = dict(width=1.5, color=theme["edge"])
        if is_augmented:
            line_style["dash"] = "dash"
            line_style["width"] = 1
        
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode='lines',
            line=line_style,
            hoverinfo='skip',
            showlegend=False
        ))
        
        # Hover marker at 1/3 and 2/3 for directionality hint and better hover access
        for m in [0.5]:
            mx, my = x0 + m*(x1-x0), y0 + m*(y1-y0)
            edge_traces.append(go.Scatter(
                x=[mx], y=[my],
                mode='markers',
                marker=dict(size=12, color='rgba(0,0,0,0)', opacity=0),
                hovertext=[hover_text],
                hovertemplate='%{hovertext}<extra></extra>',
                showlegend=False
            ))
    
    node_x, node_y, node_text, node_hover, node_colors, node_sizes = [], [], [], [], [], []
    for node, attrs in G.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"<b>{node}</b>")
        
        degree = G.degree(node)
        hover = f"<b>{node}</b><br><br>"
        if attrs:
            for k, v in attrs.items():
                hover += f"<b>{k}:</b> {v}<br>"
        hover += f"<br><b>Degree:</b> {degree}"
        
        node_hover.append(hover)
        node_colors.append(degree)
        node_sizes.append(20 + degree * 2) # Size based on importance
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        textfont=dict(size=11, color=theme["text"]),
        hovertemplate='%{hovertext}<extra></extra>',
        hovertext=node_hover,
        marker=dict(
            showscale=True,
            colorscale=theme["colorscale"],
            color=node_colors,
            size=node_sizes,
            colorbar=dict(
                thickness=15, 
                title=dict(text='Degree', font=dict(color=theme["text"])), 
                xanchor='left',
                tickfont=dict(color=theme["text"])
            ),
            line=dict(width=1.5, color=theme["node_line"])
        ),
        showlegend=False
    )
    
    # 5. Figure Assembly
    fig = go.Figure(data=edge_traces + [node_trace])
    
    fig.update_layout(
        title=dict(
            text=f'<b>{title}</b>', 
            x=0.5, xanchor='center', 
            font=dict(size=20, color=theme["text"])
        ),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=40, l=40, r=40, t=80),
        paper_bgcolor=theme["bg"],
        plot_bgcolor=theme["bg"],
        annotations=[dict(
            text=f"Nodes: {G.number_of_nodes()} | Edges: {G.number_of_edges()} | Layout: {layout.capitalize()}",
            showarrow=False, xref="paper", yref="paper", 
            x=0, y=-0.05, font=dict(color=theme["muted-text"] if "muted-text" in theme else theme["text"], size=10)
        )],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        width=1200,
        height=800
    )
    
    # 6. Save
    if output_path:
        fig.write_html(str(output_path), auto_open=auto_open)
    
    return fig


def batch_visualize_graphs(
    input_dir: Path | str,
    output_dir: Path | str | None = None,
    dark_mode: bool = False,
    layout: str = "spring"
) -> list[Path]:
    """Visualize all GraphML files in a directory.
    
    Args:
        input_dir: Directory containing .graphml files
        output_dir: Output directory for HTML files
        dark_mode: Whether to use dark mode
        layout: Layout algorithm
        
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
            visualize_graph(graphml_file, output_path, dark_mode=dark_mode, layout=layout)
            html_files.append(output_path)
            print(f"✓ Created: {output_path.name}")
        except Exception as e:
            print(f"✗ Error with {graphml_file.name}: {e}")
    
    return html_files


__all__ = ["visualize_graph", "batch_visualize_graphs"]
