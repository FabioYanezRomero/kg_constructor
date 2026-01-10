# Single Text Extraction Test Script Guide

## Overview

The `test_single_extraction.sh` script allows you to test the complete knowledge graph extraction pipeline on a **single text record** from a JSON file. This is perfect for:

- Testing specific texts in detail
- Debugging extraction issues
- Experimenting with different models
- Validating prompts
- Analyzing individual cases

## Quick Start

```bash
# 1. Set your API key (for Gemini only)
export LANGEXTRACT_API_KEY="your-gemini-api-key"
# Get your key from: https://aistudio.google.com/app/apikey

# 2. Edit the hyperparameters at the top of the script
nano test_single_extraction.sh

# 3. Run the script
./test_single_extraction.sh
```

**Note for Ollama/LM Studio**: No API key needed! These run locally.

## Hyperparameters

All configuration is done at the **top of the script**. Open `test_single_extraction.sh` and modify these variables:

### API Key Configuration

**For Gemini only** - choose one method:

**Method 1: Environment Variable (Recommended)**
```bash
export LANGEXTRACT_API_KEY="your-api-key-here"
# or
export GOOGLE_API_KEY="your-api-key-here"
```

**Method 2: .env File (Convenient)**
```bash
echo 'LANGEXTRACT_API_KEY=your-api-key-here' > /app/.env
```

**Method 3: In Script (Not Recommended - Security Risk)**
```bash
# Edit test_single_extraction.sh and uncomment:
GEMINI_API_KEY="your-api-key-here"
```

**Get your API key**: https://aistudio.google.com/app/apikey

**For Ollama/LM Studio**: No API key needed!

### Model Configuration

```bash
# Choose your LLM provider
MODEL_PROVIDER="gemini"  # Options: gemini, ollama, lmstudio

# Specify the model name
MODEL_NAME="gemini-2.0-flash-exp"
# For Gemini: gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash
# For Ollama: llama3.2, mistral, phi3, etc.
# For LM Studio: any model name from your LM Studio server

# Sampling temperature (0.0 = deterministic, 1.0 = creative)
TEMPERATURE=0.0
```

### Input Data Configuration

```bash
# Path to your JSON file
INPUT_JSON="/app/data/legal/sample_data.json"

# The ID/key of the specific record to process
RECORD_ID="record_001"

# The field name containing the text to analyze
TEXT_FIELD="background"
```

**JSON Format Support:**

The script supports three JSON formats:

1. **JSONL format** (JSON Lines - one JSON object per line, detected by `.jsonl` extension):
```jsonl
{"id": "record_001", "text": "Text to analyze...", "other_field": "..."}
{"id": "record_002", "text": "Another text...", "other_field": "..."}
{"id": "record_003", "text": "More text...", "other_field": "..."}
```

2. **Array format** (searches by `id` field):
```json
[
  {
    "id": "record_001",
    "background": "Text to analyze...",
    "other_field": "..."
  },
  {
    "id": "record_002",
    "background": "Another text..."
  }
]
```

3. **Dictionary format** (uses key as record ID):
```json
{
  "record_001": {
    "background": "Text to analyze...",
    "other_field": "..."
  },
  "record_002": {
    "background": "Another text..."
  }
}
```

### Prompt Configuration

**For simple one-step extraction** (`USE_ITERATIVE_EXTRACTION=false`):
```bash
# Single prompt for all extraction
PROMPT_FILE="/app/src/prompts/legal_background_prompt.txt"
```

**For iterative two-step extraction** (`USE_ITERATIVE_EXTRACTION=true`):
```bash
# Step 1: Initial extraction prompt
PROMPT_FILE_STEP1="/app/src/prompts/legal_background_prompt_step1_initial.txt"

# Step 2: Bridging/refinement prompt
PROMPT_FILE_STEP2="/app/src/prompts/legal_background_prompt_step2_bridging.txt"
```

**Available prompt templates**:
- `legal_background_prompt.txt` - Original all-in-one prompt (for simple extraction)
- `legal_background_prompt_step1_initial.txt` - Step 1: Comprehensive initial extraction
- `legal_background_prompt_step2_bridging.txt` - Step 2: Connectivity-focused bridging

