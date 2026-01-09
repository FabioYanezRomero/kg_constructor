"""Hugging Face dataset builder for legal case background summaries."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Dict, Iterable, Tuple

import datasets

_DESCRIPTION = """Dataset exposing the background section of legal case summaries."""
_CITATION = """"""


class LegalBackgroundConfig(datasets.BuilderConfig):
    """Builder configuration allowing optional sampling of the dataset."""

    def __init__(self, **kwargs) -> None:
        super().__init__(version=datasets.Version("1.0.0"), **kwargs)


class LegalBackground(datasets.GeneratorBasedBuilder):
    """Generator-based dataset that reads the local CSV file."""

    BUILDER_CONFIG_CLASS = LegalBackgroundConfig
    BUILDER_CONFIGS = [LegalBackgroundConfig(name="default", description=_DESCRIPTION)]
    DEFAULT_CONFIG_NAME = "default"

    def _info(self) -> datasets.DatasetInfo:
        features = datasets.Features(
            {
                "id": datasets.Value("string"),
                "text": datasets.Value("string"),
                "decision_label": datasets.Value("string"),
                "label": datasets.Value("int32"),
                "reasoning": datasets.Value("string"),
                "title": datasets.Value("string"),
            }
        )
        return datasets.DatasetInfo(
            description=_DESCRIPTION,
            features=features,
            citation=_CITATION,
            homepage="",
        )

    def _split_generators(self, dl_manager: datasets.DownloadManager) -> Iterable[datasets.SplitGenerator]:
        csv_path = self._resolve_csv_path()
        return [
            datasets.SplitGenerator(name=datasets.Split.TRAIN, gen_kwargs={"filepath": csv_path}),
        ]

    def _generate_examples(self, filepath: Path) -> Iterable[Tuple[int, Dict[str, str]]]:
        rows = self._load_rows(filepath)
        label_map = self._build_label_map(rows)

        for index, row in enumerate(rows):
            decision_label = row["decision_label"].strip()
            yield index, {
                "id": row["id"].strip(),
                "text": self._clean_text(row["background"]),
                "decision_label": decision_label,
                "label": label_map[decision_label],
                "reasoning": self._clean_text(row["reasoning"]),
                "title": row["title"].strip(),
            }

    @staticmethod
    def _load_rows(filepath: Path) -> list[Dict[str, str]]:
        with filepath.open(encoding="utf-8") as buffer:
            reader = csv.DictReader(buffer, delimiter="|")
            return [dict(row) for row in reader]

    @staticmethod
    def _build_label_map(rows: Iterable[Dict[str, str]]) -> Dict[str, int]:
        labels = sorted({row["decision_label"].strip() for row in rows})
        return {label: index for index, label in enumerate(labels)}

    @staticmethod
    def _clean_text(value: str) -> str:
        text = value.strip()
        # Collapse consecutive whitespace to single spaces for stability.
        return " ".join(text.split())

    def _resolve_csv_path(self) -> Path:
        """Locate the source CSV, allowing overrides via environment variables."""

        env_path = os.getenv("LEGAL_BACKGROUND_SOURCE")
        if env_path:
            candidate = Path(env_path).expanduser()
            if candidate.exists():
                return candidate

        search_roots = [Path.cwd()] + list(Path.cwd().parents)
        for root in search_roots:
            candidate = root / "data" / "legal" / "sample_data.csv"
            if candidate.exists():
                return candidate

        # Fallback to a path relative to this file in case it is executed in-place.
        local_candidate = Path(__file__).resolve().with_name("sample_data.csv")
        if local_candidate.exists():
            return local_candidate

        raise FileNotFoundError(
            "Unable to locate sample_data.csv. Set LEGAL_BACKGROUND_SOURCE to the CSV path."
        )


# Allow datasets.load_dataset to locate the builder when the module is executed.
if __name__ == "__main__":
    builder = LegalBackground()
    builder.download_and_prepare()
