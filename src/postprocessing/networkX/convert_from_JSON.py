import networkx as nx 
import json
import os
import argparse
from collections import defaultdict


def normalize_entity_name(name: str) -> str:
    """
    Normalize entity name by:
    - Stripping whitespace
    - Converting to a canonical form (preserve original case but use for matching)
    
    Args:
        name: Original entity name
    
    Returns:
        Normalized entity name (lowercase for matching, but we'll use canonical form)
    """
    if not name:
        return ""
    # Strip whitespace
    normalized = name.strip()
    return normalized


def get_canonical_name(name: str, entity_map: dict) -> str:
    """
    Get the canonical form of an entity name, creating it if needed.
    Uses case-insensitive matching to find existing entities.
    
    Args:
        name: Entity name to normalize
        entity_map: Dictionary mapping normalized (lowercase) names to canonical forms
    
    Returns:
        Canonical entity name
    """
    normalized = normalize_entity_name(name)
    if not normalized:
        return ""
    
    # Use lowercase for matching (case-insensitive)
    key = normalized.lower()
    
    # If we've seen this entity before (case-insensitive), use the canonical form
    if key in entity_map:
        return entity_map[key]
    
    # First time seeing this entity (or this case variation)
    # Use the normalized form as canonical (preserves original case/formatting)
    entity_map[key] = normalized
    return normalized


def convert_from_JSON(input_dir: str, output_dir: str):
    """
    Convert JSON files containing triples to GraphML format.
    Normalizes entity names to avoid disconnected components due to case/whitespace variations.
    Processes all edges regardless of inference type, preserving all available attributes.
    
    Args:
        input_dir: Directory containing JSON files
        output_dir: Directory to save GraphML files
    """
    for file in os.listdir(input_dir):
        if file.endswith(".json"):
            filename = file.split(".")[0]
            with open(os.path.join(input_dir, file), "r") as f:
                data = json.load(f)
                G = nx.DiGraph()
                
                # Map to track canonical entity names (case-insensitive matching)
                entity_map = {}
                
                # Track statistics
                normalization_stats = {
                    "total_edges": 0,
                    "normalized_heads": 0,
                    "normalized_tails": 0
                }
                
                # data is a list of dictionaries with at least the fields "head", "relation", "tail", "inference"
                for item in data:
                    # Head, Relation, and Tail are required fields
                    original_head = item["head"]
                    original_tail = item["tail"]
                    relation = item["relation"]
                    
                    # Normalize entity names (case-insensitive, whitespace-trimmed)
                    head = get_canonical_name(original_head, entity_map)
                    tail = get_canonical_name(original_tail, entity_map)
                    
                    # Track if entity was normalized (merged with existing entity due to case/whitespace)
                    normalized_head = normalize_entity_name(original_head)
                    normalized_tail = normalize_entity_name(original_tail)
                    
                    # Check if canonical form differs from normalized form (means it was merged)
                    if head != normalized_head:
                        normalization_stats["normalized_heads"] += 1
                    if tail != normalized_tail:
                        normalization_stats["normalized_tails"] += 1
                    
                    # Skip if entities are empty after normalization
                    if not head or not tail:
                        continue
                    
                    # Optional fields
                    inference = item.get("inference", None)
                    justification = item.get("justification", None)
                    
                    # Store original names as node attributes if they differ from canonical
                    if head not in G.nodes():
                        G.add_node(head)
                        if head != original_head.strip():
                            G.nodes[head]["original_name"] = original_head
                    
                    if tail not in G.nodes():
                        G.add_node(tail)
                        if tail != original_tail.strip():
                            G.nodes[tail]["original_name"] = original_tail
                    
                    # Build edge attributes - include all available attributes
                    edge_attrs = {"relation": relation}
                    if inference:
                        edge_attrs["inference"] = inference
                    if justification:
                        edge_attrs["justification"] = justification
                    
                    # Add edge with all attributes (process all edges regardless of inference type)
                    G.add_edge(head, tail, **edge_attrs)
                    normalization_stats["total_edges"] += 1
                
                # Print normalization statistics
                if normalization_stats["normalized_heads"] > 0 or normalization_stats["normalized_tails"] > 0:
                    print(f"  {filename}: Normalized {normalization_stats['normalized_heads']} heads, "
                          f"{normalization_stats['normalized_tails']} tails")

            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Save the graph in networkx format
            nx.write_graphml(G, os.path.join(output_dir, f"{filename}.graphml"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, required=False, default="/app/outputs")
    parser.add_argument("--output_dir", type=str, required=False, default="/app/processed")
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir

    convert_from_JSON(input_dir, output_dir)