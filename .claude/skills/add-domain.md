# Adding a New Knowledge Domain

This skill documents how to add a new knowledge domain to the `src/domains` module.

## Overview

Domains are bundled resource sets that include prompts and few-shot examples for both extraction and augmentation. The domain system uses:
1. A registry pattern with `@domain()` decorator
2. Automatic resource discovery via `inspect.getfile()`
3. Strategy-based augmentation folders

## File Structure

```
src/domains/<domain_name>/
├── __init__.py                 # Domain class with @domain decorator
├── extraction/
│   ├── prompt_open.txt         # Open extraction prompt
│   ├── prompt_constrained.txt  # Constrained extraction prompt
│   └── examples.json           # Few-shot extraction examples
├── augmentation/
│   └── connectivity/           # Strategy folder (matches CLI)
│       ├── prompt.txt
│       └── examples.json
└── schema.json                 # Optional: entity/relation type constraints
```

## Step 1: Create Resource Files

### Extraction Prompts

Create `extraction/prompt_open.txt` and `extraction/prompt_constrained.txt` as plain text.

> **IMPORTANT:** Do NOT include format instructions (e.g., "Return JSON...") in prompts. The `langextract` framework generates format instructions from examples.

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

### Augmentation Resources

Create `augmentation/connectivity/prompt.txt` and `augmentation/connectivity/examples.json`.

## Step 2: Create Domain Class

Create `src/domains/<domain_name>/__init__.py`:

```python
from ..base import KnowledgeDomain
from ..registry import domain

@domain("my_domain")  # This ID is used with --domain CLI flag
class MyDomain(KnowledgeDomain):
    """Description of the domain."""
    pass

__all__ = ["MyDomain"]
```

The `@domain()` decorator registers the class when the module is imported.

## Step 3: Add Schema (Optional)

Create `schema.json` for constrained extraction:

```json
{
  "entity_types": ["Person", "Company", "Drug"],
  "relation_types": ["works_for", "developed", "treats"]
}
```

Access via: `domain.schema.entity_types`, `domain.schema.relation_types`

## Step 4: Register in Domain Hub

Update `src/domains/__init__.py`:

```python
from . import my_domain  # This import triggers @domain decorator
```

## Step 5: Verify

```python
from src.domains import get_domain, list_available_domains

assert "my_domain" in list_available_domains()

domain = get_domain("my_domain")
print(domain.extraction.prompt[:100])
print(domain.get_augmentation("connectivity").prompt[:100])
```

## How Auto-Discovery Works

The `KnowledgeDomain` base class locates resources using:

```python
self._root_dir = Path(inspect.getfile(self.__class__)).parent
```

This means:
- No manual path configuration needed
- Works regardless of where the package is installed
- Override with `root_dir=` parameter if needed

## Validation Timing

Resources are validated **on first access** (lazy loading):

| Resource | Validated When |
|----------|----------------|
| `domain.extraction.prompt` | First `.prompt` access |
| `domain.extraction.examples` | First `.examples` access |
| `domain.schema` | First `.schema` access |

Errors raise `DomainResourceError` with file path and details.

## CLI Usage

```bash
# Extract with your domain
python -m src.extract_cli extract --input data.jsonl --domain my_domain

# Augment with connectivity strategy
python -m src.extract_cli augment connectivity --input data.jsonl --domain my_domain
```

## Adding New Augmentation Strategies

Strategy folders are **NOT auto-discovered** for CLI. You must:

1. Create folder: `augmentation/<strategy_name>/`
2. Add `prompt.txt` and `examples.json`
3. Add CLI subcommand in `src/extract_cli.py`:
```python
@augment_app.command("strategy_name")
def augment_strategy_name(...):
    ...
```

> **Note:** The domain's `list_augmentation_strategies()` method auto-discovers folders, but CLI subcommands require manual registration.

## Testing Your Domain

```python
import pytest
from pathlib import Path
from src.domains import get_domain

def test_domain_registration():
    """Verify domain is registered."""
    from src.domains import list_available_domains
    assert "my_domain" in list_available_domains()

def test_extraction_resources():
    """Verify extraction resources load correctly."""
    domain = get_domain("my_domain")
    assert len(domain.extraction.prompt) > 0
    assert isinstance(domain.extraction.examples, list)

def test_augmentation_strategy():
    """Verify augmentation strategy resources load."""
    domain = get_domain("my_domain")
    strategies = domain.list_augmentation_strategies()
    assert "connectivity" in strategies
    
    conn = domain.get_augmentation("connectivity")
    assert len(conn.prompt) > 0

def test_with_override_root(tmp_path):
    """Test with temporary resource directory."""
    # Create minimal resources
    (tmp_path / "extraction").mkdir()
    (tmp_path / "extraction" / "prompt_open.txt").write_text("Test prompt")
    (tmp_path / "extraction" / "examples.json").write_text("[]")
    
    from src.domains.base import KnowledgeDomain
    domain = KnowledgeDomain(root_dir=tmp_path)
    assert domain.extraction.prompt == "Test prompt"
```

## Root Directory Override

Use `root_dir=` when:
- Testing with temporary resources
- Loading resources from non-standard locations
- Sharing resources between multiple domains

```python
from pathlib import Path
from src.domains.base import KnowledgeDomain

# Testing with mock resources
domain = KnowledgeDomain(root_dir=Path("/tmp/test_resources"))

# Using shared resource directory
domain = MyDomain(root_dir=Path("src/domains/shared_legal"))
```

## Error Handling

Errors are raised **on first access** (lazy loading), not at registration time:

| Error | Cause | Solution |
|-------|-------|----------|
| `DomainResourceError: Resource not found` | Missing file | Check path |
| `DomainResourceError: Invalid JSON` | Malformed JSON | Fix syntax |
| `ValueError: Unknown domain` | Not registered | Add import to `__init__.py` |
| `ValidationError` | Examples don't match model | Check `models.py` schema |