**To use custom prompts**:
```bash
# Create your own prompts
nano /app/prompts/my_custom_initial.txt
nano /app/prompts/my_custom_bridging.txt

# Configure the script
PROMPT_FILE_STEP1="/app/prompts/my_custom_initial.txt"
PROMPT_FILE_STEP2="/app/prompts/my_custom_bridging.txt"
```

**Bridging prompt template variables**:
- `{num_components}` - Number of disconnected components
- `{component_info}` - Formatted list of component entities
- `{text}` - Original input text

### Output Configuration

```bash
# Where to save all outputs (auto-timestamped)
OUTPUT_DIR="/app/test_outputs/single_extraction_$(date +%Y%m%d_%H%M%S)"

# Or use a fixed path:
OUTPUT_DIR="/app/test_outputs/my_test"
```

### Visualization Options

```bash
# Create langextract HTML visualization (highlights entities in text)
CREATE_ENTITY_VIZ=true

# Create NetworkX/Plotly graph visualization (network view)
CREATE_GRAPH_VIZ=true

# How to group entities in entity visualization
ENTITY_GROUP_BY="entity_type"  # Options: entity_type, relation
```

### Connectivity Configuration (Iterative Approach - DEFAULT)

```bash
# Use iterative connectivity-aware extraction (recommended, DEFAULT)
USE_ITERATIVE_EXTRACTION=true

# Maximum acceptable disconnected components (if using iterative)
MAX_DISCONNECTED=3

# Maximum refinement iterations (if using iterative)
MAX_ITERATIONS=2
```

**What is Iterative Connectivity-Aware Extraction?**

By default, the script now uses a **two-phase iterative extraction approach** that produces more connected knowledge graphs:

1. **Phase 1: Initial Extraction** - Extracts explicit and contextual triples from the text
2. **Phase 2: Connectivity Refinement** - If the graph has too many disconnected components, the LLM iteratively adds bridging triples to improve connectivity

This approach:
- ✅ Produces graphs with fewer disconnected components
- ✅ Finds implicit relationships that connect entities
- ✅ Maintains semantic validity (no hallucinations)
- ⚠️ Uses 1-3 API calls instead of 1 (slightly higher cost)

**To disable iterative extraction** and use simple one-step extraction:
```bash
USE_ITERATIVE_EXTRACTION=false
```

## What the Script Does

The script runs these steps automatically:

### Step 1: Loading Input Data
- Loads the specified JSON file
- Extracts the record with the given ID
- Retrieves the text from the specified field
- Shows a preview of the text

### Step 2: Initializing Extraction Pipeline
- Configures the LLM client (Gemini/Ollama/LM Studio)
- Sets up the extraction pipeline
- Loads the prompt template (if specified)

### Step 3: Extracting Triples with LangExtract

**Default: Iterative Connectivity-Aware Extraction**

When `USE_ITERATIVE_EXTRACTION=true` (default):

1. **Initial Extraction**: Sends text to LLM to extract explicit and contextual triples
2. **Connectivity Analysis**: Builds graph and counts disconnected components
3. **Iterative Refinement** (if needed): If components > `MAX_DISCONNECTED`, iteratively extracts bridging triples to improve connectivity
4. **Output**: Final connected graph with metadata about refinement process

Shows progress during extraction:
```
Initial extraction:
  • Triples: 34
  • Components: 11

Refinement iterations:
  Iteration 1: +6 triples, 6 components
  Iteration 2: +7 triples, 1 components

Final results:
  • Total triples: 47
  • Disconnected components: 1
  • Is connected: True
  • Total API calls: 3
```

**Alternative: Simple One-Step Extraction**

When `USE_ITERATIVE_EXTRACTION=false`:
- Sends the text to the LLM once
- Parses the response into structured triples
- Uses 1 API call

**Output**: Saves triples as JSON: `{output_dir}/json/{record_id}.json`

**Triple Format:**
```json
[
  {
    "head": "John Smith",
    "relation": "works_at",
    "tail": "Google Inc.",
    "inference": "explicit",
    "justification": "The text states 'employed at Google'"
  }
]
```

### Step 4: Converting to GraphML
- Converts JSON triples to NetworkX graph
- Saves as GraphML: `{output_dir}/graphml/{record_id}.graphml`
- GraphML is an XML-based graph format

### Step 5: Generating Metadata and Analytics
- Analyzes the extracted graph structure
- Calculates comprehensive statistics
- Saves metadata as JSON: `{output_dir}/metadata/{record_id}_metadata.json`

