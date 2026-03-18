# Adding a Converter

This skill documents how to add a new output format converter to `kgb/io/writers/`.

## Overview

Converters transform JSON triples into various output formats for use with external tools. The system provides:
- GraphML for graph analysis tools (Gephi, Cytoscape)
- Extensible architecture for custom formats (CSV, RDF, etc.)

## Architecture

```
                        IO Writers Module
    ┌───────────────────────────────────────────────────────────┐
    │                                                           │
    │  io/writers/__init__.py    ← Public exports               │
    │                                                           │
    │  io/writers/graphml.py     ← NetworkX GraphML format      │
    │  ├─ json_to_graphml()        Single file conversion       │
    │  └─ convert_json_directory() Batch conversion             │
    │                                                           │
    │  io/writers/csv.py         ← Your new format              │
    │  ├─ json_to_csv()                                         │
    │  └─ convert_csv_directory()                               │
    │                                                           │
    └───────────────────────────────────────────────────────────┘

Data Flow:
  list[Triple] → Validation → Field Mapping → Format Rendering → File
```

**Key Files:**
- `kgb/io/writers/graphml.py` — Reference implementation (GraphML)
- `kgb/io/writers/__init__.py` — Public exports
- `kgb/io/__init__.py` — Top-level IO exports

## Dependencies

| Format | Required Library | Purpose |
|--------|-----------------|---------|
| CSV | `csv` (stdlib) | Tabular export |
| GraphML | `networkx>=3.0` | Graph format |
| RDF | `rdflib>=6.0` | Semantic web |

## Field Mapping

| Triple Field | GraphML | CSV | RDF |
|--------------|---------|-----|-----|
| `head` | Source node | `head` column | Subject URI |
| `tail` | Target node | `tail` column | Object URI |
| `relation` | Edge label | `relation` column | Predicate URI |
| `inference` | Edge attribute | `inference` column | Annotation |

## Step 1: Understand the Interface

The existing GraphML converter follows this pattern (in `kgb/io/writers/graphml.py`):

```python
def json_to_graphml(
    triples: list[Triple] | list[dict[str, Any]],
    output_path: Path | str | None = None
) -> nx.DiGraph:
    """Convert triples to a NetworkX DiGraph (optionally saved as GraphML).

    - Validates/converts to Triple objects
    - Normalizes entity names (case-insensitive dedup)
    - Stores relation and inference as edge attributes
    - Uses inference.value (not str(inference)) for clean enum serialization
    """
```

Key implementation details from the reference:
- Accept both `list[Triple]` and `list[dict]` inputs
- Use `Triple(**t)` to validate dict inputs, skip invalid with warning
- Entity name canonicalization via `get_canonical_name()` to avoid duplicates
- Preserve `inference` as `.value` string (`"explicit"` / `"contextual"`)

## Step 2: Implement Your Converter

Create `kgb/io/writers/csv.py`:

```python
"""CSV converter for knowledge graph triples."""

from __future__ import annotations
import csv
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ...domains import Triple


def json_to_csv(
    triples: list[Triple] | list[dict[str, Any]],
    output_path: Path | str,
    *,
    include_metadata: bool = True,
    delimiter: str = ","
) -> Path:
    """Convert triples to CSV edge list format."""
    if not triples:
        raise ValueError("Cannot convert empty triple list")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate and convert to Triple objects
    validated: list[Triple] = []
    for t in triples:
        try:
            if isinstance(t, Triple):
                validated.append(t)
            else:
                validated.append(Triple(**t))
        except ValidationError as e:
            print(f"Warning: Skipping invalid triple: {e}")
            continue

    if not validated:
        raise ValueError("No valid triples after validation")

    # Determine columns
    fieldnames = ["head", "relation", "tail"]
    if include_metadata:
        fieldnames.extend(["inference", "justification"])

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()

        for triple in validated:
            row = {
                "head": triple.head,
                "relation": triple.relation,
                "tail": triple.tail,
            }
            if include_metadata:
                row.update({
                    "inference": triple.inference.value,
                    "justification": triple.justification or "",
                })
            writer.writerow(row)

    return output_path


def convert_csv_directory(
    input_dir: Path | str,
    output_dir: Path | str,
    *,
    include_metadata: bool = True
) -> list[Path]:
    """Convert all JSON files to CSV format."""
    import json

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = []
    for json_file in input_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            output_path = output_dir / f"{json_file.stem}.csv"
            json_to_csv(data, output_path, include_metadata=include_metadata)
            print(f"Converted: {json_file.name} -> {output_path.name}")
            csv_files.append(output_path)
        except ValueError as e:
            print(f"Skipped {json_file.name}: {e}")

    return csv_files
```

