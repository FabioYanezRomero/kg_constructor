#!/bin/bash

################################################################################
# HYPERPARAMETERS - Configure these at the top
################################################################################

# API Key Configuration (for Gemini only)
# Option 1: Set here (not recommended for security)
# GEMINI_API_KEY="your-api-key-here"

# Option 2: Set as environment variable (recommended)
# export LANGEXTRACT_API_KEY="your-api-key-here"
# or
# export GOOGLE_API_KEY="your-api-key-here"

# Option 3: Load from .env file
# The script will automatically check for .env file in /app

# Model Configuration
MODEL_PROVIDER="gemini"  # Options: gemini, ollama, lmstudio
MODEL_NAME="gemini-2.0-flash"  # For gemini: gemini-2.0-flash, gemini-2.5-flash, etc.
TEMPERATURE=0.0

# LangExtract Configuration (NEW - leverages full langextract features)
EXTRACTION_PASSES=1      # Multiple passes for higher recall (1-3 recommended)
MAX_WORKERS=10           # Parallel processing workers for long documents
MAX_CHAR_BUFFER=8000     # Maximum characters per chunk for long documents

# Input Data
INPUT_JSON="/app/data/legal/processed/legal_background.jsonl"  # Path to your JSON file
RECORD_ID="UKSC-2009-0143"  # The ID/key of the specific record to process
TEXT_FIELD="text"  # Field name containing the text to analyze

# Prompt Configuration (Two-Step Extraction)
PROMPT_FILE_STEP1="/app/src/prompts/legal_background_prompt_step1_initial.txt"  # Initial extraction prompt
PROMPT_FILE_STEP2="/app/src/prompts/legal_background_prompt_step2_bridging.txt"  # Bridging/refinement prompt

# Output Configuration
OUTPUT_DIR="/app/test_outputs/single_extraction_$(date +%Y%m%d_%H%M%S)"

# Visualization Options
CREATE_ENTITY_VIZ=true  # Create langextract HTML visualization
CREATE_GRAPH_VIZ=true   # Create NetworkX/Plotly graph visualization
ENTITY_GROUP_BY="entity_type"  # Options: entity_type, relation

# Connectivity Configuration (Two-Step Extraction)
MAX_DISCONNECTED=1  # Maximum acceptable disconnected components
MAX_ITERATIONS=5    # Max refinement iterations (increased to 5 to push for full connectivity)

################################################################################
# Script Execution - Do not modify below this line
################################################################################

set -e  # Exit on error

# Load .env file if it exists
if [ -f "/app/.env" ]; then
    echo "Loading environment variables from /app/.env"
    export $(grep -v '^#' /app/.env | xargs)
fi

