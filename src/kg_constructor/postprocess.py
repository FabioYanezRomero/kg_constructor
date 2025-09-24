from __future__ import annotations

"""Utilities to post-process model outputs into the canonical graph schema."""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

import typer

app = typer.Typer(help="Normalize raw model outputs into structured graph JSON.")

logger = logging.getLogger(__name__)


def clean_code_fence(text: str) -> str:
    """Strip Markdown code fences from a string."""

    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    # Remove opening fence with optional language tag.
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    # Remove trailing fence if present.
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def try_load_json(text: str) -> Any | None:
    """Attempt to parse a JSON payload from text."""

    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def slugify(value: str) -> str:
    """Produce a filesystem and identifier friendly slug for node ids."""

    token = re.sub(r"[^A-Za-z0-9_.-]", "-", value.strip())
    token = re.sub(r"-+", "-", token)
    return token.strip("-") or "entity"


@dataclass
class Triple:
    head: str
    relation: str
    tail: str
    attributes: Dict[str, Any]

    @classmethod
    def from_mapping(cls, payload: Dict[str, Any]) -> "Triple" | None:
        head = payload.get("head")
        relation = payload.get("relation")
        tail = payload.get("tail")
        if not isinstance(head, str) or not isinstance(relation, str) or not isinstance(tail, str):
            return None
        attributes = {
            key: value
            for key, value in payload.items()
            if key not in {"head", "relation", "tail"}
        }
        return cls(head=head.strip(), relation=relation.strip(), tail=tail.strip(), attributes=attributes)


def triples_from_payload(payload: Any) -> List[Triple]:
    """Extract triples from the decoded raw response."""

    triples: List[Triple] = []
    if isinstance(payload, dict):
        candidate = Triple.from_mapping(payload)
        if candidate:
            triples.append(candidate)
        return triples

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                candidate = Triple.from_mapping(item)
                if candidate:
                    triples.append(candidate)
    return triples


def build_graph(triples: Iterable[Triple]) -> Dict[str, Any]:
    """Convert triples into the canonical graph structure."""

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    for triple in triples:
        head_id = nodes.setdefault(
            slugify(triple.head),
            {
                "id": slugify(triple.head),
                "type": "entity",
                "properties": {"name": triple.head},
            },
        )["id"]
        tail_id = nodes.setdefault(
            slugify(triple.tail),
            {
                "id": slugify(triple.tail),
                "type": "entity",
                "properties": {"name": triple.tail},
            },
        )["id"]

        edge_properties = dict(triple.attributes)
        if triple.head != head_id:
            edge_properties.setdefault("head_label", triple.head)
        if triple.tail != tail_id:
            edge_properties.setdefault("tail_label", triple.tail)

        edges.append(
            {
                "source": head_id,
                "target": tail_id,
                "type": triple.relation or "related_to",
                "properties": edge_properties,
            }
        )

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def process_file(path: Path, force: bool) -> bool:
    """Normalize a single JSON document."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("graph") is not None and not force:
        return False

    raw_response = document.get("raw_response")
    if not isinstance(raw_response, str):
        logger.warning("Skipping %s: raw_response missing or not a string", path)
        return False

    cleaned = clean_code_fence(raw_response)
    payload = try_load_json(cleaned)
    if payload is None:
        logger.warning("Skipping %s: unable to parse JSON from raw_response", path)
        return False

    triples = triples_from_payload(payload)
    if not triples:
        logger.warning("Skipping %s: no valid triples extracted", path)
        return False

    graph = build_graph(triples)
    document["graph"] = graph
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


@app.command()
def run(
    input_dir: Path = typer.Argument(Path("data/output"), help="Directory containing pipeline outputs."),
    force: bool = typer.Option(False, "--force", help="Rebuild graphs even if already present."),
) -> None:
    """Post-process every JSON document under the provided directory."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    updated = 0
    for file_path in sorted(input_dir.rglob("*.json")):
        try:
            if process_file(file_path, force=force):
                updated += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to process %s: %s", file_path, exc)
    logger.info("Post-processing complete. Updated %s file(s).", updated)


if __name__ == "__main__":
    app()
