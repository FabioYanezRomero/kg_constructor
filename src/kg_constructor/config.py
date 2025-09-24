from __future__ import annotations

"""Configuration models for the knowledge graph construction pipeline."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


@dataclass(frozen=True)
class DatasetConfig:
    """Defines which Hugging Face dataset and splits to process."""

    name: str
    config: str | None = None
    splits: Tuple[str, ...] = ("train",)
    sample_size: int | None = None

    @classmethod
    def from_cli(
        cls,
        dataset_name: str,
        dataset_config: str | None,
        splits: Iterable[str],
        sample_size: int | None,
    ) -> "DatasetConfig":
        filtered_splits = tuple(split.strip() for split in splits if split.strip())
        if not filtered_splits:
            msg = "At least one dataset split must be provided"
            raise ValueError(msg)
        return cls(
            name=dataset_name,
            config=dataset_config,
            splits=filtered_splits,
            sample_size=sample_size,
        )


@dataclass(frozen=True)
class RunConfig:
    """Top-level configuration for orchestrating the pipeline."""

    dataset: DatasetConfig
    prompt_path: Path
    output_dir: Path
    model: str = "pytorch/gemma-3-12b-it-INT4"
    inference_backend: str = "vllm"
    inference_url: str = "http://localhost:8000"
    api_key: str | None = None
    request_timeout: int = 120
    overwrite: bool = False
    include_prompt_in_output: bool = False
    parallelism: int = 1
    warmup: bool = True
    warmup_prompt: str = "Warm up model. Respond with OK."
    system_prompt: str | None = None
    max_tokens: int | None = 1024
    temperature: float = 0.0
    top_p: float | None = None
    top_k: int | None = None
    repetition_penalty: float | None = None

    def __post_init__(self) -> None:
        if self.inference_backend.lower() != "vllm":
            msg = f"Unsupported inference backend: {self.inference_backend}"
            raise ValueError(msg)
        if not self.prompt_path.exists():
            msg = f"Prompt template not found: {self.prompt_path}"
            raise FileNotFoundError(msg)
        object.__setattr__(self, "prompt_path", self.prompt_path.resolve())
        object.__setattr__(self, "output_dir", self.output_dir.resolve())
        if self.parallelism < 1:
            msg = "Parallelism must be at least 1"
            raise ValueError(msg)


def expand_output_dir(base_dir: Path, dataset: DatasetConfig) -> Path:
    """Return the directory where outputs for a dataset should be stored."""

    return base_dir.joinpath(dataset.name.replace("/", "__"))


def build_generation_parameters(config: RunConfig) -> Dict[str, Any]:
    """Create the parameter payload for the inference backend."""

    params: Dict[str, Any] = {}
    if config.max_tokens is not None:
        params["max_tokens"] = config.max_tokens
    if config.temperature is not None:
        params["temperature"] = config.temperature
    if config.top_p is not None:
        params["top_p"] = config.top_p
    if config.top_k is not None:
        params["top_k"] = config.top_k
    if config.repetition_penalty is not None:
        params["repetition_penalty"] = config.repetition_penalty
    return params


__all__ = [
    "DatasetConfig",
    "RunConfig",
    "expand_output_dir",
    "build_generation_parameters",
]
