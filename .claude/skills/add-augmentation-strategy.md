# Adding an Augmentation Strategy

This skill documents how to add a new augmentation strategy to the `src/builder` module.

## Overview

Augmentation strategies are iterative graph refinement algorithms that improve the knowledge graph after initial extraction. The system uses:
1. A registry pattern with `@register_strategy()` decorator
2. Protocol-based design for type safety
3. Strategy-specific kwargs for flexibility

## Architecture

```
Step 1: Extraction          Step 2: Augmentation
    Text                        Initial Triples
      │                              │
      ▼                              ▼
extract_from_text           Strategy Dispatcher
      │                       ┌──────┴──────┐
      ▼                       ▼             ▼
Initial Triples        connectivity    your_strategy
                              │             │
                              └──────┬──────┘
                                     ▼
                              Refined Triples
```

**Key Files:**
- `src/builder/augmentation.py` - Strategy Protocol, Registry, implementations
- `src/builder/__init__.py` - Public exports

## Step 1: Understand the Protocol

All strategies must conform to the `AugmentationStrategy` Protocol:

```python
class AugmentationStrategy(Protocol):
    def __call__(
        self,
        client: BaseLLMClient,
        domain: KnowledgeDomain,
        text: str,
        triples: list[Triple],
        **kwargs: Any  # Strategy-specific parameters
    ) -> tuple[list[Triple], dict[str, Any]]:
        """Returns (refined_triples, metadata)."""
        ...
```

Strategy-specific parameters (e.g., `max_iterations`) are passed via `**kwargs`. Define and document them in your strategy's docstring.

## Step 2: Implement Your Strategy

Add to `src/builder/augmentation.py`:

```python
from .augmentation import (
    register_strategy,
    _build_graph_from_triples,  # Converts list[Triple] to NetworkX DiGraph
    _format_example_for_client,  # Transforms domain examples to langextract format
)
from ..clients import BaseLLMClient, LLMClientError
from ..domains import KnowledgeDomain, Triple, InferenceType
from pydantic import ValidationError


@register_strategy("enrichment")
def enrichment_strategy(
    client: BaseLLMClient,
    domain: KnowledgeDomain,
    text: str,
    triples: list[Triple],
    *,
    max_iterations: int = 3,
    temperature: float = 0.0,
    **kwargs: Any
) -> tuple[list[Triple], dict[str, Any]]:
    """Enrichment augmentation: Add missing entity attributes.
    
    Args:
        client: LLM client for generation
        domain: Knowledge domain with prompts/examples
        text: Source text to analyze
        triples: Initial triples from extraction
        max_iterations: Max refinement iterations (default: 3)
        temperature: Sampling temperature for LLM (0.0 = deterministic)
        
    Returns:
        Tuple of (enriched_triples, metadata)
    """
    # 1. Fetch strategy-specific resources from domain
    augmentation = domain.get_augmentation("enrichment")
    aug_prompt = augmentation.prompt
    aug_examples = [_format_example_for_client(ex) for ex in augmentation.examples]
    
    all_triples = list(triples)  # Copy to avoid mutation
    metadata = {"strategy": "enrichment", "iterations": [], "partial_result": False}

    # 2. Iteration loop with error preservation
    for i in range(max_iterations):
        try:
            new_triples_raw = client.generate_json(
                text=aug_prompt.format(text=text, triples=all_triples),
                prompt_description="Enrich entities with missing attributes",
                format_type=Triple,
                temperature=temperature
            )
            
            new_triples = []
            for t_raw in new_triples_raw:
                try:
                    t_dict = t_raw if isinstance(t_raw, dict) else t_raw.model_dump()
                    t_dict["inference"] = InferenceType.CONTEXTUAL
                    new_triples.append(Triple(**t_dict))
                except ValidationError as e:
                    print(f"Warning: Skipping invalid triple: {e}")
                    continue
            
            all_triples.extend(new_triples)
            metadata["iterations"].append({
                "iteration": i + 1,
                "new_triples": len(new_triples),
                "status": "success"
            })
            
        except LLMClientError as e:
            metadata["iterations"].append({
                "iteration": i + 1,
                "status": "failed",
                "error": str(e)
            })
            metadata["partial_result"] = True
            break

    return all_triples, metadata
```

