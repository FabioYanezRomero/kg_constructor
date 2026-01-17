# Adding a Dataset Format

This skill documents how to add a new input format loader to `src/datasets/__init__.py`.

## Overview

Dataset loaders parse input files and return normalized records for extraction. The system provides:
- JSONL for large datasets (streaming-friendly)
- JSON for small datasets
- CSV for spreadsheet exports
- Extensible architecture for custom formats

## Architecture

```
                        Datasets Module
    ┌───────────────────────────────────────────────────────────┐
    │                                                           │
    │  __init__.py                                              │
    │  ├─ DataLoadError         # Custom exception              │
    │  ├─ detect_format()       # Auto-detect from extension    │
    │  ├─ load_records()        # Main dispatcher + normalizer  │
    │  │                                                        │
    │  ├─ _load_jsonl()         # JSONL loader (one obj/line)   │
    │  ├─ _load_json()          # JSON loader (array of objs)   │
    │  ├─ _load_csv()           # CSV loader (tabular)          │
    │  └─ _load_<format>()      # Your new loader               │
    │                                                           │
    └───────────────────────────────────────────────────────────┘

Data Flow:
  File → detect_format() → _load_<format>() → load_records() → Normalized Records
```

## Dependencies

| Format | Required Library | Installation |
|--------|-----------------|--------------|
| JSONL | `json` (stdlib) | Built-in |
| JSON | `json` (stdlib) | Built-in |
| CSV | `csv` (stdlib) | Built-in |
| Parquet | `pyarrow>=10.0` | `pip install pyarrow` |
| Excel | `openpyxl>=3.0` | `pip install openpyxl` |

## DataLoadError Class

The custom exception used by all loaders:

```python
class DataLoadError(Exception):
    """Raised when data loading fails."""
    def __init__(self, message: str, path: Path, line_number: int | None = None):
        super().__init__(message)
        self.path = path
        self.line_number = line_number
```

---

## Step 1: Understand the Interface

All loaders follow this pattern:

```python
def _load_<format>(path: Path) -> list[dict[str, Any]]:
    """Load records from <Format> file.
    
    Args:
        path: Path to input file
        
    Returns:
        List of record dictionaries (unnormalized)
        
    Raises:
        DataLoadError: If file cannot be parsed
    """
```

> Loaders return **raw** records. Field normalization happens in `load_records()`.

## Step 2: Implement Your Loader

Add to `src/datasets/__init__.py`:

```python
def _load_parquet(path: Path) -> list[dict[str, Any]]:
    """Load records from Parquet file.
    
    Requires: pip install pyarrow
    """
    try:
        import pandas as pd
    except ImportError:
        raise DataLoadError(
            "Parquet support requires pandas: pip install pandas pyarrow",
            path
        )
    
    try:
        df = pd.read_parquet(path)
    except Exception as e:
        raise DataLoadError(f"Failed to read Parquet file: {e}", path) from e
    
    if df.empty:
        raise DataLoadError(f"Parquet file is empty", path)
    
    return df.to_dict('records')
```

## Step 3: Register in Dispatcher

### Update `detect_format`

```python
def detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == '.jsonl':
        return 'jsonl'
    elif suffix == '.json':
        return 'json'
    elif suffix == '.csv':
        return 'csv'
    elif suffix in ('.parquet', '.pq'):  # Add new extensions
        return 'parquet'
    else:
        raise DataLoadError(f"Unknown file format: {suffix}", path)
```

### Update `load_records` Dispatcher

```python
if format_type == 'jsonl':
    records = _load_jsonl(path)
elif format_type == 'json':
    records = _load_json(path)
elif format_type == 'csv':
    records = _load_csv(path)
elif format_type == 'parquet':  # Add new format
    records = _load_parquet(path)
```

## Step 4: Verify

### Check Import

```bash
python -c "from src.datasets import load_records; print('OK')"
```

### Unit Test

```python
def test_load_parquet_basic(tmp_path):
    import pandas as pd
    from src.datasets import load_records
    
    df = pd.DataFrame({
        "doc_id": ["1", "2"],
        "content": ["Text A", "Text B"],
        "meta": ["X", "Y"]
    })
    
    parquet_file = tmp_path / "test.parquet"
    df.to_parquet(parquet_file)
    
    records = load_records(
        parquet_file,
        text_field="content",
        id_field="doc_id"
    )
    
    assert len(records) == 2
    assert records[0]["text"] == "Text A"  # Normalized
    assert records[0]["id"] == "1"


def test_load_parquet_missing_field(tmp_path):
    import pandas as pd
    from src.datasets import load_records, DataLoadError
    import pytest
    
    df = pd.DataFrame({"wrong_field": ["A", "B"]})
    parquet_file = tmp_path / "bad.parquet"
    df.to_parquet(parquet_file)
    
    with pytest.raises(DataLoadError, match="Missing text field"):
        load_records(parquet_file)


def test_detect_format_parquet():
    from src.datasets import detect_format
    from pathlib import Path
    
    assert detect_format(Path("data.parquet")) == "parquet"
    assert detect_format(Path("data.pq")) == "parquet"
```

## Field Normalization

All loaders return raw records. `load_records()` normalizes field names:

**Input (`data.csv`):**
```csv
doc_id,body,author
1,"Sample text","Alice"
```

**Load Call:**
```python
records = load_records("data.csv", text_field="body", id_field="doc_id")
```

**Output:**
```python
[{"text": "Sample text", "id": "1", "body": "Sample text", "doc_id": "1", "author": "Alice"}]
```

Original fields are preserved alongside normalized `text` and `id` keys.

## CLI Usage

```bash
# Auto-detect format from extension
python -m src extract --input data.parquet --domain legal

# Custom field names
python -m src extract --input data.csv --text-field content --id-field doc_id

# Limit records for testing
python -m src extract --input large.jsonl --domain legal --limit 10
```

## Key Principles

| Principle | Implementation |
|-----------|---------------|
| **Raw Records** | Loaders return unnormalized dicts |
| **Lazy Import** | Import heavy libs inside function |
| **Clear Errors** | Use `DataLoadError` with path and context |
| **Encoding** | Use `utf-8` or `utf-8-sig` (BOM) for CSV |

## Error Handling

| Exception | When | Action |
|-----------|------|--------|
| `DataLoadError` | Parse failure, empty file, missing field | Fail with path |
| `FileNotFoundError` | File doesn't exist | Raised by `load_records` |
| `ImportError` | Missing optional library | Catch, raise `DataLoadError` |

## Verification Checklist

- [ ] Loader returns `list[dict[str, Any]]`
- [ ] Uses `DataLoadError` for all failures
- [ ] Lazy imports for optional dependencies
- [ ] Extension(s) in `detect_format`
- [ ] Dispatcher updated in `load_records`
- [ ] Tests for happy path, errors, empty file
