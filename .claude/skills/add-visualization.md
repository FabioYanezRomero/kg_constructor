# Adding a Visualization

This skill documents how to add a new visualization type to the `kgb/visualization/` module.

## Overview

Visualizations render knowledge graphs as interactive HTML. The system provides:
- **Network topology** (`graph_viz.py`) — Cytoscape.js + NetworkX graph with origin-based coloring, node dragging, search/filter, and context menus
- **Text highlighting** (`text_viz.py`) — langextract-based entity highlighting in source text
- Extensible architecture for custom visualizations

## Architecture

```
                     Visualization Module
    ┌────────────────────────────────────────────────────┐
    │                                                    │
    │  graph_viz.py             text_viz.py              │
    │  ├─ render_graph()        ├─ TextVisualizer        │
    │  ├─ batch_render_graphs() │   ├─ render_triples_   │
    │  │                        │   │   in_text()        │
    │  │  Cytoscape.js          │   ├─ save_html()       │
    │  │  Node/edge topology    │   └─ batch_render()    │
    │  │  Origin coloring       │                        │
    │  │  (Extracted/Augmented) │   langextract-based    │
    │  │  Node dragging         │   Entity highlighting  │
    │  │  Search/filter         │                        │
    │  │  Context menus         │                        │
    │  │                        │                        │
    │  │  your_viz.py                                    │
    │  │  └─ Your new visualization                      │
    │  │                                                 │
    │  └─────────────────────────────────────────────────┘

Data Flow:
  list[Triple] or GraphML → Graph Construction → Layout → Rendering → HTML
```

**Key Files:**
- `kgb/visualization/graph_viz.py` — Graph topology (Cytoscape.js + NetworkX)
- `kgb/visualization/text_viz.py` — Text entity highlighting (langextract)
- `kgb/visualization/__init__.py` — Public exports

## Dependencies

**Required:**
- `networkx>=3.0` — Graph data structures and layout computation
- Cytoscape.js v3.30.4 (CDN) — Interactive graph rendering in the browser
- cytoscape-dagre (CDN) — Hierarchical layout plugin
- cytoscape-cxtmenu (CDN) — Right-click context menu plugin

**Optional:**
- `langextract` — For text-based entity highlighting

## Existing Visualizations Reference

### graph_viz.py — `render_graph()`

Key features to understand:
- **Input flexibility**: Accepts `nx.Graph | str | Path | list[Triple] | list[dict]`
- **Origin coloring**: Nodes colored by extraction origin (Extracted=blue, Augmented=amber, Both=violet)
- **Edge styling**: Solid lines for extracted edges, dashed for augmented
- **Inference detection**: Uses `edge_attrs.get("inference") == "contextual"` to classify
- **Theme system**: Dark/light mode via theme dict
- **Layout algorithms**: cose (force-directed), circle, dagre (hierarchical) — switchable in-browser
- **Interactive features**: Node dragging, search/filter bar, right-click context menus, path finder, export (PNG/SVG/JSON)

### text_viz.py — `TextVisualizer`

Key features:
- **Class-based**: Instance holds configuration (animation_speed, show_legend, gif_optimized)
- **langextract integration**: Converts triples to `AnnotatedDocument` for visualization
- **Entity grouping**: By entity_type or relation
- **Augmented distinction**: Adds "(Augmented)" suffix to entity type for CSS styling

## Step 1: Understand the Interface

Follow the patterns from existing visualizations:

**Function-based** (like `render_graph`):
```python
def visualize_<type>(
    data: Path | list[Triple] | nx.Graph,
    output_path: Path | str,
    *,
    dark_mode: bool = False,
    **kwargs: Any
) -> Path | go.Figure:
```

**Class-based** (like `TextVisualizer`):
```python
class YourVisualizer:
    def __init__(self, config_option: type = default, ...) -> None: ...
    def render(self, data, **kwargs) -> str: ...
    def save_html(self, data, output_path, **kwargs) -> Path: ...
    def batch_render(self, records, output_dir, **kwargs) -> list[Path]: ...
```

## Step 2: Implement Your Visualization

Create `kgb/visualization/timeline_viz.py`:

