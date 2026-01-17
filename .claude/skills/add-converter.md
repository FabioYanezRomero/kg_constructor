# Adding a Converter

This skill documents how to add a new output format converter to `src/converters/`.

## Overview

Converters transform JSON triples into various output formats for use with external tools. The system provides:
- GraphML for graph analysis tools (Gephi, Cytoscape)
- CSV for spreadsheets and databases
- Extensible architecture for custom formats

## Architecture

```
                      Converters Module
    ┌───────────────────────────────────────────────────────────┐
    │                                                           │
    │  graphml.py            csv.py             rdf.py          │
    │  ├─ Uses: NetworkX     ├─ Uses: stdlib    ├─ Uses: rdflib │
    │  ├─ For: Gephi         ├─ For: Excel      ├─ For: SPARQL  │
    │  └─ For: Cytoscape     └─ For: Databases  └─ For: Protégé │
    │                                                           │
    │  your_format.py                                           │
    │  ├─ Uses: <library>                                       │
    │  └─ For: <tool>                                           │
    │                                                           │
    └───────────────────────────────────────────────────────────┘

Data Flow:
  list[Triple] → Validation → Field Mapping → Format Rendering → File
```

**Key Files:**
- `src/converters/graphml.py` - NetworkX graph format
- `src/converters/__init__.py` - Public exports

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

All converters should follow this pattern:

```python
def json_to_<format>(
    triples: list[Triple] | list[dict[str, Any]],
    output_path: Path | str,
    *,
    include_metadata: bool = True,
) -> Path:
    """Convert triples to <format>.
    
    Args:
        triples: List of Triple objects or dictionaries
        output_path: Destination file path
        include_metadata: Include inference type and positions
        
    Returns:
        Path to created file
        
    Raises:
        ValueError: If triples list is empty
    """
```

## Step 2: Implement Your Converter

Create `src/converters/csv.py`:

```python
"""CSV converter for knowledge graph triples."""

from __future__ import annotations
import csv
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ..domains import Triple


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
        fieldnames.extend(["inference", "char_start", "char_end"])
    
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
                    "inference": triple.inference.value if triple.inference else "",
                    "char_start": triple.char_start if triple.char_start is not None else "",
                    "char_end": triple.char_end if triple.char_end is not None else "",
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
            print(f"Converted: {json_file.name} → {output_path.name}")
            csv_files.append(output_path)
        except ValueError as e:
            print(f"Skipped {json_file.name}: {e}")
    
    return csv_files
```

## Step 3: Register in Module

Update `src/converters/__init__.py`:

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

## Step 4: Add CLI Subcommand

Update `src/__main__.py`:

```python
@app.command()
def convert(
    input_dir: Path = typer.Option(..., "--input", "-i", exists=True),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o"),
    format: str = typer.Option("graphml", "--format", "-f"),
):
    """Convert JSON triples to specified format."""
    from .converters import convert_json_directory, convert_csv_directory
    
    out_dir = output_dir or input_dir.parent / format
    
    if format == "graphml":
        files = convert_json_directory(input_dir, out_dir)
    elif format == "csv":
        files = convert_csv_directory(input_dir, out_dir)
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(code=1)
    
    console.print(f"\n[green]✓ Converted {len(files)} files to {format}[/green]")
```

## Step 5: Verify

### Check Import

```bash
python -c "from src.converters import json_to_csv; print('OK')"
```

### Unit Test

```python
def test_json_to_csv_basic(tmp_path):
    from src.converters.csv import json_to_csv
    from src.domains import Triple
    
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


def test_json_to_csv_empty_list(tmp_path):
    from src.converters.csv import json_to_csv
    import pytest
    
    with pytest.raises(ValueError, match="empty"):
        json_to_csv([], tmp_path / "empty.csv")


def test_json_to_csv_round_trip(tmp_path):
    """Verify data preservation through conversion."""
    from src.converters.csv import json_to_csv
    from src.domains import Triple
    import csv
    
    original = [Triple(head="X", relation="related_to", tail="Y")]
    csv_path = tmp_path / "roundtrip.csv"
    json_to_csv(original, csv_path)
    
    with open(csv_path) as f:
        row = next(csv.DictReader(f))
    
    assert row["head"] == original[0].head
    assert row["relation"] == original[0].relation
    assert row["tail"] == original[0].tail
```

## Example Output

### Input (JSON)
```json
[{"head": "Alice", "relation": "knows", "tail": "Bob", "inference": "explicit"}]
```

### Output (CSV)
```csv
head,relation,tail,inference,char_start,char_end
Alice,knows,Bob,explicit,,
```

## Key Principles

| Principle | Implementation |
|-----------|---------------|
| **Accept `list[Triple]`** | Use isinstance check with validation |
| **Handle Dictionaries** | Convert with `Triple(**t)` + try-except |
| **Create Directories** | `output_path.parent.mkdir(parents=True, exist_ok=True)` |
| **Skip Invalid Data** | Log warning and continue |

## Error Handling

| Exception | When | Action |
|-----------|------|--------|
| `ValueError` | Empty input or no valid triples | Fail with message |
| `ValidationError` | Triple validation fails | Log, skip, continue |
| `FileNotFoundError` | Input directory doesn't exist | Fail loudly |

## Verification Checklist

Before submitting, verify your converter:

- [ ] Implementation includes validation
- [ ] Tests pass (unit + round-trip)
- [ ] Batch function for directory processing
- [ ] Registered in `__init__.py`
- [ ] CLI format dispatch works
- [ ] Example output verified
