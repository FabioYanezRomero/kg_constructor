---
name: add-augmentation-strategy
description: Adds a new iterative augmentation strategy (e.g., enrichment, summarization) to the builder module.
---

# Adding an Augmentation Strategy

This skill documents how to add a new augmentation strategy to the `kgb/builder` module.

## Overview

Augmentation strategies are iterative graph refinement algorithms that improve the knowledge graph after initial extraction. The system uses:
1. A registry pattern with `@register_strategy()` decorator
2. Protocol-based design for type safety
3. Strategy-specific kwargs for flexibility
4. Schema validation for generated triples

## Architecture

```
Step 1: Extraction          Step 2: Augmentation
    Text                        Initial Triples
      │                              │
      ▼                              ▼
extract_triples()           augment_triples() orchestrator
      │                       ┌──────┴──────┐
      ▼                       ▼             ▼
Initial Triples        connectivity    your_strategy
                              │             │
                              └──────┬──────┘
                                     ▼
                              Refined Triples + Metadata
```

**Key Files:**
- `kgb/builder/augmentation.py` — Strategy Protocol, Registry, implementations, orchestrator
- `kgb/builder/validation.py` — Schema validation, prompt rendering
- `kgb/builder/__init__.py` — Public exports

## Step 1: Understand the Protocol

All strategies must conform to the `AugmentationStrategy` Protocol (in `kgb/builder/augmentation.py`):

```python
class AugmentationStrategy(Protocol):
    def __call__(
        self,
        client: BaseLLMClient,
        domain: KnowledgeDomain,
        text: str,
        triples: list[Triple],
        **kwargs: Any
    ) -> tuple[list[Triple], dict[str, Any]]:
        """Returns (refined_triples, metadata)."""
        ...
```

Strategy-specific parameters (e.g., `max_iterations`) are passed via `**kwargs`. Define and document them with keyword-only args in your function signature.

### extract() vs augment() — Why Strategies Use augment()

Strategies call `client.augment()` (NOT `client.extract()`):
- `extract()` uses langextract's source-grounding pipeline (char positions) — appropriate for initial extraction
- `augment()` is a direct LLM call that generates inferred triples without source grounding — appropriate for bridging and enrichment

## Step 2: Implement Your Strategy

Add to `kgb/builder/augmentation.py`:

```python
@register_strategy("enrichment")
def enrichment_strategy(
    client: BaseLLMClient,
    domain: KnowledgeDomain,
    text: str,
    triples: list[Triple],
    *,
    max_iterations: int = 3,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    augmentation_prompt_override: str | None = None,
    **kwargs: Any
) -> tuple[list[Triple], dict[str, Any]]:
    """Enrichment augmentation: Add missing entity attributes and relations.

    Args:
        client: LLM client for generation
        domain: Knowledge domain with prompts/examples
        text: Source text to analyze
        triples: Initial triples from extraction
        max_iterations: Max refinement iterations (default: 3)
        temperature: Sampling temperature for LLM (0.0 = deterministic)
        max_tokens: Max tokens for LLM
        augmentation_prompt_override: Override the default prompt

    Returns:
        Tuple of (enriched_triples, metadata)
    """
    # 1. Fetch strategy-specific resources from domain
    augmentation_component = domain.get_augmentation("enrichment")
    aug_prompt_template = augmentation_prompt_override or augmentation_component.prompt
    constraints = collect_schema_constraints(domain, augmentation_component.examples)

    all_triples = list(triples)  # Copy to avoid mutation
    iterations_data = []
    error_occurred = False

    # 2. Iteration loop with error preservation
    for i in range(max_iterations):
        try:
            # Build prompt with current state
            current_triples_dicts = [t.model_dump() for t in all_triples]
            record = {
                "text": text,
                "current_triples": current_triples_dicts,
            }

            final_prompt = render_prompt_template(
                aug_prompt_template,
                record,
                schema_guidance=build_schema_guidance(constraints),
            )

            # Call client.augment() — NOT extract()
            new_triples_raw = client.augment(
                text=final_prompt,
                prompt_description="Enrich entities with missing attributes and relations",
                format_type=Triple,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # 3. Validate and force CONTEXTUAL inference type
            new_triples = []
            normalized_raw: list[dict[str, Any]] = []
            for t_raw in new_triples_raw:
                try:
                    t_dict = t_raw if isinstance(t_raw, dict) else t_raw.model_dump()
                    t_dict["inference"] = InferenceType.CONTEXTUAL
                    new_triples.append(Triple(**t_dict))
                    normalized_raw.append(t_dict)
                except Exception as e:
                    print(f"Warning: Skipping invalid augmented triple: {e}")
                    continue

            # 4. Schema validation
            validated_triples, validation_summary = validate_triples_against_schema(
                new_triples,
                constraints,
                raw_triples=normalized_raw,
            )
            warn_on_schema_validation("enrichment", validation_summary)

            all_triples.extend(validated_triples)
            iterations_data.append({
                "iteration": i + 1,
                "new_triples_count": len(validated_triples),
                "status": "success",
                "schema_validation": validation_summary,
            })

        except Exception as e:
            print(f"Error during enrichment iteration {i+1}: {e}")
            iterations_data.append({
                "iteration": i + 1,
                "status": "failed",
                "error": str(e)
            })
            error_occurred = True
            break

    metadata = {
        "strategy": "enrichment",
        "iterations": iterations_data,
        "partial_result": error_occurred,
        "schema_constraints_applied": constraints.enforce,
        "allowed_entity_types": list(constraints.entity_types),
        "allowed_relation_types": list(constraints.relation_types),
    }

    return all_triples, metadata
```

