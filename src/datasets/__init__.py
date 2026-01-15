"""Data loaders for the extraction pipeline.

Supports multiple input formats:
- JSONL (recommended): One JSON object per line
- JSON: Array of objects
- CSV: Comma-separated values

All formats should have at least 'id' and 'text' fields.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterator


class DataLoadError(Exception):
    """Raised when data loading fails."""
    def __init__(self, message: str, path: Path, line_number: int | None = None):
        super().__init__(message)
        self.path = path
        self.line_number = line_number


def detect_format(path: Path) -> str:
    """Detect file format from extension.
    
    Returns:
        One of: 'jsonl', 'json', 'csv'
        
    Raises:
        DataLoadError: If format cannot be determined
    """
    suffix = path.suffix.lower()
    if suffix == '.jsonl':
        return 'jsonl'
    elif suffix == '.json':
        return 'json'
    elif suffix == '.csv':
        return 'csv'
    else:
        raise DataLoadError(
            f"Unknown file format: {suffix}. Supported: .jsonl, .json, .csv",
            path
        )


def load_records(
    path: Path,
    text_field: str = "text",
    id_field: str = "id",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load records from a file.
    
    Supports JSONL, JSON, and CSV formats (auto-detected by extension).
    
    Args:
        path: Path to input file
        text_field: Name of the field containing text (default: "text")
        id_field: Name of the field containing record IDs (default: "id")
        limit: Optional limit on number of records
        
    Returns:
        List of records, each with at least 'id' and 'text' keys (normalized)
        
    Raises:
        DataLoadError: If file cannot be loaded or parsed
    """
    if not path.exists():
        raise DataLoadError(f"File not found: {path}", path)
    
    format_type = detect_format(path)
    
    if format_type == 'jsonl':
        records = _load_jsonl(path)
    elif format_type == 'json':
        records = _load_json(path)
    else:  # csv
        records = _load_csv(path)
    
    # Normalize field names and validate
    normalized = []
    for i, record in enumerate(records):
        if limit and len(normalized) >= limit:
            break
            
        if text_field not in record:
            raise DataLoadError(
                f"Missing text field '{text_field}' in record {i}",
                path,
                line_number=i + 1
            )
        if id_field not in record:
            raise DataLoadError(
                f"Missing id field '{id_field}' in record {i}",
                path,
                line_number=i + 1
            )
        
        # Normalize to standard field names
        normalized_record = dict(record)
        if text_field != "text":
            normalized_record["text"] = record[text_field]
        if id_field != "id":
            normalized_record["id"] = record[id_field]
        
        normalized.append(normalized_record)
    
    return normalized


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load records from JSONL file (one JSON object per line)."""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise DataLoadError(
                    f"Invalid JSON on line {line_num}: {e}",
                    path,
                    line_number=line_num
                ) from e
    return records


def _load_json(path: Path) -> list[dict[str, Any]]:
    """Load records from JSON file (array of objects)."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataLoadError(f"Invalid JSON: {e}", path) from e
    
    if not isinstance(data, list):
        raise DataLoadError("JSON file must contain an array of objects", path)
    
    return data


def _load_csv(path: Path) -> list[dict[str, Any]]:
    """Load records from CSV file."""
    records = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    return records


__all__ = ["load_records", "detect_format", "DataLoadError"]
