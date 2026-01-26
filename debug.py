"""Debug script for stepping through extraction with a Python debugger.

Usage:
    python debug.py                    # Run extraction
    python -m pdb debug.py             # Run with pdb debugger
    python -m debugpy --listen 5678 debug.py  # Remote debugging (VS Code)

Set breakpoints anywhere to inspect the extraction process.
"""

from pathlib import Path

# Import the new modular API
from src.clients import ClientConfig, ClientFactory
from src.domains import get_domain, ExtractionMode
from src.builder import extract_from_text, extract_connected_graph
from src.datasets import load_records


# =============================================================================
# Configuration - Edit these values
# =============================================================================

# Model Configuration
MODEL_PROVIDER = "gemini"  # Options: gemini, ollama, lmstudio
MODEL_NAME = "gemini-2.0-flash"
TEMPERATURE = 0.0

# Input Data
INPUT_FILE = Path("/app/data/legal/legal_background.jsonl")
TEXT_FIELD = "text"
ID_FIELD = "id"
RECORD_IDS = ["UKSC-2009-0143"]  # List of record IDs to process

# Domain Configuration  
DOMAIN = "legal"  # Use: python -m src list domains
MODE = ExtractionMode.OPEN  # Options: OPEN, CLOSED

# Connectivity Augmentation
MAX_DISCONNECTED = 1
MAX_ITERATIONS = 5

# Output
OUTPUT_DIR = Path("/app/test_outputs/debug_output")


# =============================================================================
# Main Debugging Entry Point
# =============================================================================

def main():
    """Main function - set breakpoints here to debug extraction."""
    
    print("=" * 80)
    print("DEBUG: Knowledge Graph Extraction")
    print("=" * 80)
    
    # Step 1: Create LLM client
    print("\n[1] Creating LLM client...")
    config = ClientConfig(
        client_type=MODEL_PROVIDER,
        model_id=MODEL_NAME,
        temperature=TEMPERATURE,
        show_progress=True
    )
    client = ClientFactory.create(config)
    print(f"    Client: {client.get_model_name()}")
    
    # Step 2: Get domain
    print("\n[2] Loading domain...")
    domain = get_domain(DOMAIN, extraction_mode=MODE)
    print(f"    Domain: {DOMAIN}")
    print(f"    Mode: {MODE}")
    
    # Step 3: Load records
    print("\n[3] Loading records...")
    records = load_records(
        path=INPUT_FILE,
        text_field=TEXT_FIELD,
        id_field=ID_FIELD,
        record_ids=RECORD_IDS
    )
    print(f"    Loaded {len(records)} record(s)")
    
    # Step 4: Process each record
    all_results = {}
    
    for record in records:
        record_id = str(record["id"])
        text = str(record["text"])
        
        print(f"\n[4] Processing record: {record_id}")
        print(f"    Text length: {len(text)} chars")
        print(f"    Text preview: {text[:100]}...")
        
        # ------------------------------------------------------------------
        # SET BREAKPOINT HERE to step into extraction
        # ------------------------------------------------------------------
        
        # Option A: Simple extraction (Step 1 only)
        # triples = extract_from_text(
        #     client=client,
        #     domain=domain,
        #     text=text,
        #     record_id=record_id,
        #     temperature=TEMPERATURE
        # )
        # metadata = {}
        
        # Option B: Connected graph extraction (Step 1 + Augmentation)
        triples, metadata = extract_connected_graph(
            client=client,
            domain=domain,
            text=text,
            record_id=record_id,
            temperature=TEMPERATURE,
            max_disconnected=MAX_DISCONNECTED,
            max_iterations=MAX_ITERATIONS
        )
        
        # ------------------------------------------------------------------
        # SET BREAKPOINT HERE to inspect results
        # ------------------------------------------------------------------
        
        print(f"\n[5] Results for {record_id}:")
        print(f"    Triples extracted: {len(triples)}")
        print(f"    Final components: {metadata.get('final_components', 'N/A')}")
        
        # Show first few triples
        print("\n    Sample triples:")
        for i, triple in enumerate(triples[:5], 1):
            print(f"      {i}. {triple.head} --[{triple.relation}]--> {triple.tail}")
        
        if len(triples) > 5:
            print(f"      ... and {len(triples) - 5} more")
        
        all_results[record_id] = {
            "triples": triples,
            "metadata": metadata
        }
    
    print("\n" + "=" * 80)
    print("DEBUG: Extraction Complete")
    print("=" * 80)
    
    # Return results for inspection in debugger
    return all_results


if __name__ == "__main__":
    # You can set a breakpoint on this line
    results = main()
    
    # Inspect results in debugger here
    print(f"\nTotal records processed: {len(results)}")