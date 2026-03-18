"""Interactive graph visualization using Cytoscape.js.

Creates interactive HTML visualizations of knowledge graphs with
directed edges, edge labels, node dragging, search/filter, and
origin-based coloring (extracted vs augmented).
"""

from __future__ import annotations

import json
import math
import webbrowser
from pathlib import Path
from typing import Any

import networkx as nx
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


# ---------------------------------------------------------------------------
# Cytoscape.js helpers
# ---------------------------------------------------------------------------

def _build_cytoscape_elements(
    G: nx.DiGraph | nx.Graph, pos: dict | None = None
) -> list[dict]:
    """Convert a NetworkX graph into Cytoscape.js elements JSON."""

    # Classify nodes
    nodes_in_explicit: set[str] = set()
    nodes_in_contextual: set[str] = set()
    for u, v, attrs in G.edges(data=True):
        if "contextual" in str(attrs.get("inference", "")).lower():
            nodes_in_contextual.add(str(u))
            nodes_in_contextual.add(str(v))
        else:
            nodes_in_explicit.add(str(u))
            nodes_in_explicit.add(str(v))

    # Detect communities for layout grouping
    UG = G.to_undirected() if G.is_directed() else G
    try:
        communities = list(greedy_modularity_communities(UG))
    except Exception:
        communities = [set(G.nodes())]
    node_community: dict[str, int] = {}
    for i, comm in enumerate(communities):
        for nd in comm:
            node_community[str(nd)] = i

    elements: list[dict] = []

    # Nodes
    for node, attrs in G.nodes(data=True):
        node_id = str(node)
        degree = G.degree(node)
        if node_id in nodes_in_explicit:
            origin = "extracted"
        elif node_id in nodes_in_contextual:
            origin = "augmented"
        else:
            origin = "extracted"

        max_label_len = 25
        label = node_id if len(node_id) <= max_label_len else node_id[:max_label_len] + "..."

        node_data: dict[str, Any] = {
            "id": node_id,
            "label": label,
            "fullLabel": node_id,
            "degree": degree,
            "origin": origin,
            "community": node_community.get(node_id, 0),
            "showLabel": degree >= 3,
        }
        # Include all GraphML attributes
        for k, v in attrs.items():
            if k not in node_data:
                node_data[k] = str(v)

        entry: dict[str, Any] = {
            "group": "nodes",
            "data": node_data,
            "classes": origin,
        }
        if pos and node in pos:
            x, y = pos[node]
            entry["position"] = {"x": x, "y": y}
        elements.append(entry)

    # Edges
    for idx, (u, v, attrs) in enumerate(G.edges(data=True)):
        inference = attrs.get("inference", "explicit")
        relation = attrs.get("relation", "")
        edge_class = "augmented" if "contextual" in str(inference).lower() else "explicit"

        edge_data: dict[str, Any] = {
            "id": f"e{idx}",
            "source": str(u),
            "target": str(v),
            "label": str(relation),
            "inference": str(inference),
        }
        for k, v_val in attrs.items():
            if k not in edge_data:
                edge_data[k] = str(v_val)

        elements.append({
            "group": "edges",
            "data": edge_data,
            "classes": edge_class,
        })

    return elements


