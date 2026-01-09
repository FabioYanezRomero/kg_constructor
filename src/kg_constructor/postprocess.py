from __future__ import annotations

"""Utilities to post-process model outputs into the canonical graph schema."""

import json
import logging
import re
from typing import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

import typer

app = typer.Typer(help="Normalize raw model outputs into structured graph JSON.")

logger = logging.getLogger(__name__)


def clean_code_fence(text: str) -> str:
    """Strip Markdown code fences from a string."""

    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    fence_pos = stripped.find("```")
    if fence_pos != -1:
        after_fence = stripped[fence_pos + 3 :]
        newline_pos = after_fence.find("\n")
        if newline_pos != -1:
            after_lang = after_fence[newline_pos + 1 :]
        else:
            after_lang = ""
        closing_pos = after_lang.find("```")
        if closing_pos != -1:
            return after_lang[:closing_pos].strip()

    return stripped


_KEY_PATTERN = re.compile(r'(?m)(^|[\{\[,])\s*(?P<key>[A-Za-z0-9_]+)\s*:(?=\s)')
_STRING_VALUE_PATTERN = re.compile(
    r'("(?P<key>head|relation|tail|inference|justification|source|target|type|name|label|role|relation_type)"\s*:\s*)(?P<value>(?:[^"\s\[{][^,\n\r}\]]*))(?P<suffix>\s*[\},\n])',
    flags=re.IGNORECASE,
)
_TRAILING_COMMA_PATTERN = re.compile(r',\s*([\]}])')
_INVALID_ESCAPE_PATTERN = re.compile(r'\\(?P<char>[^"\\/bfnrtu])')


def _attempt_parse(text: str, transforms: tuple[Callable[[str], str], ...] = ()) -> Any | None:
    candidate = text
    for transform in transforms:
        candidate = transform(candidate)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _quote_object_keys(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        prefix = match.group(1)
        key = match.group("key")
        return f"{prefix} \"{key}\":"

    return _KEY_PATTERN.sub(replace, text)


def _quote_common_string_values(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        prefix = match.group(1)
        value = match.group("value").strip()
        suffix = match.group("suffix")
        lowered = value.lower()
        if lowered in {"true", "false", "null"}:
            return match.group(0)
        if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
            return match.group(0)
        return f"{prefix}\"{value}\"{suffix}"

    return _STRING_VALUE_PATTERN.sub(replace, text)


def _strip_trailing_commas(text: str) -> str:
    return _TRAILING_COMMA_PATTERN.sub(r"\1", text)


def _escape_invalid_sequences(text: str) -> str:
    return _INVALID_ESCAPE_PATTERN.sub(lambda match: r"\\" + match.group("char"), text)


def try_load_json(text: str) -> Any | None:
    """Attempt to parse a JSON payload from text, applying minor repairs when needed."""

    if not text:
        return None

    direct = _attempt_parse(text)
    if direct is not None:
        return direct

    repaired = _attempt_parse(
        text,
        transforms=(
            _quote_object_keys,
            _quote_common_string_values,
            _escape_invalid_sequences,
            _strip_trailing_commas,
        ),
    )
    if repaired is not None:
        return repaired

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
