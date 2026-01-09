# LangExtract Knowledge Graph Extraction Module

This module provides a complete pipeline for extracting knowledge graphs from legal case text using the **langextract** library instead of local language models. It reuses all existing GraphML conversion and visualization code.

## Overview

The langextract module consists of three main components:

1. **`langextract_extractor.py`** - Core extraction logic using langextract API
2. **`langextract_pipeline.py`** - Pipeline orchestration for batch processing
3. **`langextract_cli.py`** - Command-line interface for easy usage

## Features

- Entity and relation extraction using langextract with Gemini models
- Reuses existing GraphML conversion code from `convert_from_JSON.py`
- Reuses existing visualization code from `visualisation.py`
- Supports batch processing of CSV files
- Configurable extraction parameters
- Few-shot learning with legal domain examples
- Parallel processing for efficiency
- Progress tracking and error handling

## Installation

The langextract library is already installed. Ensure you have an API key for Google's Gemini models.

## Quick Start

### Command-Line Usage

The easiest way to use the module is via the command-line interface:

```bash
# Set your API key
export LANGEXTRACT_API_KEY="your-gemini-api-key"
# or
export GOOGLE_API_KEY="your-gemini-api-key"

# Process a CSV file (limit to 3 records for testing)
python -m kg_constructor.langextract_cli \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/langextract_results \
  --limit 3

# Full pipeline with all records
python -m kg_constructor.langextract_cli \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/langextract_results \
  --model gemini-2.0-flash-exp \
  --temperature 0.0 \
  --max-workers 10
```

### Python API Usage

#### Example 1: Extract from Single Text

```python
from kg_constructor.langextract_extractor import ExtractionConfig, LangExtractExtractor

# Create extractor with custom config
config = ExtractionConfig(
    model_id="gemini-2.0-flash-exp",
    temperature=0.0,
    max_workers=10
)
extractor = LangExtractExtractor(config)

# Extract triples from text
text = "Your legal case background text here..."
triples = extractor.extract_from_text(text, record_id="case-001")

for triple in triples:
    print(f"{triple['head']} -> {triple['relation']} -> {triple['tail']}")
```

#### Example 2: Full Pipeline from CSV

```python
from pathlib import Path
from kg_constructor.langextract_pipeline import LangExtractPipeline
from kg_constructor.langextract_extractor import ExtractionConfig

# Setup
config = ExtractionConfig(
    model_id="gemini-2.0-flash-exp",
    api_key="your-api-key"
)
pipeline = LangExtractPipeline(
    output_dir=Path("outputs/results"),
    extraction_config=config
)

# Run full pipeline
results = pipeline.run_full_pipeline(
    csv_path=Path("data/legal/sample_data.csv"),
    text_column="background",
    id_column="id",
    limit=5,  # Process only 5 records
    create_visualizations=True
)

print(f"Created {len(results['json_files'])} JSON files")
print(f"Created {len(results['graphml_files'])} GraphML files")
print(f"Created {len(results['html_files'])} HTML visualizations")
```

#### Example 3: Step-by-Step Processing

```python
from pathlib import Path
from kg_constructor.langextract_pipeline import LangExtractPipeline

pipeline = LangExtractPipeline(output_dir=Path("outputs"))

# Step 1: Extract triples
json_files = pipeline.process_csv(
    csv_path=Path("data/legal/sample_data.csv"),
    text_column="background",
    id_column="id",
    limit=3
)

# Step 2: Convert to GraphML
json_dir = Path("outputs/langextract_json")
graphml_dir = Path("outputs/langextract_graphml")
graphml_files = pipeline.export_to_graphml(json_dir, graphml_dir)

# Step 3: Create visualizations
viz_dir = Path("outputs/langextract_visualizations")
html_files = pipeline.visualize_graphs(graphml_dir, viz_dir)
```

## Configuration

### ExtractionConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_id` | str | `"gemini-2.0-flash-exp"` | Gemini model to use |
| `api_key` | str | None | API key (or use env var) |
| `temperature` | float | 0.0 | Sampling temperature (0.0 = deterministic) |
| `max_workers` | int | 10 | Parallel workers for concurrent processing |
| `batch_length` | int | 10 | Number of chunks processed per batch |
| `max_char_buffer` | int | 8000 | Max characters for inference |
| `use_schema_constraints` | bool | True | Enable structured outputs |
| `show_progress` | bool | True | Show progress bar |

### CLI Arguments

```bash
# Input/Output
--csv PATH                 Input CSV file path (required)
--output-dir PATH          Output directory (default: outputs/langextract_results)
--text-column NAME         CSV column with text (default: background)
--id-column NAME           CSV column with IDs (default: id)
--limit N                  Process only N records (default: all)

# Model Configuration
--model MODEL_ID           Model to use (default: gemini-2.0-flash-exp)
--api-key KEY             API key (or use env var)
--temperature FLOAT        Sampling temperature (default: 0.0)
--max-workers N           Parallel workers (default: 10)
--batch-length N          Chunks per batch (default: 10)
--max-char-buffer N       Max characters (default: 8000)

# Pipeline Options
--no-visualizations       Skip HTML visualizations
--no-schema-constraints   Disable schema constraints
--no-progress            Hide progress bar
```

