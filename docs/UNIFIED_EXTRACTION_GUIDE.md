## Unified Knowledge Graph Extraction System

This system provides a clean, modular architecture for extracting knowledge graphs from text using multiple LLM backends (Gemini API, Ollama, LM Studio). All backends produce identical output formats compatible with the existing GraphML conversion and visualization pipeline.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Client Abstraction Layer                   │
├─────────────────────────────────────────────────────────────┤
│  BaseLLMClient (Interface)                                   │
│    ├── GeminiClient      (Gemini API via langextract)       │
│    ├── OllamaClient      (Ollama via langextract)           │
│    └── LMStudioClient    (LM Studio via langextract)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              KnowledgeGraphExtractor                         │
│  - Loads prompts from src/prompts/                          │
│  - Uses client abstraction for extraction                    │
│  - Returns standardized triple format                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              ExtractionPipeline                              │
│  - Orchestrates extraction workflow                          │
│  - Reuses convert_from_JSON.py for GraphML conversion       │
│  - Reuses visualisation.py for HTML generation              │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

```
src/kg_constructor/
├── clients/                    # Client abstraction layer
│   ├── __init__.py
│   ├── base.py                # BaseLLMClient interface
│   ├── factory.py             # ClientConfig & create_client()
│   ├── gemini_client.py       # Gemini API implementation
│   ├── ollama_client.py       # Ollama implementation
│   └── lmstudio_client.py     # LM Studio implementation
│
├── extractor.py               # KnowledgeGraphExtractor
├── extraction_pipeline.py     # ExtractionPipeline
├── extract_cli.py             # Unified CLI
│
├── vllm_client.py            # DEPRECATED (kept for legacy support)
├── pipeline.py               # DEPRECATED (kept for legacy support)
└── langextract_*.py          # DEPRECATED (superseded by new architecture)
```

## Quick Start

### Command-Line Interface

The unified CLI supports all backends:

#### Using Gemini API (Cloud)

```bash
export LANGEXTRACT_API_KEY="your-gemini-api-key"

python -m kg_constructor.extract_cli \
  --client gemini \
  --model gemini-2.0-flash-exp \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/gemini_results \
  --limit 3
```

#### Using Ollama (Local)

```bash
# Start Ollama server first: ollama serve
# Pull a model: ollama pull llama3.1

python -m kg_constructor.extract_cli \
  --client ollama \
  --model llama3.1 \
  --base-url http://localhost:11434 \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/ollama_results \
  --limit 3
```

#### Using LM Studio (Local)

```bash
# Start LM Studio server and load a model

python -m kg_constructor.extract_cli \
  --client lmstudio \
  --model local-model \
  --base-url http://localhost:1234/v1 \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/lmstudio_results \
  --limit 3
```

### Python API

#### Example 1: Using Gemini Client

```python
from pathlib import Path
from kg_constructor.clients import ClientConfig
from kg_constructor.extraction_pipeline import ExtractionPipeline

# Configure Gemini client
config = ClientConfig(
    client_type="gemini",
    model_id="gemini-2.0-flash-exp",
    api_key="your-key",
    temperature=0.0,
    max_workers=10
)

# Create pipeline
pipeline = ExtractionPipeline(
    output_dir=Path("outputs/gemini_results"),
    client_config=config,
    prompt_path=Path("src/prompts/legal_background_prompt.txt")
)

# Run full pipeline
results = pipeline.run_full_pipeline(
    csv_path=Path("data/legal/sample_data.csv"),
    text_column="background",
    id_column="id",
    limit=5
)

print(f"Model: {results['model']}")
print(f"GraphML files: {len(results['graphml_files'])}")
```

#### Example 2: Using Ollama Client

```python
from pathlib import Path
from kg_constructor.clients import ClientConfig
from kg_constructor.extraction_pipeline import ExtractionPipeline

# Configure Ollama client
config = ClientConfig(
    client_type="ollama",
    model_id="llama3.1",
    base_url="http://localhost:11434",
    temperature=0.0,
    max_workers=5  # Lower for local models
)

# Create pipeline
pipeline = ExtractionPipeline(
    output_dir=Path("outputs/ollama_results"),
    client_config=config
)

# Run pipeline
results = pipeline.run_full_pipeline(
    csv_path=Path("data/legal/sample_data.csv"),
    limit=3
)
```

#### Example 3: Using LM Studio Client

```python
from pathlib import Path
from kg_constructor.clients import ClientConfig
from kg_constructor.extraction_pipeline import ExtractionPipeline

# Configure LM Studio client
config = ClientConfig(
    client_type="lmstudio",
    model_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    base_url="http://localhost:1234/v1",
    temperature=0.0
)

# Create pipeline
pipeline = ExtractionPipeline(
    output_dir=Path("outputs/lmstudio_results"),
    client_config=config
)

# Run pipeline
results = pipeline.run_full_pipeline(
    csv_path=Path("data/legal/sample_data.csv"),
    limit=3
)
```

#### Example 4: Direct Client Usage

```python
from kg_constructor.extractor import KnowledgeGraphExtractor
from kg_constructor.clients import GeminiClient

# Create client directly
client = GeminiClient(
    model_id="gemini-2.0-flash-exp",
    api_key="your-key"
)

# Create extractor
extractor = KnowledgeGraphExtractor(
    client=client,
    prompt_path="src/prompts/default_prompt.txt"
)

# Extract from text
text = "Your text here..."
triples = extractor.extract_from_text(text)

for triple in triples:
    print(f"{triple['head']} -> {triple['relation']} -> {triple['tail']}")
```

## Configuration Reference

### ClientConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `client_type` | str | `"gemini"` | Client type: "gemini", "ollama", or "lmstudio" |
| `model_id` | str | Auto | Model identifier (provider-specific) |
| `temperature` | float | 0.0 | Sampling temperature (0.0 = deterministic) |
| `max_workers` | int | Auto | Parallel workers (10 for cloud, 5 for local) |
| `batch_length` | int | Auto | Chunks per batch (10 for cloud, 5 for local) |
| `max_char_buffer` | int | 8000 | Maximum characters per inference |
| `show_progress` | bool | True | Show progress bar |
| `api_key` | str | None | API key (Gemini only) |
| `base_url` | str | Auto | Server URL (Ollama/LM Studio) |
| `timeout` | int | 120 | Request timeout in seconds (local only) |

### Default Model IDs

- **Gemini**: `gemini-2.0-flash-exp`
- **Ollama**: `llama3.1`
- **LM Studio**: `local-model`

### Default Base URLs

- **Ollama**: `http://localhost:11434`
- **LM Studio**: `http://localhost:1234/v1`

## Prompt Templates

Prompts are loaded from `src/prompts/`:

- **`default_prompt.txt`** - Generic knowledge graph extraction
- **`legal_background_prompt.txt`** - Legal domain-specific extraction

Use `--prompt` flag or `prompt_path` parameter to specify custom templates.

### Prompt Template Variables

Templates can use the following placeholders:

- `{{record_json}}` - JSON representation of the input record

Example:
```
Extract knowledge graph triples from the following text:

{{record_json}}

Return a JSON array of triples with head, relation, tail, inference.
```

## Output Format

All clients produce identical output format:

### JSON Triples

```json
[
  {
    "head": "Entity A",
    "relation": "related_to",
    "tail": "Entity B",
    "inference": "explicit"
  },
  {
    "head": "Entity C",
    "relation": "involves",
    "tail": "Entity A",
    "inference": "contextual",
    "justification": "Bridges disconnected components"
  }
]
```

### Directory Structure

```
outputs/
└── [client]_results/
    ├── extracted_json/       # JSON triples
    │   ├── case-001.json
    │   └── case-002.json
    ├── graphml/             # GraphML files (via convert_from_JSON.py)
    │   ├── case-001.graphml
    │   └── case-002.graphml
    └── visualizations/      # HTML files (via visualisation.py)
        ├── case-001.html
        └── case-002.html
```

## Integration with Existing Code

The new architecture **reuses all existing postprocessing code**:

1. **GraphML Conversion**: Uses `postprocessing.networkX.convert_from_JSON`
   - Entity normalization
   - Graph construction
   - NetworkX compatibility

2. **Visualization**: Uses `postprocessing.networkX.visualisation`
   - Interactive Plotly graphs
   - Node/edge styling
   - Hover information

This ensures **100% compatibility** with existing tools and workflows.

## Comparison Matrix

| Feature | Gemini | Ollama | LM Studio | Legacy vLLM |
|---------|--------|--------|-----------|-------------|
| Setup Complexity | Low (API key) | Medium (server) | Medium (server) | High (server + GPU) |
| Infrastructure | Cloud | Local | Local | Local |
| Scalability | High | Hardware-limited | Hardware-limited | Hardware-limited |
| Cost | Pay-per-use | Free | Free | Free |
| Structured Output | ✓ (native) | Limited | Limited | Limited |
| Parallel Processing | ✓ (10+ workers) | Limited (5 workers) | Limited (5 workers) | Limited |
| Output Format | Identical | Identical | Identical | Identical |

## Migration Guide

### From vLLM Client

**Old code:**
```python
from kg_constructor.vllm_client import VLLMClient

client = VLLMClient(
    base_url="http://localhost:8000",
    model="my-model"
)
```

**New code:**
```python
from kg_constructor.clients import LMStudioClient

client = LMStudioClient(
    model_id="my-model",
    base_url="http://localhost:1234/v1"
)
```

### From LangExtract Module

**Old code:**
```python
from kg_constructor.langextract_pipeline import LangExtractPipeline

pipeline = LangExtractPipeline(output_dir=Path("outputs"))
```

**New code:**
```python
from kg_constructor.extraction_pipeline import ExtractionPipeline
from kg_constructor.clients import ClientConfig

config = ClientConfig(client_type="gemini")
pipeline = ExtractionPipeline(
    output_dir=Path("outputs"),
    client_config=config
)
```

## Best Practices

1. **Use Gemini for Production**: Best quality and scalability
2. **Use Ollama for Development**: Fast local testing
3. **Use LM Studio for Custom Models**: Fine-tuned domain-specific models
4. **Set Temperature=0.0**: For reproducible results
5. **Lower Workers for Local**: Prevent resource exhaustion
6. **Use Custom Prompts**: For domain-specific extraction
7. **Leverage Examples**: Few-shot learning improves quality

## Troubleshooting

### Gemini API Issues

```
Error: No API key provided
```
**Solution**: Set `LANGEXTRACT_API_KEY` or `--api-key`

### Ollama Connection Errors

```
Error: Failed to connect to Ollama server
```
**Solution**:
1. Start Ollama: `ollama serve`
2. Verify URL: `http://localhost:11434`
3. Pull model: `ollama pull llama3.1`

### LM Studio Connection Errors

```
Error: Failed to connect to LM Studio
```
**Solution**:
1. Start LM Studio server
2. Load a model in the UI
3. Verify URL: `http://localhost:1234/v1`

### Memory Issues (Local)

```
Out of memory
```
**Solution**:
1. Reduce `max_workers` to 1-3
2. Reduce `batch_length` to 1-3
3. Reduce `max_char_buffer` to 4000

## Environment Variables

- `LANGEXTRACT_API_KEY` - Gemini API key
- `GOOGLE_API_KEY` - Alternative for Gemini
- No environment variables needed for Ollama/LM Studio

## License

Part of the Knowledge Graph Constructor project.