```python
"""Timeline visualization for temporal knowledge graphs."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from datetime import datetime

import networkx as nx
import plotly.graph_objects as go

from ..domains import Triple


def visualize_timeline(
    data: Path | list[Triple] | list[dict[str, Any]],
    output_path: Path | str,
    *,
    dark_mode: bool = False,
    date_field: str = "date",
    height: int = 600,
    **kwargs: Any
) -> Path:
    """Generate interactive timeline visualization.

    Args:
        data: GraphML path or list of triples with date attributes
        output_path: Output HTML file path
        dark_mode: Use dark color theme
        date_field: Attribute name containing dates
        height: Canvas height in pixels

    Returns:
        Path to created HTML file

    Raises:
        ValueError: If data format is invalid or dates missing
        FileNotFoundError: If GraphML path doesn't exist
    """
    output_path = Path(output_path)

    # 1. Load Data
    if isinstance(data, Path):
        if not data.exists():
            raise FileNotFoundError(f"GraphML file not found: {data}")
        G = nx.read_graphml(str(data))
        events = _extract_events_from_graph(G, date_field)
    elif isinstance(data, list):
        events = _extract_events_from_triples(data, date_field)
    else:
        raise ValueError(f"Unsupported data type: {type(data)}")

    if not events:
        raise ValueError(f"No events with '{date_field}' attribute found")

    # 2. Theme Configuration (follow graph_viz.py pattern)
    theme = {
        "bg": "#0f172a" if dark_mode else "#ffffff",
        "text": "#f1f5f9" if dark_mode else "#1e293b",
        "grid": "#334155" if dark_mode else "#e2e8f0",
        "accent": "#3b82f6",
    }

    # 3. Build Timeline Figure
    fig = go.Figure()

    sorted_events = sorted(events, key=lambda e: e["date"])
    dates = [e["date"] for e in sorted_events]
    labels = [e["label"] for e in sorted_events]
    hovers = [e["hover"] for e in sorted_events]

    fig.add_trace(go.Scatter(
        x=dates,
        y=[1] * len(dates),
        mode="markers+text",
        marker=dict(size=12, color=theme["accent"]),
        text=labels,
        textposition="top center",
        hovertext=hovers,
        hoverinfo="text"
    ))

    # 4. Apply Theme
    fig.update_layout(
        title="Knowledge Graph Timeline",
        height=height,
        paper_bgcolor=theme["bg"],
        plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
        xaxis=dict(showgrid=True, gridcolor=theme["grid"], title="Date"),
        yaxis=dict(visible=False),
        showlegend=False
    )

    # 5. Save HTML
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path))

    return output_path


def _extract_events_from_triples(triples, date_field):
    """Extract timeline events from triples."""
    events = []
    for t in triples:
        if isinstance(t, Triple):
            t = t.model_dump()

        date_str = t.get(date_field)
        if not date_str:
            continue

        try:
            date = datetime.fromisoformat(str(date_str))
        except ValueError:
            continue

        events.append({
            "date": date,
            "label": f"{t.get('head', '')} -> {t.get('tail', '')}",
            "hover": f"<b>{t.get('relation', '')}</b><br>{t.get('head')} -> {t.get('tail')}"
        })

    return events


def _extract_events_from_graph(G, date_field):
    """Extract timeline events from a NetworkX graph."""
    events = []
    for u, v, attrs in G.edges(data=True):
        date_str = attrs.get(date_field)
        if not date_str:
            continue
        try:
            date = datetime.fromisoformat(str(date_str))
        except ValueError:
            continue
        events.append({
            "date": date,
            "label": f"{u} -> {v}",
            "hover": f"<b>{attrs.get('relation', '')}</b><br>{u} -> {v}"
        })
    return events
```

## Step 3: Register in Module

Update `kgb/visualization/__init__.py`:

```python
from .graph_viz import render_graph, batch_render_graphs
from .text_viz import TextVisualizer
from .timeline_viz import visualize_timeline  # Add this

__all__ = [
    "render_graph",
    "batch_render_graphs",
    "TextVisualizer",
    "visualize_timeline",  # Add this
]
```

## Step 4: Add CLI Subcommand

Update `kgb/__main__.py` (follow the pattern of `visualize_network` and `visualize_extraction`):