### Available Utilities (already imported in augmentation.py)

| Utility | Purpose |
|---------|---------|
| `_build_graph_from_triples(triples)` | Build NetworkX DiGraph from Triple list |
| `_format_components(components, G, triples)` | Format disconnected components for prompts |
| `collect_schema_constraints(domain, examples)` | Get schema constraints from domain |
| `build_schema_guidance(constraints)` | Format constraints as prompt text |
| `render_prompt_template(template, record, schema_guidance)` | Fill `{{variables}}` in prompt |
| `validate_triples_against_schema(triples, constraints)` | Validate against schema |
| `warn_on_schema_validation(stage, summary)` | Log validation warnings |

## Step 3: Create Domain Resources

Add prompts and examples for your strategy in each domain that supports it:

```
kgb/domains/<domain>/augmentation/enrichment/
├── prompt.md          # Strategy-specific prompt (must be .md)
└── examples.json      # Few-shot augmentation examples
```

**`prompt.md` template variables** (filled by `render_prompt_template()`):
- `{{text}}` — source text
- `{{current_triples}}` — current triple list (JSON)
- `{{disconnected_components}}` — formatted component analysis
- `{{schema_constraints}}` — entity/relation type guidance

**`examples.json` structure:**
```json
[
  {
    "input": {"text": "...", "entities": ["..."]},
    "output": [{"head": "...", "relation": "...", "tail": "...", "inference": "contextual", "justification": "..."}]
  }
]
```

## Step 4: Add CLI Subcommand

Update `kgb/__main__.py` (follow the pattern of `augment_connectivity`):

```python
@augment_app.command("enrichment")
def augment_enrichment(
    input_file: Path = typer.Option(..., "--input", "-i", exists=True),
    output_dir: Path = typer.Option("outputs/kg_extraction", "--output-dir", "-o"),
    domain: str = typer.Option(..., "--domain", "-d"),
    max_iterations: int = typer.Option(3, "--max-iterations"),
    client: str = typer.Option("gemini", "--client", "-c"),
    # ... other common options
):
    """Enrichment augmentation: Add missing entity attributes."""
    from .builder import augment_triples
    from .io import load_records
    from .domains import get_domain

    # Load records, create client, iterate, save results
    # See existing augment_connectivity command for the full pattern
```

> See existing `augment_connectivity` command in `kgb/__main__.py` for the complete implementation reference.

## Step 5: Verify

### Check Registration

```bash
python -c "from kgb.builder import list_strategies; print(list_strategies())"
# Output: ['connectivity', 'enrichment']
```

### Unit Test

