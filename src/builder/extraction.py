"""Core extraction logic for converting text to triples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import langextract as lx
from ..clients import BaseLLMClient
from ..domains import KnowledgeDomain, Triple


def _prepare_prompt(prompt_template: str, record: dict[str, Any]) -> str:
    """Prepare the extraction prompt from template."""
    prompt = prompt_template.replace(
        "{{record_json}}",
        json.dumps(record, ensure_ascii=False, indent=2)
    )
    return prompt


def _create_examples(domain: KnowledgeDomain) -> list[lx.data.ExampleData]:
    """Create few-shot examples for langextract extraction."""
    raw_examples = domain.get_extraction_examples()
    return [lx.data.ExampleData(**ex) for ex in raw_examples]


def _normalize_triple(raw_triple: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw extraction to standard Triple format."""
    return {
        "head": raw_triple.get("head", ""),
        "relation": raw_triple.get("relation", ""),
        "tail": raw_triple.get("tail", ""),
        "inference": raw_triple.get("inference", "explicit"),
        "justification": raw_triple.get("justification"),
        "char_start": raw_triple.get("char_start"),
        "char_end": raw_triple.get("char_end"),
        "extraction_text": raw_triple.get("extraction_text"),
    }


def extract_from_text(
    client: BaseLLMClient,
    domain: KnowledgeDomain,
    text: str,
    record_id: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    prompt_override: str | None = None
) -> list[dict[str, Any]]:
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
        List of extracted triple dictionaries
    """
    record = {"text": text}
    if record_id:
        record["id"] = record_id

    prompt_template = prompt_override or domain.extraction.prompt
    prompt_text = _prepare_prompt(prompt_template, record)
    examples = _create_examples(domain)

    raw_triples = client.extract(
        text=prompt_text,
        prompt_description="Extract meaningful knowledge graph triples from the text, focusing on explicit relationships between entities.",
        examples=examples,
        format_type=Triple,
        temperature=temperature,
        max_tokens=max_tokens
    )

    return [_normalize_triple(t) for t in raw_triples]
