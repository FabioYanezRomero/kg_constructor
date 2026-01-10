#!/bin/bash

################################################################################
# Connectivity Comparison Test
# Compares one-step vs two-step extraction approaches for graph connectivity
################################################################################

# Configuration
MODEL_PROVIDER="gemini"
MODEL_NAME="gemini-2.0-flash-exp"
TEMPERATURE=0.0
INPUT_JSON="/app/data/legal/processed/legal_background.jsonl"
RECORD_ID="UKSC-2009-0143"
TEXT_FIELD="text"
PROMPT_FILE="/app/src/prompts/legal_background_prompt.txt"

# Output directories
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_BASE="/app/test_outputs/connectivity_comparison_${TIMESTAMP}"
OUTPUT_ONE_STEP="${OUTPUT_BASE}/one_step"
OUTPUT_TWO_STEP="${OUTPUT_BASE}/two_step"

echo "================================================================================"
echo "CONNECTIVITY COMPARISON TEST"
echo "================================================================================"
echo "Testing one-step vs two-step extraction approaches"
echo "Output: $OUTPUT_BASE"
echo "================================================================================"
echo ""

# Load .env file if it exists
if [ -f "/app/.env" ]; then
    export $(grep -v '^#' /app/.env | xargs)
fi

# Create output directory
mkdir -p "$OUTPUT_BASE"

# Create comparison script
cat > "${OUTPUT_BASE}/compare_approaches.py" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""Compare one-step vs two-step extraction approaches."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from kg_constructor import KnowledgeGraphExtractor, ClientConfig
import networkx as nx

