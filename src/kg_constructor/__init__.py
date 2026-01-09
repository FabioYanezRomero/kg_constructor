"""Knowledge graph constructor package."""

from __future__ import annotations

from typing import Any

__all__ = [
    "build_and_save_graphs",
    "LangExtractExtractor",
    "LangExtractPipeline",
    "ExtractionConfig",
]


def build_and_save_graphs(*args: Any, **kwargs: Any) -> Any:
    from .pipeline import build_and_save_graphs as _impl

    return _impl(*args, **kwargs)


def LangExtractExtractor(*args: Any, **kwargs: Any) -> Any:
    from .langextract_extractor import LangExtractExtractor as _impl

    return _impl(*args, **kwargs)


def LangExtractPipeline(*args: Any, **kwargs: Any) -> Any:
    from .langextract_pipeline import LangExtractPipeline as _impl

    return _impl(*args, **kwargs)


def ExtractionConfig(*args: Any, **kwargs: Any) -> Any:
    from .langextract_extractor import ExtractionConfig as _impl

    return _impl(*args, **kwargs)
