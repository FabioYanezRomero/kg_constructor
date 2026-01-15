"""Base classes for knowledge domains."""

from __future__ import annotations

import json
import inspect
from abc import ABC
from pathlib import Path
from typing import Any, Optional, Union

from .models import DomainExamples, ExtractionMode, DomainSchema


class DomainComponent:
    """Groups prompt and examples for a specific domain activity (Extraction or Augmentation)."""

    def __init__(
        self,
        prompt_path: Path,
        examples_path: Path,
        loader: "KnowledgeDomain",
        activity_key: str  # "extraction" or "augmentation"
    ) -> None:
        self._prompt_path = prompt_path
        self._examples_path = examples_path
        self._loader = loader
        self._activity_key = activity_key
        self._prompt: Optional[str] = None
        self._examples: Optional[list[dict[str, Any]]] = None

    @property
    def prompt(self) -> str:
        """The prompt text for this component."""
        if self._prompt is None:
            self._prompt = self._loader._load_text(self._prompt_path)
        return self._prompt

    @property
    def examples(self) -> list[dict[str, Any]]:
        """The examples list for this component."""
        if self._examples is None:
            raw_examples = self._loader.all_examples
            if self._activity_key == "extraction":
                self._examples = [ex.model_dump() for ex in raw_examples.extraction]
            else:
                self._examples = [ex.model_dump() for ex in raw_examples.augmentation]
        return self._examples


class KnowledgeDomain(ABC):
    """Abstract base class for a knowledge domain.
    
    A domain manages resource-based prompts, validated examples, and schemas.
    """

    def __init__(
        self,
        extraction_mode: Union[ExtractionMode, str] = ExtractionMode.OPEN,
        root_dir: Optional[Union[str, Path]] = None,
        extraction_prompt_path: Optional[Union[str, Path]] = None,
        extraction_examples_path: Optional[Union[str, Path]] = None,
        augmentation_prompt_path: Optional[Union[str, Path]] = None,
        augmentation_examples_path: Optional[Union[str, Path]] = None,
        schema_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.extraction_mode = ExtractionMode(extraction_mode)
        
        # 1. Automatic Root Resolution
        if root_dir:
            self._root_dir = Path(root_dir)
        else:
            # Fallback to the directory where the concrete subclass is defined
            self._root_dir = Path(inspect.getfile(self.__class__)).parent

        # 2. Resource Paths (with overrides)
        ext_mode_file = "prompt_open.txt" if self.extraction_mode == ExtractionMode.OPEN else "prompt_constrained.txt"
        
        self._ext_prompt_path = Path(extraction_prompt_path) if extraction_prompt_path else self._root_dir / "extraction" / ext_mode_file
        self._ext_examples_path = Path(extraction_examples_path) if extraction_examples_path else self._root_dir / "extraction" / "examples.json"
        
        self._aug_prompt_path = Path(augmentation_prompt_path) if augmentation_prompt_path else self._root_dir / "augmentation" / "prompt.txt"
        self._aug_examples_path = Path(augmentation_examples_path) if augmentation_examples_path else self._root_dir / "augmentation" / "examples.json"
        
        self._schema_path = Path(schema_path) if schema_path else self._root_dir / "schema.json"

        # 3. Grouped API
        self.extraction = DomainComponent(self._ext_prompt_path, self._ext_examples_path, self, "extraction")
        self.augmentation = DomainComponent(self._aug_prompt_path, self._aug_examples_path, self, "augmentation")

        # Lazy loaded data
        self._all_examples: Optional[DomainExamples] = None
        self._schema: Optional[DomainSchema] = None

    @property
    def schema(self) -> DomainSchema:
        """Get the validated schema for this domain."""
        if self._schema is None:
            self._schema = self._load_schema()
        return self._schema

    @property
    def all_examples(self) -> DomainExamples:
        """Get all validated examples for this domain."""
        if self._all_examples is None:
            self._all_examples = self._load_examples_bundle()
        return self._all_examples

    # Backward compatibility flat methods (delegating to grouped API)
    def get_extraction_prompt(self) -> str:
        return self.extraction.prompt

    def get_augmentation_prompt(self) -> str:
        return self.augmentation.prompt

    def get_extraction_examples(self) -> list[dict[str, Any]]:
        return self.extraction.examples

    def get_augmentation_examples(self) -> list[dict[str, Any]]:
        return self.augmentation.examples

    def _load_schema(self) -> DomainSchema:
        if not self._schema_path.exists():
            return DomainSchema()  # Empty schema if not provided
        data = self._load_json(self._schema_path)
        return DomainSchema(**data)

    def _load_examples_bundle(self) -> DomainExamples:
        """Load and validate examples bundle."""
        extraction_data = self._load_json(self._ext_examples_path) if self._ext_examples_path.exists() else []
        augmentation_data = self._load_json(self._aug_examples_path) if self._aug_examples_path.exists() else []
        
        return DomainExamples(
            extraction=extraction_data,
            augmentation=augmentation_data
        )

    @staticmethod
    def _load_text(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"Resource not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    @staticmethod
    def _load_json(path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"Resource not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


__all__ = ["KnowledgeDomain", "DomainComponent"]
