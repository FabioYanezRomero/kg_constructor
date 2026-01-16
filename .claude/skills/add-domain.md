# Adding a Knowledge Domain

This skill documents how to add a new knowledge domain to `src/domains/`.

## Overview

Domains are bundled resource sets containing prompts and few-shot examples for extraction and augmentation. The system provides:
- Registry pattern with `@domain()` decorator
- Automatic resource discovery via `inspect.getfile()`
- Strategy-based augmentation folders

## Architecture

```
                          Domains Module
    ┌───────────────────────────────────────────────────────────┐
    │                                                           │
    │  registry.py                base.py                       │
    │  ├─ @domain()               ├─ KnowledgeDomain            │
    │  ├─ register_domain()       ├─ DomainResourceError        │
    │  ├─ get_domain()            └─ ExtractionResources        │
    │  └─ list_available_domains()                              │
    │                                                           │
    │  legal/                     default/                      │
    │  ├─ __init__.py             ├─ __init__.py                │
    │  ├─ extraction/             ├─ extraction/                │
    │  └─ augmentation/           └─ augmentation/              │
    │                                                           │
    └───────────────────────────────────────────────────────────┘

Registration Flow:
  @domain("name") → register_domain() → _DOMAIN_REGISTRY → get_domain()
```

## Dependencies

| Component | Library | Purpose |
|-----------|---------|---------|
| Schema validation | `pydantic>=2.0` | Triple validation |
| Extraction | `langextract>=0.1` | Prompt framework |
| Resource loading | `pathlib` (stdlib) | File operations |

## Directory Structure

```text
src/domains/<domain_name>/
├── __init__.py                 # Domain class with @domain decorator
├── extraction/
│   ├── prompt_open.txt         # Open extraction prompt
│   ├── prompt_constrained.txt  # Type-constrained extraction prompt
│   └── examples.json           # Few-shot extraction examples
├── augmentation/
│   └── connectivity/           # Strategy folder
│       ├── prompt.txt
│       └── examples.json
└── schema.json                 # Optional: type constraints
```

## Step 1: Create Resource Files

### Extraction Prompts

Create `extraction/prompt_open.txt`:

```text
Extract all knowledge graph triples from the following text.
Focus on explicit relationships between entities.
```

> **Important:** Do NOT include output format instructions. The `langextract` framework generates format instructions from examples.

### Extraction Examples (`extraction/examples.json`)

```json
[
  {
    "text": "PharmaCorp developed X-123 on January 5th.",
    "extractions": [
      {
        "extraction_class": "Triple",
        "extraction_text": "PharmaCorp developed X-123",
        "char_start": 0,
        "char_end": 26,
        "attributes": {
          "head": "PharmaCorp",
          "relation": "developed",
          "tail": "X-123",
          "inference": "explicit"
        }
      }
    ]
  }
]
```

### Augmentation Examples (`augmentation/connectivity/examples.json`)

```json
[
  {
    "input": {
      "text": "Alice knows Bob. Bob works at Acme.",
      "components": [
        {"entities": ["Alice", "Bob"]},
        {"entities": ["Bob", "Acme"]}
      ]
    },
    "output": [
      {
        "head": "Alice",
        "relation": "connected_to",
        "tail": "Acme",
        "inference": "contextual",
        "justification": "Alice is connected to Acme through Bob."
      }
    ]
  }
]
```

## Step 2: Implement the Domain Class

Create `src/domains/medical/__init__.py`:

```python
"""Medical knowledge domain for clinical document analysis."""

from __future__ import annotations
from ..base import KnowledgeDomain
from ..registry import domain


@domain("medical")  # This ID is used with --domain CLI flag
class MedicalDomain(KnowledgeDomain):
    """Domain for medical and clinical document analysis.
    
    Focuses on:
    - Medical entities (drugs, diseases, symptoms)
    - Clinical relationships (treats, causes, indicates)
    """
    pass


__all__ = ["MedicalDomain"]
```

### How the Decorator Works

```python
# The @domain decorator calls register_domain():
def domain(name: str):
    def decorator(cls):
        register_domain(name, cls)  # Adds to _DOMAIN_REGISTRY
        return cls
    return decorator
```

## Step 3: Add Schema (Optional)

Create `schema.json`:

```json
{
  "entity_types": ["Drug", "Disease", "Symptom"],
  "relation_types": ["treats", "causes", "indicates"]
}
```

Access with: `domain.schema.entity_types`, `domain.schema.relation_types`

## Step 4: Register in Domain Hub

Update `src/domains/__init__.py`:

```python
from . import medical  # Triggers @domain decorator
```

## Step 5: Verify

### Check Registration

```bash
python -c "from src.domains import list_available_domains; print(list_available_domains())"
```

### Unit Tests

```python
import pytest
from src.domains import get_domain, list_available_domains, DomainResourceError


def test_domain_registered():
    assert "medical" in list_available_domains()


def test_extraction_prompt_loads():
    domain = get_domain("medical")
    assert len(domain.extraction.prompt) > 50


def test_extraction_examples_valid():
    domain = get_domain("medical")
    examples = domain.extraction.examples
    assert isinstance(examples, list)
    assert "text" in examples[0]


def test_augmentation_strategy_exists():
    domain = get_domain("medical")
    assert "connectivity" in domain.list_augmentation_strategies()
    
    conn = domain.get_augmentation("connectivity")
    assert len(conn.prompt) > 0


def test_root_dir_override(tmp_path):
    (tmp_path / "extraction").mkdir()
    (tmp_path / "extraction" / "prompt_open.txt").write_text("Test")
    (tmp_path / "extraction" / "examples.json").write_text("[]")
    
    from src.domains.base import KnowledgeDomain
    domain = KnowledgeDomain(root_dir=tmp_path)
    assert domain.extraction.prompt == "Test"


def test_missing_resource_error(tmp_path):
    from src.domains.base import KnowledgeDomain
    domain = KnowledgeDomain(root_dir=tmp_path)
    
    with pytest.raises(DomainResourceError):
        _ = domain.extraction.prompt
```

## Auto-Discovery

The `KnowledgeDomain` base class uses `inspect.getfile()`:

```python
self._root_dir = Path(inspect.getfile(self.__class__)).parent
```

- No manual path configuration needed
- Override with `root_dir=` for testing

## CLI Usage

```bash
# Extract with your domain
python -m src extract --input data.jsonl --domain medical

# Augment with connectivity
python -m src augment connectivity --input data.jsonl --domain medical
```

## Troubleshooting

### "DomainResourceError: Resource not found"
- Verify file exists: `ls src/domains/medical/extraction/`
- Check filename matches exactly (case-sensitive)

### "ValueError: Unknown domain 'medical'"
- Add import in `src/domains/__init__.py`: `from . import medical`
- Restart Python interpreter

### "ValidationError: examples[0]..."
- Check `examples.json` matches ExtractionExample schema
- Validate JSON: `python -m json.tool examples.json`

## Error Handling

```python
from src.domains import get_domain, DomainResourceError

try:
    domain = get_domain("medical")
    prompt = domain.extraction.prompt
except DomainResourceError as e:
    print(f"Resource error: {e} (file: {e.path})")
except ValueError as e:
    print(f"Domain not found: {e}")
```

## Verification Checklist

- [ ] Directory structure matches expected layout
- [ ] `@domain("name")` decorator applied
- [ ] Prompts do NOT include format instructions
- [ ] `examples.json` matches ExtractionExample schema
- [ ] Import added in `src/domains/__init__.py`
- [ ] Tests pass for registration and resources
