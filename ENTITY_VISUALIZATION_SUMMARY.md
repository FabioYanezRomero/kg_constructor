# Entity Visualization Integration Summary

## What Was Added

Integrated **langextract's built-in visualization** for highlighting entities in the original text. This complements the existing graph visualization by showing WHERE entities appear in the source text.

## Two Types of Visualizations

### 1. Graph Visualization (Existing)
- **Shows**: Network structure with entities as nodes and relations as edges
- **Technology**: Plotly + NetworkX
- **Location**: `outputs/graph_visualizations/`
- **Answers**: "What relates to what?"

### 2. Entity Visualization (NEW)
- **Shows**: Entities highlighted in the original text with animation
- **Technology**: langextract built-in visualize()
- **Location**: `outputs/entity_visualizations/`
- **Answers**: "Where did this entity come from?"

## New Files

### [src/kg_constructor/visualizer.py](src/kg_constructor/visualizer.py)
**Purpose**: Create interactive HTML visualizations using langextract

**Key Class**: `EntityVisualizer`

**Features**:
- Converts triples to langextract `AnnotatedDocument` format
- Highlights entities in original text
- Creates animated HTML visualizations
- Batch processing for multiple records

**Usage**:
```python
from kg_constructor import EntityVisualizer

visualizer = EntityVisualizer(
    animation_speed=1.0,
    show_legend=True,
    gif_optimized=False
)

# Visualize single record
html = visualizer.visualize_triples(
    text="John works at Google.",
    triples=[
        {"head": "John", "relation": "works at", "tail": "Google", "inference": "explicit"}
    ],
    document_id="record_001"
)

# Save to file
visualizer.save_visualization(
    text=text,
    triples=triples,
    output_path="output.html"
)

# Batch process
visualizer.batch_visualize(
    records={"id1": (text1, triples1), "id2": (text2, triples2)},
    output_dir="visualizations/"
)
```

## Updated Files

### [src/kg_constructor/extraction_pipeline.py](src/kg_constructor/extraction_pipeline.py)

**Changes**:
1. Added `EntityVisualizer` import and initialization
2. Added `enable_entity_viz` parameter to `__init__()`
3. Updated `process_csv()` to save original texts
4. Added `visualize_entities()` method
5. Updated `run_full_pipeline()` with two visualization options:
   - `create_graph_viz`: Network visualizations (Plotly)
   - `create_entity_viz`: Entity highlighting (langextract)

**New Method**: `visualize_entities()`
```python
def visualize_entities(
    self,
    texts: dict[str, str],
    triples: dict[str, list[dict[str, Any]]],
    entity_viz_dir: Path,
    group_by: str = "entity_type"
) -> list[Path]:
    """Create entity highlighting visualizations in original text."""
```

**Updated Method**: `run_full_pipeline()`
```python
def run_full_pipeline(
    self,
    csv_path: Path,
    create_graph_viz: bool = True,   # Network view (relations)
    create_entity_viz: bool = True,  # Text highlights (entities)
    ...
) -> dict[str, Any]:
```

### [src/kg_constructor/__init__.py](src/kg_constructor/__init__.py)

**Changes**:
- Added `EntityVisualizer` to `__all__`
- Added lazy-loading function for `EntityVisualizer`

## How It Works

### Entity Visualization Pipeline

1. **Extract triples** from text
   ```json
   [
     {"head": "John", "relation": "works at", "tail": "Google", "inference": "explicit"}
   ]
   ```

2. **Find entity spans** in original text
   ```
   "John works at Google in California."
    ^^^^           ^^^^^^
   ```

3. **Create langextract objects**
   ```python
   Extraction(
       extraction_class="Head Entity",
       extraction_text="John",
       char_interval=CharInterval(start=0, end=4)
   )
   ```

4. **Generate animated HTML**
   - Highlights each entity sequentially
   - Color-coded by type or relation
   - Interactive legend

### Integration with Existing Pipeline

The entity visualization is **fully integrated** with the existing pipeline:

```python
# Run complete pipeline
pipeline = ExtractionPipeline(
    output_dir=Path("outputs"),
    client_config=config,
    enable_entity_viz=True  # Enable entity highlighting
)

results = pipeline.run_full_pipeline(
    csv_path=Path("data.csv"),
    create_graph_viz=True,   # Create network visualizations
    create_entity_viz=True   # Create entity highlighting
)
```

**Output structure**:
```
outputs/
├── extracted_json/          # Triples as JSON
├── graphml/                 # GraphML for NetworkX
├── graph_visualizations/    # Network view (Plotly) - SHOWS RELATIONS
└── entity_visualizations/   # Text highlights (langextract) - SHOWS ENTITIES
```

## Key Design Decisions

### 1. Two Complementary Visualizations

**Graph viz** shows the **structure** (relations between entities)
**Entity viz** shows the **source** (where entities appear in text)

