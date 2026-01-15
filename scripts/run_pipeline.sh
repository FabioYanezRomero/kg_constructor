#!/bin/bash
# =============================================================================
# Knowledge Graph Extraction Pipeline
# =============================================================================
# This script runs the complete extraction pipeline using CLI commands.
#
# Usage: ./run_pipeline.sh --input data.jsonl --domain legal
# =============================================================================

set -e  # Exit on error

# Default values
INPUT_FILE=""
DOMAIN=""
OUTPUT_DIR="outputs/kg_extraction"
CLIENT="gemini"
MAX_DISCONNECTED=3
MAX_ITERATIONS=2

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input|-i)
            INPUT_FILE="$2"
            shift 2
            ;;
        --domain|-d)
            DOMAIN="$2"
            shift 2
            ;;
        --output|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --client|-c)
            CLIENT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required args
if [[ -z "$INPUT_FILE" || -z "$DOMAIN" ]]; then
    echo "Usage: $0 --input <file> --domain <domain>"
    echo "Example: $0 --input data.jsonl --domain legal"
    exit 1
fi

echo "=========================================="
echo "Knowledge Graph Extraction Pipeline"
echo "=========================================="
echo "Input:  $INPUT_FILE"
echo "Domain: $DOMAIN"
echo "Output: $OUTPUT_DIR"
echo "=========================================="

# Step 1: Extract triples
echo ""
echo "[Step 1/4] Extracting triples..."
# Start time
start_time=$(date +%s)

# Step 1: Extraction
echo "Step 1: Extracting triples..."
python3 -m src extract --input "$INPUT_FILE" --domain "$DOMAIN" --output-dir "$OUTPUT_DIR" --client "$CLIENT"

# Step 2: Augmentation
echo -e "\nStep 2: Augmenting connectivity..."
python3 -m src augment connectivity --input "$INPUT_FILE" --domain "$DOMAIN" --output-dir "$OUTPUT_DIR" --client "$CLIENT" --max-disconnected "$MAX_DISCONNECTED" --max-iterations "$MAX_ITERATIONS"

# Step 3: Conversion
echo -e "\nStep 3: Converting to GraphML..."
python3 -m src convert --input "$OUTPUT_DIR/extracted_json"

# Step 4: Visualization
echo -e "\nStep 4: Creating visualizations..."
python3 -m src visualize network --input "$OUTPUT_DIR/graphml" --dark-mode

echo ""
echo "=========================================="
echo "Pipeline complete!"
echo "=========================================="
echo "Outputs:"
echo "  - JSON triples: $OUTPUT_DIR/extracted_json/"
echo "  - GraphML:      $OUTPUT_DIR/graphml/"
echo "  - HTML viz:     $OUTPUT_DIR/visualizations/"
echo "=========================================="