def _build_stylesheet(dark_mode: bool, max_degree: int, edge_count: int) -> list[dict]:
    """Generate Cytoscape.js stylesheet."""
    text_color = "#f1f5f9" if dark_mode else "#1e293b"
    node_border = "#94a3b8" if dark_mode else "#475569"
    blue = "#93c5fd" if dark_mode else "#1d4ed8"
    amber = "#fde68a" if dark_mode else "#b45309"
    edge_opacity = 0.9 if dark_mode else 0.75
    edge_width = 3 if dark_mode else 2

    styles: list[dict] = [
        # Base node
        {
            "selector": "node",
            "style": {
                "width": f"mapData(degree, 0, {max(max_degree, 1)}, 25, 60)",
                "height": f"mapData(degree, 0, {max(max_degree, 1)}, 25, 60)",
                "label": "data(label)",
                "font-size": "10px",
                "color": text_color,
                "text-valign": "top",
                "text-halign": "center",
                "text-margin-y": "-6px",
                "text-wrap": "ellipsis",
                "text-max-width": "120px",
                "border-width": 2.5 if dark_mode else 2,
                "border-color": node_border,
                "text-outline-width": 2,
                "text-outline-color": "#0f172a" if dark_mode else "#e2e8f0",
                "min-zoomed-font-size": 8,
            },
        },
        # Hide labels for low-degree nodes
        {
            "selector": "node[!showLabel]",
            "style": {
                "label": "",
            },
        },
        # Extracted nodes (blue)
        {
            "selector": "node.extracted",
            "style": {
                "background-color": blue,
            },
        },
        # Augmented nodes (amber)
        {
            "selector": "node.augmented",
            "style": {
                "background-color": amber,
            },
        },
        # Base edge
        {
            "selector": "edge",
            "style": {
                "width": edge_width,
                "curve-style": "bezier",
                "control-point-step-size": 50,
                "target-arrow-shape": "triangle",
                "target-arrow-color": blue,
                "arrow-scale": 1.0,
                "opacity": edge_opacity,
                "font-size": "9px",
                "color": text_color,
                "text-rotation": "autorotate",
                "text-background-color": "#0f172a" if dark_mode else "#e2e8f0",
                "text-background-opacity": 0.7,
                "text-background-padding": "2px",
                "min-zoomed-font-size": 8,
            },
        },
        # Explicit edges (solid blue)
        {
            "selector": "edge.explicit",
            "style": {
                "line-color": blue,
                "target-arrow-color": blue,
                "line-style": "solid",
            },
        },
        # Augmented edges (dashed amber)
        {
            "selector": "edge.augmented",
            "style": {
                "line-color": amber,
                "target-arrow-color": amber,
                "line-style": "dashed",
                "line-dash-pattern": [6, 3],
            },
        },
        # Faded class for search dimming
        {
            "selector": ".faded",
            "style": {
                "opacity": 0.15,
            },
        },
        # Highlighted class for search matches
        {
            "selector": ".highlighted",
            "style": {
                "border-width": 4,
                "border-color": "#22c55e",
                "opacity": 1,
                "z-index": 999,
            },
        },
        # Hover highlight class
        {
            "selector": ".hover-highlight",
            "style": {
                "opacity": 1,
                "border-width": 2.5,
                "z-index": 900,
            },
        },
        # Hover dim class
        {
            "selector": ".hover-dim",
            "style": {
                "opacity": 0.12,
            },
        },
    ]

    # Path finder classes
    styles.append({
        "selector": ".path-source",
        "style": {
            "border-width": 4,
            "border-color": "#22c55e",
            "background-blacken": -0.3,
            "z-index": 999,
        },
    })
    styles.append({
        "selector": ".path-target",
        "style": {
            "border-width": 4,
            "border-color": "#ef4444",
            "background-blacken": -0.3,
            "z-index": 999,
        },
    })
    styles.append({
        "selector": "node.path-member",
        "style": {
            "opacity": 1,
            "z-index": 999,
            "border-color": "#a855f7",
            "border-width": 3,
        },
    })
    styles.append({
        "selector": "edge.path-member",
        "style": {
            "opacity": 1,
            "z-index": 999,
            "width": 3,
            "line-color": "#a855f7",
            "target-arrow-color": "#a855f7",
        },
    })
    # Pinned node class
    styles.append({
        "selector": ".pinned",
        "style": {
            "border-style": "dashed",
            "border-color": "#f472b6",
            "border-width": 2.5,
        },
    })

    # Edge labels: show inline for small graphs, hover-only for large ones
    if edge_count <= 50:
        styles.append({
            "selector": "edge",
            "style": {
                "label": "data(label)",
            },
        })
    else:
        styles.append({
            "selector": "edge:active",
            "style": {
                "label": "data(label)",
            },
        })

    return styles


def _build_layout_config(layout_name: str, node_count: int) -> dict:
    """Map layout name to Cytoscape.js layout config."""
    config = {
        "name": "cose",
        "animate": True,
        "animationDuration": 500,
        "nodeRepulsion": 400000,
        "idealEdgeLength": 100,
        "edgeElasticity": 100,
        "gravity": 1,
        "numIter": 1000,
        "randomize": True,
        "nodeOverlap": 20,
        "componentSpacing": 100,
    }
    return config


def _build_html_template(
    elements_json: str,
    stylesheet_json: str,
    layout_json: str,
    title: str,
    node_count: int,
    edge_count: int,
    layout_name: str,
    dark_mode: bool,
) -> str:
    """Generate standalone HTML with embedded Cytoscape.js."""
    bg = "#0f172a" if dark_mode else "#e2e8f0"
    card_bg = "rgba(30, 41, 59, 0.7)" if dark_mode else "rgba(241, 245, 249, 0.85)"
    text_color = "#f1f5f9" if dark_mode else "#1e293b"
    muted = "#94a3b8" if dark_mode else "#475569"
    border_color = "rgba(255, 255, 255, 0.1)" if dark_mode else "rgba(0, 0, 0, 0.12)"
    input_bg = "rgba(255,255,255,0.05)" if dark_mode else "rgba(0,0,0,0.06)"
    initial_theme = "dark" if dark_mode else "light"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.30.4/cytoscape.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cytoscape-cxtmenu@3.5.0/cytoscape-cxtmenu.min.js"></script>
