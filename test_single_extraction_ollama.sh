#!/bin/bash

################################################################################
# HYPERPARAMETERS - Configure these at the top
################################################################################

# Ollama Configuration
# Make sure Ollama is running and has a model loaded
# Default server URL is http://localhost:11434

# Model Configuration
MODEL_PROVIDER="ollama"  # Using Ollama local model
MODEL_NAME="gemma3:27b"  # Use the model name shown in Ollama (ollama list)
TEMPERATURE=0.0

# Base directory detection (Docker vs local)
if [ -d "/app/src" ]; then
    BASE_DIR="/app"
    OLLAMA_BASE_URL="http://host.docker.internal:11434"  # Docker networking
else
    BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
    OLLAMA_BASE_URL="http://localhost:11434"  # Local networking
fi

# Input Data
INPUT_FILE="${BASE_DIR}/data/legal/legal_background.jsonl"  # Path to your input file
TEXT_FIELD="text"  # Field name containing the text to analyze
ID_FIELD="id"  # Field name containing record IDs
RECORD_IDS="UKSC-2009-0143"  # Specific record ID(s) to process (comma-separated, or empty for all)

# Domain Configuration
DOMAIN="legal"  # Use: python -m src list domains

# Extraction Mode
MODE="open"  # Options: open, closed

# Output Configuration
OUTPUT_DIR="${BASE_DIR}/test_outputs/single_extraction_ollama_$(date +%Y%m%d_%H%M%S)"

# Connectivity Augmentation Configuration
MAX_DISCONNECTED=1  # Maximum acceptable disconnected components
MAX_ITERATIONS=3    # Max refinement iterations (lower for local models)

# Visualization Options
CREATE_NETWORK_VIZ=true  # Create NetworkX/Plotly graph visualization
CREATE_EXTRACTION_VIZ=true  # Create langextract HTML visualization
DARK_MODE=false  # Enable dark mode for network visualization
LAYOUT="spring"  # Graph layout (spring, circular, kamada_kawai, shell)
GROUP_BY="entity_type"  # Options: entity_type, relation

# Processing Options
MAX_WORKERS=3  # Lower for local models
TIMEOUT=300  # Higher timeout for local models

################################################################################
# Script Execution - Do not modify below this line
################################################################################

set -e  # Exit on error

echo "================================================================================"
echo "KNOWLEDGE GRAPH EXTRACTION - SINGLE TEXT TEST (Ollama)"
echo "Using Typer CLI for unified command-line interface"
echo "================================================================================"
echo "Model Provider: $MODEL_PROVIDER"
echo "Model Name: $MODEL_NAME"
echo "Ollama URL: $OLLAMA_BASE_URL"
echo "Input File: $INPUT_FILE"
echo "Record IDs: $RECORD_IDS"
echo "Domain: $DOMAIN"
echo "Mode: $MODE"
echo "Output Directory: $OUTPUT_DIR"
echo ""
echo "Connectivity Configuration:"
echo "  • Max disconnected: $MAX_DISCONNECTED"
echo "  • Max iterations: $MAX_ITERATIONS"
echo "================================================================================"

# Check if Ollama is reachable
echo ""
echo "Checking Ollama connection..."
python3 -c "
import requests
import sys
try:
    r = requests.get('$OLLAMA_BASE_URL/api/tags', timeout=5)
    if r.status_code == 200:
        print('✓ Ollama is reachable at $OLLAMA_BASE_URL')
        models = r.json().get('models', [])
        if models:
            print(f'  Available models: {[m.get(\"name\", \"unknown\") for m in models]}')
        sys.exit(0)
except Exception as e:
    pass
print('================================================================================')
print('WARNING: Cannot reach Ollama at $OLLAMA_BASE_URL')
print('================================================================================')
print('')
print('Please ensure:')
print('1. Ollama is running (ollama serve)')
print('2. A model is loaded (ollama pull $MODEL_NAME)')
print('3. The URL is correct (default: http://localhost:11434)')
print('')
print('Continuing anyway - the script will fail if Ollama is not available.')
print('================================================================================')
"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build common CLI options
CLI_OPTS=""
CLI_OPTS="$CLI_OPTS --input $INPUT_FILE"
CLI_OPTS="$CLI_OPTS --output-dir $OUTPUT_DIR"
CLI_OPTS="$CLI_OPTS --domain $DOMAIN"
CLI_OPTS="$CLI_OPTS --mode $MODE"
CLI_OPTS="$CLI_OPTS --client $MODEL_PROVIDER"
CLI_OPTS="$CLI_OPTS --text-field $TEXT_FIELD"
CLI_OPTS="$CLI_OPTS --id-field $ID_FIELD"
CLI_OPTS="$CLI_OPTS --record-ids $RECORD_IDS"
CLI_OPTS="$CLI_OPTS --temp $TEMPERATURE"
CLI_OPTS="$CLI_OPTS --timeout $TIMEOUT"
CLI_OPTS="$CLI_OPTS --base-url $OLLAMA_BASE_URL"

