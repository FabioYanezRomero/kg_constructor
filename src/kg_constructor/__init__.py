"""Knowledge graph constructor package."""

from __future__ import annotations

from typing import Any

__all__ = ["build_and_save_graphs"]


def build_and_save_graphs(*args: Any, **kwargs: Any) -> Any:
    from .pipeline import build_and_save_graphs as _impl

    return _impl(*args, **kwargs)