**Metadata includes:**
- **Extraction info**: Model used, temperature, timestamp, prompt file, extraction method (iterative vs simple)
- **Input data**: Source file, text length (chars & words)
- **Extraction results**: Total triples, explicit vs contextual counts and percentages
- **Graph structure**: Number of nodes, edges, disconnected components, connectivity status, average degree
- **Entity analysis**: Total unique entities, entities found in text vs inferred, percentages
- **Relation analysis**: Unique relations count, most common relations with frequencies
- **Iterative extraction** (if enabled): Initial extraction stats, refinement iterations, final state, total API calls

**Example analytics output:**
```
Key Analytics:
  • Total triples: 21 (20 explicit, 1 contextual)
  • Unique entities: 28 (22 in text, 6 inferred)
  • Graph nodes: 27, edges: 21
  • Connected components: 6
  • Average degree: 1.56
```

### Step 6: Creating Entity Visualization (LangExtract HTML)
- Highlights entities in the original text
- Shows relation info in entity attributes (hover/click)
- Animated sequential highlighting
- Saves as: `{output_dir}/entity_viz/{record_id}.html`

**Features:**
- Color-coded entities (by type or relation)
- Interactive tooltips showing:
  - Entity type
  - Relation it participates in
  - Role (head/tail)
  - Inference type

### Step 7: Creating Graph Visualization (Plotly Network)
- Creates interactive network graph
- Entities as nodes, relations as edges
- Saves as: `{output_dir}/graph_viz/{record_id}.html`

**Features:**
- Interactive zoom and pan
- Hover tooltips with details
- Color-coded nodes and edges
- Shows complete graph structure

## Output Structure

After running, you'll get this directory structure:

```
test_outputs/single_extraction_20240315_143052/
├── json/
│   └── record_001.json                    # Extracted triples (raw)
├── graphml/
│   └── record_001.graphml                 # NetworkX graph format
├── metadata/
│   └── record_001_metadata.json           # Metadata and analytics
├── entity_viz/
│   └── record_001.html                    # Entity highlighting visualization
└── graph_viz/
    └── record_001.html                    # Network graph visualization
```

## Example Usage

### Example 1: Test with Default Settings

```bash
# Just run the script with defaults
./test_single_extraction.sh
```

### Example 2: Custom Model and Record

Edit the script:
```bash
MODEL_PROVIDER="gemini"
MODEL_NAME="gemini-1.5-pro"
RECORD_ID="record_002"
TEXT_FIELD="background"
```

Then run:
```bash
./test_single_extraction.sh
```

### Example 3: Use Custom Prompt

Create a custom prompt:
```bash
cat > /app/prompts/my_prompt.txt << 'EOF'
You are an expert at extracting entities and relations from legal documents.

Extract all entities (people, organizations, locations, dates, amounts) and their relationships.

Format your response as a JSON array of triples...
EOF
```

Edit the script:
```bash
PROMPT_FILE="/app/prompts/my_prompt.txt"
```

Run:
```bash
./test_single_extraction.sh
```

### Example 4: Group by Relation

Edit the script to group entities by which relation they participate in:
```bash
ENTITY_GROUP_BY="relation"  # Instead of "entity_type"
```

This colors entities based on their relationship roles:
- "works_at (source)" - blue
- "works_at (target)" - green
- "filed_lawsuit (source)" - red
- etc.

### Example 5: Compare Iterative vs Simple Extraction

Test the same text with both approaches to see the connectivity improvement:

```bash
# Test 1: Iterative (default)
USE_ITERATIVE_EXTRACTION=true
MAX_DISCONNECTED=3
MAX_ITERATIONS=2
OUTPUT_DIR="/app/test_outputs/iterative_test"
./test_single_extraction.sh

# Test 2: Simple one-step
USE_ITERATIVE_EXTRACTION=false
OUTPUT_DIR="/app/test_outputs/simple_test"
./test_single_extraction.sh

# Compare the metadata files to see connectivity improvement
cat /app/test_outputs/iterative_test/metadata/*_metadata.json | jq '.graph_structure'
cat /app/test_outputs/simple_test/metadata/*_metadata.json | jq '.graph_structure'
```

### Example 6: Only Graph Visualization

If you only want the network graph (no entity highlighting):
```bash
CREATE_ENTITY_VIZ=false
CREATE_GRAPH_VIZ=true
```