They answer different questions:
- Graph: "What's connected?" → Relationships and patterns
- Entity: "Where is it?" → Original context and validation

### 2. Inside kg_constructor Module

The entity visualizer belongs in `kg_constructor` because:
- It uses extraction results directly (triples + original text)
- It's part of the extraction workflow
- It helps validate extraction quality
- langextract is already a dependency for extraction

The graph visualizer stays in `postprocessing` because:
- It works with GraphML (post-extraction format)
- It's used by multiple systems
- It doesn't need original text

### 3. Configurable but Enabled by Default

Both visualizations are enabled by default but can be disabled:

```python
# Only graph visualization
pipeline.run_full_pipeline(
    csv_path=path,
    create_graph_viz=True,
    create_entity_viz=False
)

# Only entity visualization
pipeline.run_full_pipeline(
    csv_path=path,
    create_graph_viz=False,
    create_entity_viz=True
)

# Neither (just extract and convert to GraphML)
pipeline.run_full_pipeline(
    csv_path=path,
    create_graph_viz=False,
    create_entity_viz=False
)
```

### 4. Grouping Strategies

Entities can be grouped two ways:

**By entity type** (default):
- "Head Entity" (blue)
- "Tail Entity" (green)
- Simple and clear

**By relation**:
- "works at (source)" (color 1)
- "works at (target)" (color 2)
- "located in (source)" (color 3)
- Shows which entities play which roles

## Usage Examples

### Basic Usage

```python
from pathlib import Path
from kg_constructor import ExtractionPipeline, ClientConfig

# Configure
config = ClientConfig(client_type="gemini", api_key="your-key")
pipeline = ExtractionPipeline(
    output_dir=Path("outputs"),
    client_config=config
)

# Run with both visualizations
results = pipeline.run_full_pipeline(
    csv_path=Path("data/legal/sample_data.csv"),
    limit=5
)

# Access results
print(f"Graph viz: {results['graph_viz_dir']}")
print(f"Entity viz: {results['entity_viz_dir']}")
```

### Custom Visualizer

```python
from kg_constructor import EntityVisualizer

# Create custom visualizer
visualizer = EntityVisualizer(
    animation_speed=2.0,      # Slower animation
    show_legend=True,
    gif_optimized=True        # Better for screen recording
)

# Single record
visualizer.save_visualization(
    text="John works at Google.",
    triples=[{"head": "John", "relation": "works at", "tail": "Google"}],
    output_path="output.html",
    group_by="relation"  # Group by relation instead of type
)
```

## Benefits

### For Users
1. **Validation**: See where entities were found in original text
2. **Context**: Understand entity usage in context
3. **Debugging**: Identify extraction errors quickly
4. **Presentation**: Beautiful animated visualizations

### For Development
1. **Clean integration**: Uses langextract's built-in features
2. **Minimal code**: Leverages existing functionality
3. **Flexible**: Configurable grouping and styling
4. **Maintainable**: Simple wrapper around langextract

## Answer to "Does it highlight relations?"

**No, entity visualization does NOT show relations between entities.** It only highlights where **individual entities** appear in the text.

For **relations**, use the **graph visualization** (Plotly/NetworkX), which shows:
- Entities as nodes
- Relations as edges (arrows)
- Complete graph structure

**Both visualizations together** provide the complete picture:
- Entity viz: "John" and "Google" are highlighted in text
- Graph viz: "John" → [works at] → "Google" shows the relationship

## Files Summary

### Created
- [src/kg_constructor/visualizer.py](src/kg_constructor/visualizer.py) - EntityVisualizer class
- [VISUALIZATION_GUIDE.md](VISUALIZATION_GUIDE.md) - Complete documentation
- This file - Implementation summary

### Modified
- [src/kg_constructor/extraction_pipeline.py](src/kg_constructor/extraction_pipeline.py) - Added entity visualization
- [src/kg_constructor/__init__.py](src/kg_constructor/__init__.py) - Export EntityVisualizer

### Not Modified
- [src/postprocessing/networkX/visualisation.py](src/postprocessing/networkX/visualisation.py) - Graph viz (unchanged)
- [src/postprocessing/networkX/convert_from_JSON.py](src/postprocessing/networkX/convert_from_JSON.py) - Conversion (unchanged)

## Conclusion

The system now provides **two complementary visualization types**:

1. **Graph visualizations** (Plotly) - Show relationships between entities
2. **Entity visualizations** (langextract) - Show entities highlighted in text

Both are **automatically generated** by the pipeline and provide different insights into the knowledge graph extractions.

The integration is:
- ✅ Clean and minimal
- ✅ Fully integrated with existing pipeline
- ✅ Configurable and flexible
- ✅ Well-documented
- ✅ Uses langextract's built-in features correctly
