from __future__ import annotations

"""Utilities for loading and iterating over Hugging Face datasets."""

from dataclasses import dataclass
from typing import Any, Dict, Iterator

from datasets import Dataset, IterableDataset, load_dataset

from .config import DatasetConfig


@dataclass(frozen=True)
class Example:
    """Represents a single dataset example with a stable identifier."""

    example_id: str
    payload: Dict[str, Any]


class DatasetLoader:
    """Load dataset splits according to the provided configuration."""

    def __init__(self, config: DatasetConfig) -> None:
        self._config = config

    def load_split(self, split_name: str) -> Dataset | IterableDataset:
        """Load and return a dataset split."""

        kwargs: Dict[str, Any] = {}
        if self._config.config:
            kwargs["name"] = self._config.config
        return load_dataset(self._config.name, split=split_name, **kwargs)

    def split_length(self, split_name: str) -> int | None:
        dataset = self.load_split(split_name)
        return self._split_length(dataset)

    def estimate_length(self, dataset: Dataset | IterableDataset) -> int | None:
        return self._split_length(dataset)

    def iter_split(
        self, split_name: str, dataset: Dataset | IterableDataset | None = None
    ) -> Iterator[Example]:
        """Yield examples for a given split, respecting sample limits."""

        dataset = dataset or self.load_split(split_name)
        if isinstance(dataset, IterableDataset):
            generator = dataset.take(self._config.sample_size) if self._config.sample_size else dataset
            for index, record in enumerate(generator):
                yield Example(example_id=self._record_id(record, index), payload=dict(record))
            return

        size = len(dataset)  # type: ignore[arg-type]
        limit = min(self._config.sample_size or size, size)
        for index in range(limit):
            record = dataset[index]
            yield Example(example_id=self._record_id(record, index), payload=dict(record))

    def _split_length(self, dataset: Dataset | IterableDataset) -> int | None:
        if isinstance(dataset, IterableDataset):
            return self._config.sample_size
        size = len(dataset)  # type: ignore[arg-type]
        return min(self._config.sample_size or size, size)

    @staticmethod
    def _record_id(record: Dict[str, Any], index: int) -> str:
        if "id" in record and isinstance(record["id"], str):
            return record["id"]
        if "guid" in record and isinstance(record["guid"], str):
            return record["guid"]
        return f"row_{index:06d}"


__all__ = [
    "DatasetLoader",
    "Example",
]
