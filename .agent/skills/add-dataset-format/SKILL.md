---
name: add-dataset-format
description: Adds a new input format loader (e.g., Parquet, Excel) to the datasets module.
---

# Add Dataset Format: New Input Loader

This skill guides you through adding a new input format loader to `src/datasets/__init__.py`.

## Architecture Overview

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

**Key File:**
- [__init__.py](file:///app/src/datasets/__init__.py) - All loaders and dispatcher

## Dependencies

| Format | Required Library | Installation |
|--------|-----------------|--------------|
| JSONL | `json` (stdlib) | Built-in |
| JSON | `json` (stdlib) | Built-in |
| CSV | `csv` (stdlib) | Built-in |
| Parquet | `pyarrow>=10.0` | `pip install pyarrow` |
| Excel | `openpyxl>=3.0` | `pip install openpyxl` |

## Supported Formats

| Format | Extensions | Structure | Use Case |
|--------|-----------|-----------|----------|
| JSONL | `.jsonl` | One JSON object per line | Large datasets, streaming |
| JSON | `.json` | Array of objects | Small datasets |
| CSV | `.csv` | Tabular with headers | Spreadsheet exports |

---

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

> [!NOTE]
> Loaders return **raw** records. Field normalization (`text_field` → `"text"`) happens in `load_records()`.

---

## Step 2: Implement Your Loader

Add to `src/datasets/__init__.py`:

```python
def _load_parquet(path: Path) -> list[dict[str, Any]]:
    """Load records from Parquet file.
    
    Requires: pip install pyarrow
    
    Args:
        path: Path to Parquet file
        
    Returns:
        List of record dictionaries
        
    Raises:
        DataLoadError: If file cannot be read
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

---

## Step 3: Register in Dispatcher

Update `detect_format()` and `load_records()`:

### 3.1 Update `detect_format`

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
        raise DataLoadError(
            f"Unknown file format: {suffix}. Supported: .jsonl, .json, .csv, .parquet",
            path
        )
```

### 3.2 Update `load_records` Dispatcher

```python
def load_records(path: Path, text_field: str = "text", ...):
    ...
    format_type = detect_format(path)
    
    if format_type == 'jsonl':
        records = _load_jsonl(path)
    elif format_type == 'json':
        records = _load_json(path)
    elif format_type == 'csv':
        records = _load_csv(path)
    elif format_type == 'parquet':  # Add new format
        records = _load_parquet(path)
    else:
        raise DataLoadError(f"Unknown format: {format_type}", path)
    
    # ... normalization continues below
```

---

## Step 4: Verification

### 4.1 Check Import

```bash
python -c "from src.datasets import load_records; print('OK')"
```

### 4.2 Unit Tests

```python
import pytest
from pathlib import Path
from src.datasets import load_records, detect_format, DataLoadError


def test_load_parquet_basic(tmp_path):
    """Test basic Parquet loading with field normalization."""
    import pandas as pd
    
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
    assert records[0]["id"] == "1"         # Normalized
    assert records[0]["meta"] == "X"       # Preserved


def test_load_parquet_missing_field(tmp_path):
    """Test error when required field missing."""
    import pandas as pd
    
    df = pd.DataFrame({"wrong_field": ["A", "B"]})
    parquet_file = tmp_path / "bad.parquet"
    df.to_parquet(parquet_file)
    
    with pytest.raises(DataLoadError, match="Missing text field"):
        load_records(parquet_file)


def test_detect_format_parquet():
    """Test format detection for Parquet extensions."""
    assert detect_format(Path("data.parquet")) == "parquet"
    assert detect_format(Path("data.pq")) == "parquet"


def test_detect_format_unsupported():
    """Test error for unsupported format."""
    with pytest.raises(DataLoadError, match="Unknown file format"):
        detect_format(Path("data.xlsx"))


def test_load_empty_parquet(tmp_path):
    """Test error on empty file."""
    import pandas as pd
    
    df = pd.DataFrame()
    empty_file = tmp_path / "empty.parquet"
    df.to_parquet(empty_file)
    
    with pytest.raises(DataLoadError, match="empty"):
        load_records(empty_file)
```

### 4.3 Integration Test

```python
def test_parquet_cli_integration(tmp_path):
    """End-to-end CLI test with Parquet input."""
    import pandas as pd
    from typer.testing import CliRunner
    
    # Create test Parquet
    df = pd.DataFrame({
        "id": ["1"],
        "text": ["Sample text for extraction."]
    })
    parquet_file = tmp_path / "test.parquet"
    df.to_parquet(parquet_file)
    
    from src.__main__ import app
    runner = CliRunner()
    
    result = runner.invoke(app, [
        "extract",
        "--input", str(parquet_file),
        "--domain", "default",
        "--limit", "1"
    ])
    
    # Should not fail on format detection
    assert "Unknown file format" not in result.output
```

---

## Field Normalization

All loaders return raw records. `load_records()` normalizes field names:

### Example: CSV with Custom Fields

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

> [!NOTE]
> Original fields are preserved alongside normalized `text` and `id` keys.

---

## CLI Usage

Dataset loaders are used automatically by extraction commands:

```bash
# Auto-detect format from extension
python -m src extract --input data.parquet --domain legal

# Custom field names
python -m src extract --input data.csv --text-field content --id-field doc_id

# Limit records for testing
python -m src extract --input large.jsonl --domain legal --limit 10
```

---

## Key Principles

| Principle | Implementation | Example |
|-----------|---------------|---------|
| **Raw Records** | Loaders return unnormalized dicts | `return df.to_dict('records')` |
| **Lazy Import** | Import heavy libs inside function | `import pandas as pd` inside `_load_parquet` |
| **Clear Errors** | Use `DataLoadError` with path and context | `raise DataLoadError(f"...: {e}", path)` |
| **Encoding** | Use `utf-8` or `utf-8-sig` (BOM) | `encoding='utf-8-sig'` for CSV |

---

## Error Handling Reference

| Exception | When | Action |
|-----------|------|--------|
| `DataLoadError` | Parse failure, empty file, missing field | Fail with path and line number |
| `FileNotFoundError` | File doesn't exist | Raised by `load_records` |
| `ImportError` | Missing optional library | Catch and raise `DataLoadError` with install hint |

---

## Comparison Checklist

Before submitting, verify your loader:

- [ ] Loader function returns `list[dict[str, Any]]`
- [ ] Uses `DataLoadError` for all failures
- [ ] Lazy imports for optional dependencies
- [ ] Extension(s) registered in `detect_format`
- [ ] Dispatcher updated in `load_records`
- [ ] Unit tests for happy path, missing fields, empty file
- [ ] Integration test with CLI
- [ ] Example input/output documented
