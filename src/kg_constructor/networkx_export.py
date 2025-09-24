from __future__ import annotations

"""Generate NetworkX graphs from structured knowledge graph JSON files."""

import json
from pathlib import Path
from typing import Any, Dict

import networkx as nx
from networkx.readwrite import json_graph
import typer

app = typer.Typer(help="Build NetworkX graphs from processed pipeline outputs.")


def build_networkx_graph(document: Dict[str, Any]) -> nx.MultiDiGraph:
    data = document.get("graph")
    if not isinstance(data, dict):
        raise ValueError("Document does not contain a structured 'graph' field")

    graph = nx.MultiDiGraph()

    for node in data.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str):
            continue
        attributes = {k: v for k, v in node.items() if k != "id"}
        graph.add_node(node_id, **attributes)

    for edge in data.get("edges", []):
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        attributes = {k: v for k, v in edge.items() if k not in {"source", "target"}}
        key = attributes.get("type")
        graph.add_edge(source, target, key=key, **attributes)

    return graph


def write_graph(graph: nx.MultiDiGraph, output: Path, fmt: str) -> None:
    fmt = fmt.lower()
    if fmt == "graphml":
        nx.write_graphml(graph, output)
    elif fmt == "gpickle":
        nx.write_gpickle(graph, output)
    elif fmt == "json":
        payload = json_graph.node_link_data(graph, source="source", target="target")
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        raise typer.BadParameter(f"Unsupported output format: {fmt}")


@app.command()
def export(
    source: Path = typer.Argument(..., help="Path to a post-processed JSON document."),
    destination: Path = typer.Option(None, "--output", "-o", help="File to write the NetworkX graph to."),
    output_format: str = typer.Option(
        "graphml",
        "--format",
        "-f",
        help="Serialization format: graphml, gpickle, or json.",
    ),
) -> None:
    """Load a JSON document and export its graph using NetworkX."""

    document = json.loads(source.read_text(encoding="utf-8"))
    graph = build_networkx_graph(document)

    if destination is None:
        destination = source.with_suffix(f".{output_format}")

    write_graph(graph, destination, output_format)


if __name__ == "__main__":
    app()
