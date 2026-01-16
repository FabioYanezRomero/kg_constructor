# Adding a Visualization

This skill documents how to add a new visualization type to the `src/visualization/` module.

## Overview

Visualizations render knowledge graphs as interactive HTML. The system provides:
- Network topology views (Plotly + NetworkX)
- Entity text highlighting (langextract)
- Extensible architecture for custom visualizations

## Architecture

```
                     Visualization Module
    ┌────────────────────────────────────────────────────┐
    │                                                    │
    │  network_viz.py          entity_viz.py             │
    │  ├─ Plotly-based         ├─ langextract-based      │
    │  ├─ Graph topology       ├─ Text highlighting      │
    │  └─ Nodes & edges        └─ Entity spans           │
    │                                                    │
    │  your_viz.py                                       │
    │  └─ Your new visualization                         │
    │                                                    │
    └────────────────────────────────────────────────────┘

Data Flow:
  list[Triple] or GraphML → Graph Construction → Layout → Rendering → HTML
```

**Key Files:**
- `src/visualization/network_viz.py` - Graph topology using Plotly + NetworkX
- `src/visualization/entity_viz.py` - Text entity highlighting using langextract
- `src/visualization/__init__.py` - Public exports

## Dependencies

**Required:**
- `networkx>=3.0` - Graph data structures and layouts
- `plotly>=5.0` - Interactive HTML visualizations

**Optional:**
- `langextract` - For text-based entity highlighting

## Step 1: Understand the Interface

All visualization functions should follow this pattern:

```python
def visualize_<type>(
    data: Path | list[Triple] | nx.Graph,
    output_path: Path | str,
    *,
    dark_mode: bool = False,
    **kwargs: Any
) -> Path:
    """Generate visualization.
    
    Args:
        data: Input (GraphML path, Triple list, or NetworkX graph)
        output_path: Destination HTML file
        dark_mode: Use dark theme
        
    Returns:
        Path to created HTML file
        
    Raises:
        ValueError: Invalid data format
        FileNotFoundError: GraphML path doesn't exist
    """
```

## Step 2: Implement Your Visualization

Create `src/visualization/timeline_viz.py`:

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
    
    # 2. Theme Configuration
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
    fig.write_html(str(output_path), include_plotlyjs="cdn")
    
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
            "label": f"{t.get('head', '')} → {t.get('tail', '')}",
            "hover": f"<b>{t.get('relation', '')}</b><br>{t.get('head')} → {t.get('tail')}"
        })
    
    return events
```

## Step 3: Register in Module

Update `src/visualization/__init__.py`:

```python
from .network_viz import visualize_graph, batch_visualize_graphs
from .entity_viz import EntityVisualizer
from .timeline_viz import visualize_timeline

__all__ = [
    "visualize_graph",
    "batch_visualize_graphs",
    "EntityVisualizer",
    "visualize_timeline",
]
```

## Step 4: Add CLI Subcommand

Update `src/__main__.py`:

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

> See existing `visualize_network` command in `src/__main__.py` for complete reference.

## Step 5: Verify

### Check Import

```bash
python -c "from src.visualization import visualize_timeline; print('OK')"
```

### Unit Test

```python
def test_visualize_timeline_from_triples(tmp_path):
    from src.visualization.timeline_viz import visualize_timeline
    from src.domains import Triple
    
    triples = [
        Triple(head="EventA", relation="occurred", tail="LocationX", date="2024-01-15"),
        Triple(head="EventB", relation="happened", tail="LocationY", date="2024-02-20"),
    ]
    
    output = tmp_path / "timeline.html"
    result = visualize_timeline(triples, output)
    
    assert result.exists()
    html = result.read_text()
    assert "plotly" in html.lower()
```

### Integration Test

```python
def test_timeline_cli_integration(tmp_path):
    import json
    from typer.testing import CliRunner
    from src.__main__ import app
    
    input_dir = tmp_path / "json"
    input_dir.mkdir()
    (input_dir / "test.json").write_text(json.dumps([
        {"head": "A", "relation": "r", "tail": "B", "date": "2024-01-01"}
    ]))
    
    runner = CliRunner()
    result = runner.invoke(app, [
        "visualize", "timeline",
        "--input", str(input_dir),
        "--output", str(tmp_path / "viz"),
    ])
    
    assert result.exit_code == 0
    assert (tmp_path / "viz" / "test.html").exists()
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
| **Dark Mode** | Use theme dict with conditional colors |
| **Type Safety** | Accept `Path \| list[Triple]` with isinstance checks |
| **Self-Containment** | Use `include_plotlyjs="cdn"` for portability |
| **Error Handling** | Raise `ValueError` for invalid inputs |

## Error Handling

| Exception | When | Action |
|-----------|------|--------|
| `ValueError` | Invalid data format or missing dates | Fail with descriptive message |
| `FileNotFoundError` | GraphML path doesn't exist | Fail loudly |
| `PermissionError` | Cannot write output file | Re-raise with context |