def main():
    # Read configuration
    model_provider = sys.argv[1]
    model_name = sys.argv[2]
    temperature = float(sys.argv[3])
    input_json = sys.argv[4]
    record_id = sys.argv[5]
    text_field = sys.argv[6]
    prompt_file = sys.argv[7] if sys.argv[7] else None
    output_base = Path(sys.argv[8])

    # Load input data
    print("Loading input data...")
    with open(input_json, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            if str(item.get('id', '')) == record_id:
                record = item
                break

    text = record[text_field]
    print(f"✓ Loaded record: {record_id}")
    print(f"✓ Text length: {len(text)} characters\n")

    # Configure client
    config = ClientConfig(
        client_type=model_provider,
        model_id=model_name
    )

    # Initialize extractor
    extractor = KnowledgeGraphExtractor(
        client_config=config,
        prompt_path=prompt_file
    )

    print("="*80)
    print("APPROACH 1: ONE-STEP EXTRACTION")
    print("="*80)
    print("Extracting all triples in a single API call...\n")

    # One-step extraction
    one_step_triples = extractor.extract_from_text(
        text=text,
        record_id=record_id,
        temperature=temperature
    )

    # Analyze one-step results
    G_one = nx.DiGraph()
    for triple in one_step_triples:
        if triple.get('head') and triple.get('tail'):
            G_one.add_edge(triple['head'], triple['tail'])

    components_one = list(nx.weakly_connected_components(G_one))

    one_step_results = {
        "approach": "one_step",
        "triples": len(one_step_triples),
        "nodes": G_one.number_of_nodes(),
        "edges": G_one.number_of_edges(),
        "disconnected_components": len(components_one),
        "is_connected": len(components_one) == 1,
        "avg_degree": round(2 * G_one.number_of_edges() / G_one.number_of_nodes(), 2) if G_one.number_of_nodes() > 0 else 0,
        "largest_component_size": max(len(c) for c in components_one) if components_one else 0,
        "api_calls": 1
    }

    print(f"Results:")
    print(f"  • Triples extracted: {one_step_results['triples']}")
    print(f"  • Graph nodes: {one_step_results['nodes']}")
    print(f"  • Graph edges: {one_step_results['edges']}")
    print(f"  • Disconnected components: {one_step_results['disconnected_components']}")
    print(f"  • Is connected: {one_step_results['is_connected']}")
    print(f"  • Average degree: {one_step_results['avg_degree']}")
    print(f"  • API calls: {one_step_results['api_calls']}")

    # Save one-step results
    output_one = output_base / "one_step"
    output_one.mkdir(parents=True, exist_ok=True)

    with open(output_one / "triples.json", 'w', encoding='utf-8') as f:
        json.dump(one_step_triples, f, ensure_ascii=False, indent=2)

    with open(output_one / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(one_step_results, f, ensure_ascii=False, indent=2)

    nx.write_graphml(G_one, str(output_one / "graph.graphml"))

    print("\n" + "="*80)
    print("APPROACH 2: TWO-STEP EXTRACTION WITH CONNECTIVITY REFINEMENT")
    print("="*80)
    print("Step 1: Initial extraction")
    print("Step 2: Iterative connectivity improvement\n")

    # Two-step extraction
    two_step_triples, two_step_metadata = extractor.extract_connected_graph(
        text=text,
        record_id=record_id,
        temperature=temperature,
        max_disconnected=2,  # Try to get at most 2 components
        max_iterations=2
    )

    # Analyze two-step results
    G_two = nx.DiGraph()
    for triple in two_step_triples:
        if triple.get('head') and triple.get('tail'):
            G_two.add_edge(triple['head'], triple['tail'])

    components_two = list(nx.weakly_connected_components(G_two))

    two_step_results = {
        "approach": "two_step",
        "triples": len(two_step_triples),
        "nodes": G_two.number_of_nodes(),
        "edges": G_two.number_of_edges(),
        "disconnected_components": len(components_two),
        "is_connected": len(components_two) == 1,
        "avg_degree": round(2 * G_two.number_of_edges() / G_two.number_of_nodes(), 2) if G_two.number_of_nodes() > 0 else 0,
        "largest_component_size": max(len(c) for c in components_two) if components_two else 0,
        "api_calls": 1 + two_step_metadata["final_state"]["iterations_used"],
        "refinement_metadata": two_step_metadata
    }

    print(f"Initial extraction:")
    print(f"  • Triples: {two_step_metadata['initial_extraction']['triples']}")
    print(f"  • Components: {two_step_metadata['initial_extraction']['disconnected_components']}")

    if two_step_metadata["refinement_iterations"]:
        print(f"\nRefinement iterations:")
        for it in two_step_metadata["refinement_iterations"]:
            print(f"  Iteration {it['iteration']}: +{it['new_triples']} triples, {it['disconnected_components']} components")

    print(f"\nFinal results:")
    print(f"  • Total triples: {two_step_results['triples']}")
    print(f"  • Graph nodes: {two_step_results['nodes']}")
    print(f"  • Graph edges: {two_step_results['edges']}")
    print(f"  • Disconnected components: {two_step_results['disconnected_components']}")
    print(f"  • Is connected: {two_step_results['is_connected']}")
    print(f"  • Average degree: {two_step_results['avg_degree']}")
    print(f"  • Total API calls: {two_step_results['api_calls']}")

    # Save two-step results
    output_two = output_base / "two_step"
    output_two.mkdir(parents=True, exist_ok=True)

    with open(output_two / "triples.json", 'w', encoding='utf-8') as f:
        json.dump(two_step_triples, f, ensure_ascii=False, indent=2)

    with open(output_two / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(two_step_results, f, ensure_ascii=False, indent=2)

    nx.write_graphml(G_two, str(output_two / "graph.graphml"))

    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)

    print(f"\nConnectivity Improvement:")
    print(f"  One-step:  {one_step_results['disconnected_components']} components")
    print(f"  Two-step:  {two_step_results['disconnected_components']} components")
    improvement = one_step_results['disconnected_components'] - two_step_results['disconnected_components']
    print(f"  Reduction: {improvement} components ({round(100 * improvement / one_step_results['disconnected_components'], 1)}%)")

    print(f"\nGraph Density:")
    print(f"  One-step:  {one_step_results['avg_degree']:.2f} avg degree")
    print(f"  Two-step:  {two_step_results['avg_degree']:.2f} avg degree")

    print(f"\nCost:")
    print(f"  One-step:  {one_step_results['api_calls']} API call")
    print(f"  Two-step:  {two_step_results['api_calls']} API calls")

    print(f"\nTriples Added:")
    print(f"  One-step:  {one_step_results['triples']} triples")
    print(f"  Two-step:  {two_step_results['triples']} triples (+{two_step_results['triples'] - one_step_results['triples']})")

    # Save comparison
    comparison = {
        "one_step": one_step_results,
        "two_step": two_step_results,
        "improvement": {
            "components_reduced": improvement,
            "components_reduction_percentage": round(100 * improvement / one_step_results['disconnected_components'], 1) if one_step_results['disconnected_components'] > 0 else 0,
            "additional_triples": two_step_results['triples'] - one_step_results['triples'],
            "additional_api_calls": two_step_results['api_calls'] - one_step_results['api_calls']
        }
    }

    with open(output_base / "comparison.json", 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

    print(f"\n✓ All results saved to: {output_base}")
    print("="*80)

if __name__ == "__main__":
    main()

PYTHON_EOF

# Run comparison
chmod +x "${OUTPUT_BASE}/compare_approaches.py"

python3 "${OUTPUT_BASE}/compare_approaches.py" \
    "$MODEL_PROVIDER" \
    "$MODEL_NAME" \
    "$TEMPERATURE" \
    "$INPUT_JSON" \
    "$RECORD_ID" \
    "$TEXT_FIELD" \
    "$PROMPT_FILE" \
    "$OUTPUT_BASE"

echo ""
echo "View results:"
echo "  Comparison: $OUTPUT_BASE/comparison.json"
echo "  One-step:   $OUTPUT_BASE/one_step/"
echo "  Two-step:   $OUTPUT_BASE/two_step/"
