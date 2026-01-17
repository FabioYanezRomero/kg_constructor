---
name: add-converter
description: Adds a new output format converter (e.g., CSV, RDF) to the converters module.
---

# Add Converter: New Export Format

This skill guides you through adding a new output format converter to `src/converters/`.

## Architecture Overview

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
- [graphml.py](file:///app/src/converters/graphml.py) - NetworkX graph format (Gephi, Cytoscape)
- [__init__.py](file:///app/src/converters/__init__.py) - Public exports

## Dependencies

| Format | Required Library | Version | Purpose |
|--------|-----------------|---------|---------|
| CSV | `csv` (stdlib) | - | Tabular export |
| GraphML | `networkx>=3.0` | Latest | Graph format |
| RDF/Turtle | `rdflib>=6.0` | Latest | Semantic web |
| JSON-LD | `pyld>=2.0` | Latest | Linked data |

## Field Mapping

| Triple Field | GraphML | CSV | RDF |
|--------------|---------|-----|-----|
| `head` | Source node | `head` column | Subject URI |
| `tail` | Target node | `tail` column | Object URI |
| `relation` | Edge label | `relation` column | Predicate URI |
| `inference` | Edge attribute | `inference` column | Annotation |

---

## Step 1: Understand the Interface

All converters should follow this pattern:

```python
def json_to_<format>(
    triples: list[Triple] | list[dict[str, Any]],
    output_path: Path | str,
    *,
    include_metadata: bool = True,
    **kwargs: Any
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
        ValidationError: If triple validation fails
    """
```

---

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
    """Convert triples to CSV edge list format.
    
    Args:
        triples: List of Triple objects or dictionaries
        output_path: Destination CSV file path
        include_metadata: Include inference and char position columns
        delimiter: Field delimiter (default: comma)
        
    Returns:
        Path to created CSV file
        
    Raises:
        ValueError: If triples list is empty or no valid triples
    """
    if not triples:
        raise ValueError("Cannot convert empty triple list")
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Validate and convert to Triple objects
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
    
    # 2. Determine CSV columns
    fieldnames = ["head", "relation", "tail"]
    if include_metadata:
        fieldnames.extend(["inference", "char_start", "char_end"])
    
    # 3. Write CSV file
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
    """Convert all JSON files in a directory to CSV format.
    
    Args:
        input_dir: Directory containing JSON files
        output_dir: Directory to save CSV files
        include_metadata: Include extra columns
        
    Returns:
        List of paths to created CSV files
    """
    import json
    
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_files = []
    
    for json_file in input_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                print(f"Skipping {json_file.name}: Not a list")
                continue
            
            output_path = output_dir / f"{json_file.stem}.csv"
            json_to_csv(data, output_path, include_metadata=include_metadata)
            
            print(f"Converted: {json_file.name} → {output_path.name}")
            csv_files.append(output_path)
            
        except ValueError as e:
            print(f"Skipped {json_file.name}: {e}")
        except Exception as e:
            print(f"Error {json_file.name}: {e}")
    
    return csv_files


__all__ = ["json_to_csv", "convert_csv_directory"]
```

---

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

---

## Step 4: Add CLI Subcommand

Update `src/__main__.py` to add format dispatch:

```python
@app.command()
def convert(
    input_dir: Path = typer.Option(..., "--input", "-i", exists=True),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o"),
    format: str = typer.Option("graphml", "--format", "-f", help="Output format: graphml, csv"),
):
    """Convert JSON triples to specified format.
    
    \b
    Examples:
        python -m src convert --input outputs/extracted_json --format csv
    """
    from .converters import convert_json_directory, convert_csv_directory
    
    out_dir = output_dir or input_dir.parent / format
    
    try:
        if format == "graphml":
            files = convert_json_directory(input_dir, out_dir)
        elif format == "csv":
            files = convert_csv_directory(input_dir, out_dir)
        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            console.print("Supported: graphml, csv")
            raise typer.Exit(code=1)
        
        console.print(f"\n[green]✓ Converted {len(files)} files to {format}[/green]")
        console.print(f"Output: {out_dir}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
```

> [!TIP]
> See the existing `convert` command in [__main__.py](file:///app/src/__main__.py) for structure reference.

---

## Step 5: Verification

### 5.1 Check Import

```bash
python -c "from src.converters import json_to_csv; print('OK')"
```

### 5.2 Unit Tests

```python
import pytest
from pathlib import Path
from src.converters.csv import json_to_csv
from src.domains import Triple


def test_json_to_csv_basic(tmp_path):
    """Test basic CSV conversion."""
    triples = [
        Triple(head="Alice", relation="knows", tail="Bob"),
        Triple(head="Bob", relation="works_at", tail="Acme"),
    ]
    
    output = tmp_path / "graph.csv"
    result = json_to_csv(triples, output)
    
    assert result.exists()
    
    # Verify CSV structure
    import csv
    with open(result) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) == 2
    assert rows[0]["head"] == "Alice"
    assert rows[0]["relation"] == "knows"
    assert rows[0]["tail"] == "Bob"


def test_json_to_csv_with_metadata(tmp_path):
    """Test metadata columns are included."""
    triples = [Triple(head="A", relation="r", tail="B", inference="explicit")]
    
    output = tmp_path / "meta.csv"
    json_to_csv(triples, output, include_metadata=True)
    
    import csv
    with open(output) as f:
        reader = csv.DictReader(f)
        row = next(reader)
    
    assert "inference" in row
    assert row["inference"] == "explicit"


def test_json_to_csv_empty_list(tmp_path):
    """Test error on empty input."""
    with pytest.raises(ValueError, match="empty"):
        json_to_csv([], tmp_path / "empty.csv")


def test_json_to_csv_invalid_triples(tmp_path):
    """Test that invalid triples are skipped."""
    triples = [
        {"head": "A", "relation": "r", "tail": "B"},  # Valid
        {"head": "", "relation": "r", "tail": "C"},   # Invalid (empty head)
    ]
    
    output = tmp_path / "partial.csv"
    result = json_to_csv(triples, output)
    
    import csv
    with open(result) as f:
        rows = list(csv.DictReader(f))
    
    assert len(rows) == 1  # Only valid triple


def test_json_to_csv_round_trip(tmp_path):
    """Test data preservation through conversion."""
    original = [Triple(head="X", relation="related_to", tail="Y")]
    
    csv_path = tmp_path / "roundtrip.csv"
    json_to_csv(original, csv_path)
    
    import csv
    with open(csv_path) as f:
        row = next(csv.DictReader(f))
    
    assert row["head"] == original[0].head
    assert row["relation"] == original[0].relation
    assert row["tail"] == original[0].tail
```

### 5.3 Integration Test

```python
def test_convert_cli_integration(tmp_path):
    """End-to-end CLI test."""
    import json
    from typer.testing import CliRunner
    from src.__main__ import app
    
    # Create test input
    input_dir = tmp_path / "json"
    input_dir.mkdir()
    (input_dir / "test.json").write_text(json.dumps([
        {"head": "A", "relation": "r", "tail": "B"}
    ]))
    
    runner = CliRunner()
    result = runner.invoke(app, [
        "convert",
        "--input", str(input_dir),
        "--output", str(tmp_path / "csv"),
        "--format", "csv"
    ])
    
    assert result.exit_code == 0
    assert (tmp_path / "csv" / "test.csv").exists()
```

---

## Example Output

### Input (JSON)
```json
[
  {"head": "Alice", "relation": "knows", "tail": "Bob", "inference": "explicit"},
  {"head": "Bob", "relation": "works_at", "tail": "Acme Corp", "inference": "contextual"}
]
```

### Output (CSV)
```csv
head,relation,tail,inference,char_start,char_end
Alice,knows,Bob,explicit,,
Bob,works_at,Acme Corp,contextual,,
```

### Output (GraphML)
```xml
<?xml version='1.0' encoding='utf-8'?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="relation" for="edge" attr.name="relation" attr.type="string"/>
  <graph id="G" edgedefault="directed">
    <node id="Alice"/>
    <node id="Bob"/>
    <edge source="Alice" target="Bob">
      <data key="relation">knows</data>
    </edge>
  </graph>
</graphml>
```

---

## Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_metadata` | bool | True | Include inference/position columns |
| `delimiter` | str | "," | CSV field separator |
| `output_dir` | Path | Auto | Output directory |

---

## Key Principles

| Principle | Implementation | Example |
|-----------|---------------|---------|
| **Accept `list[Triple]`** | Use isinstance check | `if isinstance(t, Triple): validated.append(t)` |
| **Handle Dictionaries** | Convert with validation | `Triple(**t)` with try-except |
| **Create Directories** | Use mkdir with parents | `output_path.parent.mkdir(parents=True, exist_ok=True)` |
| **Skip Invalid Data** | Log and continue | `print(f"Warning: Skipping: {e}")` |
| **Return Path** | Enable chaining | `return output_path` |

---

## Error Handling Reference

| Exception | When | Action |
|-----------|------|--------|
| `ValueError` | Empty input or no valid triples | Fail with descriptive message |
| `ValidationError` | Triple field validation fails | Log warning, skip triple, continue |
| `FileNotFoundError` | Input directory doesn't exist | Fail loudly |
| `PermissionError` | Cannot write output file | Re-raise with context |

---

## Comparison Checklist

Before submitting, verify your converter matches quality standards:

- [ ] Complete implementation with validation
- [ ] Type hints for all parameters
- [ ] Docstring with Args, Returns, Raises
- [ ] Error handling for empty/invalid input
- [ ] Batch processing function
- [ ] Unit tests with tmp_path
- [ ] Integration test for CLI
- [ ] Registered in `__init__.py`
- [ ] CLI subcommand with format dispatch
- [ ] Example input/output shown
- [ ] Field mapping documented
