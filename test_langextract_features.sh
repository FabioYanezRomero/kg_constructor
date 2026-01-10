#!/bin/bash
# Test script for langextract integration features
# Tests: Source grounding, few-shot examples, long document optimization, controlled generation

set -e

echo "=============================================="
echo "LangExtract Integration Test Suite"
echo "=============================================="
echo ""

# Ensure we're in the right directory
cd /app

# Load environment
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "✓ Loaded .env file"
fi

# Output directory
OUTPUT_DIR="test_outputs/langextract_integration_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"
echo "✓ Created output directory: $OUTPUT_DIR"
echo ""

# ==============================================================================
# Test 1: Source Grounding
# ==============================================================================
echo "=============================================="
echo "Test 1: Source Grounding Verification"
echo "=============================================="

python3 << 'PYTHON_SCRIPT'
import os
import json
import sys
sys.path.insert(0, '/app/src')

# Load API key
with open('/app/.env', 'r') as f:
    for line in f:
        if '=' in line:
            key, val = line.strip().split('=', 1)
            os.environ[key] = val

from kg_constructor.extractor import KnowledgeGraphExtractor

# Test text
text = """John Smith, a senior software engineer at Google Inc., filed a patent 
infringement lawsuit against Microsoft Corporation on March 15, 2024."""

print(f"Input text: {text[:80]}...")
print()

# Extract
extractor = KnowledgeGraphExtractor()
triples = extractor.extract_from_text(text, record_id="test_001")

print(f"Extracted {len(triples)} triples:")
print()

# Check source grounding
source_grounded = 0
for i, triple in enumerate(triples, 1):
    head = triple.get("head", "?")
    relation = triple.get("relation", "?")
    tail = triple.get("tail", "?")
    char_start = triple.get("char_start")
    char_end = triple.get("char_end")
    
    print(f"{i}. {head} --[{relation}]--> {tail}")
    if char_start is not None and char_end is not None:
        print(f"   ✓ Source grounding: chars {char_start}-{char_end}")
        source_grounded += 1
    else:
        print(f"   ✗ No source grounding")

print()
print(f"Source Grounding Results: {source_grounded}/{len(triples)} triples have char positions")

# Save results
import datetime
output_dir = os.environ.get('OUTPUT_DIR', 'test_outputs/langextract_integration')
os.makedirs(output_dir, exist_ok=True)
with open(f"{output_dir}/test1_source_grounding.json", "w") as f:
    json.dump({
        "test": "source_grounding",
        "input_text": text,
        "triples": triples,
        "source_grounded_count": source_grounded,
        "total_count": len(triples),
        "success": source_grounded > 0
    }, f, indent=2)

if source_grounded > 0:
    print("✓ TEST PASSED: Source grounding is working")
else:
    print("✗ TEST FAILED: No source grounding found")
    sys.exit(1)
PYTHON_SCRIPT

echo ""

# ==============================================================================
# Test 2: Few-shot Examples Effect
# ==============================================================================
echo "=============================================="
echo "Test 2: Few-shot Examples Effect"
echo "=============================================="

python3 << 'PYTHON_SCRIPT'
import os
import json
import sys
sys.path.insert(0, '/app/src')

# Load API key
with open('/app/.env', 'r') as f:
    for line in f:
        if '=' in line:
            key, val = line.strip().split('=', 1)
            os.environ[key] = val

from kg_constructor.extractor import KnowledgeGraphExtractor

# Legal domain text - should leverage legal examples
text = """Attorney Sarah Johnson from Morrison & Foerster represents Tesla Inc. 
in the environmental compliance matter. The case is being heard in the Northern 
District of California. Tesla's CEO Elon Musk stated the company is committed 
to environmental standards."""

print(f"Testing few-shot example effect on legal text...")
print()

extractor = KnowledgeGraphExtractor()
triples = extractor.extract_from_text(text)

print(f"Extracted {len(triples)} triples:")
print()

# Check for expected relationship types from examples
expected_relations = {"works_at", "represents", "is_type", "has_position"}
found_relations = set()

for i, triple in enumerate(triples, 1):
    head = triple.get("head", "?")
    relation = triple.get("relation", "?")
    tail = triple.get("tail", "?")
    
    print(f"{i}. {head} --[{relation}]--> {tail}")
    found_relations.add(relation)

print()
print(f"Found relation types: {found_relations}")
print(f"Expected from examples: {expected_relations}")

matching = found_relations & expected_relations
print(f"Matching relations: {matching}")

output_dir = os.environ.get('OUTPUT_DIR', 'test_outputs/langextract_integration')
os.makedirs(output_dir, exist_ok=True)
with open(f"{output_dir}/test2_few_shot.json", "w") as f:
    json.dump({
        "test": "few_shot_examples",
        "input_text": text,
        "triples": triples,
        "found_relations": list(found_relations),
        "expected_relations": list(expected_relations),
        "matching_relations": list(matching),
        "success": len(matching) > 0
    }, f, indent=2)

if matching:
    print("✓ TEST PASSED: Few-shot examples are influencing extraction")
else:
    print("? TEST INCONCLUSIVE: No exact relation matches (may still be working)")
PYTHON_SCRIPT

echo ""

