from __future__ import annotations

"""Helpers to work with JSON content returned by the language model."""

import json
from typing import Any


def try_parse_json(text: str) -> Any | None:
    """Return a JSON object if the text is valid or contains an embedded JSON payload."""

    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


__all__ = ["try_parse_json"]