<style>
  :root {{
    --bg: {bg};
    --card-bg: {card_bg};
    --text: {text_color};
    --muted: {muted};
    --border: {border_color};
    --input-bg: {input_bg};
    --accent: #3b82f6;
    --blue: #2563eb;
    --amber: #f59e0b;
    --green: #22c55e;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    overflow: hidden;
    height: 100vh;
  }}

  #cy {{
    width: 100%;
    height: 100vh;
    position: absolute;
    top: 0;
    left: 0;
  }}

  .panel {{
    position: absolute;
    background: var(--card-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    z-index: 10;
    font-size: 13px;
  }}

  .control-panel {{
    top: 16px;
    left: 16px;
    min-width: 240px;
    max-width: 280px;
  }}

  .control-panel h2 {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 4px;
    letter-spacing: -0.02em;
  }}

  .stats {{
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 12px;
  }}

  .control-group {{
    margin-bottom: 10px;
  }}

  .control-group label {{
    display: block;
    font-size: 11px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }}

  .control-group input,
  .control-group select {{
    width: 100%;
    padding: 6px 10px;
    background: var(--input-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
  }}

  .control-group input:focus,
  .control-group select:focus {{
    border-color: var(--accent);
  }}

  .btn-row {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 10px;
  }}

  .btn {{
    width: 100%;
    padding: 8px 12px;
    background: var(--input-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s, border-color 0.2s, transform 0.1s;
    white-space: nowrap;
    text-align: center;
  }}

  .btn:hover {{
    border-color: var(--accent);
    background: rgba(59, 130, 246, 0.12);
  }}

  .btn:active {{
    transform: scale(0.97);
  }}

  .legend {{
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--border);
  }}

  .legend-title {{
    font-size: 11px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }}

  .legend-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    margin-bottom: 4px;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 4px;
    transition: opacity 0.2s;
    user-select: none;
  }}

  .legend-item:hover {{
    background: var(--input-bg);
  }}

  .legend-item.off {{
    opacity: 0.35;
    text-decoration: line-through;
  }}

  .legend-dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }}

  .legend-line {{
    width: 20px;
    height: 0;
    border-top: 2px solid;
    flex-shrink: 0;
  }}

  .legend-line.dashed {{
    border-top-style: dashed;
  }}

  .info-panel {{
    bottom: 16px;
    right: 16px;
    min-width: 260px;
    max-width: 320px;
    max-height: 300px;
    overflow-y: auto;
    display: none;
  }}

  .info-panel h3 {{
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 8px;
  }}

  .info-panel .attr {{
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
  }}

  .info-panel .attr-key {{
    font-weight: 600;
    color: var(--muted);
    margin-right: 12px;
  }}

  .info-panel .attr-val {{
    text-align: right;
    word-break: break-word;
    max-width: 180px;
  }}

  .tooltip {{
    position: fixed;
    background: var(--card-bg);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
    color: var(--text);
    pointer-events: none;
    z-index: 20;
    display: none;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    max-width: 280px;
    white-space: nowrap;
  }}

  .shortcuts-hint {{
    font-size: 10px;
    color: var(--muted);
    margin-top: 8px;
    line-height: 1.5;
    letter-spacing: 0.01em;
  }}

  .path-status {{
    font-size: 11px;
    color: var(--muted);
    margin-top: 6px;
    min-height: 16px;
  }}

  .btn.active {{
    border-color: var(--accent);
    background: rgba(59, 130, 246, 0.2);
  }}

  /* Theme overrides */
  body.light {{
    --bg: #e2e8f0;
    --card-bg: rgba(241, 245, 249, 0.85);
    --text: #1e293b;
    --muted: #475569;
    --border: rgba(0, 0, 0, 0.12);
    --input-bg: rgba(0, 0, 0, 0.06);
  }}

  body.dark {{
    --bg: #0f172a;
    --card-bg: rgba(30, 41, 59, 0.7);
    --text: #f1f5f9;
    --muted: #94a3b8;
    --border: rgba(255, 255, 255, 0.1);
    --input-bg: rgba(255, 255, 255, 0.05);
  }}
</style>
</head>
<body class="{initial_theme}">

<div id="cy"></div>
<div class="tooltip" id="tooltip"></div>

