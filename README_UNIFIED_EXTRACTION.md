## Unified Knowledge Graph Extraction System

A clean, modular architecture for extracting knowledge graphs from text using multiple LLM backends. Supports **Gemini API**, **Ollama**, and **LM Studio** with a unified interface.

## Quick Start

```bash
# Set API key for Gemini
export LANGEXTRACT_API_KEY="your-gemini-api-key"

# Extract using Gemini API
python -m kg_constructor.extract_cli \
  --client gemini \
  --csv data/legal/sample_data.csv \
  --limit 3

# Extract using Ollama (local)
python -m kg_constructor.extract_cli \
  --client ollama \
  --model llama3.1 \
  --csv data/legal/sample_data.csv \
  --limit 3

# Extract using LM Studio (local)
python -m kg_constructor.extract_cli \
  --client lmstudio \
  --model local-model \
  --csv data/legal/sample_data.csv \
  --limit 3
```

## Architecture

The system follows clean software design principles with a client abstraction layer:

```
Client Interface (BaseLLMClient)
    ├── GeminiClient      (Cloud API)
    ├── OllamaClient      (Local server)
    └── LMStudioClient    (Local server)
          ↓
KnowledgeGraphExtractor
    - Loads prompts from src/prompts/
    - Unified extraction interface
          ↓
ExtractionPipeline
    - Reuses convert_from_JSON.py
    - Reuses visualisation.py
    - Produces identical outputs
```

## New Module Structure

```
src/kg_constructor/
├── clients/                  # ✨ NEW: Client abstraction layer
│   ├── base.py              # Interface definition
│   ├── factory.py           # ClientConfig & factory
│   ├── gemini_client.py     # Gemini implementation
│   ├── ollama_client.py     # Ollama implementation
│   └── lmstudio_client.py   # LM Studio implementation
│
├── extractor.py             # ✨ NEW: Unified extractor
├── extraction_pipeline.py   # ✨ NEW: Unified pipeline
├── extract_cli.py           # ✨ NEW: Unified CLI
│
├── vllm_client.py          # DEPRECATED
└── pipeline.py             # DEPRECATED
```

## Features

- **Multiple Backends**: Switch between Gemini, Ollama, LM Studio
- **Clean Architecture**: Client abstraction with factory pattern
- **Prompt Templates**: Load from `src/prompts/` directory
- **Reuses Existing Code**: 100% compatible with GraphML/visualization
- **Identical Outputs**: Same format regardless of backend
- **Easy Migration**: Simple API changes from old code

## Python API Examples

### Gemini API (Cloud)

```python
from pathlib import Path
from kg_constructor.clients import ClientConfig
from kg_constructor.extraction_pipeline import ExtractionPipeline

# Configure Gemini
config = ClientConfig(
    client_type="gemini",
    model_id="gemini-2.0-flash-exp",
    api_key="your-key",
    temperature=0.0
)

# Create pipeline
pipeline = ExtractionPipeline(
    output_dir=Path("outputs/results"),
    client_config=config,
    prompt_path=Path("src/prompts/legal_background_prompt.txt")
)

# Run extraction
results = pipeline.run_full_pipeline(
    csv_path=Path("data/legal/sample_data.csv"),
    limit=5
)
```

### Ollama (Local)

```python
from kg_constructor.clients import ClientConfig
from kg_constructor.extraction_pipeline import ExtractionPipeline

# Configure Ollama
config = ClientConfig(
    client_type="ollama",
    model_id="llama3.1",
    base_url="http://localhost:11434",
    max_workers=5  # Lower for local
)

# Create and run pipeline
pipeline = ExtractionPipeline(
    output_dir=Path("outputs/ollama_results"),
    client_config=config
)

results = pipeline.run_full_pipeline(
    csv_path=Path("data/legal/sample_data.csv")
)
```

### LM Studio (Local)

```python
from kg_constructor.clients import ClientConfig
from kg_constructor.extraction_pipeline import ExtractionPipeline

# Configure LM Studio
config = ClientConfig(
    client_type="lmstudio",
    model_id="your-model-name",
    base_url="http://localhost:1234/v1"
)

# Create and run pipeline
pipeline = ExtractionPipeline(
    output_dir=Path("outputs/lmstudio_results"),
    client_config=config
)

results = pipeline.run_full_pipeline(
    csv_path=Path("data/legal/sample_data.csv")
)
```

