# Adding a Knowledge Domain

This skill documents how to add a new knowledge domain to `kgb/domains/`.

## Overview

Domains are bundled resource sets containing prompts and few-shot examples for extraction and augmentation. The system provides:
- Registry pattern with `@domain()` decorator
- Automatic resource discovery via `inspect.getfile()`
- Strategy-based augmentation folders
- Optional schema constraints (entity types + relation types)

## Architecture

```
                          Domains Module
    ┌───────────────────────────────────────────────────────────┐
    │                                                           │
    │  registry.py                base.py                       │
    │  ├─ @domain()               ├─ KnowledgeDomain (ABC)      │
    │  ├─ register_domain()       ├─ DomainComponent            │
    │  ├─ get_domain()            ├─ DomainLike (Protocol)      │
    │  └─ list_available_domains()└─ DomainResourceError        │
    │                                                           │
    │  models.py                                                │
    │  ├─ Triple, InferenceType, ExtractionMode                 │
    │  ├─ Extraction, ExtractionExample                         │
    │  ├─ AugmentationExample, DomainSchema                     │
    │  └─ DomainExamples                                        │
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

## Dependencies

| Component | Library | Purpose |
|-----------|---------|---------|
| Schema validation | `pydantic>=2.0` | Triple validation |
| Extraction | `langextract>=0.1` | Prompt framework |
| Resource loading | `pathlib` (stdlib) | File operations |

## Directory Structure

```text
kgb/domains/<domain_name>/
├── __init__.py                 # Domain class with @domain decorator
├── extraction/
│   ├── prompt_open.md          # Open extraction prompt
│   ├── prompt_constrained.md   # Type-constrained extraction prompt
│   └── examples.json           # Few-shot extraction examples
├── augmentation/
│   └── connectivity/           # Strategy folder (one per strategy)
│       ├── prompt.md           # Strategy-specific augmentation prompt
│       └── examples.json       # Few-shot augmentation examples
└── schema.json                 # Optional: entity/relation type constraints
```

> **File extensions**: Prompts use `.md` (markdown). The base class resolves `prompt_open.md` or `prompt_constrained.md` based on `extraction_mode`, and `prompt.md` for augmentation strategies.

## Step 1: Create Resource Files

### Extraction Prompts

Create `extraction/prompt_open.md`:

```markdown
Extract all knowledge graph triples from the following biomedical text.
Focus on explicit relationships between biomedical entities.

For each relationship identified, extract:
- **head**: The source entity
- **relation**: The relationship type
- **tail**: The target entity

{{schema_constraints}}
```

> **Important:** Do NOT include output format instructions. The `langextract` framework generates format instructions from examples. You can include `{{schema_constraints}}` to inject entity/relation type guidance.

Create `extraction/prompt_constrained.md` (for `--mode constrained`):

```markdown
Extract knowledge graph triples from the following biomedical text.
Only extract entities and relations that match the provided schema types.

{{schema_constraints}}
```

### Extraction Examples (`extraction/examples.json`)

```json
[
  {
    "text": "Aspirin is used to treat headaches and reduce fever.",
    "extractions": [
      {
        "extraction_class": "Triple",
        "extraction_text": "Aspirin is used to treat headaches",
        "char_start": 0,
        "char_end": 35,
        "attributes": {
          "head": "Aspirin",
          "relation": "treats",
          "tail": "headaches",
          "inference": "explicit"
        }
      },
      {
        "extraction_class": "Triple",
        "extraction_text": "Aspirin is used to reduce fever",
        "char_start": 0,
        "char_end": 50,
        "attributes": {
          "head": "Aspirin",
          "relation": "reduces",
          "tail": "fever",
          "inference": "explicit"
        }
      }
    ]
  }
]
```

> **Key fields**: `char_start`/`char_end` must be valid character positions in the `text`. `extraction_text` is the span that justifies the extraction. `inference` must be `"explicit"` for extraction examples.

### Augmentation Prompt (`augmentation/connectivity/prompt.md`)

```markdown
You are a biomedical knowledge graph expert.

Given the following text and a partially extracted knowledge graph with disconnected components,
generate new triples that bridge the disconnected components.

## Source Text
{{text}}

## Current Triples
{{current_triples}}

## Disconnected Components
{{disconnected_components}}

{{schema_constraints}}

Generate bridging triples as a JSON array. Each triple must have:
- head, relation, tail, inference ("contextual"), justification
```

### Augmentation Examples (`augmentation/connectivity/examples.json`)

```json
[
  {
    "input": {
      "text": "Aspirin treats headaches. Ibuprofen is an NSAID.",
      "components": [
        {"entities": ["Aspirin", "headaches"]},
        {"entities": ["Ibuprofen", "NSAID"]}
      ]
    },
    "output": [
      {
        "head": "Aspirin",
        "relation": "is_a",
        "tail": "NSAID",
        "inference": "contextual",
        "justification": "Aspirin is also classified as an NSAID, bridging the two components."
      }
    ]
  }
]
```

## Step 2: Create Schema (Optional)

Create `schema.json`:

```json
{
  "entity_types": ["Drug", "Disease", "Symptom", "Gene", "Protein"],
  "relation_types": ["treats", "causes", "indicates", "inhibits", "binds_to"]
}
```

When present, schema constraints are:
- Injected into prompts via `{{schema_constraints}}`
- Used for validation warnings (not hard enforcement by default)
- Accessible via `domain.schema.entity_types` and `domain.schema.relation_types`

## Step 3: Implement the Domain Class

Create `kgb/domains/biomedical/__init__.py`:

```python
"""Biomedical knowledge domain for clinical and research document analysis."""

