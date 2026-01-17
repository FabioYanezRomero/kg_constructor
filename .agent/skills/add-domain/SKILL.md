---
name: add-domain
description: Manage knowledge domains (e.g., Medical, Finance). Covers adding new domains, updating prompts, and adding few-shot examples.
---

# Add Domain: New Knowledge Domain

This skill guides you through adding a new knowledge domain to `src/domains/`.

## Architecture Overview

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
    │  ├─ augmentation/           └─ augmentation/              │
    │  └─ schema.json                                           │
    │                                                           │
    └───────────────────────────────────────────────────────────┘

Registration Flow:
  @domain("name") → register_domain() → _DOMAIN_REGISTRY → get_domain()
```

**Key Files:**
- [registry.py](file:///app/src/domains/registry.py) - Registration decorator and lookup
- [base.py](file:///app/src/domains/base.py) - Base class with auto-discovery
- [models.py](file:///app/src/domains/models.py) - Triple and extraction Pydantic models

## Dependencies

| Component | Library | Purpose |
|-----------|---------|---------|
| Schema validation | `pydantic>=2.0` | Triple and example validation |
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
│   └── connectivity/           # Strategy folder (matches CLI)
│       ├── prompt.txt
│       └── examples.json
└── schema.json                 # Optional: entity/relation type constraints
```

---

## Step 1: Create Resource Files

### Extraction Prompts

Create `extraction/prompt_open.txt`:

```text
Extract all knowledge graph triples from the following text.
Focus on explicit relationships between entities.
Identify the head entity, the relationship, and the tail entity.
```

> [!IMPORTANT]
> **DO NOT include output format instructions** (e.g., "Return JSON...") in prompts.
> The `langextract` framework generates format instructions from examples.

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

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `extraction_class` | str | Always `"Triple"` |
| `extraction_text` | str | Span of text containing the triple |
| `char_start` / `char_end` | int | Character offsets in source text |
| `attributes.inference` | str | `"explicit"` or `"contextual"` |

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

> [!NOTE]
> Augmentation examples use a different structure than extraction examples. The `input` contains disconnected graph components; the `output` contains bridging triples.

