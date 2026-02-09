#!/bin/bash

################################################################################
# TEST AUGMENTATION ONLY - OLLAMA
# This script runs only the augmentation step from existing extracted data.
# Use this to test the connectivity augmentation with intermediate results.
################################################################################

################################################################################
# HYPERPARAMETERS - Configure these at the top
################################################################################

# Ollama Configuration
MODEL_PROVIDER="ollama"
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

# Input Data - Path to original input file (for text context)
INPUT_FILE="${BASE_DIR}/data/legal/legal_background.jsonl"
TEXT_FIELD="text"
ID_FIELD="id"
RECORD_IDS="UKSC-2009-0143"

# Source data directory - Where the extracted JSON is located (from previous extraction)
# Change this to point to an existing extraction output
SOURCE_OUTPUT_DIR="${BASE_DIR}/test_outputs/single_extraction_lmstudio_20260124_181032"

# Domain Configuration
DOMAIN="legal"
MODE="open"

# Output Configuration - Where to save augmented results
OUTPUT_DIR="${BASE_DIR}/test_outputs/augmentation_only_ollama_$(date +%Y%m%d_%H%M%S)"

# Connectivity Augmentation Configuration
MAX_DISCONNECTED=1  # Target: single connected component
MAX_ITERATIONS=3    # Max refinement iterations

# Visualization Options
CREATE_NETWORK_VIZ=true
CREATE_EXTRACTION_VIZ=true
DARK_MODE=false
LAYOUT="spring"
GROUP_BY="entity_type"

# Processing Options
MAX_WORKERS=3
TIMEOUT=300

################################################################################
# Script Execution
################################################################################

set -e

echo "================================================================================"
echo "KNOWLEDGE GRAPH AUGMENTATION TEST - Ollama"
echo "Testing augmentation step from existing extracted data"
echo "================================================================================"
echo "Model Provider: $MODEL_PROVIDER"
echo "Model Name: $MODEL_NAME"
echo "Ollama URL: $OLLAMA_BASE_URL"
echo ""
echo "Source Data: $SOURCE_OUTPUT_DIR"
echo "Output Directory: $OUTPUT_DIR"
echo ""
echo "Connectivity Configuration:"
echo "  • Max disconnected: $MAX_DISCONNECTED"
echo "  • Max iterations: $MAX_ITERATIONS"
echo "================================================================================"

# Check if source data exists
SOURCE_JSON_DIR="$SOURCE_OUTPUT_DIR/extracted_json"
if [ ! -d "$SOURCE_JSON_DIR" ]; then
    echo "ERROR: Source JSON directory not found: $SOURCE_JSON_DIR"
    echo "Please run the full extraction first or update SOURCE_OUTPUT_DIR."
    exit 1
fi

echo ""
echo "Found source extraction data at: $SOURCE_JSON_DIR"
ls -la "$SOURCE_JSON_DIR"

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
print('================================================================================')
"

# Create output directory and copy existing extraction data
mkdir -p "$OUTPUT_DIR/extracted_json"
echo ""
echo "Copying source extraction data to output directory..."
cp "$SOURCE_JSON_DIR"/*.json "$OUTPUT_DIR/extracted_json/"
echo "✓ Copied $(ls -1 "$OUTPUT_DIR/extracted_json" | wc -l) JSON files"

# Build CLI options for augmentation
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
# STEP 1: AUGMENT CONNECTIVITY (Main test)
# ================================================================================
echo ""
echo "================================================================================"
echo "STEP 1: AUGMENTING CONNECTIVITY"
echo "Starting from existing extraction with $(ls -1 "$OUTPUT_DIR/extracted_json" | wc -l) files"
echo "================================================================================"

if ! python3 -m src augment connectivity $CLI_OPTS \
    --max-disconnected $MAX_DISCONNECTED \
    --max-iterations $MAX_ITERATIONS; then
    echo "ERROR: Augmentation failed"
    exit 1
fi

# ================================================================================
# STEP 2: CONVERT TO GRAPHML
# ================================================================================
echo ""
echo "================================================================================"
echo "STEP 2: CONVERTING TO GRAPHML"
echo "================================================================================"

JSON_DIR="$OUTPUT_DIR/extracted_json"
GRAPHML_DIR="$OUTPUT_DIR/graphml"

if ! python3 -m src convert --input "$JSON_DIR" --output "$GRAPHML_DIR"; then
    echo "ERROR: Conversion failed"
    exit 1
fi

# ================================================================================
# STEP 3: CREATE VISUALIZATIONS
# ================================================================================

# Network visualization
if [ "$CREATE_NETWORK_VIZ" = true ]; then
    echo ""
    echo "================================================================================"
    echo "STEP 3a: CREATING NETWORK VISUALIZATION"
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
    echo "STEP 3b: CREATING EXTRACTION VISUALIZATION"
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
echo "AUGMENTATION TEST COMPLETE"
echo "================================================================================"
echo ""
echo "Output Directory: $OUTPUT_DIR"
echo ""
echo "Generated Files:"
ls -la "$OUTPUT_DIR/extracted_json/" 2>/dev/null || echo "  (no JSON files)"
echo ""

# Compare before and after
echo "Comparing extraction before and after augmentation:"
echo ""
BEFORE_TRIPLES=$(python3 -c "
import json
import glob
total = 0
for f in glob.glob('$SOURCE_JSON_DIR/*.json'):
    with open(f) as fp:
        total += len(json.load(fp))
print(total)
")
AFTER_TRIPLES=$(python3 -c "
import json
import glob
total = 0
for f in glob.glob('$OUTPUT_DIR/extracted_json/*.json'):
    with open(f) as fp:
        total += len(json.load(fp))
print(total)
")

echo "  Before augmentation: $BEFORE_TRIPLES triples"
echo "  After augmentation:  $AFTER_TRIPLES triples"
echo "  New bridging triples: $((AFTER_TRIPLES - BEFORE_TRIPLES))"
echo ""

if [ "$CREATE_NETWORK_VIZ" = true ]; then
    echo "Network Visualization:"
    ls -la "$OUTPUT_DIR/network_viz/" 2>/dev/null || echo "  (no visualization files)"
    echo ""
fi

if [ "$CREATE_EXTRACTION_VIZ" = true ]; then
    echo "Extraction Visualization:"
    ls -la "$OUTPUT_DIR/extraction_viz/" 2>/dev/null || echo "  (no visualization files)"
    echo ""
fi

echo "================================================================================"
echo "Done! Review the output at: $OUTPUT_DIR"
echo "================================================================================"