from __future__ import annotations
from ..base import KnowledgeDomain
from ..registry import domain


@domain("biomedical")  # This name is used with --domain CLI flag
class BiomedicalDomain(KnowledgeDomain):
    """Domain for biomedical and clinical document analysis.

    Focuses on:
    - Biomedical entities (drugs, diseases, symptoms, genes)
    - Clinical relationships (treats, causes, indicates, inhibits)
    """
    pass


__all__ = ["BiomedicalDomain"]
```

### How Auto-Discovery Works

The `KnowledgeDomain` base class uses `inspect.getfile()` to find resources:

```python
# In KnowledgeDomain.__init__():
self._root_dir = Path(inspect.getfile(self.__class__)).parent
# → resolves to kgb/domains/biomedical/
```

From there it finds:
- `extraction/prompt_open.md` (or `prompt_constrained.md`)
- `extraction/examples.json`
- `augmentation/<strategy>/prompt.md`
- `augmentation/<strategy>/examples.json`
- `schema.json`

Override with `root_dir=` for testing.

## Step 4: Register in Domain Hub

Update `kgb/domains/__init__.py`:

```python
# Import domains to trigger registration
from . import legal
from . import default
from . import biomedical  # Add this — triggers @domain decorator
```

## Step 5: Verify

### Check Registration

```bash
python -c "from kgb.domains import list_available_domains; print(list_available_domains())"
# Output: ['legal', 'default', 'biomedical']
```

### Unit Tests

```python
import pytest
from kgb.domains import get_domain, list_available_domains, DomainResourceError


def test_domain_registered():
    assert "biomedical" in list_available_domains()


def test_extraction_prompt_loads():
    domain = get_domain("biomedical")
    assert len(domain.extraction.prompt) > 50


def test_extraction_examples_valid():
    domain = get_domain("biomedical")
    examples = domain.extraction.examples
    assert isinstance(examples, list)
    assert len(examples) > 0
    assert "text" in examples[0]
    assert "extractions" in examples[0]


def test_augmentation_strategy_exists():
    domain = get_domain("biomedical")
    assert "connectivity" in domain.list_augmentation_strategies()

    conn = domain.get_augmentation("connectivity")
    assert len(conn.prompt) > 0
    assert isinstance(conn.examples, list)


def test_schema_loads():
    domain = get_domain("biomedical")
    assert "Drug" in domain.schema.entity_types
    assert "treats" in domain.schema.relation_types


def test_constrained_mode():
    domain = get_domain("biomedical", extraction_mode="constrained")
    assert "constrained" in domain.extraction._prompt_path.name


def test_missing_strategy():
    domain = get_domain("biomedical")
    with pytest.raises(DomainResourceError):
        domain.get_augmentation("nonexistent")
```

## CLI Usage

```bash
# Extract with your domain
kgb extract --input data.jsonl --domain biomedical

# Constrained mode (uses prompt_constrained.md)
kgb extract --input data.jsonl --domain biomedical --mode constrained

# Augment with connectivity strategy
kgb augment connectivity --input data.jsonl --domain biomedical

# List available domains
kgb list domains
```

## Troubleshooting

### "DomainResourceError: Resource not found"
- Verify file exists: `ls kgb/domains/biomedical/extraction/`
- Check filename matches exactly: `prompt_open.md` (not `.txt`)
- Augmentation prompts must be `prompt.md` inside strategy folders

### "ValueError: Unknown domain 'biomedical'"
- Add import in `kgb/domains/__init__.py`: `from . import biomedical`
- Restart Python interpreter (imports are cached)

### "ValidationError: examples[0]..."
- Check `examples.json` matches the ExtractionExample schema
- Validate JSON: `python -m json.tool examples.json`
- Ensure `char_start`/`char_end` are valid integers

## Error Handling

```python
from kgb.domains import get_domain, DomainResourceError

try:
    domain = get_domain("biomedical")
    prompt = domain.extraction.prompt
except DomainResourceError as e:
    print(f"Resource error: {e} (file: {e.resource_path})")
except ValueError as e:
    print(f"Domain not found: {e}")
```

## Files to Create/Modify

| File | Action |
|------|--------|
| `kgb/domains/biomedical/__init__.py` | Create — domain class |
| `kgb/domains/biomedical/extraction/prompt_open.md` | Create — open extraction prompt |
| `kgb/domains/biomedical/extraction/prompt_constrained.md` | Create — constrained prompt |
| `kgb/domains/biomedical/extraction/examples.json` | Create — few-shot examples |
| `kgb/domains/biomedical/augmentation/connectivity/prompt.md` | Create — augmentation prompt |
| `kgb/domains/biomedical/augmentation/connectivity/examples.json` | Create — augmentation examples |
| `kgb/domains/biomedical/schema.json` | Create — entity/relation types |
| `kgb/domains/__init__.py` | Modify — add import |

## Verification Checklist

- [ ] Directory structure matches layout above (`.md` extensions for prompts)
- [ ] `@domain("name")` decorator applied to class
- [ ] Class inherits from `KnowledgeDomain`
- [ ] Extraction prompts do NOT include format instructions (langextract handles that)
- [ ] `examples.json` includes `char_start`/`char_end` and `extraction_text`
- [ ] Augmentation folder per strategy (at least `connectivity/`)
- [ ] Import added in `kgb/domains/__init__.py`
- [ ] Optional `schema.json` with entity_types and relation_types
- [ ] Tests pass for registration, resource loading, and schema
