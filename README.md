# Knowledge Graph Constructor

A modular system for extracting knowledge graphs from text using multiple LLM backends. Supports **Gemini API**, **Ollama**, and **LM Studio** with a unified client abstraction interface.

## ✨ Features

### Core Capabilities
- **Multi-Backend LLM Support**: Clean abstraction layer for Gemini API (cloud), Ollama (local), and LM Studio (local)
- **Knowledge Graph Extraction**: Extract structured triples (head-relation-tail) from unstructured text
- **Graph Augmentation**: Iterative refinement strategies to improve graph connectivity
- **Multiple Export Formats**: GraphML (NetworkX compatible), JSON, with extensible converter system
- **Interactive Visualizations**: Plotly-based network graphs and entity highlighting with dark mode support

### Data Handling
- **Multiple Input Formats**: CSV, JSON, and JSONL file support with auto-detection
- **Batch Processing**: Process large datasets with progress tracking
- **Domain-Specific Extraction**: Customizable prompts and examples per knowledge domain

---

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Prerequisites

- Python 3.11+
- **For Gemini**: API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **For Ollama**: [Ollama](https://ollama.ai/) installed and running locally
- **For LM Studio**: [LM Studio](https://lmstudio.ai/) server running with a loaded model

### Basic Usage

```bash
# Extract with Gemini
kg_constructor extract --input data.jsonl --domain legal --client gemini

# Extract with Ollama
kg_constructor extract --input data.jsonl --domain default --client ollama --model llama3.1

# Extract with LM Studio
kg_constructor extract --input data.csv --domain legal --client lmstudio --base-url http://localhost:1234/v1
```

---

## 📋 Available Commands

| Command | Description |
|---------|-------------|
| `extract` | Extract knowledge graph triples from text (Step 1) |
| `augment connectivity` | Reduce disconnected graph components (Step 2) |
| `convert` | Convert JSON triples to GraphML format |
| `visualize network` | Create interactive network visualizations |
| `visualize extraction` | Create text visualizations with entity highlights |
| `list domains` | List available knowledge domains |
| `list clients` | List available LLM client types |

### Step 1: Extract

```bash
kg_constructor extract \
  --input data.jsonl \
  --domain legal \
  --client gemini \
  --output-dir outputs/kg_extraction \
  --limit 10
```

**Options:**
- `--input, -i`: Input file (JSONL, JSON, or CSV)
- `--domain, -d`: Knowledge domain (default, legal)
- `--client, -c`: LLM backend (gemini, ollama, lmstudio)
- `--model`: Model identifier (optional, uses defaults)
- `--output-dir, -o`: Output directory
- `--text-field`: Field containing text (default: "text")
- `--id-field`: Field for record IDs (default: "id")
- `--limit`: Maximum records to process
- `--temperature`: LLM temperature (default: 0.0)
- `--workers`: Max parallel workers
- `--timeout`: Request timeout in seconds

### Step 2: Augment

```bash
kg_constructor augment connectivity \
  --input data.jsonl \
  --domain legal \
  --client gemini \
  --max-iterations 3
```

**Options:**
- `--max-iterations`: Max refinement iterations (default: 3)
- All extraction options apply

### Convert

```bash
kg_constructor convert --input outputs/extracted_json --output outputs/graphml
```

### Visualize

```bash
# Network visualization
kg_constructor visualize network --input outputs/graphml --dark-mode

# Entity extraction visualization
kg_constructor visualize extraction --input data.jsonl --triples outputs/extracted_json
```

---

## 📁 Output Structure

```
outputs/kg_extraction/
├── extracted_json/       # JSON triples with metadata
├── graphml/              # NetworkX-compatible GraphML files
└── visualizations/       # Interactive HTML visualizations
```

### JSON Triple Format

```json
{
  "head": "Entity 1",
  "relation": "relates to",
  "tail": "Entity 2",
  "inference": "explicit",
  "char_start": 0,
  "char_end": 25,
  "extraction_text": "Entity 1 relates to Entity 2"
}
```

---

## 🔧 Architecture

### Module Structure

```
kg_constructor/
├── __init__.py              # Package initialization
├── __main__.py              # CLI entry point (Typer-based)
├── builder/                 # Graph construction
│   ├── extraction.py        # Initial triple extraction
│   └── augmentation.py      # Augmentation strategies (connectivity, etc.)
├── clients/                 # LLM client abstraction
│   ├── base.py              # BaseLLMClient interface
│   ├── config.py            # ClientConfig dataclass
│   ├── factory.py           # ClientFactory for client creation
│   └── providers/           # Provider implementations
│       ├── gemini.py        # Gemini API client
│       ├── ollama.py        # Ollama client
│       └── lmstudio.py      # LM Studio client
├── converters/              # Output format converters
│   └── graphml.py           # JSON → GraphML converter
├── datasets/                # Input format loaders
│   └── __init__.py          # CSV, JSON, JSONL loaders
├── domains/                 # Knowledge domain definitions
│   ├── base.py              # KnowledgeDomain base class
│   ├── registry.py          # Domain registration
│   ├── models.py            # Triple, Example Pydantic models
│   ├── default/             # Default domain resources
│   └── legal/               # Legal domain resources
└── visualization/           # Visualization engines
    ├── network_viz.py       # Plotly network graphs
    └── entity_viz.py        # Entity text highlighting
```

### Client Abstraction

All LLM backends implement the `BaseLLMClient` interface:

```python
from kg_constructor.clients import ClientFactory, ClientConfig

config = ClientConfig(
    client_type="gemini",
    model_id="gemini-2.0-flash-exp",
    api_key="your-key"
)
client = ClientFactory.create(config)

result = client.extract(
    text="Sample document text...",
    prompt_description="Extract entities and relationships"
)
```

### Domain System

Domains define prompts and examples for specific knowledge areas:

```python
from kg_constructor.domains import get_domain, list_available_domains

# List available domains
print(list_available_domains())  # ['default', 'legal']

# Get domain with resources
domain = get_domain("legal")
prompt = domain.extraction.prompt
examples = domain.extraction.examples
```

---

## 🛠️ Extensibility (Agent Skills)

This repository includes Claude agent skills for guided extensibility:

| Skill | Description |
|-------|-------------|
| `add-llm-client` | Add new LLM provider (e.g., Anthropic, OpenAI, Groq) |
| `add-domain` | Create new knowledge domain with prompts and examples |
| `add-augmentation-strategy` | Add graph refinement strategy (e.g., enrichment, summarization) |
| `add-converter` | Add output format converter (e.g., CSV, RDF, JSON-LD) |
| `add-dataset-format` | Add input format loader (e.g., Parquet, Excel) |
| `add-visualization` | Add visualization type (e.g., timeline, hierarchical) |

### Skill Locations

Skills are located in `.agent/skills/` and provide step-by-step guides with:
- Architecture diagrams
- Complete code implementations
- CLI integration patterns
- Unit and integration tests
- Error handling reference

---

## 🗂️ Supported Domains

| Domain | Description | Resources |
|--------|-------------|-----------|
| `default` | Generic entity-relationship extraction | Open/constrained prompts, examples |
| `legal` | Legal document analysis | Legal-specific prompts, entity types |

### Domain Structure

```
kg_constructor/domains/<domain>/
├── __init__.py                 # Domain class with @domain decorator
├── extraction/
│   ├── prompt_open.txt         # Open extraction prompt
│   ├── prompt_constrained.txt  # Type-constrained extraction
│   └── examples.json           # Few-shot examples
├── augmentation/
│   └── connectivity/           # Augmentation strategy resources
│       ├── prompt.txt
│       └── examples.json
└── schema.json                 # Entity/relation type constraints (optional)
```

---

## 🔌 LLM Clients

| Client | Type | Default Model | Requirements |
|--------|------|---------------|--------------|
| `gemini` | Cloud | gemini-2.0-flash | `LANGEXTRACT_API_KEY` env var |
| `ollama` | Local | llama3.1 | Ollama running on localhost:11434 |
| `lmstudio` | Local | (loaded model) | LM Studio server running |

### Environment Variables

```bash
export LANGEXTRACT_API_KEY="your-gemini-api-key"
```

---

## 📊 Visualization Options

### Network Visualization

- **Layouts**: spring, circular, kamada_kawai, shell
- **Dark Mode**: Premium dark theme with glassmorphism
- **Interactive**: Hover tooltips, zoom, pan

### Entity Visualization

- **Text Highlighting**: Entity spans with color coding
- **Animations**: Smooth highlight transitions
- **Grouping**: By entity type or relation

---

## 🧪 Testing

```bash
# Quick validation
kg_constructor extract --input data/sample.jsonl --domain default --limit 1

# List available resources
kg_constructor list domains
kg_constructor list clients
```

---

## 📖 Documentation

- [Unified Extraction Guide](docs/UNIFIED_EXTRACTION_GUIDE.md) - Complete system documentation
- [Agent Skills](.agent/skills/) - Extensibility guides for developers

---

## 📄 License

See LICENSE file for details.