```python
@visualize_app.command("timeline")
def visualize_timeline_cmd(
    input_dir: Path = typer.Option(..., "--input", "-i", exists=True),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o"),
    dark_mode: bool = typer.Option(False, "--dark-mode"),
    date_field: str = typer.Option("date", "--date-field"),
    height: int = typer.Option(600, "--height"),
):
    """Create timeline visualization from extracted triples."""
    import json
    from .visualization import visualize_timeline

    viz_dir = output_dir or input_dir.parent / "visualizations_timeline"
    viz_dir.mkdir(parents=True, exist_ok=True)

    for json_file in input_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                triples = json.load(f)

            output_path = viz_dir / f"{json_file.stem}.html"
            visualize_timeline(
                data=triples,
                output_path=output_path,
                dark_mode=dark_mode,
                date_field=date_field,
                height=height
            )
            console.print(f"Created: {output_path}")

        except ValueError as e:
            console.print(f"[yellow]Skipped {json_file.name}: {e}[/yellow]")
        except Exception as e:
            console.print(f"[red]Error {json_file.name}: {e}[/red]")
```

> See existing `visualize_network` and `visualize_extraction` commands in `kgb/__main__.py` for complete reference.

## Step 5: Verify

### Check Import

```bash
python -c "from kgb.visualization import visualize_timeline; print('OK')"
```

### Unit Tests

```python
def test_visualize_timeline_from_triples(tmp_path):
    from kgb.visualization.timeline_viz import visualize_timeline

    triples = [
        {"head": "EventA", "relation": "occurred", "tail": "LocationX",
         "inference": "explicit", "date": "2024-01-15"},
        {"head": "EventB", "relation": "happened", "tail": "LocationY",
         "inference": "explicit", "date": "2024-02-20"},
    ]

    output = tmp_path / "timeline.html"
    result = visualize_timeline(triples, output)

    assert result.exists()
    html = result.read_text()
    assert "plotly" in html.lower()


def test_timeline_no_dates(tmp_path):
    from kgb.visualization.timeline_viz import visualize_timeline
    import pytest

    triples = [{"head": "A", "relation": "r", "tail": "B", "inference": "explicit"}]

    with pytest.raises(ValueError, match="No events"):
        visualize_timeline(triples, tmp_path / "no_dates.html")


def test_timeline_dark_mode(tmp_path):
    from kgb.visualization.timeline_viz import visualize_timeline

    triples = [
        {"head": "A", "relation": "r", "tail": "B",
         "inference": "explicit", "date": "2024-01-01"},
    ]

    output = tmp_path / "dark.html"
    result = visualize_timeline(triples, output, dark_mode=True)
    assert result.exists()
```

## Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dark_mode` | bool | False | Use dark color theme |
| `date_field` | str | "date" | Attribute name containing dates |
| `height` | int | 600 | Canvas height in pixels |

## Key Principles

| Principle | Implementation |
|-----------|---------------|
| **Dark Mode** | Use theme dict with conditional colors (follow `graph_viz.py` pattern) |
| **Type Safety** | Accept `Path \| list[Triple] \| list[dict]` with isinstance checks |
| **Self-Containment** | Use CDN scripts (cytoscape.js, dagre, cxtmenu) for portability |
| **Error Handling** | Raise `ValueError` for invalid inputs, `FileNotFoundError` for missing files |
| **Inference Awareness** | Use `inference.value` (not `str(inference)`) — `"explicit"` / `"contextual"` |

## Files to Create/Modify

| File | Action |
|------|--------|
| `kgb/visualization/your_viz.py` | Create — visualization implementation |
| `kgb/visualization/__init__.py` | Modify — add imports and exports |
| `kgb/__main__.py` | Modify — add CLI subcommand |

## Verification Checklist

- [ ] Implementation handles multiple input types (Path, list[Triple], list[dict])
- [ ] Dark/light mode support via theme dict
- [ ] Output directory created with `mkdir(parents=True, exist_ok=True)`
- [ ] Registered in `kgb/visualization/__init__.py`
- [ ] CLI subcommand added under `visualize_app`
- [ ] Tests for happy path, error cases, and theme options