# Check API key for Gemini
if [ "$MODEL_PROVIDER" = "gemini" ]; then
    if [ -z "$LANGEXTRACT_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ] && [ -z "$GEMINI_API_KEY" ]; then
        echo "================================================================================"
        echo "ERROR: Gemini API key not found!"
        echo "================================================================================"
        echo ""
        echo "Please set your API key using one of these methods:"
        echo ""
        echo "1. Environment variable (recommended):"
        echo "   export LANGEXTRACT_API_KEY='your-api-key-here'"
        echo "   or"
        echo "   export GOOGLE_API_KEY='your-api-key-here'"
        echo ""
        echo "2. Create .env file:"
        echo "   echo 'LANGEXTRACT_API_KEY=your-api-key-here' > /app/.env"
        echo ""
        echo "3. Set in script (not recommended):"
        echo "   Edit this script and uncomment the GEMINI_API_KEY line at the top"
        echo ""
        echo "Get your API key from: https://aistudio.google.com/app/apikey"
        echo "================================================================================"
        exit 1
    fi

    # Use GEMINI_API_KEY if set in script, otherwise use env vars
    if [ -n "$GEMINI_API_KEY" ]; then
        export LANGEXTRACT_API_KEY="$GEMINI_API_KEY"
    fi
fi

echo "================================================================================"
echo "KNOWLEDGE GRAPH EXTRACTION - SINGLE TEXT TEST"
echo "Using LangExtract for: Source Grounding, Few-shot Learning, Long Doc Optimization"
echo "================================================================================"
echo "Model Provider: $MODEL_PROVIDER"
echo "Model Name: $MODEL_NAME"
echo "Input JSON: $INPUT_JSON"
echo "Record ID: $RECORD_ID"
echo "Text Field: $TEXT_FIELD"
echo "Output Directory: $OUTPUT_DIR"
echo ""
echo "LangExtract Configuration:"
echo "  • Extraction passes: $EXTRACTION_PASSES"
echo "  • Max workers: $MAX_WORKERS"
echo "  • Max char buffer: $MAX_CHAR_BUFFER"
echo ""
echo "Extraction Method: Two-Step Connectivity-Aware"
echo "  • Max disconnected: $MAX_DISCONNECTED"
echo "  • Max iterations: $MAX_ITERATIONS"
if [ "$MODEL_PROVIDER" = "gemini" ]; then
    if [ -n "$LANGEXTRACT_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ]; then
        echo "API Key: ✓ Configured"
    fi
fi
echo "================================================================================"

# Create output directory structure
mkdir -p "$OUTPUT_DIR"/{json,graphml,metadata,entity_viz,graph_viz}

# Create a temporary Python script for extraction
PYTHON_SCRIPT="$OUTPUT_DIR/extract_single.py"

cat > "$PYTHON_SCRIPT" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""Single text extraction script using full LangExtract integration.

This script leverages all langextract features:
- Source Grounding: Character-level positions for each extraction
- Few-shot Examples: Schema enforcement via examples
- Long Document Optimization: Chunking and parallel processing
- Controlled Generation: Native JSON schema constraints
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kg_constructor import ExtractionPipeline, ClientConfig

def main():
    # Read configuration from command line
    model_provider = sys.argv[1]
    model_name = sys.argv[2]
    temperature = float(sys.argv[3])
    input_json = sys.argv[4]
    record_id = sys.argv[5]
    text_field = sys.argv[6]
    output_dir = Path(sys.argv[7])
    create_entity_viz = sys.argv[8].lower() == 'true'
    create_graph_viz = sys.argv[9].lower() == 'true'
    entity_group_by = sys.argv[10]
    max_disconnected = int(sys.argv[11])
    max_iterations = int(sys.argv[12])
    prompt_file_step1 = sys.argv[13] if sys.argv[13] else None
    prompt_file_step2 = sys.argv[14] if sys.argv[14] else None
    extraction_passes = int(sys.argv[15])
    max_workers = int(sys.argv[16])
    max_char_buffer = int(sys.argv[17])

    print(f"\n{'='*80}")
    print("STEP 1: LOADING INPUT DATA")
    print(f"{'='*80}")

    # Determine if it's JSONL or JSON based on file extension
    is_jsonl = input_json.endswith('.jsonl')

    record = None

    if is_jsonl:
        # Load JSONL file (each line is a separate JSON object)
        print(f"Loading JSONL file: {input_json}")
        with open(input_json, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if str(item.get('id', '')) == record_id:
                        record = item
                        print(f"✓ Found record at line {line_num}")
                        break
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON at line {line_num}: {e}")
                    continue

        if not record:
            print(f"ERROR: Record with ID '{record_id}' not found in JSONL file")
            sys.exit(1)
    else:
        # Load regular JSON file
        print(f"Loading JSON file: {input_json}")
        with open(input_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract the specific record
        if isinstance(data, list):
            # If it's a list, find by ID
            for item in data:
                if str(item.get('id', '')) == record_id:
                    record = item
                    break
            if not record:
                print(f"ERROR: Record with ID '{record_id}' not found in list")
                sys.exit(1)
        elif isinstance(data, dict):
            # If it's a dict, use the record_id as key
            if record_id in data:
                record = data[record_id]
            else:
                print(f"ERROR: Record with ID '{record_id}' not found in dict")
                sys.exit(1)
        else:
            print(f"ERROR: Unexpected JSON structure (not list or dict)")
            sys.exit(1)

    # Extract the text
    if text_field not in record:
        print(f"ERROR: Field '{text_field}' not found in record")
        print(f"Available fields: {list(record.keys())}")
        sys.exit(1)

    text = str(record[text_field])
    print(f"✓ Loaded record: {record_id}")
    print(f"✓ Text field: {text_field}")
    print(f"✓ Text length: {len(text)} characters")
    print(f"\nText preview (first 200 chars):")
    print(f"{text[:200]}...")

    print(f"\n{'='*80}")
    print("STEP 2: INITIALIZING EXTRACTION PIPELINE (WITH LANGEXTRACT)")
    print(f"{'='*80}")

    # Configure client with langextract parameters
    config = ClientConfig(
        client_type=model_provider,
        model_id=model_name,
        temperature=temperature,
        extraction_passes=extraction_passes,
        max_workers=max_workers,
        max_char_buffer=max_char_buffer,
        show_progress=True,
    )

    # Two-step extraction prompts
    initial_prompt = prompt_file_step1 if prompt_file_step1 else None
    bridging_prompt = prompt_file_step2 if prompt_file_step2 else None
    print(f"Using two-step extraction prompts:")
    print(f"  • Step 1 (initial): {initial_prompt or 'default'}")
    print(f"  • Step 2 (bridging): {bridging_prompt or 'hardcoded default'}")

    # Initialize pipeline
    pipeline = ExtractionPipeline(
        output_dir=output_dir,
        client_config=config,
        prompt_path=initial_prompt,
        bridging_prompt_path=bridging_prompt,
        enable_entity_viz=create_entity_viz
    )

    print(f"✓ Client: {pipeline.extractor.client.__class__.__name__}")
    print(f"✓ Model: {pipeline.extractor.get_model_name()}")
    print(f"✓ Temperature: {temperature}")
    print(f"\nLangExtract Features Enabled:")
    print(f"  ✓ Source Grounding (char_start, char_end for each triple)")
    print(f"  ✓ Few-shot Examples (guiding extraction quality)")
    print(f"  ✓ Controlled Generation (JSON schema constraints)")
    print(f"  ✓ Long Document Optimization (passes={extraction_passes}, workers={max_workers})")

    print(f"\n{'='*80}")
    print("STEP 3: EXTRACTING TRIPLES WITH LANGEXTRACT")
    print(f"{'='*80}")

    # Two-step extraction with connectivity awareness
    print(f"Using Two-Step Connectivity-Aware Extraction")
    print(f"  • Max disconnected components: {max_disconnected}")
    print(f"  • Max iterations: {max_iterations}\n")

    triples, metadata = pipeline.extractor.extract_connected_graph(
        text=text,
        record_id=record_id,
        temperature=temperature,
        max_disconnected=max_disconnected,
        max_iterations=max_iterations
    )

    # Show extraction progress
    print(f"\nInitial extraction:")
    print(f"  • Triples: {metadata['initial_extraction']['triples']}")
    print(f"  • Components: {metadata['initial_extraction']['disconnected_components']}")

    if metadata['refinement_iterations']:
        print(f"\nRefinement iterations:")
        for it in metadata['refinement_iterations']:
            print(f"  Iteration {it['iteration']}: +{it['new_triples']} triples, {it['disconnected_components']} components")

    print(f"\nFinal results:")
    print(f"  • Total triples: {metadata['final_state']['total_triples']}")
    print(f"  • Disconnected components: {metadata['final_state']['disconnected_components']}")
    print(f"  • Is connected: {metadata['final_state']['is_connected']}")
    print(f"  • Total API calls: {1 + metadata['final_state']['iterations_used']}")

    print(f"\n✓ Extracted {len(triples)} triples")

    # Show source grounding and iteration tracking statistics
    print(f"\n{'='*80}")
    print("TRACEABILITY ANALYSIS (LangExtract Features)")
    print(f"{'='*80}")
    
    source_grounded = sum(1 for t in triples if t.get("char_start") is not None)
    print(f"Source grounded triples: {source_grounded}/{len(triples)} ({100*source_grounded/len(triples):.1f}%)")
    
    # Iteration tracking stats
    initial_count = sum(1 for t in triples if t.get("iteration_source") == 0)
    bridging_count = sum(1 for t in triples if t.get("iteration_source", 0) > 0)
    print(f"Initial extraction triples: {initial_count}")
    print(f"Bridging triples (iterations 1+): {bridging_count}")
    
    print(f"\nSample triples with traceability:")
    for i, triple in enumerate(triples[:5], 1):
        head = triple.get('head', 'N/A')
        relation = triple.get('relation', 'N/A')
        tail = triple.get('tail', 'N/A')
        char_start = triple.get('char_start')
        char_end = triple.get('char_end')
        iteration_source = triple.get('iteration_source', 'N/A')
        extraction_text = triple.get('extraction_text', '')
        
        iter_label = "initial" if iteration_source == 0 else f"bridging-{iteration_source}"
        print(f"\n  {i}. [{iter_label}] {head} → [{relation}] → {tail}")
        if char_start is not None and char_end is not None:
            print(f"     ✓ Source: chars {char_start}-{char_end}")
            if extraction_text:
                # Show the extracted text span (truncated)
                span = extraction_text[:60] + "..." if len(extraction_text) > 60 else extraction_text
                print(f"     ✓ Text: \"{span}\"")
        else:
            print(f"     ✗ No source grounding")
    
    if len(triples) > 5:
        print(f"\n  ... and {len(triples) - 5} more triples")

    # Save JSON files with traceability
    print(f"\n{'='*80}")
    print("SAVING TRACEABILITY FILES")
    print(f"{'='*80}")
    
    # 1. All triples (with iteration_source)
    json_path = output_dir / "json" / f"{record_id}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(triples, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved all triples: {json_path}")
    
    # 2. Bridging triples only
    bridging_triples = metadata.get("bridging_triples", [])
    bridging_path = output_dir / "json" / f"{record_id}_bridging.json"
    with open(bridging_path, 'w', encoding='utf-8') as f:
        json.dump(bridging_triples, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved bridging triples: {bridging_path} ({len(bridging_triples)} triples)")
    
    # 3. Few-shot examples used
    examples = pipeline.extractor.get_examples_as_dict()
    examples_path = output_dir / "json" / f"{record_id}_examples.json"
    with open(examples_path, 'w', encoding='utf-8') as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved few-shot examples: {examples_path} ({len(examples)} examples)")

    print(f"\n{'='*80}")
    print("STEP 4: CONVERTING TO GRAPHML")
    print(f"{'='*80}")

    # Convert to GraphML
    graphml_files = pipeline.export_to_graphml(
        json_input_dir=output_dir / "json",
        graphml_output_dir=output_dir / "graphml"
    )

    print(f"✓ Created {len(graphml_files)} GraphML file(s)")
    for gml_file in graphml_files:
        print(f"  - {gml_file}")

    print(f"\n{'='*80}")
    print("STEP 5: GENERATING METADATA AND ANALYTICS")
    print(f"{'='*80}")

    # Generate metadata and analytics
    import networkx as nx
    from datetime import datetime

    # Load the GraphML to analyze graph structure
    graphml_path = output_dir / "graphml" / f"{record_id}.graphml"
    G = nx.read_graphml(str(graphml_path))

    # Calculate analytics
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    num_components = nx.number_weakly_connected_components(G)

    # Analyze inference types
    explicit_count = sum(1 for t in triples if t.get('inference') == 'explicit')
    contextual_count = sum(1 for t in triples if t.get('inference') == 'contextual')

    # Check which entities appear in the text
    text_lower = text.lower()
    entities_in_text = 0
    entities_inferred = 0
    all_entities = set()

    for triple in triples:
        head = triple.get('head', '')
        tail = triple.get('tail', '')
        all_entities.add(head)
        all_entities.add(tail)

    for entity in all_entities:
        if entity.lower() in text_lower:
            entities_in_text += 1
        else:
            entities_inferred += 1

    total_entities = len(all_entities)

    # Build metadata (preserve iterative extraction metadata if available)
    output_metadata = {
        "extraction_info": {
            "record_id": record_id,
            "timestamp": datetime.now().isoformat(),
            "model_provider": model_provider,
            "model_name": model_name,
            "temperature": temperature,
            "prompt_step1": str(prompt_file_step1) if prompt_file_step1 else "default",
            "prompt_step2": str(prompt_file_step2) if prompt_file_step2 else "hardcoded",
            "extraction_method": "two_step_connectivity_aware",
        },
        "langextract_config": {
            "extraction_passes": extraction_passes,
            "max_workers": max_workers,
            "max_char_buffer": max_char_buffer,
            "features_enabled": [
                "source_grounding",
                "few_shot_examples",
                "controlled_generation",
                "long_document_optimization",
            ],
            "merge_strategy": "first_pass_wins (non-overlapping)",
        },
        "input_data": {
            "source_file": input_json,
            "text_field": text_field,
            "text_length_chars": len(text),
            "text_length_words": len(text.split()),
        },
        "extraction_results": {
            "total_triples": len(triples),
            "initial_triples": initial_count,
            "bridging_triples": bridging_count,
            "explicit_triples": explicit_count,
            "contextual_triples": contextual_count,
            "explicit_percentage": round(100 * explicit_count / len(triples), 2) if triples else 0,
            "contextual_percentage": round(100 * contextual_count / len(triples), 2) if triples else 0,
            "source_grounded_triples": source_grounded,
            "source_grounded_percentage": round(100 * source_grounded / len(triples), 2) if triples else 0,
        },
        "graph_structure": {
            "total_nodes": num_nodes,
            "total_edges": num_edges,
            "disconnected_components": num_components,
            "is_connected": num_components == 1,
            "avg_degree": round(2 * num_edges / num_nodes, 2) if num_nodes > 0 else 0,
        },
        "entity_analysis": {
            "total_unique_entities": total_entities,
            "entities_found_in_text": entities_in_text,
            "entities_inferred": entities_inferred,
            "entities_in_text_percentage": round(100 * entities_in_text / total_entities, 2) if total_entities else 0,
            "entities_inferred_percentage": round(100 * entities_inferred / total_entities, 2) if total_entities else 0,
        },
        "relation_analysis": {
            "unique_relations": len(set(t.get('relation', '') for t in triples)),
            "most_common_relations": {},
        }
    }

    # Count relation frequencies
    from collections import Counter
    relation_counts = Counter(t.get('relation', '') for t in triples)
    output_metadata["relation_analysis"]["most_common_relations"] = dict(relation_counts.most_common(10))

    # Add iterative extraction metadata if available
    if metadata:
        output_metadata["iterative_extraction"] = {
            "max_disconnected": max_disconnected,
            "max_iterations": max_iterations,
            "initial_extraction": metadata["initial_extraction"],
            "refinement_iterations": metadata["refinement_iterations"],
            "final_state": metadata["final_state"],
            "total_api_calls": 1 + metadata["final_state"]["iterations_used"]
        }

    # Save metadata
    metadata_path = output_dir / "metadata" / f"{record_id}_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(output_metadata, f, ensure_ascii=False, indent=2)

    print(f"✓ Generated metadata: {metadata_path}")
    print(f"\nKey Analytics:")
    print(f"  • Total triples: {len(triples)} ({explicit_count} explicit, {contextual_count} contextual)")
    print(f"  • Source grounded: {source_grounded}/{len(triples)} ({output_metadata['extraction_results']['source_grounded_percentage']}%)")
    print(f"  • Unique entities: {total_entities} ({entities_in_text} in text, {entities_inferred} inferred)")
    print(f"  • Graph nodes: {num_nodes}, edges: {num_edges}")
    print(f"  • Connected components: {num_components}")
    print(f"  • Average degree: {output_metadata['graph_structure']['avg_degree']}")

    # Create visualizations
    if create_entity_viz and pipeline.entity_visualizer:
        print(f"\n{'='*80}")
        print("STEP 6: CREATING ENTITY VISUALIZATION (LANGEXTRACT HTML)")
        print(f"{'='*80}")

        entity_html_files = pipeline.visualize_entities(
            texts={record_id: text},
            triples={record_id: triples},
            entity_viz_dir=output_dir / "entity_viz",
            group_by=entity_group_by
        )

        print(f"✓ Created {len(entity_html_files)} entity visualization(s)")
        for html_file in entity_html_files:
            print(f"  - {html_file}")

    if create_graph_viz:
        print(f"\n{'='*80}")
        print("STEP 7: CREATING GRAPH VISUALIZATION (PLOTLY NETWORK)")
        print(f"{'='*80}")

        graph_html_files = pipeline.visualize_graphs(
            graphml_dir=output_dir / "graphml",
            viz_output_dir=output_dir / "graph_viz"
        )

        print(f"✓ Created {len(graph_html_files)} graph visualization(s)")
        for html_file in graph_html_files:
            print(f"  - {html_file}")

    print(f"\n{'='*80}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*80}")
    print(f"Output directory: {output_dir}")
    print(f"\nGenerated files:")
    print(f"  - JSON triples: {output_dir / 'json' / f'{record_id}.json'}")
    print(f"  - Bridging triples: {output_dir / 'json' / f'{record_id}_bridging.json'}")
    print(f"  - Few-shot examples: {output_dir / 'json' / f'{record_id}_examples.json'}")
    print(f"  - GraphML: {output_dir / 'graphml' / f'{record_id}.graphml'}")
    print(f"  - Metadata: {output_dir / 'metadata' / f'{record_id}_metadata.json'}")
    if create_entity_viz:
        print(f"  - Entity HTML: {output_dir / 'entity_viz' / f'{record_id}.html'}")
    if create_graph_viz:
        print(f"  - Graph HTML: {output_dir / 'graph_viz' / f'{record_id}.html'}")
    print(f"\nTraceability Summary:")
    print(f"  ✓ Source Grounding: {source_grounded}/{len(triples)} triples with char positions")
    print(f"  ✓ Iteration Tracking: {initial_count} initial + {bridging_count} bridging triples")
    print(f"  ✓ Few-shot Examples: {len(examples)} examples saved")
    print(f"  ✓ Long Doc Optimization: passes={extraction_passes}, workers={max_workers}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()

PYTHON_EOF

# Make the Python script executable
chmod +x "$PYTHON_SCRIPT"

# Run the extraction
echo ""
echo "Running extraction pipeline with LangExtract..."
echo ""

python3 "$PYTHON_SCRIPT" \
    "$MODEL_PROVIDER" \
    "$MODEL_NAME" \
    "$TEMPERATURE" \
    "$INPUT_JSON" \
    "$RECORD_ID" \
    "$TEXT_FIELD" \
    "$OUTPUT_DIR" \
    "$CREATE_ENTITY_VIZ" \
    "$CREATE_GRAPH_VIZ" \
    "$ENTITY_GROUP_BY" \
    "$MAX_DISCONNECTED" \
    "$MAX_ITERATIONS" \
    "$PROMPT_FILE_STEP1" \
    "$PROMPT_FILE_STEP2" \
    "$EXTRACTION_PASSES" \
    "$MAX_WORKERS" \
    "$MAX_CHAR_BUFFER"

EXTRACTION_EXIT_CODE=$?

if [ $EXTRACTION_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "================================================================================"
    echo "SUCCESS! All files generated in: $OUTPUT_DIR"
    echo "================================================================================"
    echo ""
    echo "View the results:"
    echo "  Metadata & Analytics: $OUTPUT_DIR/metadata/${RECORD_ID}_metadata.json"
    if [ "$CREATE_ENTITY_VIZ" = true ]; then
        echo "  Entity visualization: file://$OUTPUT_DIR/entity_viz/$RECORD_ID.html"
    fi
    if [ "$CREATE_GRAPH_VIZ" = true ]; then
        echo "  Graph visualization:  file://$OUTPUT_DIR/graph_viz/$RECORD_ID.html"
    fi
    echo ""
    echo "Output structure:"
    tree -L 2 "$OUTPUT_DIR" 2>/dev/null || ls -R "$OUTPUT_DIR"
else
    echo ""
    echo "================================================================================"
    echo "ERROR: Extraction failed with exit code $EXTRACTION_EXIT_CODE"
    echo "================================================================================"
    exit $EXTRACTION_EXIT_CODE
fi