### Example 7: Compare Different Models

Run multiple times with different models:

```bash
# Test 1: Gemini Flash
MODEL_NAME="gemini-2.0-flash-exp"
OUTPUT_DIR="/app/test_outputs/comparison_gemini_flash"
./test_single_extraction.sh

# Test 2: Gemini Pro
MODEL_NAME="gemini-1.5-pro"
OUTPUT_DIR="/app/test_outputs/comparison_gemini_pro"
./test_single_extraction.sh

# Test 3: Ollama Llama
MODEL_PROVIDER="ollama"
MODEL_NAME="llama3.2"
OUTPUT_DIR="/app/test_outputs/comparison_ollama_llama"
./test_single_extraction.sh
```

Then compare the results!

## Viewing Results

### Metadata and Analytics

View the comprehensive metadata file:
```bash
cat test_outputs/single_extraction_*/metadata/record_001_metadata.json
```

**What's included:**

1. **Extraction Information**: Model used, temperature, timestamp
2. **Input Data**: Source file, text length statistics
3. **Extraction Results**: Triple counts and inference type breakdown
4. **Graph Structure**: Nodes, edges, connectivity analysis
5. **Entity Analysis**: How many entities appear in text vs inferred
6. **Relation Analysis**: Most common relationship types

**Example metadata (with iterative extraction):**
```json
{
  "extraction_info": {
    "model_name": "gemini-2.0-flash-exp",
    "temperature": 0.0,
    "extraction_method": "iterative_connectivity_aware"
  },
  "graph_structure": {
    "total_nodes": 38,
    "total_edges": 47,
    "disconnected_components": 1,
    "is_connected": true,
    "avg_degree": 2.47
  },
  "entity_analysis": {
    "entities_in_text_percentage": 81.58,
    "entities_inferred_percentage": 18.42
  },
  "iterative_extraction": {
    "max_disconnected": 3,
    "max_iterations": 2,
    "initial_extraction": {
      "triples": 34,
      "disconnected_components": 11
    },
    "refinement_iterations": [
      {
        "iteration": 1,
        "new_triples": 6,
        "disconnected_components": 6
      },
      {
        "iteration": 2,
        "new_triples": 7,
        "disconnected_components": 1
      }
    ],
    "final_state": {
      "total_triples": 47,
      "disconnected_components": 1,
      "is_connected": true,
      "iterations_used": 2
    },
    "total_api_calls": 3
  }
}
```

This metadata is useful for:
- **Comparing different models** on the same text
- **Quality assessment** (e.g., high inference percentages might indicate hallucination)
- **Graph connectivity analysis** (disconnected components might indicate missing relations)
- **Reproducibility** (all extraction parameters are logged)

### Entity Visualization (Text Highlights)

Open in browser:
```bash
# On Linux with browser
xdg-open test_outputs/single_extraction_*/entity_viz/record_001.html

# On macOS
open test_outputs/single_extraction_*/entity_viz/record_001.html

# Or just navigate to the file in your file manager
```

**What you'll see:**
- Original text with entities highlighted
- Animated highlighting (one entity at a time)
- Hover over entities to see:
  - Entity type
  - **Relation** it participates in
  - **Role** (head/tail)
  - Inference type
- Color legend

### Graph Visualization (Network View)

Open in browser:
```bash
xdg-open test_outputs/single_extraction_*/graph_viz/record_001.html
```

**What you'll see:**
- Interactive network graph
- Nodes = entities
- Arrows = relations
- Hover for details
- Zoom and pan
- Complete graph structure

### Raw Data Files

View the extracted triples:
```bash
cat test_outputs/single_extraction_*/json/record_001.json | jq
```

View the GraphML (XML format):
```bash
cat test_outputs/single_extraction_*/graphml/record_001.graphml
```

## Troubleshooting

### Error: "Gemini API key not found!"

**Cause:** The script can't find your Gemini API key.

**Solution:** Set your API key using one of these methods:

```bash
# Option 1: Export environment variable (for current session)
export LANGEXTRACT_API_KEY="your-api-key-here"

# Option 2: Add to .bashrc (permanent)
echo 'export LANGEXTRACT_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# Option 3: Create .env file
echo 'LANGEXTRACT_API_KEY=your-api-key-here' > /app/.env

# Option 4: Edit the script
nano test_single_extraction.sh
# Uncomment and set: GEMINI_API_KEY="your-api-key-here"
```

