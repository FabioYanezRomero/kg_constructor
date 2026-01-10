from __future__ import annotations

"""Group individual graph pickles into larger batches."""

import pickle
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence

import typer
from tqdm import tqdm


def chunked(sequence: Sequence[Path], size: int) -> Iterator[List[Path]]:
    for index in range(0, len(sequence), size):
        yield list(sequence[index : index + size])


def load_graph(path: Path):
    with path.open("rb") as buffer:
        return pickle.load(buffer)


def remove_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


app = typer.Typer(help="Batch NetworkX graph pickles by dataset and split.")


@app.command()
def batch(
    input_dir: Path = typer.Argument(Path("outputs"), help="Directory containing per-record graph pickles."),
    output_dir: Path = typer.Argument(Path("outputs_batched"), help="Directory where batch pickles will be stored."),
    batch_size: int = typer.Option(1000, "--batch-size", min=1, help="Number of graphs per batch file."),
    delete_source: bool = typer.Option(
        False,
        "--delete-source/--keep-source",
        help="Remove original per-record files after batching.",
    ),
) -> None:
    """Group graphs into pickle batches for each dataset split."""

    if not input_dir.exists():
        raise typer.BadParameter(f"Input directory not found: {input_dir}")

    datasets = [d for d in sorted(input_dir.iterdir()) if d.is_dir()]
    total_files = 0
    for dataset_dir in datasets:
        for split_dir in dataset_dir.iterdir():
            if not split_dir.is_dir():
                continue
            files = sorted(split_dir.glob("*.gpickle"))
            if not files:
                continue

            output_split_dir = output_dir / dataset_dir.name / split_dir.name
            output_split_dir.mkdir(parents=True, exist_ok=True)

            progress = tqdm(
                list(chunked(files, batch_size)),
                desc=f"Batching {dataset_dir.name}/{split_dir.name}",
                unit="batch",
            )
            for batch_index, batch_paths in enumerate(progress):
                records = []
                dataset_name = dataset_dir.name.replace("__", "/")
                split_name = split_dir.name
                for path in batch_paths:
                    record_payload = load_graph(path)
                    if isinstance(record_payload, dict) and "graph" in record_payload:
                        record_id = record_payload.get("record_id") or path.stem
                        records.append(
                            {
                                "record_id": record_id,
                                "label": record_payload.get("label"),
                                "label_text": record_payload.get("label_text"),
                                "graph": record_payload.get("graph"),
                            }
                        )
                        dataset_name = record_payload.get("dataset", dataset_name)
                        split_name = record_payload.get("split", split_name)
                    else:
                        record_id = path.stem
                        records.append({"record_id": record_id, "graph": record_payload})
                payload = {
                    "dataset": dataset_name,
                    "split": split_name,
                    "records": records,
                }
                batch_path = output_split_dir / f"batch_{batch_index:05d}.pkl"
                with batch_path.open("wb") as buffer:
                    pickle.dump(payload, buffer)

                if delete_source:
                    for path in batch_paths:
                        remove_file(path)

                total_files += len(batch_paths)

    if delete_source:
        for dataset_dir in datasets:
            for split_dir in dataset_dir.iterdir():
                if split_dir.is_dir() and not any(split_dir.iterdir()):
                    split_dir.rmdir()
            if not any(dataset_dir.iterdir()):
                dataset_dir.rmdir()

    typer.secho(
        f"Batching complete. Processed {total_files} graph files into batches.",
        fg=typer.colors.GREEN,
    )


if __name__ == "__main__":
    app()
