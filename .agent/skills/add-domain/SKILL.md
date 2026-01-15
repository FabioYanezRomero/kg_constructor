---
name: add-domain
description: Manage knowledge domains (e.g., Medical, Finance). Covers adding new domains, updating prompts, and adding few-shot examples.
---

# Domain Management: Adding and Modifying Domains

This skill guides you through adding a new domain to the Knowledge Graph Constructor. Domains are bundled resource sets that include prompts and few-shot examples for both extraction and augmentation.

## Directory Structure

All domains must live in `src/domains/<domain_name>/` with the following structure:

```text
src/domains/<domain_name>/
├── __init__.py
├── extraction/
│   ├── prompt_open.txt        # Comprehensive extraction prompt
│   ├── prompt_constrained.txt # Type-constrained extraction prompt
│   └── examples.json          # Few-shot extraction examples
├── augmentation/
│   └── connectivity/          # Strategy folder (matches CLI: augment connectivity)
│       ├── prompt.txt
│       └── examples.json
└── schema.json                # Optional: entity/relation type constraints
```

---

## How Resource Auto-Discovery Works

The `KnowledgeDomain` base class uses Python's `inspect.getfile()` to locate the directory where your subclass is defined:

```python
# In KnowledgeDomain.__init__():
self._root_dir = Path(inspect.getfile(self.__class__)).parent
```

This means:
- **No manual path configuration needed** - the class finds its own resources
- **Portable** - works regardless of where the package is installed
- **Override available** - pass `root_dir=` to the constructor for custom locations

> [!NOTE]
> If you move the domain class file, the resource lookup moves with it. Keep the class file in the same directory as the resource folders.

---

## Step 1: Create the Resource Files

### Extraction Prompts
Create `extraction/prompt_open.txt` and `extraction/prompt_constrained.txt`:
- `prompt_open.txt`: Capture all explicit relationships
- `prompt_constrained.txt`: Use with `schema.json` for type-restricted extraction

> [!IMPORTANT]
> **DO NOT include output format instructions** (e.g., "Return a JSON array...") in prompts.
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

### Augmentation Resources (`augmentation/<strategy>/`)
Each strategy has its own folder with `prompt.txt` and `examples.json`.

---

## Step 2: Implement the Domain Class

Create `src/domains/<domain_name>/__init__.py`:

```python
from ..base import KnowledgeDomain
from ..registry import domain  # Decorator-based registration

@domain("my_domain")  # This ID is used with --domain CLI flag
class MyDomain(KnowledgeDomain):
    """Description of the domain."""
    pass

__all__ = ["MyDomain"]
```

The `@domain("my_domain")` decorator calls `register_domain()` when the module is imported.

---

## Step 3: Add a Schema (Optional)

Create `schema.json` to define allowed types for constrained extraction:

```json
{
  "entity_types": ["Person", "Company", "Drug"],
  "relation_types": ["works_for", "developed", "treats"]
}
```

**How schema integrates:**
- Loaded via `domain.schema` property (lazy-loaded on first access)
- Used by `prompt_constrained.txt` to restrict output types
- Access with: `domain.schema.entity_types`, `domain.schema.relation_types`

---

## Step 4: Register in Domain Hub

Update `src/domains/__init__.py` to import your domain:

```python
# This import triggers the @domain decorator → registration
from . import my_domain
```

---

## Step 5: Verification

```python
from src.domains import get_domain, list_available_domains

# Check registration
assert "my_domain" in list_available_domains()

# Check resource loading
domain = get_domain("my_domain")
print(domain.extraction.prompt[:100])  # First 100 chars
print(domain.get_augmentation("connectivity").prompt[:100])
print(domain.schema.entity_types)  # Empty list if no schema.json
```

---

## Pydantic Validation Timing

Validation occurs **on first access** (lazy loading):

| Resource | Validated When |
|----------|----------------|
| `domain.extraction.prompt` | First `.prompt` access |
| `domain.extraction.examples` | First `.examples` access |
| `domain.schema` | First `.schema` access |

**Error handling:** If JSON is malformed or doesn't match the Pydantic model, a `DomainResourceError` is raised with the file path and error details.

---

## CLI Input/Output Formats

### Input (JSONL recommended)
```jsonl
{"id": "doc_001", "text": "The plaintiff filed a lawsuit..."}
{"id": "doc_002", "text": "The defendant responded..."}
```

### Output (per-document JSON)
```
outputs/kg_extraction/extracted_json/
├── doc_001.json   # Array of Triple objects
├── doc_002.json
```

### CLI Commands
```bash
# Full Pipeline Execution (Compound)
python -m src extract --input data.jsonl --domain legal
python -m src augment connectivity --input data.jsonl --domain legal

# Extract (Step 1)
python -m src extract --input data.jsonl --domain my_domain

# Augment connectivity (Step 2)
python -m src augment connectivity --input data.jsonl --domain my_domain

# Key options:
#   --max-disconnected N   Target max disconnected components (default: 3)
#   --max-iterations N     Max augmentation iterations (default: 2)
#   --mode constrained     Use prompt_constrained.txt + schema.json
```

---

## Adding New Augmentation Strategies

To add a new strategy (e.g., `enrichment`):

1. Create folder: `src/domains/<domain>/augmentation/enrichment/`
2. Add `prompt.txt` and `examples.json`
3. Add CLI subcommand in `src/extract_cli.py`:
```python
@augment_app.command("enrichment")
def augment_enrichment(...):
    ...
```
4. Use: `python -m src.extract_cli augment enrichment --input data.jsonl --domain my_domain`

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `DomainResourceError: Resource not found` | Missing prompt/examples file | Check file path |
| `DomainResourceError: Invalid JSON` | Malformed JSON | Fix syntax |
| `ValidationError` | Examples don't match Pydantic model | Check schema in `models.py` |
| `ValueError: Unknown domain` | Domain not registered | Add import to `__init__.py` |
