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
└── augmentation/
    └── connectivity/          # Strategy folder (matches CLI: augment connectivity)
        ├── prompt.txt
        └── examples.json
```


## Step 1: Create the Resource Files

### Extraction Prompts (`extraction/prompt_open.txt` & `extraction/prompt_constrained.txt`)
Create these as plain text files. 
- `prompt_open.txt`: Focus on capturing all explicit relationships.
- `prompt_constrained.txt`: Focus on specific entity/relation types relevant to the domain.

> [!IMPORTANT]
> **DO NOT include output format instructions** (e.g., "Return a JSON array...") in extraction prompts. 
> The `langextract` framework automatically generates the output schema instructions based on the provided few-shot examples. 
> Including formatting instructions in the prompt text can conflict with the framework's internal logic and confuse the LLM.

### Extraction Examples (`extraction/examples.json`)
Create a JSON file following the `ExtractionExample` model:

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

### Augmentation Resources (`augmentation/prompt.txt` & `augmentation/examples.json`)
The augmentation prompt guides the generative LLM to connect disconnected graph components. Examples follow the `AugmentationExample` model.

## Step 2: Implement the Domain Class

Create `src/domains/<domain_name>/__init__.py`. This class inherits from `KnowledgeDomain` and registers itself. The system automatically finds the resource files based on the directory where your class is defined.

```python
from ..base import KnowledgeDomain
from ..registry import register_domain

class NewDomain(KnowledgeDomain):
    """Description of the new domain."""
    pass

# Register the domain with a unique identifier
register_domain("new_domain_id", NewDomain)

__all__ = ["NewDomain"]
```

## Step 3: Add a Schema (Optional but Recommended)
Create `src/domains/<domain_name>/schema.json` to define allowed types:

```json
{
  "entity_types": ["Person", "Company", "Location"],
  "relation_types": ["works_for", "located_in"]
}
```

## Step 4: Register in the Domain Hub

Update `src/domains/__init__.py` to import your new domain:

```python
# src/domains/__init__.py
from . import legal
from . import new_domain  # Add this line
```

## Step 5: Verification

```python
from src.domains import get_domain, list_available_domains

# Check registration
assert "new_domain_id" in list_available_domains()

# Check resource loading
domain = get_domain("new_domain_id")
print(domain.get_extraction_prompt())
print(len(domain.get_extraction_examples()))
```

## Modifying an Existing Domain

Since domains are resource-based, modifying them is straightforward and usually doesn't require code changes.

### 1. Updating Prompts
To change how an extraction or augmentation is performed:
- Locate the domain folder: `src/domains/<domain_name>/`
- Edit the corresponding `.txt` file:
    - `extraction/prompt_open.txt`
    - `extraction/prompt_constrained.txt`
    - `augmentation/prompt.txt`
- Changes take effect as soon as a new `KnowledgeDomain` instance is created.

### 2. Adding Few-Shot Examples
To improve performance with more examples:
- Open the `examples.json` file in either the `extraction/` or `augmentation/` folder.
- Append new objects following the schema.
- **Validation**: The next time the domain is used, Pydantic will automatically validate your new examples. If you made a JSON syntax or schema error, you will get a clear error message.

### 3. Overriding at Runtime (via CLI)
The Typer CLI uses composable subcommands:

```bash
# Step 1: Extract triples from text
python -m src.extract_cli extract --csv data.csv --domain legal

# Step 2: Augment with connectivity strategy
python -m src.extract_cli augment connectivity --csv data.csv

# Full pipeline = run both commands in sequence
python -m src.extract_cli extract --csv data.csv --domain legal
python -m src.extract_cli augment connectivity --csv data.csv --max-disconnected 1
```

Future augmentation strategies can be added as new subcommands under `augment`.



## Validation Guardrails
The system uses **Pydantic** models defined in `src/domains/models.py`. Any JSON examples will be validated during the first access to `domain.examples`. If the JSON structure is incorrect, a descriptive validation error will be raised.