```python
def test_enrichment_strategy():
    from unittest.mock import MagicMock
    from kgb.builder.augmentation import enrichment_strategy
    from kgb.domains import Triple, InferenceType

    mock_client = MagicMock()
    mock_client.augment.return_value = [
        {"head": "A", "relation": "has_attr", "tail": "B"}
    ]
    mock_domain = MagicMock()
    mock_domain.get_augmentation.return_value.prompt = "Test prompt {{text}}"
    mock_domain.get_augmentation.return_value.examples = []
    mock_domain.schema.entity_types = []
    mock_domain.schema.relation_types = []

    initial_triples = [Triple(head="X", relation="r", tail="Y")]

    result_triples, metadata = enrichment_strategy(
        client=mock_client,
        domain=mock_domain,
        text="Sample text",
        triples=initial_triples,
        max_iterations=1
    )

    assert len(result_triples) > len(initial_triples)
    assert metadata["strategy"] == "enrichment"
    # Verify augmented triples are CONTEXTUAL
    augmented = [t for t in result_triples if t not in initial_triples]
    assert all(t.inference == InferenceType.CONTEXTUAL for t in augmented)
```

### Integration Test

```python
def test_enrichment_via_orchestrator():
    from unittest.mock import MagicMock
    from kgb.builder import augment_triples
    from kgb.domains import Triple

    mock_client = MagicMock()
    mock_client.augment.return_value = [
        {"head": "NewEntity", "relation": "attr", "tail": "Value"}
    ]
    mock_domain = MagicMock()
    mock_domain.get_augmentation.return_value.prompt = "Test {{text}}"
    mock_domain.get_augmentation.return_value.examples = []
    mock_domain.schema.entity_types = []
    mock_domain.schema.relation_types = []

    initial = [Triple(head="A", relation="r", tail="B")]

    result, metadata = augment_triples(
        client=mock_client,
        domain=mock_domain,
        text="Sample text about A and B.",
        initial_triples=initial,
        augmentation_strategy="enrichment",
        max_iterations=1
    )

    assert len(result) > len(initial)
```

## Key Principles

| Principle | Description |
|-----------|-------------|
| **Use `client.augment()`** | NOT `extract()` — augmentation generates inferred triples without source grounding |
| **Iteration Resilience** | Wrap LLM calls in try-except. Set `metadata["partial_result"] = True` on failure. |
| **Type Safety** | All augmented triples MUST have `inference=InferenceType.CONTEXTUAL` |
| **Stateless Logic** | Copy input triples: `all_triples = list(triples)`. No state between records. |
| **Schema Validation** | Use `validate_triples_against_schema()` + `warn_on_schema_validation()` |
| **Metadata Contract** | Always return `{"strategy": "...", "iterations": [...], "partial_result": bool}` |

## Error Handling

| Exception | When | Action |
|-----------|------|--------|
| `LLMClientError` | API failure | Log, set `partial_result=True`, break loop |
| `ValidationError` | Triple parsing | Log warning, skip triple, continue |
| `DomainResourceError` | Missing prompt/examples | Fail loudly (don't catch) |

## Files to Create/Modify

| File | Action |
|------|--------|
| `kgb/builder/augmentation.py` | Modify — add strategy function with `@register_strategy()` |
| `kgb/domains/<domain>/augmentation/<strategy>/prompt.md` | Create — strategy prompt |
| `kgb/domains/<domain>/augmentation/<strategy>/examples.json` | Create — few-shot examples |
| `kgb/__main__.py` | Modify — add CLI subcommand (optional) |

## Verification Checklist

- [ ] Decorated with `@register_strategy("name")`
- [ ] Conforms to `AugmentationStrategy` Protocol signature
- [ ] Uses `client.augment()` (not `extract()`)
- [ ] Forces `inference=InferenceType.CONTEXTUAL` on all generated triples
- [ ] Uses `collect_schema_constraints()` + `validate_triples_against_schema()`
- [ ] Returns `(all_triples, metadata)` with iteration logs
- [ ] Domain resources created: `augmentation/<name>/prompt.md` + `examples.json`
- [ ] Tests cover strategy function and orchestrator dispatch
