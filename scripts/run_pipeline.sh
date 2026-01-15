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
python -m src.extract_cli extract \
    --input "$INPUT_FILE" \
    --domain "$DOMAIN" \
    --output-dir "$OUTPUT_DIR" \
    --client "$CLIENT"

# Step 2: Augment with connectivity
echo ""
echo "[Step 2/4] Augmenting graph connectivity..."
python -m src.extract_cli augment connectivity \
    --input "$INPUT_FILE" \
    --domain "$DOMAIN" \
    --output-dir "$OUTPUT_DIR" \
    --client "$CLIENT" \
    --max-disconnected "$MAX_DISCONNECTED" \
    --max-iterations "$MAX_ITERATIONS"

# Step 3: Convert to GraphML
echo ""
echo "[Step 3/4] Converting to GraphML..."
python -m src.extract_cli convert \
    --input "$OUTPUT_DIR/extracted_json"

# Step 4: Visualize
echo ""
echo "[Step 4/4] Creating visualizations..."
python -m src.extract_cli visualize \
    --input "$OUTPUT_DIR/graphml"

echo ""
echo "=========================================="
echo "Pipeline complete!"
echo "=========================================="
echo "Outputs:"
echo "  - JSON triples: $OUTPUT_DIR/extracted_json/"
echo "  - GraphML:      $OUTPUT_DIR/graphml/"
echo "  - HTML viz:     $OUTPUT_DIR/visualizations/"
echo "=========================================="