## Step 3: Register in Module

Update `kgb/io/writers/__init__.py`:

```python
from .graphml import json_to_graphml, convert_json_directory
from .csv import json_to_csv, convert_csv_directory

__all__ = [
    "json_to_graphml",
    "convert_json_directory",
    "json_to_csv",
    "convert_csv_directory",
]
```

Update `kgb/io/__init__.py` to export the new functions:

```python
from .readers import load_records, detect_format, DataLoadError
from .writers import json_to_graphml, convert_json_directory, json_to_csv, convert_csv_directory

__all__ = [
    "load_records",
    "detect_format",
    "DataLoadError",
    "json_to_graphml",
    "convert_json_directory",
    "json_to_csv",
    "convert_csv_directory",
]
```

## Step 4: Add CLI Support

Update the `convert` command in `kgb/__main__.py` to support the new format:

```python
@app.command()
def convert(
    input_dir: Path = typer.Option(..., "--input", "-i", exists=True),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o"),
    format: str = typer.Option("graphml", "--format", "-f"),
):
    """Convert JSON triples to specified format."""
    from .io.writers import convert_json_directory, convert_csv_directory

    out_dir = output_dir or input_dir.parent / format

    if format == "graphml":
        files = convert_json_directory(input_dir, out_dir)
    elif format == "csv":
        files = convert_csv_directory(input_dir, out_dir)
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[green]Converted {len(files)} files to {format}[/green]")
```

## Step 5: Verify

### Check Import

```bash
python -c "from kgb.io.writers.csv import json_to_csv; print('OK')"
```

### Unit Tests

```python
def test_json_to_csv_basic(tmp_path):
    from kgb.io.writers.csv import json_to_csv
    from kgb.domains import Triple

    triples = [
        Triple(head="Alice", relation="knows", tail="Bob"),
        Triple(head="Bob", relation="works_at", tail="Acme"),
    ]

    output = tmp_path / "graph.csv"
    result = json_to_csv(triples, output)

    assert result.exists()

    import csv
    with open(result) as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert rows[0]["head"] == "Alice"
    assert rows[0]["inference"] == "explicit"


def test_json_to_csv_empty_list(tmp_path):
    from kgb.io.writers.csv import json_to_csv
    import pytest

    with pytest.raises(ValueError, match="empty"):
        json_to_csv([], tmp_path / "empty.csv")


def test_json_to_csv_from_dicts(tmp_path):
    from kgb.io.writers.csv import json_to_csv
    import csv

    dicts = [{"head": "X", "relation": "r", "tail": "Y", "inference": "explicit"}]
    csv_path = tmp_path / "roundtrip.csv"
    json_to_csv(dicts, csv_path)

    with open(csv_path) as f:
        row = next(csv.DictReader(f))

    assert row["head"] == "X"
    assert row["relation"] == "r"
    assert row["tail"] == "Y"
```

## Key Principles

| Principle | Implementation |
|-----------|---------------|
| **Accept `list[Triple]` and `list[dict]`** | Use isinstance check with `Triple(**t)` validation |
| **Use `.value` for enums** | `triple.inference.value` → `"explicit"` (not `"InferenceType.EXPLICIT"`) |
| **Create Directories** | `output_path.parent.mkdir(parents=True, exist_ok=True)` |
| **Skip Invalid Data** | Log warning and continue |

## Error Handling

| Exception | When | Action |
|-----------|------|--------|
| `ValueError` | Empty input or no valid triples | Fail with message |
| `ValidationError` | Triple validation fails | Log, skip, continue |
| `FileNotFoundError` | Input directory doesn't exist | Fail loudly |

## Files to Create/Modify

| File | Action |
|------|--------|
| `kgb/io/writers/csv.py` | Create — converter implementation |
| `kgb/io/writers/__init__.py` | Modify — add imports |
| `kgb/io/__init__.py` | Modify — add exports |
| `kgb/__main__.py` | Modify — add format dispatch (optional) |

## Verification Checklist

- [ ] Implementation validates Triple inputs
- [ ] Uses `inference.value` for enum serialization
- [ ] Tests pass (unit + round-trip)
- [ ] Batch function for directory processing
- [ ] Registered in `kgb/io/writers/__init__.py`
- [ ] Exported in `kgb/io/__init__.py`
- [ ] CLI format dispatch works (if added)