## Step 3: Create Domain Resources

Add prompts and examples for your strategy:

```
src/domains/<domain>/augmentation/enrichment/
├── prompt.txt
└── examples.json
```

**`examples.json` structure:**
```json
[
  {
    "input": {"text": "...", "entities": ["..."]},
    "output": [{"head": "...", "relation": "...", "tail": "..."}]
  }
]
```

## Step 4: Add CLI Subcommand

Update `src/__main__.py`:

```python
@augment_app.command("enrichment")
def augment_enrichment(
    input_file: Path = typer.Option(..., "--input", "-i", exists=True),
    output_dir: Path = typer.Option("outputs/kg_extraction", "--output-dir", "-o"),
    domain: str = typer.Option(..., "--domain", "-d"),
    max_iterations: int = typer.Option(3, "--max-iterations"),
    client: ClientType = typer.Option(ClientType.GEMINI, "--client", "-c"),
):
    """Enrichment augmentation: Add missing entity attributes."""
    from .builder import extract_connected_graph
    from .datasets import load_records
    from .domains import get_domain
    
    records = load_records(input_file, text_field="text", id_field="id")
    domain_obj = get_domain(domain)
    config = _build_client_config(client, ...)
    llm_client = ClientFactory.create(config)
    
    json_dir = output_dir / "extracted_json"
    json_dir.mkdir(parents=True, exist_ok=True)
    
    for record in records:
        record_id = str(record["id"])
        triples, metadata = extract_connected_graph(
            client=llm_client,
            domain=domain_obj,
            text=record["text"],
            augmentation_strategy="enrichment",
            max_iterations=max_iterations
        )
        
        output_path = json_dir / f"{record_id}.json"
        with open(output_path, "w") as f:
            json.dump([t.model_dump() for t in triples], f, indent=2)
```

> See existing `augment_connectivity` command in `src/__main__.py` for complete reference.

## Step 5: Verify

### Check Registration

```bash
python -c "from src.builder import list_strategies; print(list_strategies())"
# Output: ['connectivity', 'enrichment']
```

### Unit Test

```python
def test_enrichment_strategy():
    from unittest.mock import MagicMock
    from src.builder.augmentation import enrichment_strategy
    from src.domains import Triple
    
    mock_client = MagicMock()
    mock_client.generate_json.return_value = [
        {"head": "A", "relation": "has_attr", "tail": "B"}
    ]
    mock_domain = MagicMock()
    mock_domain.get_augmentation.return_value.prompt = "Test prompt"
    mock_domain.get_augmentation.return_value.examples = []
    
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
```

### Integration Test

```python
def test_enrichment_integration():
    from src.domains import get_domain
    from src.builder.augmentation import enrichment_strategy
    from unittest.mock import MagicMock
    
    domain = get_domain("default")
    mock_client = MagicMock()
    mock_client.generate_json.return_value = [
        {"head": "NewEntity", "relation": "attr", "tail": "Value"}
    ]
    
    initial = [Triple(head="A", relation="r", tail="B")]
    
    result, metadata = enrichment_strategy(
        client=mock_client,
        domain=domain,
        text="Sample text about A and B.",
        triples=initial,
        max_iterations=1
    )
    
    augmented = [t for t in result if t not in initial]
    assert all(t.inference == InferenceType.CONTEXTUAL for t in augmented)
```

## Key Principles

| Principle | Description |
|-----------|-------------|
| **Iteration Resilience** | Wrap LLM calls in `try-except LLMClientError`. Set `metadata["partial_result"] = True` on failure. |
| **Type Safety** | Augmented triples must have `inference=InferenceType.CONTEXTUAL`. |
| **Stateless Logic** | Copy input triples: `all_triples = list(triples)`. No state between records. |
| **Metadata Contract** | Always return `{"strategy": "...", "iterations": [...], "partial_result": bool}`. |

## Error Handling

| Exception | When | Action |
|-----------|------|--------|
| `LLMClientError` | API failure | Log, set `partial_result=True`, break loop |
| `ValidationError` | Triple parsing | Log warning, skip triple, continue |
| `DomainResourceError` | Missing prompt/examples | Fail loudly (don't catch) |
