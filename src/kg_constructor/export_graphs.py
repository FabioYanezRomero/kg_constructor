from __future__ import annotations

"""Clean model responses and export NetworkX graphs for downstream use."""

import json
from pathlib import Path
from typing import Iterable

import pickle

import networkx as nx
import typer
from tqdm import tqdm

# Local copy to avoid importing heavy dependencies.
import re


def sanitize_path_component(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "-", value)
    return safe.strip("-") or "record"
from .postprocess import build_graph, clean_code_fence, triples_from_payload, try_load_json
from .networkx_export import build_networkx_graph

app = typer.Typer(help="Export cleaned knowledge graphs to NetworkX pickles.")


def ensure_graph(document: dict, source_path: Path) -> dict | None:
    """Return a populated graph dict, attempting to parse raw_response if needed."""

    graph = document.get("graph")
    if isinstance(graph, dict):
        return graph

    raw_response = document.get("raw_response")
    if not isinstance(raw_response, str) or not raw_response.strip():
        return None

    cleaned = clean_code_fence(raw_response)
    payload = try_load_json(cleaned)
    if payload is None:
        typer.secho(f"Failed to parse JSON from {source_path}", fg=typer.colors.YELLOW)
        return None

    triples = triples_from_payload(payload)
    if not triples:
        typer.secho(f"No triples extracted from {source_path}", fg=typer.colors.YELLOW)
        return None

    graph = build_graph(triples)
    document["graph"] = graph
    return graph


def save_graph(document: dict, graph: dict, output_root: Path) -> Path:
    dataset = document.get("dataset", "unknown-dataset")
    split = document.get("split", "unspecified")
    record_id = document.get("record_id", "record")

    dataset_dir = str(dataset).replace("/", "__")
    split_dir = sanitize_path_component(str(split))
    record_name = sanitize_path_component(str(record_id))

    destination_dir = output_root / dataset_dir / split_dir
    destination_dir.mkdir(parents=True, exist_ok=True)

    nx_graph = build_networkx_graph({"graph": graph})
    output_path = destination_dir / f"{record_name}.gpickle"
    with output_path.open("wb") as buffer:
        pickle.dump(nx_graph, buffer)
    return output_path


def iter_json_files(root: Path) -> Iterable[Path]:
    return sorted(root.rglob("*.json"))


@app.command()
def export(
    input_dir: Path = typer.Argument(Path("data/output"), help="Directory containing JSON outputs."),
    output_dir: Path = typer.Argument(Path("outputs"), help="Directory where NetworkX graphs will be stored."),
) -> None:
    """Generate NetworkX pickles for every available knowledge graph."""

    files = list(iter_json_files(input_dir))
    progress = tqdm(files, desc="Exporting graphs", unit="file")
    exported = 0
    skipped = 0

    for json_path in progress:
        document = json.loads(json_path.read_text(encoding="utf-8"))
        graph = ensure_graph(document, json_path)
        if graph is None:
            skipped += 1
            continue
        save_graph(document, graph, output_dir)
        exported += 1

    typer.secho(
        f"Export complete: {exported} graph(s) saved, {skipped} skipped.",
        fg=typer.colors.GREEN,
    )


if __name__ == "__main__":
    app()