if [ -n "$MODEL_NAME" ]; then
    CLI_OPTS="$CLI_OPTS --model $MODEL_NAME"
fi

if [ -n "$MAX_WORKERS" ]; then
    CLI_OPTS="$CLI_OPTS --workers $MAX_WORKERS"
fi

# ================================================================================
# STEP 1: EXTRACT TRIPLES
# ================================================================================
echo ""
echo "================================================================================"
echo "STEP 1: EXTRACTING TRIPLES"
echo "================================================================================"

if ! python3 -m src extract $CLI_OPTS; then
    echo "ERROR: Extraction failed"
    exit 1
fi

# ================================================================================
# STEP 2: AUGMENT CONNECTIVITY
# ================================================================================
echo ""
echo "================================================================================"
echo "STEP 2: AUGMENTING CONNECTIVITY"
echo "================================================================================"

if ! python3 -m src augment connectivity $CLI_OPTS \
    --max-disconnected $MAX_DISCONNECTED \
    --max-iterations $MAX_ITERATIONS; then
    echo "ERROR: Augmentation failed"
    exit 1
fi

# ================================================================================
# STEP 3: CONVERT TO GRAPHML
# ================================================================================
echo ""
echo "================================================================================"
echo "STEP 3: CONVERTING TO GRAPHML"
echo "================================================================================"

JSON_DIR="$OUTPUT_DIR/extracted_json"
GRAPHML_DIR="$OUTPUT_DIR/graphml"

if ! python3 -m src convert --input "$JSON_DIR" --output "$GRAPHML_DIR"; then
    echo "ERROR: Conversion failed"
    exit 1
fi

# ================================================================================
# STEP 4: CREATE VISUALIZATIONS
# ================================================================================

# Network visualization
if [ "$CREATE_NETWORK_VIZ" = true ]; then
    echo ""
    echo "================================================================================"
    echo "STEP 4a: CREATING NETWORK VISUALIZATION"
    echo "================================================================================"

    NETWORK_VIZ_DIR="$OUTPUT_DIR/network_viz"
    VIZ_OPTS="--input $GRAPHML_DIR --output $NETWORK_VIZ_DIR --layout $LAYOUT"
    if [ "$DARK_MODE" = true ]; then
        VIZ_OPTS="$VIZ_OPTS --dark-mode"
    fi

    if ! python3 -m src visualize network $VIZ_OPTS; then
        echo "WARNING: Network visualization failed"
    fi
fi

# Extraction visualization
if [ "$CREATE_EXTRACTION_VIZ" = true ]; then
    echo ""
    echo "================================================================================"
    echo "STEP 4b: CREATING EXTRACTION VISUALIZATION"
    echo "================================================================================"

    EXTRACTION_VIZ_DIR="$OUTPUT_DIR/extraction_viz"
    
    if ! python3 -m src visualize extraction \
        --input "$INPUT_FILE" \
        --triples "$JSON_DIR" \
        --output "$EXTRACTION_VIZ_DIR" \
        --text-field "$TEXT_FIELD" \
        --id-field "$ID_FIELD" \
        --group-by "$GROUP_BY"; then
        echo "WARNING: Extraction visualization failed"
    fi
fi

# ================================================================================
# SUMMARY
# ================================================================================
echo ""
echo "================================================================================"
echo "SUCCESS! All files generated in: $OUTPUT_DIR"
echo "================================================================================"
echo ""
echo "View the results:"
echo "  JSON triples: $JSON_DIR/"
echo "  GraphML: $GRAPHML_DIR/"
if [ "$CREATE_NETWORK_VIZ" = true ]; then
    echo "  Network visualization: file://$OUTPUT_DIR/network_viz/"
fi
if [ "$CREATE_EXTRACTION_VIZ" = true ]; then
    echo "  Extraction visualization: file://$OUTPUT_DIR/extraction_viz/"
fi
echo ""
echo "Output structure:"
tree -L 2 "$OUTPUT_DIR" 2>/dev/null || ls -R "$OUTPUT_DIR"
echo ""
echo "================================================================================"
echo "To explore available commands, run:"
echo "  python -m src --help"
echo "  python -m src list domains"
echo "  python -m src list clients"
echo "================================================================================"
