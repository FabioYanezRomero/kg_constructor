"""Core extraction logic for converting text to triples."""

from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass
from typing import Any

import langextract as lx
from ..clients import BaseLLMClient
from ..domains import DomainSchema, ExtractionMode, KnowledgeDomain, Triple

_TYPE_RELATION_ALIASES = {
    "is_type",
    "is_type_of",
    "type_of",
    "instance_of",
    "entity_type",
    "category_of",
}


@dataclass(frozen=True)
class _SchemaConstraints:
    """Normalized schema constraints used by the builder orchestrators."""

    enforce: bool
    entity_types: tuple[str, ...]
    relation_types: tuple[str, ...]
    normalized_entity_types: frozenset[str]
    normalized_relation_types: frozenset[str]


def _normalize_constraint_label(value: str) -> str:
    """Normalize labels so schema validation tolerates case and punctuation variance."""
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def _iter_example_triples(raw_example: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract triple payloads from domain example formats."""
    triples: list[dict[str, Any]] = []

    for extraction in raw_example.get("extractions", []):
        attributes = extraction.get("attributes")
        if isinstance(attributes, dict):
            triples.append(attributes)

    for output_triple in raw_example.get("output", []):
        if isinstance(output_triple, dict):
            triples.append(output_triple)

    return triples


def _collect_schema_constraints(
    domain: KnowledgeDomain,
    raw_examples: list[dict[str, Any]] | None = None,
) -> _SchemaConstraints:
    """Build a normalized constraint set from the schema and domain examples."""
    if domain.extraction_mode != ExtractionMode.CONSTRAINED:
        return _SchemaConstraints(False, tuple(), tuple(), frozenset(), frozenset())

    schema: DomainSchema = domain.schema

    entity_types: list[str] = []
    normalized_entity_types: set[str] = set()
    for entity_type in schema.entity_types:
        normalized = _normalize_constraint_label(entity_type)
        if normalized and normalized not in normalized_entity_types:
            entity_types.append(entity_type.strip())
            normalized_entity_types.add(normalized)

    relation_types: list[str] = []
    normalized_relation_types: set[str] = set()

    def _register_relation(label: str) -> None:
        normalized = _normalize_constraint_label(label)
        if normalized and normalized not in normalized_relation_types:
            relation_types.append(label.strip())
            normalized_relation_types.add(normalized)

    for relation_type in schema.relation_types:
        _register_relation(relation_type)

    for raw_example in raw_examples or []:
        for triple in _iter_example_triples(raw_example):
            relation = triple.get("relation")
            if isinstance(relation, str):
                _register_relation(relation)

    return _SchemaConstraints(
        enforce=bool(entity_types or relation_types),
        entity_types=tuple(entity_types),
        relation_types=tuple(relation_types),
        normalized_entity_types=frozenset(normalized_entity_types),
        normalized_relation_types=frozenset(normalized_relation_types),
    )


def _build_schema_guidance(constraints: _SchemaConstraints) -> str:
    """Build prompt guidance from normalized constraints."""
    if not constraints.enforce:
        return ""

    lines = ["Schema constraints:"]

    if constraints.entity_types:
        lines.append("Allowed entity types:")
        lines.extend(f"- {entity_type}" for entity_type in constraints.entity_types)
        lines.append(
            "If entity types are implicit in the text, keep extracted entities semantically within these categories."
        )

    if constraints.relation_types:
        lines.append("Allowed relation labels:")
        lines.extend(f"- {relation_type}" for relation_type in constraints.relation_types)
        lines.append("Use only relation labels from this list. Non-matching labels will be discarded.")

    return "\n".join(lines)


def _render_prompt_template(
    prompt_template: str,
    record: dict[str, Any],
    schema_guidance: str = "",
) -> str:
    """Render a prompt template with the current record payload."""
    prompt = prompt_template.replace(
        "{{record_json}}",
        json.dumps(record, ensure_ascii=False, indent=2)
    )
    prompt = prompt.replace("{{schema_constraints}}", schema_guidance)
    if schema_guidance and "{{schema_constraints}}" not in prompt_template:
        prompt = f"{prompt.rstrip()}\n\n{schema_guidance}"
    return prompt


def _build_examples(domain: KnowledgeDomain) -> list[lx.data.ExampleData]:
    """Build extraction examples from the domain configuration.
    
    Converts raw example dicts to proper langextract ExampleData objects
    with Extraction objects (not plain dicts).
    """
    raw_examples = domain.extraction.examples
    examples = []
    
    # Valid fields for lx.data.Extraction
    valid_extraction_fields = {
        "extraction_text", "extraction_class", "attributes",
        "char_interval", "description", "extraction_index",
        "group_index", "alignment_status"
    }

    for ex_data in raw_examples:
        # Make a copy to avoid mutating original
        ex_data = dict(ex_data)

        # Convert dict extractions to Extraction objects
        if "extractions" in ex_data:
            extractions = []
            for ext in ex_data["extractions"]:
                if isinstance(ext, dict):
                    ext = dict(ext)  # Copy to avoid mutation

                    # Convert char_start/char_end to char_interval
                    if "char_start" in ext and "char_end" in ext:
                        char_start = ext.pop("char_start")
                        char_end = ext.pop("char_end")
                        if char_start is not None and char_end is not None:
                            ext["char_interval"] = lx.data.CharInterval(
                                start_pos=char_start,
                                end_pos=char_end
                            )

                    # Filter keys to valid fields
                    filtered_ext = {k: v for k, v in ext.items() if k in valid_extraction_fields}
                    extractions.append(lx.data.Extraction(**filtered_ext))
                else:
                    extractions.append(ext)
            ex_data["extractions"] = extractions
        examples.append(lx.data.ExampleData(**ex_data))
    return examples


def _normalize_triple(raw_triple: dict[str, Any]) -> Triple | None:
    """Normalize a raw extraction to standard Triple format."""
    try:
        # Grounding info doesn't fit in the current Triple model, 
        # but we can filter for the fields Triple expects.
        return Triple(
            head=raw_triple.get("head", ""),
            relation=raw_triple.get("relation", ""),
            tail=raw_triple.get("tail", ""),
            inference=raw_triple.get("inference", "explicit"),
            justification=raw_triple.get("justification")
        )
    except Exception as e:
        # Log and skip invalid triples
        print(f"Warning: Skipping invalid triple: {e}")
        return None


def _extract_explicit_entity_type_labels(raw_triple: dict[str, Any]) -> list[str]:
    """Collect explicit entity type annotations if a client/provider emitted them."""
    labels: list[str] = []
    candidate_keys = ("head_type", "tail_type", "entity_type", "source_type", "target_type")

    for key in candidate_keys:
        value = raw_triple.get(key)
        if isinstance(value, str) and value.strip():
            labels.append(value.strip())
        elif isinstance(value, list):
            labels.extend(
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            )

    return labels


def _validate_entity_types(
    triple: Triple,
    raw_triple: dict[str, Any],
    constraints: _SchemaConstraints,
) -> tuple[bool | None, list[str]]:
    """Validate entity type information when the builder can do so defensibly."""
    if not constraints.normalized_entity_types:
        return True, []

    explicit_labels = _extract_explicit_entity_type_labels(raw_triple)
    if explicit_labels:
        invalid_labels = [
            label for label in explicit_labels
            if _normalize_constraint_label(label) not in constraints.normalized_entity_types
        ]
        return not invalid_labels, invalid_labels

    if _normalize_constraint_label(triple.relation) in _TYPE_RELATION_ALIASES:
        candidate_labels = [triple.head, triple.tail]
        is_valid = any(
            _normalize_constraint_label(label) in constraints.normalized_entity_types
            for label in candidate_labels
        )
        return is_valid, candidate_labels if not is_valid else []

    return None, []


def _validate_triples_against_schema(
    triples: list[Triple],
    constraints: _SchemaConstraints,
    *,
    raw_triples: list[dict[str, Any]] | None = None,
) -> tuple[list[Triple], dict[str, Any]]:
    """Filter triples against the normalized schema constraints."""
    summary = {
        "applied": constraints.enforce,
        "allowed_entity_types": list(constraints.entity_types),
        "allowed_relation_types": list(constraints.relation_types),
        "accepted_triples": 0,
        "rejected_triples": 0,
        "rejected_due_to_relation": 0,
        "rejected_due_to_entity_type": 0,
        "entity_type_validation_skipped": 0,
        "rejected_samples": [],
    }

    if not constraints.enforce:
        summary["accepted_triples"] = len(triples)
        return triples, summary

    accepted: list[Triple] = []
    raw_triples = raw_triples or []

    for index, triple in enumerate(triples):
        raw_triple = raw_triples[index] if index < len(raw_triples) and isinstance(raw_triples[index], dict) else {}
        rejected_for: list[str] = []

        if constraints.normalized_relation_types:
            normalized_relation = _normalize_constraint_label(triple.relation)
            if normalized_relation not in constraints.normalized_relation_types:
                rejected_for.append("relation")
                summary["rejected_due_to_relation"] += 1

        entity_validation_result, invalid_entity_labels = _validate_entity_types(triple, raw_triple, constraints)
        if entity_validation_result is None:
            summary["entity_type_validation_skipped"] += 1
        elif not entity_validation_result:
            rejected_for.append("entity_type")
            summary["rejected_due_to_entity_type"] += 1

        if rejected_for:
            summary["rejected_triples"] += 1
            if len(summary["rejected_samples"]) < 5:
                summary["rejected_samples"].append({
                    "triple": triple.model_dump(),
                    "reasons": rejected_for,
                    "invalid_entity_labels": invalid_entity_labels,
                })
            continue

        accepted.append(triple)

    summary["accepted_triples"] = len(accepted)
    return accepted, summary


def _warn_on_schema_validation(stage: str, summary: dict[str, Any]) -> None:
    """Emit a compact warning when schema post-validation discards output."""
    if not summary.get("applied"):
        return

    rejected = summary.get("rejected_triples", 0)
    if rejected == 0:
        return

    warnings.warn(
        f"Schema validation during {stage} discarded {rejected} triple(s).",
        stacklevel=2,
    )


def extract_triples(
    client: BaseLLMClient,
    domain: KnowledgeDomain,
    text: str,
    record_id: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    prompt_override: str | None = None
) -> list[Triple]:
    """Extract triples from a single text.

    Args:
        client: LLM client to use
        domain: Knowledge domain providing prompts and examples
        text: Input text
        record_id: Optional record ID for logging
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        prompt_override: Optional prompt template override

    Returns:
        List of extracted Triple objects
    """
    record = {"text": text}
    if record_id:
        record["id"] = record_id

    prompt_template = prompt_override or domain.extraction.prompt
    raw_examples = domain.extraction.examples
    constraints = _collect_schema_constraints(domain, raw_examples)
    final_prompt = _render_prompt_template(
        prompt_template,
        record,
        schema_guidance=_build_schema_guidance(constraints),
    )
    examples = _build_examples(domain)

    # Use langextract for extraction (required for visualizations)
    raw_triples = client.extract(
        text=final_prompt,
        prompt_description="Extract meaningful knowledge graph triples from the text, focusing on explicit relationships between entities.",
        examples=examples,
        format_type=Triple,
        temperature=temperature,
        max_tokens=max_tokens
    )

    triples = []
    normalized_raw_triples: list[dict[str, Any]] = []
    for t in raw_triples:
        if not isinstance(t, dict):
            continue
        normalized = _normalize_triple(t)
        if normalized:
            triples.append(normalized)
            normalized_raw_triples.append(t)

    validated_triples, validation_summary = _validate_triples_against_schema(
        triples,
        constraints,
        raw_triples=normalized_raw_triples,
    )
    _warn_on_schema_validation("extraction", validation_summary)
    return validated_triples


def extract_from_text(
    client: BaseLLMClient,
    domain: KnowledgeDomain,
    text: str,
    record_id: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    prompt_override: str | None = None
) -> list[Triple]:
    """Backward-compatible alias for ``extract_triples``."""
    return extract_triples(
        client=client,
        domain=domain,
        text=text,
        record_id=record_id,
        temperature=temperature,
        max_tokens=max_tokens,
        prompt_override=prompt_override,
    )
