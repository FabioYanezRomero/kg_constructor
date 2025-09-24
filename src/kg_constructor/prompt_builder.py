from __future__ import annotations

"""Prompt composition helpers."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PromptContext:
    dataset_name: str
    dataset_config: str | None
    split: str
    record_id: str
    model_name: str


class PromptBuilder:
    """Load a template from disk and render prompts for dataset records."""

    def __init__(self, template_path: Path) -> None:
        self._template = template_path.read_text(encoding="utf-8")

    def build(self, payload: dict, context: PromptContext) -> str:
        prompt = self._template
        replacements = {
            "{{dataset_name}}": context.dataset_name,
            "{{dataset_config}}": context.dataset_config or "default",
            "{{split}}": context.split,
            "{{record_id}}": context.record_id,
            "{{model_name}}": context.model_name,
            "{{record_json}}": json.dumps(payload, ensure_ascii=False, indent=2),
        }
        for token, value in replacements.items():
            prompt = prompt.replace(token, value)
        return prompt


__all__ = [
    "PromptBuilder",
    "PromptContext",
]