<div class="panel control-panel">
  <h2>{title}</h2>
  <div class="stats">{node_count} nodes &middot; {edge_count} edges &middot; {layout_name}</div>

  <div class="control-group">
    <label>Search nodes</label>
    <input type="text" id="search" placeholder="Type to filter..." autocomplete="off">
  </div>

  <div class="control-group">
    <label>Layout</label>
    <select id="layoutSelect">
      <option value="cose" {"selected" if layout_name in ("community", "spring") else ""}>Force-directed</option>
      <option value="circle">Circular</option>
      <option value="dagre">Hierarchical (Dagre)</option>
    </select>
  </div>

  <div class="control-group">
    <label>Export</label>
    <select id="exportSelect">
      <option value="" disabled selected>Choose format...</option>
      <option value="png">PNG (image)</option>
      <option value="svg">SVG (vector)</option>
      <option value="json">JSON (data)</option>
    </select>
  </div>

  <div class="btn-row">
    <button class="btn" id="fitBtn">Fit to screen</button>
    <button class="btn" id="themeBtn">{"Light mode" if dark_mode else "Dark mode"}</button>
    <button class="btn" id="pathBtn">Find path</button>
  </div>
  <div class="path-status" id="pathStatus"></div>

  <div class="legend">
    <div class="legend-title">Legend (click to toggle)</div>
    <div class="legend-item" data-filter="node.extracted">
      <span class="legend-dot" style="background: var(--blue);"></span>
      Extracted
    </div>
    <div class="legend-item" data-filter="node.augmented">
      <span class="legend-dot" style="background: var(--amber);"></span>
      Augmented
    </div>
    <div class="legend-item" data-filter="edge.explicit">
      <span class="legend-line" style="border-color: var(--blue);"></span>
      Explicit edge
    </div>
    <div class="legend-item" data-filter="edge.augmented">
      <span class="legend-line dashed" style="border-color: var(--amber);"></span>
      Augmented edge
    </div>
  </div>
  <div class="shortcuts-hint">
    Esc reset &middot; Dblclick focus &middot; / search &middot; F fit &middot; P path &middot; 1-3 layout &middot; Right-click menu
  </div>
</div>

<div class="panel info-panel" id="infoPanel">
  <h3 id="infoTitle"></h3>
  <div id="infoContent"></div>
</div>

