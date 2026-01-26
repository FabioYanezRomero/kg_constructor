# Unified Knowledge Graph Extraction System

This system provides a modular architecture for extracting knowledge graphs from text using multiple LLM backends (Gemini API, Ollama, LM Studio). All backends produce identical output formats compatible with GraphML conversion and visualization.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Client Abstraction Layer                  │
├─────────────────────────────────────────────────────────────┤
│  BaseLLMClient (Interface)                                  │
│    ├── GeminiClient      (Gemini API via langextract)       │
│    ├── OllamaClient      (Ollama via langextract)           │
│    └── LMStudioClient    (LM Studio via langextract)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Builder Module                                 │
│  - extraction.py: Extract triples from text                 │
│  - augmentation.py: Connectivity augmentation               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Output Modules                                 │
│  - converters/: JSON → GraphML conversion                   │
│  - visualization/: Network & extraction visualizations      │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

```
src/
├── clients/                    # Client abstraction layer
│   ├── base.py                # BaseLLMClient interface
│   ├── config.py              # ClientConfig
│   └── providers/
│       ├── gemini.py          # Gemini API implementation
│       ├── ollama.py          # Ollama implementation
│       └── lmstudio.py        # LM Studio implementation
│
├── builder/                   # Core extraction logic
│   ├── extraction.py          # Triple extraction
│   └── augmentation.py        # Connectivity augmentation
│
├── domains/                   # Domain-specific prompts
│   ├── default/
│   └── legal/
│
├── converters/                # Output format converters
│   └── graphml.py
│
└── visualization/             # Visualization engines
    ├── network.py
    └── extraction.py
```

## Quick Start

### Command-Line Interface

The unified CLI is accessed via `python -m src`:

```bash
# List available commands
python -m src --help

# List available domains and clients
python -m src list domains
python -m src list clients
```

#### Using LM Studio (Local)

```bash
python -m src extract \
  --input data/legal/legal_background.jsonl \
  --output-dir outputs/lmstudio \
  --client lmstudio \
  --model local-model \
  --base-url http://host.docker.internal:1234/v1 \
  --domain legal \
  --mode open
```

#### Using Ollama (Local)

```bash
python -m src extract \
  --input data/legal/legal_background.jsonl \
  --output-dir outputs/ollama \
  --client ollama \
  --model gemma3:27b \
  --base-url http://host.docker.internal:11434 \
  --domain legal \
  --mode open
```

#### Using Gemini API (Cloud)

```bash
export LANGEXTRACT_API_KEY="your-gemini-api-key"

python -m src extract \
  --input data/legal/legal_background.jsonl \
  --output-dir outputs/gemini \
  --client gemini \
  --model gemini-2.0-flash-exp \
  --domain legal \
  --mode open
```

### Full Pipeline

Run extraction → augmentation → conversion → visualization:

```bash
# Step 1: Extract triples
python -m src extract --input data.jsonl --output-dir out --client lmstudio

# Step 2: Augment connectivity
python -m src augment connectivity --input data.jsonl --output-dir out --client lmstudio

# Step 3: Convert to GraphML
python -m src convert --input out/extracted_json --output out/graphml

# Step 4: Visualize
python -m src visualize network --input out/graphml --output out/network_viz
python -m src visualize extraction --input data.jsonl --triples out/extracted_json --output out/extraction_viz
```

Or use the test scripts for a complete pipeline:

```bash
./test_single_extraction_lmstudio.sh
./test_single_extraction_ollama.sh
```

## Configuration Reference

### CLI Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `--input` | path | Input JSONL file |
| `--output-dir` | path | Output directory |
| `--client` | str | Client: `gemini`, `ollama`, `lmstudio` |
| `--model` | str | Model identifier |
| `--base-url` | str | Server URL (local clients) |
| `--domain` | str | Domain: `default`, `legal` |
| `--mode` | str | Mode: `open`, `constrained` |
| `--text-field` | str | JSON field containing text (default: `text`) |
| `--id-field` | str | JSON field containing ID (default: `id`) |
| `--record-ids` | str | Comma-separated IDs to process |
| `--temp` | float | Temperature (default: 0.0) |
| `--workers` | int | Parallel workers |
| `--timeout` | int | Request timeout in seconds |

### Default Base URLs

- **LM Studio**: `http://localhost:1234/v1`
- **Ollama**: `http://localhost:11434`
- **Docker**: Use `http://host.docker.internal:PORT` to access host services

## Output Format

All clients produce identical output:

### JSON Triples

```json
[
  {
    "head": "Sigma Finance Corporation",
    "relation": "is_a",
    "tail": "structured investment vehicle (SIV)",
    "inference": "explicit",
    "justification": null
  },
  {
    "head": "Sigma",
    "relation": "connected_to",
    "tail": "The Legal Case",
    "inference": "contextual",
    "justification": "Connects Component 2 to hub node."
  }
]
```

### Directory Structure

```
outputs/
├── extracted_json/       # JSON triples
│   └── record-001.json
├── graphml/              # GraphML files
│   └── record-001.graphml
├── network_viz/          # Network visualizations
│   └── record-001.html
└── extraction_viz/       # Extraction visualizations
    └── record-001.html
```

## Domain Configuration

Domains are configured in `src/domains/{domain}/`:

```
src/domains/legal/
├── extraction/
│   ├── prompt_open.txt
│   ├── prompt_constrained.txt
│   └── examples.json
└── augmentation/
    └── connectivity/
        ├── prompt.txt
        └── examples.json
```

Use the `add-domain` skill to create new domains.

## Comparison Matrix

| Feature | Gemini | Ollama | LM Studio |
|---------|--------|--------|-----------|
| Setup | API key | Server | Server |
| Infrastructure | Cloud | Local | Local |
| Cost | Pay-per-use | Free | Free |
| Parallel Processing | High | Limited | Limited |
| Structured Output | Native | Via prompt | Via prompt |

## Best Practices

1. **Use Temperature=0.0**: For reproducible results
2. **Use Docker URLs**: `host.docker.internal` for container access
3. **Lower Workers for Local**: Prevent resource exhaustion (3-5)
4. **Use Domain Prompts**: Domain-specific prompts improve quality
5. **Include Few-Shot Examples**: Improve extraction accuracy

## Troubleshooting

### Connection Errors

```
Error: Cannot connect to server
```

**Solution**:
1. Verify server is running
2. Check URL (use `host.docker.internal` in Docker)
3. Ensure model is loaded

### Memory Issues

```
Out of memory
```

**Solution**:
1. Reduce `--workers` to 1-3
2. Increase `--timeout`
3. Use smaller model

### Empty Extractions

**Solution**:
1. Check prompt template matches domain
2. Verify input text field name
3. Test with `--record-ids` for single record

## Environment Variables

- `LANGEXTRACT_API_KEY` - Gemini API key
- `GOOGLE_API_KEY` - Alternative for Gemini