## CLI Reference

```bash
# Basic options
--client {gemini,ollama,lmstudio}  # Choose backend
--csv PATH                         # Input CSV file
--output-dir PATH                  # Output directory
--limit N                          # Limit records

# Model configuration
--model MODEL_ID                   # Model identifier
--api-key KEY                      # Gemini API key
--base-url URL                     # Ollama/LM Studio URL
--temperature FLOAT                # Sampling temperature

# Prompt configuration
--prompt PATH                      # Custom prompt template

# Pipeline options
--no-visualizations               # Skip HTML generation
--no-progress                     # Hide progress bar
```

## Output Structure

All backends produce identical outputs:

```
outputs/
└── [client]_results/
    ├── extracted_json/      # Triples as JSON
    ├── graphml/            # GraphML files
    └── visualizations/     # Interactive HTML
```

## Comparison Table

| Feature | Gemini | Ollama | LM Studio | Legacy vLLM |
|---------|--------|--------|-----------|-------------|
| Setup | API key | Server | Server | Server + GPU |
| Location | Cloud | Local | Local | Local |
| Cost | Pay-per-use | Free | Free | Free |
| Scalability | High | Limited | Limited | Limited |
| Structured Output | ✓ | Limited | Limited | Limited |
| Output Format | ✓ | ✓ | ✓ | ✓ |

## Migration from Old Code

### From vLLMClient

**Before:**
```python
from kg_constructor.vllm_client import VLLMClient
client = VLLMClient(base_url="http://localhost:8000")
```

**After:**
```python
from kg_constructor.clients import LMStudioClient
client = LMStudioClient(base_url="http://localhost:1234/v1")
```

### From LangExtract Module

**Before:**
```python
from kg_constructor.langextract_pipeline import LangExtractPipeline
pipeline = LangExtractPipeline(output_dir=Path("outputs"))
```

**After:**
```python
from kg_constructor.extraction_pipeline import ExtractionPipeline
from kg_constructor.clients import ClientConfig

config = ClientConfig(client_type="gemini")
pipeline = ExtractionPipeline(
    output_dir=Path("outputs"),
    client_config=config
)
```

## Prompt Templates

Located in `src/prompts/`:

- **`default_prompt.txt`** - Generic extraction
- **`legal_background_prompt.txt`** - Legal domain

Use `--prompt` or `prompt_path` parameter to specify:

```python
pipeline = ExtractionPipeline(
    output_dir=Path("outputs"),
    client_config=config,
    prompt_path=Path("src/prompts/legal_background_prompt.txt")
)
```

## Integration with Existing Code

The new system **reuses all existing postprocessing**:

1. **GraphML Conversion**: `postprocessing.networkX.convert_from_JSON`
2. **Visualization**: `postprocessing.networkX.visualisation`

This ensures **100% compatibility** with existing workflows and tools.

## Documentation

- **[Complete Guide](docs/UNIFIED_EXTRACTION_GUIDE.md)** - Detailed documentation
- **[Examples](examples/unified_extraction_examples.py)** - Working code examples

## Environment Variables

- `LANGEXTRACT_API_KEY` - Gemini API key
- `GOOGLE_API_KEY` - Alternative for Gemini

## Requirements

### For Gemini

- API key from Google AI Studio

### For Ollama

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Start server
ollama serve

# Pull model
ollama pull llama3.1
```

### For LM Studio

1. Download from [lmstudio.ai](https://lmstudio.ai)
2. Load a model in the UI
3. Enable server mode

## Examples

Run the examples:

```bash
python examples/unified_extraction_examples.py
```

Includes:
- Gemini API extraction
- Ollama local extraction (info)
- LM Studio extraction (info)
- Direct client usage
- Full pipeline execution
- Client comparison
- Custom prompts

## Design Patterns

- **Strategy Pattern**: Interchangeable client implementations
- **Factory Pattern**: ClientConfig + create_client()
- **Template Method**: Prompt loading from files
- **Dependency Injection**: Client passed to extractor/pipeline

## License

Part of the Knowledge Graph Constructor project.
