"""Loader for provider-specific default configuration files."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=None)
def load_provider_defaults(provider_name: str) -> dict:
    """Load default configuration for a provider from its JSON config file.

    Args:
        provider_name: Provider name matching a file under configs/ (e.g. "ollama").

    Returns:
        Dictionary of provider defaults.
    """
    config_file = resources.files("kgb.clients") / "configs" / f"{provider_name}.json"
    return json.loads(config_file.read_text(encoding="utf-8"))