---

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
    - Medical entities (drugs, diseases, symptoms, treatments)
    - Clinical relationships (treats, causes, indicates, contraindicates)
    - Temporal information (onset, duration, dosage schedules)
    
    Resources are auto-discovered from:
    - extraction/prompt_open.txt or prompt_constrained.txt
    - extraction/examples.json
    - augmentation/connectivity/prompt.txt and examples.json
    - schema.json (optional)
    """
    pass


__all__ = ["MedicalDomain"]
```

### How the `@domain` Decorator Works

```python
# The decorator is defined in registry.py:
def domain(name: str) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        register_domain(name, cls)  # Adds class to _DOMAIN_REGISTRY
        return cls
    return decorator

# Equivalent to:
class MedicalDomain(KnowledgeDomain):
    pass

register_domain("medical", MedicalDomain)
```

---

## Step 3: Add Schema (Optional)

Create `schema.json` to define allowed types for constrained extraction:

```json
{
  "entity_types": ["Drug", "Disease", "Symptom", "Treatment", "Dosage"],
  "relation_types": ["treats", "causes", "indicates", "contraindicates", "prescribed_for"]
}
```

**How schema integrates:**
- Loaded via `domain.schema` property (lazy-loaded on first access)
- Used by `prompt_constrained.txt` to restrict output types
- Access with: `domain.schema.entity_types`, `domain.schema.relation_types`

---

## Step 4: Register in Domain Hub

Update `src/domains/__init__.py`:

```python
# This import triggers the @domain decorator → registration
from . import medical
```

---

## Step 5: Verification

### 5.1 Check Registration

```bash
python -c "from src.domains import list_available_domains; print(list_available_domains())"
# Output: ['default', 'legal', 'medical']
```

### 5.2 Unit Tests

```python
import pytest
from pathlib import Path
from src.domains import get_domain, list_available_domains, DomainResourceError


def test_domain_registered():
    """Verify domain appears in registry."""
    assert "medical" in list_available_domains()


def test_extraction_prompt_loads():
    """Verify extraction prompt loads correctly."""
    domain = get_domain("medical")
    prompt = domain.extraction.prompt
    
    assert isinstance(prompt, str)
    assert len(prompt) > 50


def test_extraction_examples_valid():
    """Verify examples match schema."""
    domain = get_domain("medical")
    examples = domain.extraction.examples
    
    assert isinstance(examples, list)
    assert len(examples) > 0
    assert "text" in examples[0]
    assert "extractions" in examples[0]


def test_schema_loads():
    """Verify schema loads and has expected types."""
    domain = get_domain("medical")
    schema = domain.schema
    
    assert "Drug" in schema.entity_types
    assert "treats" in schema.relation_types


def test_augmentation_strategy_exists():
    """Verify connectivity strategy works."""
    domain = get_domain("medical")
    strategies = domain.list_augmentation_strategies()
    
    assert "connectivity" in strategies
    
    conn = domain.get_augmentation("connectivity")
    assert len(conn.prompt) > 0
    assert isinstance(conn.examples, list)


def test_missing_resource_error(tmp_path):
    """Test error when resource file is missing."""
    from src.domains.base import KnowledgeDomain
    
    domain = KnowledgeDomain(root_dir=tmp_path)
    
    with pytest.raises(DomainResourceError, match="Resource not found"):
        _ = domain.extraction.prompt


def test_root_dir_override(tmp_path):
    """Test custom root directory."""
    (tmp_path / "extraction").mkdir()
    (tmp_path / "extraction" / "prompt_open.txt").write_text("Test prompt")
    (tmp_path / "extraction" / "examples.json").write_text("[]")
    
    from src.domains.base import KnowledgeDomain
    domain = KnowledgeDomain(root_dir=tmp_path)
    
    assert domain.extraction.prompt == "Test prompt"
```

---

## How Resource Auto-Discovery Works

The `KnowledgeDomain` base class uses Python's `inspect.getfile()`:

```python
# In KnowledgeDomain.__init__():
self._root_dir = Path(inspect.getfile(self.__class__)).parent
```

This means:
- **No manual path configuration** - class finds its own resources
- **Portable** - works regardless of where package is installed
- **Override available** - pass `root_dir=` for custom locations

### Root Directory Override

Use `root_dir=` when testing or using shared resources:

```python
from pathlib import Path
from src.domains.base import KnowledgeDomain

# Testing with mock resources
domain = KnowledgeDomain(root_dir=Path("/tmp/test_resources"))

# Using shared resource directory
from src.domains.medical import MedicalDomain
domain = MedicalDomain(root_dir=Path("src/domains/shared_medical"))
```

---

## Lazy Loading and Validation

Validation occurs **on first access**:

| Resource | Validated When |
|----------|----------------|
| `domain.extraction.prompt` | First `.prompt` access |
| `domain.extraction.examples` | First `.examples` access |
| `domain.schema` | First `.schema` access |

---

## CLI Usage

```bash
# Extract with your domain
python -m src extract --input data.jsonl --domain medical

# Augment with connectivity strategy
python -m src augment connectivity --input data.jsonl --domain medical

# Use constrained mode with schema
python -m src extract --input data.jsonl --domain medical --mode constrained
```

---

## Troubleshooting

### "DomainResourceError: Resource not found"

```python
# Debug: Check if file exists
from pathlib import Path
domain_dir = Path("src/domains/medical")
print((domain_dir / "extraction" / "prompt_open.txt").exists())
```

**Solutions:**
- Verify file exists: `ls src/domains/medical/extraction/`
- Check filename matches exactly (case-sensitive)
- Ensure `__init__.py` is in same directory as resource folders

### "ValueError: Unknown domain 'medical'"

**Solutions:**
- Add import in `src/domains/__init__.py`: `from . import medical`
- Restart Python interpreter to reload modules
- Verify decorator syntax: `@domain("medical")` not `@Domain("medical")`

### "ValidationError: examples[0].extractions[0]..."

**Solutions:**
- Check `examples.json` matches ExtractionExample schema
- Verify all required fields (head, relation, tail, inference)
- Use `python -m json.tool examples.json` to validate JSON

---

## Error Handling Reference

| Exception | When | Action |
|-----------|------|--------|
| `DomainResourceError` | Missing/invalid resource file | Check path and file contents |
| `ValidationError` | Examples don't match Pydantic model | Check schema in `models.py` |
| `ValueError` | Domain not registered | Add import to `__init__.py` |

### Catching Errors

```python
from src.domains import get_domain, DomainResourceError

try:
    domain = get_domain("medical")
    prompt = domain.extraction.prompt
except DomainResourceError as e:
    print(f"Resource error: {e}")
    print(f"File: {e.path}")
except ValueError as e:
    print(f"Domain not found: {e}")
```

---

## Verification Checklist

Before submitting, verify your domain:

- [ ] Directory structure matches expected layout
- [ ] `@domain("name")` decorator applied
- [ ] Prompts do NOT include format instructions
- [ ] `examples.json` matches ExtractionExample schema
- [ ] Augmentation examples use input/output structure
- [ ] Import added in `src/domains/__init__.py`
- [ ] Tests pass for registration, resources, schema
- [ ] CLI works: `python -m src extract --domain name`