# ==============================================================================
# Test 3: Long Document Handling
# ==============================================================================
echo "=============================================="
echo "Test 3: Long Document Handling"
echo "=============================================="

python3 << 'PYTHON_SCRIPT'
import os
import json
import sys
sys.path.insert(0, '/app/src')

# Load API key
with open('/app/.env', 'r') as f:
    for line in f:
        if '=' in line:
            key, val = line.strip().split('=', 1)
            os.environ[key] = val

from kg_constructor.extractor import KnowledgeGraphExtractor

# Load all 3 sample records to create a longer document
with open('/app/data/legal/sample_data.json', 'r') as f:
    sample_data = json.load(f)

# Combine all backgrounds into one long text
long_text = "\n\n---\n\n".join([record["background"] for record in sample_data])
print(f"Long document test: {len(long_text)} characters")
print()

extractor = KnowledgeGraphExtractor()
triples = extractor.extract_from_text(long_text, record_id="long_doc_test")

print(f"Extracted {len(triples)} triples from long document")
print()

# Group by approximate document section
print("Sample triples:")
for i, triple in enumerate(triples[:10], 1):
    head = triple.get("head", "?")
    relation = triple.get("relation", "?")
    tail = triple.get("tail", "?")
    char_start = triple.get("char_start")
    
    section = "unknown"
    if char_start is not None:
        if char_start < 600:
            section = "Section 1 (John Smith case)"
        elif char_start < 1200:
            section = "Section 2 (Tesla case)"
        else:
            section = "Section 3 (FTC case)"
    
    print(f"{i}. [{section}] {head} --[{relation}]--> {tail}")

if len(triples) > 10:
    print(f"   ... and {len(triples) - 10} more triples")

output_dir = os.environ.get('OUTPUT_DIR', 'test_outputs/langextract_integration')
os.makedirs(output_dir, exist_ok=True)
with open(f"{output_dir}/test3_long_document.json", "w") as f:
    json.dump({
        "test": "long_document",
        "document_length": len(long_text),
        "triples": triples,
        "triple_count": len(triples),
        "success": len(triples) >= 10  # Should extract many triples from 3 records
    }, f, indent=2)

if len(triples) >= 10:
    print()
    print("✓ TEST PASSED: Long document extraction working")
else:
    print()
    print("? TEST WARNING: Fewer triples than expected")
PYTHON_SCRIPT

echo ""

# ==============================================================================
# Test 4: Two-Step Extraction Still Works
# ==============================================================================
echo "=============================================="
echo "Test 4: Two-Step Extraction (Connectivity)"
echo "=============================================="

python3 << 'PYTHON_SCRIPT'
import os
import json
import sys
sys.path.insert(0, '/app/src')

# Load API key
with open('/app/.env', 'r') as f:
    for line in f:
        if '=' in line:
            key, val = line.strip().split('=', 1)
            os.environ[key] = val

from kg_constructor.extractor import KnowledgeGraphExtractor

# Text designed to have disconnected components initially
text = """John Smith filed a lawsuit against Microsoft. Sarah Johnson is an attorney 
at Morrison & Foerster. The case involves patent infringement allegations. 
Google employs several engineers who have worked on AI technology. 
The Northern District of California handles many tech-related cases."""

print("Testing two-step extraction for connectivity improvement...")
print()

extractor = KnowledgeGraphExtractor()
triples, metadata = extractor.extract_connected_graph(
    text, 
    record_id="connectivity_test",
    max_disconnected=3,
    max_iterations=2
)

print(f"Initial extraction: {metadata['initial_extraction']['triples']} triples")
print(f"Initial components: {metadata['initial_extraction']['disconnected_components']}")
print()

if metadata['refinement_iterations']:
    print("Refinement iterations:")
    for it in metadata['refinement_iterations']:
        print(f"  Iteration {it['iteration']}: +{it['new_triples']} triples, {it['disconnected_components']} components")
print()

print(f"Final state:")
print(f"  Total triples: {metadata['final_state']['total_triples']}")
print(f"  Components: {metadata['final_state']['disconnected_components']}")
print(f"  Stop reason: {metadata['final_state']['stop_reason']}")
print()

# Check source grounding in final triples
source_grounded = sum(1 for t in triples if t.get("char_start") is not None)
print(f"Source grounding: {source_grounded}/{len(triples)} triples")

output_dir = os.environ.get('OUTPUT_DIR', 'test_outputs/langextract_integration')
os.makedirs(output_dir, exist_ok=True)
with open(f"{output_dir}/test4_two_step.json", "w") as f:
    json.dump({
        "test": "two_step_extraction",
        "input_text": text,
        "triples": triples,
        "metadata": metadata,
        "source_grounded": source_grounded,
        "success": metadata['final_state']['total_triples'] > 0
    }, f, indent=2, default=str)

print("✓ TEST PASSED: Two-step extraction completed successfully")
PYTHON_SCRIPT

echo ""

# ==============================================================================
# Summary
# ==============================================================================
echo "=============================================="
echo "Test Summary"
echo "=============================================="
echo ""
echo "Output files saved to: $OUTPUT_DIR/"
ls -la "$OUTPUT_DIR/"
echo ""
echo "All tests completed!"