Get your API key from: https://aistudio.google.com/app/apikey

### Error: "Record with ID 'XXX' not found"

**Cause:** The RECORD_ID doesn't exist in your JSON file.

**Solution:** Check available IDs in your JSON:
```bash
cat /app/data/legal/sample_data.json | jq '.[].id'  # For array format
cat /app/data/legal/sample_data.json | jq 'keys'    # For dict format
```

### Error: "Field 'XXX' not found in record"

**Cause:** The TEXT_FIELD doesn't exist in your record.

**Solution:** Check available fields:
```bash
cat /app/data/legal/sample_data.json | jq '.[0] | keys'  # For array format
```

### Error: "API key not found"

**Cause:** Missing API key for Gemini.

**Solution:** Set your API key:
```bash
export GEMINI_API_KEY="your-api-key-here"
./test_single_extraction.sh
```

Or add to your `.bashrc`:
```bash
echo 'export GEMINI_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

### No Entities Found in Visualization

**Cause:** Entities extracted don't match the original text exactly.

**Possible reasons:**
- Entity normalization (e.g., "Google" extracted but text says "Google Inc.")
- Case mismatch
- Contextual entities (inferred, not explicit in text)

**Solution:** Check the JSON triples to see what was extracted:
```bash
cat test_outputs/single_extraction_*/json/record_001.json | jq '.[].head, .[].tail'
```

### Visualization HTML Shows "No entities found"

**Cause:** No valid triples were extracted.

**Solution:**
1. Check if the LLM response was empty
2. Try a different model
3. Adjust the prompt
4. Check the input text quality

## Advanced Usage

### Custom Python Processing

The script creates a temporary Python file at `{OUTPUT_DIR}/extract_single.py`. You can modify this for custom processing:

```bash
# Run the script once to generate the Python file
./test_single_extraction.sh

# Edit the generated Python file
nano test_outputs/single_extraction_*/extract_single.py

# Run it directly
python3 test_outputs/single_extraction_*/extract_single.py \
    gemini gemini-2.0-flash-exp 0.0 \
    /app/data/legal/sample_data.json \
    record_001 background "" \
    /app/test_outputs/my_test \
    true true entity_type
```

### Batch Testing

Create a wrapper script to test multiple records:

```bash
#!/bin/bash
for RECORD in record_001 record_002 record_003; do
    OUTPUT_DIR="/app/test_outputs/batch_$RECORD"
    RECORD_ID="$RECORD"
    ./test_single_extraction.sh
done
```

### Integration with CI/CD

Use the script in automated testing:

```bash
#!/bin/bash
set -e

# Test with sample data
OUTPUT_DIR="/tmp/ci_test"
./test_single_extraction.sh

# Validate outputs exist
test -f "$OUTPUT_DIR/json/record_001.json"
test -f "$OUTPUT_DIR/graphml/record_001.graphml"
test -f "$OUTPUT_DIR/entity_viz/record_001.html"
test -f "$OUTPUT_DIR/graph_viz/record_001.html"

echo "✓ All outputs generated successfully"
```

## Performance Notes

- **Gemini Flash**: Fastest, good quality, recommended for testing
- **Gemini Pro**: Slower but higher quality extractions
- **Ollama**: Runs locally, speed depends on your hardware
- **LM Studio**: Runs locally, good for privacy-sensitive data

Typical extraction times:
- Short text (< 500 words): 2-5 seconds
- Medium text (500-2000 words): 5-15 seconds
- Long text (> 2000 words): 15-60 seconds

## Next Steps

After testing with the single text script:

1. **Validate Results**: Review the extracted triples and visualizations
2. **Adjust Prompt**: If results aren't good, modify the prompt
3. **Try Different Models**: Compare quality across models
4. **Scale Up**: Use the full pipeline for batch processing:
   ```bash
   python -m kg_constructor.extract_cli \
       --client gemini \
       --csv data/legal/sample_data.csv \
       --output-dir outputs/full_batch \
       --limit 10
   ```

## Support

For issues or questions:
- Check the main README: `/app/README.md`
- Review visualization guide: `/app/VISUALIZATION_GUIDE.md`
- Check relation info guide: `/app/RELATION_VISUALIZATION_UPDATE.md`