## Output Format

### Directory Structure

```
outputs/langextract_results/
├── langextract_json/          # Extracted triples as JSON
│   ├── UKSC-2009-0001.json
│   ├── UKSC-2009-0002.json
│   └── ...
├── langextract_graphml/       # GraphML files
│   ├── UKSC-2009-0001.graphml
│   ├── UKSC-2009-0002.graphml
│   └── ...
└── langextract_visualizations/ # HTML visualizations
    ├── UKSC-2009-0001.html
    ├── UKSC-2009-0002.html
    └── ...
```

### JSON Triple Format

Each JSON file contains an array of triples:

```json
[
  {
    "head": "H",
    "relation": "is",
    "tail": "three-year-old child",
    "inference": "explicit"
  },
  {
    "head": "GB",
    "relation": "is",
    "tail": "maternal grandmother of H",
    "inference": "explicit"
  },
  {
    "head": "case",
    "relation": "involves",
    "tail": "H",
    "inference": "contextual",
    "justification": "Bridges disconnected components in the graph"
  }
]
```

### GraphML Format

GraphML files are standard NetworkX-compatible XML files with:
- **Nodes**: Entities with normalized names
- **Edges**: Relations with attributes (relation, inference, justification)

### HTML Visualizations

Interactive Plotly visualizations with:
- Node size/color based on degree (number of connections)
- Edge hover information showing all attributes
- Node hover information showing entity details
- Graph statistics

## Extraction Prompt

The module uses a carefully crafted prompt for legal domain extraction:

```
Extract all explicit knowledge graph triples (head, relation, tail) from the legal case background text.

Extraction Rules:
- Identify entities and relations explicitly stated in the background facts
- Prefer splitting complex phrases into smaller meaningful entities
- Every explicit triple must be labeled with "inference": "explicit"

Connectivity Rules:
- Build a directed graph with explicit triples, check connectivity as undirected
- If disconnected, add minimum bridging triples to connect all components
- Bridging triples must:
  - Stay faithful to context (e.g., introduce implied "event" nodes)
  - Include "inference": "contextual" with short "justification"
  - Avoid external knowledge beyond the provided background
```

## Comparison with vLLM Pipeline

| Feature | LangExtract Module | Original vLLM Pipeline |
|---------|-------------------|----------------------|
| **Extraction Method** | langextract API + Gemini | Local vLLM server |
| **Setup Complexity** | Simple (API key only) | Complex (server setup) |
| **Infrastructure** | Cloud-based | Local/self-hosted |
| **Scalability** | High (automatic) | Limited by hardware |
| **Cost** | Pay per API call | Free (after setup) |
| **GraphML Conversion** | ✓ Reuses existing code | ✓ Same code |
| **Visualization** | ✓ Reuses existing code | ✓ Same code |
| **Output Format** | Identical | Identical |

## Reused Components

This module reuses the following existing code:

1. **`convert_from_JSON.py`** - JSON to GraphML conversion
   - Entity normalization
   - NetworkX graph construction
   - GraphML export

2. **`visualisation.py`** - Interactive visualizations
   - Plotly-based rendering
   - Node/edge styling
   - Hover information
   - Batch processing

## Examples

See [examples/langextract_example.py](../examples/langextract_example.py) for complete working examples including:

- Single text extraction
- CSV batch processing
- Step-by-step pipeline
- Dataset record extraction

## Environment Variables

- `LANGEXTRACT_API_KEY` - API key for langextract (Gemini)
- `GOOGLE_API_KEY` - Alternative environment variable for Gemini API

## Error Handling

The module includes robust error handling:

- Invalid CSV files
- Missing API keys
- Extraction failures (logged, processing continues)
- Network errors (retries with exponential backoff)

## Performance Tips

1. **Parallel Processing**: Increase `max_workers` for faster processing
2. **Batch Size**: Adjust `batch_length` based on memory constraints
3. **Character Buffer**: Reduce `max_char_buffer` for shorter contexts
4. **Temperature**: Use 0.0 for deterministic, reproducible results
5. **Model Selection**: Use `gemini-2.0-flash-exp` for best speed/quality

## Troubleshooting

### No API Key Error
```bash
Error: No API key provided
```
**Solution**: Set `LANGEXTRACT_API_KEY` or `GOOGLE_API_KEY` environment variable

### Rate Limit Errors
```
Rate limit exceeded
```
**Solution**: Reduce `max_workers` or add delays between batches

### Memory Issues
```
Out of memory
```
**Solution**: Reduce `max_char_buffer` or `batch_length`

## License

This module is part of the Knowledge Graph Constructor project and follows the same license.
