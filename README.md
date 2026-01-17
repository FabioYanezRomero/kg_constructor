# Knowledge Graph Constructor

A modular system for extracting knowledge graphs from text using multiple LLM backends. Supports **Gemini API**, **Ollama**, and **LM Studio** with a unified client abstraction interface.

## Features

- Clean client abstraction layer supporting multiple LLM backends
- Support for Gemini API (cloud), Ollama (local), and LM Studio (local)
- Flexible prompt templates from `src/prompts/`
- Full GraphML export for NetworkX compatibility
- Interactive HTML visualizations using Plotly
- CSV and JSON input support
- Batch processing with progress tracking

## Prerequisites

- Python 3.11+
- **For Gemini**: API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **For Ollama**: [Ollama](https://ollama.ai/) installed and running locally
- **For LM Studio**: [LM Studio](https://lmstudio.ai/) server running with a loaded model
- langextract library (included in requirements)

## Quick Start

### Gemini API (Cloud)
```bash
# Set API key
export LANGEXTRACT_API_KEY="your-gemini-api-key"

# Extract knowledge graphs
python -m kg_constructor.extract_cli \
  --client gemini \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/results \
  --limit 3
```

### Ollama (Local)
```bash
# Ensure Ollama is running locally
python -m kg_constructor.extract_cli \
  --client ollama \
  --model llama3.1 \
  --csv data/legal/sample_data.csv \
  --limit 3
```

### LM Studio (Local)
```bash
# Ensure LM Studio server is running
python -m kg_constructor.extract_cli \
  --client lmstudio \
  --model local-model \
  --base-url http://localhost:1234/v1 \
  --csv data/legal/sample_data.csv \
  --limit 3
```

## Command-Line Usage

### Gemini API
```bash
python -m kg_constructor.extract_cli \
  --client gemini \
  --model gemini-2.0-flash-exp \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/gemini \
  --prompt src/prompts/legal_background_prompt.txt \
  --limit 10
```

### Ollama
```bash
python -m kg_constructor.extract_cli \
  --client ollama \
  --model llama3.1 \
  --base-url http://localhost:11434 \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/ollama \
  --limit 10
```

### LM Studio
```bash
python -m kg_constructor.extract_cli \
  --client lmstudio \
  --model local-model \
  --base-url http://localhost:1234/v1 \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/lmstudio \
  --limit 10
```

### CLI Options

- `--client`: LLM backend to use (`gemini`, `ollama`, `lmstudio`)
- `--model`: Model identifier (e.g., `gemini-2.0-flash-exp`, `llama3.1`)
- `--csv`: Path to input CSV file
- `--output-dir`: Directory for output files
- `--prompt`: Path to prompt template (default: `src/prompts/default_prompt.txt`)
- `--limit`: Maximum number of records to process
- `--base-url`: Base URL for Ollama/LM Studio servers
- `--api-key`: API key for Gemini (or use `LANGEXTRACT_API_KEY` env var)

## Python API

```python
from pathlib import Path
from kg_constructor.clients import ClientConfig
from kg_constructor.extraction_pipeline import ExtractionPipeline

# Configure client
config = ClientConfig(
    client_type="gemini",
    model_id="gemini-2.0-flash-exp",
    api_key="your-key"
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

### Using Different Clients

```python
# Gemini
config = ClientConfig(client_type="gemini", api_key="your-key")

# Ollama
config = ClientConfig(
    client_type="ollama",
    model_id="llama3.1",
    base_url="http://localhost:11434"
)

# LM Studio
config = ClientConfig(
    client_type="lmstudio",
    model_id="local-model",
    base_url="http://localhost:1234/v1"
)
```

## Output Structure

```
outputs/results/
├── extracted_json/       # Triples as JSON
├── graphml/             # GraphML files (NetworkX compatible)
└── visualizations/      # Interactive HTML (Plotly)
```

### JSON Format

Each extracted record produces a JSON file with triples:

```json
{
  "record_id": "row_000001",
  "triples": [
    {
      "head": "Entity 1",
      "relation": "relates to",
      "tail": "Entity 2",
      "inference": "explicit",
      "justification": "Quote from text..."
    }
  ]
}
```

### GraphML Format

GraphML files can be loaded with NetworkX:

```python
import networkx as nx

G = nx.read_graphml("outputs/results/graphml/row_000001.graphml")
```

### Visualizations

Interactive HTML files with Plotly graphs showing:
- Nodes as entities
- Edges as relationships
- Hover tooltips with metadata

## Module Structure

```
src/kg_constructor/
├── clients/                  # Client abstraction layer
│   ├── __init__.py          # Exports
│   ├── base.py              # BaseLLMClient interface
│   ├── factory.py           # ClientConfig & create_client()
│   ├── gemini_client.py     # Gemini API implementation
│   ├── ollama_client.py     # Ollama implementation
│   └── lmstudio_client.py   # LM Studio implementation
│
├── extractor.py             # KnowledgeGraphExtractor
├── extraction_pipeline.py   # ExtractionPipeline
├── extract_cli.py           # Unified CLI
└── json_utils.py            # JSON parsing helpers
```

### Postprocessing Module

```
src/postprocessing/
├── networkX/
│   ├── convert_from_JSON.py  # JSON → GraphML converter
│   └── visualisation.py      # Interactive HTML visualizations
│
└── legacy/                   # Legacy utilities
    ├── networkx_export.py    # NetworkX export
    ├── export_graphs.py      # Graph export utilities
    ├── batch_graphs.py       # Batch processing
    └── postprocess.py        # Post-processing utilities
```

### Prompt Templates

```
src/prompts/
├── default_prompt.txt           # Generic extraction
└── legal_background_prompt.txt  # Legal domain-specific
```

## Project Layout

```
├── README.md
├── requirements.txt
├── src/
│   ├── kg_constructor/          # Main package
│   ├── prompts/                 # Prompt templates
│   └── postprocessing/          # Post-processing tools
├── data/                        # Input data
├── outputs/                     # Output files
├── docs/                        # Documentation
└── examples/                    # Working examples
```

## Architecture

### Client Abstraction Layer

All LLM backends implement the `BaseLLMClient` interface:

```python
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    @abstractmethod
    def extract(
        self,
        text: str,
        prompt_description: str,
        examples: list | None = None,
        format_type: type | None = None,
        temperature: float = 0.0,
        **kwargs
    ) -> list[dict]:
        """Extract structured data from text."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier."""
        pass

    @abstractmethod
    def supports_structured_output(self) -> bool:
        """Whether this client supports structured output."""
        pass
```

### Factory Pattern

The `create_client()` factory creates the appropriate client:

```python
from kg_constructor.clients import create_client, ClientConfig

config = ClientConfig(client_type="gemini")
client = create_client(config)  # Returns GeminiClient
```

### Pipeline Architecture

1. **Extract**: `KnowledgeGraphExtractor` extracts triples from text using any LLM backend
2. **Convert**: `convert_from_JSON` converts JSON triples to GraphML format
3. **Visualize**: `batch_visualize_graphml` creates interactive HTML visualizations

All components are fully decoupled and can be used independently.

## Development

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Format Code

```bash
make format
```

### Custom Prompts

Create custom prompt templates in `src/prompts/`:

```text
Extract entities and relationships from the following text:

{{record_json}}

Return a JSON list of triples with this format:
[
  {
    "head": "Entity 1",
    "relation": "relationship",
    "tail": "Entity 2",
    "inference": "explicit or contextual",
    "justification": "supporting quote"
  }
]
```

Then use it:

```bash
python -m kg_constructor.extract_cli \
  --prompt src/prompts/my_custom_prompt.txt \
  --csv data/my_data.csv
```

## Documentation

- [Unified Extraction Guide](docs/UNIFIED_EXTRACTION_GUIDE.md) - Complete system documentation
- [Quick Reference](README_UNIFIED_EXTRACTION.md) - Fast-start guide
- [Examples](examples/unified_extraction_examples.py) - Working code examples

## Testing

Validate your setup by processing a small sample:

```bash
python -m kg_constructor.extract_cli \
  --client gemini \
  --csv data/legal/sample_data.csv \
  --limit 1 \
  --output-dir outputs/test
```

Check that the output directory contains:
- `extracted_json/` with JSON triples
- `graphml/` with GraphML files
- `visualizations/` with HTML files

## License

See LICENSE file for details.
