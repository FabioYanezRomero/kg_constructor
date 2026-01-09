# LangExtract Knowledge Graph Module

A complete module for extracting knowledge graphs from legal case text using **langextract** instead of local language models. This module integrates seamlessly with existing GraphML conversion and visualization code.

## Quick Start

### 1. Set API Key

```bash
export LANGEXTRACT_API_KEY="your-gemini-api-key"
```

### 2. Run the Pipeline

```bash
# Process 3 sample legal cases
python -m kg_constructor.langextract_cli \
  --csv data/legal/sample_data.csv \
  --output-dir outputs/langextract_results \
  --limit 3
```

### 3. View Results

The pipeline creates three output directories:

- **`langextract_json/`** - Extracted triples as JSON
- **`langextract_graphml/`** - GraphML files for network analysis
- **`langextract_visualizations/`** - Interactive HTML visualizations

Open any HTML file in `langextract_visualizations/` to explore the extracted knowledge graph interactively.

## Module Structure

```
src/kg_constructor/
├── langextract_extractor.py   # Core extraction using langextract API
├── langextract_pipeline.py    # Pipeline orchestration
└── langextract_cli.py          # Command-line interface

examples/
└── langextract_example.py      # Usage examples

docs/
└── LANGEXTRACT_USAGE.md        # Detailed documentation
```

## Python API Example

```python
from pathlib import Path
from kg_constructor.langextract_pipeline import LangExtractPipeline
from kg_constructor.langextract_extractor import ExtractionConfig

# Configure extraction
config = ExtractionConfig(
    model_id="gemini-2.0-flash-exp",
    temperature=0.0,
    max_workers=10
)

# Initialize pipeline
pipeline = LangExtractPipeline(
    output_dir=Path("outputs/results"),
    extraction_config=config
)

# Run full pipeline
results = pipeline.run_full_pipeline(
    csv_path=Path("data/legal/sample_data.csv"),
    text_column="background",
    id_column="id",
    limit=5
)

print(f"Created {len(results['graphml_files'])} knowledge graphs")
```

## Features

- Extract entities and relations from legal text using langextract
- Automatic graph connectivity checking and bridging
- Convert to GraphML format (NetworkX-compatible)
- Create interactive HTML visualizations with Plotly
- Batch processing with parallel execution
- Reuses existing conversion and visualization code

## Output Format

Each case produces a JSON file with extracted triples:

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
    "relation": "was granted",
    "tail": "residence order in respect of H",
    "inference": "explicit"
  }
]
```

These are automatically converted to:
- **GraphML** files for analysis with tools like Gephi, Cytoscape
- **HTML** visualizations for interactive exploration

## Comparison with vLLM Pipeline

| Aspect | LangExtract | vLLM |
|--------|-------------|------|
| Setup | Simple (API key) | Complex (server) |
| Infrastructure | Cloud | Local |
| Scalability | Automatic | Hardware-limited |
| Cost | Pay-per-use | Free (after setup) |
| Output | Identical | Identical |

## Documentation

- **[Complete Documentation](docs/LANGEXTRACT_USAGE.md)** - Detailed usage guide
- **[Examples](examples/langextract_example.py)** - Working code examples

## CLI Options

```bash
# Basic usage
--csv PATH              Input CSV file (required)
--output-dir PATH       Output directory
--limit N              Process only N records

# Model configuration
--model MODEL_ID        Gemini model (default: gemini-2.0-flash-exp)
--temperature FLOAT     Sampling temperature (default: 0.0)
--max-workers N        Parallel workers (default: 10)

# Pipeline options
--no-visualizations    Skip HTML visualizations
--no-progress         Hide progress bar

# Full help
python -m kg_constructor.langextract_cli --help
```

## Environment Variables

- `LANGEXTRACT_API_KEY` - Your Gemini API key
- `GOOGLE_API_KEY` - Alternative for Gemini API key

## Reused Code

This module reuses:

1. **`convert_from_JSON.py`** - Converts JSON triples to GraphML
2. **`visualisation.py`** - Creates interactive Plotly visualizations

This ensures consistency with existing outputs and maintains all features like entity normalization, graph statistics, and hover information.

## Examples

Run the examples to see the module in action:

```bash
python examples/langextract_example.py
```

This demonstrates:
- Single text extraction
- CSV batch processing
- Step-by-step pipeline
- Dataset record extraction

## License

Part of the Knowledge Graph Constructor project.