<script>
(function() {{
  var elements = {elements_json};
  var style = {stylesheet_json};
  var layoutConfig = {layout_json};

  var cy = cytoscape({{
    container: document.getElementById('cy'),
    elements: elements,
    style: style,
    layout: layoutConfig,
    wheelSensitivity: 0.3,
    minZoom: 0.1,
    maxZoom: 5,
  }});

  // --- Search ---
  var searchInput = document.getElementById('search');
  searchInput.addEventListener('input', function() {{
    var query = this.value.trim().toLowerCase();
    if (!query) {{
      cy.elements().removeClass('faded highlighted');
      return;
    }}
    cy.batch(function() {{
      cy.elements().addClass('faded').removeClass('highlighted');
      var matched = cy.nodes().filter(function(n) {{
        return n.data('fullLabel').toLowerCase().indexOf(query) !== -1;
      }});
      matched.removeClass('faded').addClass('highlighted');
      matched.connectedEdges().removeClass('faded');
      matched.connectedEdges().connectedNodes().removeClass('faded');
    }});
  }});

  // --- Layout switching ---
  var layoutSelect = document.getElementById('layoutSelect');
  layoutSelect.addEventListener('change', function() {{
    var name = this.value;
    var opts = {{ name: name, animate: true, animationDuration: 500 }};
    if (name === 'cose') {{
      opts.nodeRepulsion = 400000;
      opts.idealEdgeLength = 100;
      opts.edgeElasticity = 100;
      opts.gravity = 1;
      opts.numIter = 1000;
      opts.randomize = true;
      opts.nodeOverlap = 20;
      opts.componentSpacing = 100;
    }} else if (name === 'circle') {{
      // Custom: one circle per community, arranged around a meta-circle
      var groups = {{}};
      cy.nodes().forEach(function(n) {{
        var c = n.data('community');
        if (!groups[c]) groups[c] = [];
        groups[c].push(n);
      }});
      var keys = Object.keys(groups).sort(function(a,b) {{ return a - b; }});
      var nc = keys.length;
      var cx = cy.width() / 2, cyy = cy.height() / 2;
      // Spread community centres on a large circle (or single centre if 1 community)
      var metaR = nc > 1 ? Math.min(cx, cyy) * 0.55 : 0;
      var positions = {{}};
      keys.forEach(function(k, ci) {{
        var members = groups[k];
        var angle0 = (2 * Math.PI * ci) / nc - Math.PI / 2;
        var gcx = cx + metaR * Math.cos(angle0);
        var gcy = cyy + metaR * Math.sin(angle0);
        var localR = Math.max(30, 22 * members.length);
        members.forEach(function(n, ni) {{
          var a = (2 * Math.PI * ni) / members.length - Math.PI / 2;
          positions[n.id()] = {{
            x: gcx + localR * Math.cos(a),
            y: gcy + localR * Math.sin(a)
          }};
        }});
      }});
      cy.batch(function() {{
        cy.nodes().forEach(function(n) {{
          var p = positions[n.id()];
          if (p) n.position(p);
        }});
      }});
      cy.animate({{ fit: {{ padding: 40 }} }}, {{ duration: 400 }});
      return;
    }} else if (name === 'dagre') {{
      opts.rankDir = 'TB';
      opts.nodeSep = 50;
      opts.rankSep = 80;
    }}
    cy.layout(opts).run();
  }});

  // --- Fit ---
  document.getElementById('fitBtn').addEventListener('click', function() {{
    cy.animate({{ fit: {{ padding: 40 }} }}, {{ duration: 400 }});
  }});

  // --- Export ---
  var exportSelect = document.getElementById('exportSelect');
  exportSelect.addEventListener('change', function() {{
    var fmt = this.value;
    var bg = getComputedStyle(document.body).getPropertyValue('--bg').trim();
    var a = document.createElement('a');
    if (fmt === 'png') {{
      a.href = cy.png({{ scale: 3, bg: bg, full: true }});
      a.download = '{title.replace("'", "")}.png';
    }} else if (fmt === 'svg') {{
      var svgContent = cy.svg({{ scale: 2, bg: bg, full: true }});
      var blob = new Blob([svgContent], {{ type: 'image/svg+xml' }});
      a.href = URL.createObjectURL(blob);
      a.download = '{title.replace("'", "")}.svg';
    }} else if (fmt === 'json') {{
      var data = cy.json().elements;
      var blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
      a.href = URL.createObjectURL(blob);
      a.download = '{title.replace("'", "")}.json';
    }}
    a.click();
    // Reset dropdown to placeholder
    this.selectedIndex = 0;
  }});

  // --- Theme toggle ---
  var themeColors = {{
    dark: {{
      text: '#f1f5f9', outline: '#0f172a', border: '#94a3b8',
      blue: '#93c5fd', amber: '#fde68a',
      edgeOpacity: 0.9, edgeWidth: 3, borderWidth: 2.5, bgColor: '#0f172a'
    }},
    light: {{
      text: '#1e293b', outline: '#e2e8f0', border: '#475569',
      blue: '#1d4ed8', amber: '#b45309',
      edgeOpacity: 0.75, edgeWidth: 2, borderWidth: 2, bgColor: '#e2e8f0'
    }}
  }};

  var themeBtn = document.getElementById('themeBtn');
  themeBtn.addEventListener('click', function() {{
    var body = document.body;
    var isDark = body.classList.contains('dark');
    body.classList.remove('dark', 'light');
    var newTheme = isDark ? 'light' : 'dark';
    body.classList.add(newTheme);
    var t = themeColors[newTheme];
    cy.style()
      .selector('node')
      .style({{
        'color': t.text,
        'text-outline-color': t.outline,
        'border-color': t.border,
        'border-width': t.borderWidth,
      }})
      .selector('node.extracted')
      .style({{ 'background-color': t.blue }})
      .selector('node.augmented')
      .style({{ 'background-color': t.amber }})
      .selector('edge')
      .style({{
        'color': t.text,
        'text-background-color': t.outline,
        'opacity': t.edgeOpacity,
        'width': t.edgeWidth,
      }})
      .selector('edge.explicit')
      .style({{ 'line-color': t.blue, 'target-arrow-color': t.blue }})
      .selector('edge.augmented')
      .style({{ 'line-color': t.amber, 'target-arrow-color': t.amber }})
      .update();
    themeBtn.textContent = isDark ? 'Dark mode' : 'Light mode';
    cy.style().update();
  }});

  // --- Path finder state ---
  var pathMode = false;
  var pathSource = null;
  var pathTarget = null;
  var pathBtn = document.getElementById('pathBtn');
  var pathStatus = document.getElementById('pathStatus');

  function clearPathMode() {{
    pathMode = false;
    pathSource = null;
    pathTarget = null;
    pathBtn.classList.remove('active');
    pathStatus.textContent = '';
    cy.elements().removeClass('path-source path-target path-member');
  }}

  function enterPathMode(preselectedSource) {{
    // Clear previous path visuals
    cy.elements().removeClass('faded highlighted path-source path-target path-member');
    pathMode = true;
    pathSource = preselectedSource || null;
    pathTarget = null;
    pathBtn.classList.add('active');
    if (pathSource) {{
      pathSource.addClass('path-source');
      pathStatus.textContent = 'Click target node...';
    }} else {{
      pathStatus.textContent = 'Click source node...';
    }}
  }}

  pathBtn.addEventListener('click', function() {{
    if (pathMode) {{
      clearPathMode();
      cy.elements().removeClass('faded');
    }} else {{
      enterPathMode(null);
    }}
  }});

  // --- Info panel ---
  var infoPanel = document.getElementById('infoPanel');
  var infoTitle = document.getElementById('infoTitle');
  var infoContent = document.getElementById('infoContent');

  cy.on('tap', 'node', function(evt) {{
    // Path mode: select source/target
    if (pathMode) {{
      var node = evt.target;
      if (!pathSource) {{
        pathSource = node;
        node.addClass('path-source');
        pathStatus.textContent = 'Click target node...';
      }} else if (!pathTarget && node !== pathSource) {{
        pathTarget = node;
        node.addClass('path-target');
        // Compute shortest path
        var result = cy.elements().aStar({{ root: pathSource, goal: pathTarget, directed: true }});
        if (result.found) {{
          var pathEles = result.path;
          cy.batch(function() {{
            cy.elements().addClass('faded');
            pathEles.removeClass('faded').addClass('path-member');
            pathSource.addClass('path-source');
            pathTarget.addClass('path-target');
          }});
          pathStatus.textContent = 'Path: ' + Math.floor(pathEles.edges().length) + ' hops (' + pathEles.length + ' elements)';
        }} else {{
          pathStatus.textContent = 'No path found';
        }}
      }}
      return;
    }}

    // Normal mode: show info panel
    var d = evt.target.data();
    infoTitle.textContent = d.fullLabel || d.id;
    var html = '';
    html += '<div class="attr"><span class="attr-key">Origin</span><span class="attr-val">' + d.origin + '</span></div>';
    html += '<div class="attr"><span class="attr-key">Degree</span><span class="attr-val">' + d.degree + '</span></div>';
    var skip = {{'id':1,'label':1,'fullLabel':1,'degree':1,'origin':1,'showLabel':1}};
    for (var k in d) {{
      if (!skip[k]) {{
        html += '<div class="attr"><span class="attr-key">' + k + '</span><span class="attr-val">' + d[k] + '</span></div>';
      }}
    }}
    infoContent.innerHTML = html;
    infoPanel.style.display = 'block';
  }});

  cy.on('tap', 'edge', function(evt) {{
    var d = evt.target.data();
    infoTitle.textContent = d.source + ' \\u2192 ' + d.target;
    var html = '';
    html += '<div class="attr"><span class="attr-key">Relation</span><span class="attr-val">' + d.label + '</span></div>';
    html += '<div class="attr"><span class="attr-key">Inference</span><span class="attr-val">' + d.inference + '</span></div>';
    var skip = {{'id':1,'source':1,'target':1,'label':1,'inference':1}};
    for (var k in d) {{
      if (!skip[k]) {{
        html += '<div class="attr"><span class="attr-key">' + k + '</span><span class="attr-val">' + d[k] + '</span></div>';
      }}
    }}
    infoContent.innerHTML = html;
    infoPanel.style.display = 'block';
  }});

  cy.on('tap', function(evt) {{
    if (evt.target === cy) {{
      infoPanel.style.display = 'none';
    }}
  }});

  // --- Hover tooltips + highlight ---
  var tooltip = document.getElementById('tooltip');

  cy.on('mouseover', 'node', function(evt) {{
    var node = evt.target;
    var d = node.data();
    tooltip.innerHTML = '<strong>' + (d.fullLabel || d.id) + '</strong><br>Degree: ' + d.degree;
    tooltip.style.display = 'block';
    // Dim others, highlight neighborhood
    cy.batch(function() {{
      cy.elements().addClass('hover-dim');
      node.removeClass('hover-dim').addClass('hover-highlight');
      node.connectedEdges().removeClass('hover-dim').addClass('hover-highlight');
      node.connectedEdges().connectedNodes().removeClass('hover-dim');
    }});
  }});

  cy.on('mouseout', 'node', function() {{
    tooltip.style.display = 'none';
    cy.batch(function() {{
      cy.elements().removeClass('hover-dim hover-highlight');
    }});
  }});

  cy.on('mouseover', 'edge', function(evt) {{
    var edge = evt.target;
    var d = edge.data();
    tooltip.innerHTML = d.source + ' &rarr; ' + d.target + '<br><em>' + d.label + '</em>';
    tooltip.style.display = 'block';
    cy.batch(function() {{
      cy.elements().addClass('hover-dim');
      edge.removeClass('hover-dim').addClass('hover-highlight');
      edge.source().removeClass('hover-dim').addClass('hover-highlight');
      edge.target().removeClass('hover-dim').addClass('hover-highlight');
    }});
  }});

  cy.on('mouseout', 'edge', function() {{
    tooltip.style.display = 'none';
    cy.batch(function() {{
      cy.elements().removeClass('hover-dim hover-highlight');
    }});
  }});

  document.addEventListener('mousemove', function(e) {{
    if (tooltip.style.display === 'block') {{
      tooltip.style.left = (e.clientX + 14) + 'px';
      tooltip.style.top = (e.clientY + 14) + 'px';
    }}
  }});

  // --- Neighbor focus mode (double-click) ---
  var focusActive = false;

  cy.on('dbltap', 'node', function(evt) {{
    var node = evt.target;
    var neighborhood = node.closedNeighborhood();
    cy.batch(function() {{
      cy.elements().addClass('faded').removeClass('highlighted');
      neighborhood.removeClass('faded');
      node.addClass('highlighted');
    }});
    focusActive = true;
  }});

  cy.on('dbltap', function(evt) {{
    if (evt.target === cy) {{
      cy.batch(function() {{
        cy.elements().removeClass('faded highlighted');
      }});
      focusActive = false;
    }}
  }});

  // --- Legend toggle filters (Plotly-style click to show/hide) ---
  var legendItems = document.querySelectorAll('.legend-item[data-filter]');
  legendItems.forEach(function(item) {{
    item.addEventListener('click', function() {{
      var selector = this.getAttribute('data-filter');
      var isOff = this.classList.toggle('off');
      var eles = cy.elements(selector);
      eles.style('display', isOff ? 'none' : 'element');
    }});
  }});

  // --- Keyboard shortcuts ---
  document.addEventListener('keydown', function(e) {{
    var isInput = (document.activeElement === searchInput);

    // Escape always works
    if (e.key === 'Escape') {{
      // Clear search
      searchInput.value = '';
      searchInput.blur();
      // Clear focus mode
      focusActive = false;
      // Clear path mode
      clearPathMode();
      // Reset legend filters
      legendItems.forEach(function(item) {{ item.classList.remove('off'); }});
      // Show all hidden elements
      cy.elements().style('display', 'element');
      // Unpin all nodes
      cy.nodes().unlock().removeClass('pinned');
      // Clear all visual states
      cy.batch(function() {{
        cy.elements().removeClass('faded highlighted hover-dim hover-highlight path-source path-target path-member');
      }});
      infoPanel.style.display = 'none';
      return;
    }}

    // Other shortcuts only when not typing in search
    if (isInput) return;

    if (e.key === 'f' || e.key === 'F') {{
      e.preventDefault();
      cy.animate({{ fit: {{ padding: 40 }} }}, {{ duration: 400 }});
    }} else if (e.key === 'p' || e.key === 'P') {{
      e.preventDefault();
      if (pathMode) {{
        clearPathMode();
        cy.elements().removeClass('faded');
      }} else {{
        enterPathMode(null);
      }}
    }} else if (e.key === '/') {{
      e.preventDefault();
      searchInput.focus();
    }} else if (e.key >= '1' && e.key <= '3') {{
      var idx = parseInt(e.key) - 1;
      var options = layoutSelect.options;
      if (idx < options.length) {{
        layoutSelect.selectedIndex = idx;
        layoutSelect.dispatchEvent(new Event('change'));
      }}
    }}
  }});

  // --- Focus helper (reused by dbltap and context menu) ---
  function focusNode(node) {{
    var neighborhood = node.closedNeighborhood();
    cy.batch(function() {{
      cy.elements().addClass('faded').removeClass('highlighted');
      neighborhood.removeClass('faded');
      node.addClass('highlighted');
    }});
    focusActive = true;
  }}

  // --- Right-click context menus (cytoscape-cxtmenu) ---
  var menuDefaults = {{
    menuRadius: function(ele) {{ return 75; }},
    separatorWidth: 2,
    spotlightPadding: 4,
    adaptativeNodeSpotlightRadius: true,
    minSpotlightRadius: 16,
    maxSpotlightRadius: 30,
    openMenuEvents: 'cxttapstart taphold',
    itemColor: 'white',
    itemTextShadowColor: 'transparent',
    zIndex: 9999,
    atMouse: false,
    outsideMenuCancel: 10,
  }};

  // Node context menu
  cy.cxtmenu(Object.assign({{}}, menuDefaults, {{
    selector: 'node',
    fillColor: 'rgba(30, 41, 59, 0.88)',
    activeFillColor: 'rgba(59, 130, 246, 0.75)',
    commands: [
      {{
        content: 'Pin/Unpin',
        select: function(node) {{
          if (node.locked()) {{
            node.unlock();
            node.removeClass('pinned');
          }} else {{
            node.lock();
            node.addClass('pinned');
          }}
        }}
      }},
      {{
        content: 'Hide',
        select: function(node) {{
          node.style('display', 'none');
        }}
      }},
      {{
        content: 'Focus',
        select: function(node) {{
          focusNode(node);
        }}
      }},
      {{
        content: 'Path from',
        select: function(node) {{
          enterPathMode(node);
        }}
      }}
    ]
  }}));

  // Edge context menu
  cy.cxtmenu(Object.assign({{}}, menuDefaults, {{
    selector: 'edge',
    fillColor: 'rgba(30, 41, 59, 0.88)',
    activeFillColor: 'rgba(59, 130, 246, 0.75)',
    commands: [
      {{
        content: 'Hide',
        select: function(edge) {{
          edge.style('display', 'none');
        }}
      }},
      {{
        content: 'Focus',
        select: function(edge) {{
          cy.batch(function() {{
            cy.elements().addClass('faded').removeClass('highlighted');
            edge.removeClass('faded').addClass('highlighted');
            edge.source().removeClass('faded').addClass('highlighted');
            edge.target().removeClass('faded').addClass('highlighted');
          }});
          focusActive = true;
        }}
      }}
    ]
  }}));

  // Background context menu
  cy.cxtmenu(Object.assign({{}}, menuDefaults, {{
    selector: 'core',
    fillColor: 'rgba(30, 41, 59, 0.88)',
    activeFillColor: 'rgba(59, 130, 246, 0.75)',
    commands: [
      {{
        content: 'Show all',
        select: function() {{
          cy.elements().style('display', 'element');
          cy.elements().removeClass('faded highlighted');
          focusActive = false;
        }}
      }},
      {{
        content: 'Unpin all',
        select: function() {{
          cy.nodes().unlock().removeClass('pinned');
        }}
      }},
      {{
        content: 'Fit',
        select: function() {{
          cy.animate({{ fit: {{ padding: 40 }} }}, {{ duration: 400 }});
        }}
      }}
    ]
  }}));
}})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_graph(
    graph: nx.Graph | str | Path | list[Triple] | list[dict[str, Any]],
    output_path: Path | str | None = None,
    title: str | None = None,
    dark_mode: bool = False,
    layout: str = "community",
    auto_open: bool = False,
) -> Path | None:
    """Render a knowledge graph as an interactive Cytoscape.js HTML page.

    Args:
        graph: NetworkX graph, path to GraphML, or list of triples
        output_path: Output HTML file path
        title: Optional title for the visualization
        dark_mode: Whether to use dark mode theme
        layout: Layout algorithm ('community', 'spring', 'circular', 'kamada_kawai', 'shell')
        auto_open: Whether to open in browser after saving

    Returns:
        Path to the created HTML file, or None if no output_path was given.
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

    # 2. Layout positions are computed client-side by Cytoscape.js
    pos = None

    # 3. Build Cytoscape.js components
    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()
    max_degree = max((G.degree(n) for n in G.nodes()), default=0)

    elements = _build_cytoscape_elements(G, pos)
    stylesheet = _build_stylesheet(dark_mode, max_degree, edge_count)
    layout_config = _build_layout_config(layout, node_count)

    layout_json = json.dumps(layout_config)

    html = _build_html_template(
        elements_json=json.dumps(elements),
        stylesheet_json=json.dumps(stylesheet),
        layout_json=layout_json,
        title=title,
        node_count=node_count,
        edge_count=edge_count,
        layout_name=layout,
        dark_mode=dark_mode,
    )

    # 4. Save
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        if auto_open:
            webbrowser.open(str(output_path.resolve()))
        return output_path

    return None


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
            print(f"  Created: {output_path.name}")
        except Exception as e:
            print(f"  Error with {graphml_file.name}: {e}")

    return html_files


__all__ = [
    "render_graph",
    "batch_render_graphs",
]
