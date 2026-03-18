"""Interactive graph visualization using Plotly.

Creates interactive HTML visualizations of knowledge graphs with
node/edge hover information and origin-based coloring (extracted vs augmented).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import networkx as nx
import plotly.graph_objects as go


from networkx.algorithms.community import greedy_modularity_communities

from ..domains import Triple


def _resolve_overlaps(
    pos: dict, G: nx.DiGraph | nx.Graph, iterations: int = 50, pad: float = 0.03
) -> dict:
    """Push apart nodes whose positions overlap.

    Each node has a radius proportional to its marker size (20 + degree*2),
    normalised into layout-coordinate space.  When two radii overlap (plus
    *pad* clearance), both nodes are nudged apart along the line between
    them.  The process repeats for *iterations* rounds or until no overlaps
    remain.
    """
    nodes = list(pos.keys())
    n = len(nodes)
    if n < 2:
        return pos

    # Work with mutable lists for speed
    xs = [pos[nd][0] for nd in nodes]
    ys = [pos[nd][1] for nd in nodes]

    # Compute per-node radius in layout-coordinate scale.
    # Marker sizes are 20+degree*2 pixels on a 1400-wide figure whose
    # layout coords span roughly [-1, 1], so 1 layout unit ≈ 700 px.
    px_to_coord = 1.0 / 700.0
    radii = [(20 + G.degree(nd) * 2) * px_to_coord for nd in nodes]

    for _ in range(iterations):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                dx = xs[j] - xs[i]
                dy = ys[j] - ys[i]
                dist = math.hypot(dx, dy)
                min_dist = radii[i] + radii[j] + pad
                if dist < min_dist:
                    if dist == 0:
                        # Coincident — nudge in arbitrary direction
                        dx, dy, dist = 0.01, 0.01, math.hypot(0.01, 0.01)
                    overlap = (min_dist - dist) / 2.0
                    ux, uy = dx / dist, dy / dist
                    xs[i] -= ux * overlap
                    ys[i] -= uy * overlap
                    xs[j] += ux * overlap
                    ys[j] += uy * overlap
                    moved = True
        if not moved:
            break

    return {nd: (xs[k], ys[k]) for k, nd in enumerate(nodes)}


def _community_layout(G: nx.DiGraph | nx.Graph) -> dict:
    """Two-level layout: position community clusters, then nodes within each."""
    UG = G.to_undirected()
    communities = list(greedy_modularity_communities(UG))

    if len(communities) <= 1:
        n = G.number_of_nodes()
        k = 3.0 / math.sqrt(n) if n > 1 else 1.0
        return nx.spring_layout(G, k=k, iterations=200, seed=42)

    # Level 1: position community centroids
    meta = nx.Graph()
    for i in range(len(communities)):
        meta.add_node(i)
    for u, v in UG.edges():
        cu = next(i for i, c in enumerate(communities) if u in c)
        cv = next(i for i, c in enumerate(communities) if v in c)
        if cu != cv:
            if meta.has_edge(cu, cv):
                meta[cu][cv]['weight'] += 1
            else:
                meta.add_edge(cu, cv, weight=1)
    centroids = nx.spring_layout(meta, k=4.0, iterations=300, seed=42)

    # Level 2: position nodes within each community
    pos = {}
    for i, comm in enumerate(communities):
        cx, cy = centroids[i]
        if len(comm) == 1:
            pos[list(comm)[0]] = (cx, cy)
            continue
        sub = UG.subgraph(comm)
        k_local = 1.5 / math.sqrt(len(comm))
        local = nx.spring_layout(sub, k=k_local, iterations=100, seed=42)
        spread = 0.12 + 0.04 * len(comm)
        for nd, (lx, ly) in local.items():
            pos[nd] = (cx + lx * spread, cy + ly * spread)
    return pos


def render_graph(
    graph: nx.Graph | str | Path | list[Triple] | list[dict[str, Any]],
    output_path: Path | str | None = None,
    title: str | None = None,
    dark_mode: bool = False,
    layout: str = "community",
    auto_open: bool = False
) -> go.Figure:
    """Render a graph with interactive Plotly.

    Args:
        graph: NetworkX graph, path to GraphML, or list of triples
        output_path: Output HTML file path
        title: Optional title for the visualization
        dark_mode: Whether to use dark mode theme
        layout: Layout algorithm ('community', 'spring', 'circular', 'kamada_kawai', 'shell')
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
                G.add_edge(t.head, t.tail, relation=t.relation, inference=t.inference.value)
            else:
                G.add_edge(t.get("head"), t.get("tail"), **{k: v for k, v in t.items() if k not in ["head", "tail"]})
        if title is None:
            title = "Extracted Knowledge Graph"
    else:
        G = graph
        if title is None:
            title = "Knowledge Graph"
    
    # 2. Calculate Layout
    n = G.number_of_nodes()
    if layout == "circular":
        pos = nx.circular_layout(G)
    elif layout == "kamada_kawai":
        if n <= 150:
            pos = nx.kamada_kawai_layout(G)
        else:
            k = 3.0 / math.sqrt(n) if n > 1 else 1.0
            pos = nx.spring_layout(G, k=k, iterations=200, seed=42)
    elif layout == "shell":
        pos = nx.shell_layout(G)
    elif layout == "spring":
        k = 3.0 / math.sqrt(n) if n > 1 else 1.0
        pos = nx.spring_layout(G, k=k, iterations=200, seed=42)
    else:
        pos = _community_layout(G)

    # 2b. Resolve node overlaps
    pos = _resolve_overlaps(pos, G)

    # 3. Theme Configuration
    theme = {
        "bg": "#0f172a" if dark_mode else "white",
        "text": "#f1f5f9" if dark_mode else "#1e293b",
        "grid": "#334155" if dark_mode else "#e2e8f0",
        "edge": "#475569" if dark_mode else "#94a3b8",
        "node_line": "#1e293b" if dark_mode else "white",
        "color_extracted": "#2563eb",   # Blue — ground truth from extract()
        "color_augmented": "#f59e0b",   # Amber — inferred via augmentation
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
        
        # Color edges by inference type
        is_augmented = edge_attrs.get("inference") == "contextual"
        if is_augmented:
            line_style = dict(width=1, color=theme["color_augmented"], dash="dash")
        else:
            line_style = dict(width=1.5, color=theme["color_extracted"])

        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode='lines',
            line=line_style,
            opacity=0.45,
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
    
    # Classify each node: explicit takes priority over contextual
    nodes_in_explicit: set[str] = set()
    nodes_in_contextual: set[str] = set()
    for u, v, edge_attrs in G.edges(data=True):
        if edge_attrs.get("inference") == "contextual":
            nodes_in_contextual.add(u)
            nodes_in_contextual.add(v)
        else:
            nodes_in_explicit.add(u)
            nodes_in_explicit.add(v)

    origin_colors = {
        "Extracted": theme["color_extracted"],
        "Augmented": theme["color_augmented"],
    }

    # Group nodes: Extracted if in any explicit edge, Augmented only if exclusively contextual
    origin_groups: dict[str, list] = {"Extracted": [], "Augmented": []}
    for node, attrs in G.nodes(data=True):
        if node in nodes_in_explicit:
            category = "Extracted"
        elif node in nodes_in_contextual:
            category = "Augmented"
        else:
            category = "Extracted"  # Isolated nodes default to Extracted
        origin_groups[category].append((node, attrs))

    max_label_len = 25
    node_traces = []
    for category, nodes in origin_groups.items():
        if not nodes:
            continue
        nx_list, ny_list, texts, hovers, sizes, font_sizes = [], [], [], [], [], []
        for node, attrs in nodes:
            x, y = pos[node]
            nx_list.append(x)
            ny_list.append(y)

            degree = G.degree(node)
            if degree >= 3:
                label = node if len(node) <= max_label_len else node[:max_label_len] + "..."
                texts.append(f"<b>{label}</b>")
            else:
                texts.append("")
            font_sizes.append(9 + min(degree, 10))

            hover = f"<b>{node}</b><br><br>"
            if attrs:
                for k, v in attrs.items():
                    hover += f"<b>{k}:</b> {v}<br>"
            hover += f"<b>Origin:</b> {category}<br>"
            hover += f"<b>Degree:</b> {degree}"
            hovers.append(hover)
            sizes.append(20 + degree * 2)

        node_traces.append(go.Scatter(
            x=nx_list, y=ny_list,
            mode='markers+text',
            name=category,
            text=texts,
            textposition="top center",
            textfont=dict(size=font_sizes, color=theme["text"]),
            hovertemplate='%{hovertext}<extra></extra>',
            hovertext=hovers,
            marker=dict(
                color=origin_colors[category],
                size=sizes,
                line=dict(width=1.5, color=theme["node_line"])
            ),
            showlegend=True,
            legendgroup=category,
        ))
    
    # 5. Figure Assembly
    fig = go.Figure(data=edge_traces + node_traces)

    fig.update_layout(
        title=dict(
            text=f'<b>{title}</b>',
            x=0.5, xanchor='center',
            font=dict(size=20, color=theme["text"])
        ),
        showlegend=True,
        legend=dict(
            title=dict(text="Origin", font=dict(color=theme["text"])),
            font=dict(color=theme["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
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
        width=1400,
        height=900
    )
    
    # 6. Save
    if output_path:
        fig.write_html(str(output_path), auto_open=auto_open)
    
    return fig


def batch_render_graphs(
    input_dir: Path | str,
    output_dir: Path | str | None = None,
    dark_mode: bool = False,
    layout: str = "spring"
) -> list[Path]:
    """Render all GraphML files in a directory.
    
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
            render_graph(graphml_file, output_path, dark_mode=dark_mode, layout=layout)
            html_files.append(output_path)
            print(f"✓ Created: {output_path.name}")
        except Exception as e:
            print(f"✗ Error with {graphml_file.name}: {e}")
    
    return html_files



__all__ = [
    "render_graph",
    "batch_render_graphs",
]
