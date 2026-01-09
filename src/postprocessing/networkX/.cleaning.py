import networkx as nx
import os
from pathlib import Path


def get_largest_connected_component(graph: nx.Graph) -> nx.Graph:
    """
    Extract the largest connected component from a graph.
    
    For directed graphs, uses weakly connected components.
    For undirected graphs, uses connected components.
    
    Args:
        graph: NetworkX graph (directed or undirected)
    
    Returns:
        Subgraph containing only the largest connected component
    """
    if graph.is_directed():
        # For directed graphs, use weakly connected components
        # (treats edges as undirected for connectivity)
        components = list(nx.weakly_connected_components(graph))
    else:
        # For undirected graphs, use connected components
        components = list(nx.connected_components(graph))
    
    if not components:
        # Empty graph, return as is
        return graph
    
    # Find the largest component
    largest_component = max(components, key=len)
    
    # Create subgraph with only the largest component
    if graph.is_directed():
        subgraph = graph.subgraph(largest_component).copy()
    else:
        subgraph = graph.subgraph(largest_component).copy()
    
    return subgraph


def clean_graphml(input_file: str, output_file: str) -> tuple[int, int, int, int]:
    """
    Clean a GraphML file by keeping only the largest connected component.
    
    Args:
        input_file: Path to input GraphML file
        output_file: Path to output GraphML file
    
    Returns:
        Tuple of (original_nodes, original_edges, cleaned_nodes, cleaned_edges)
    """
    # Load the graph
    G = nx.read_graphml(input_file)
    
    original_nodes = G.number_of_nodes()
    original_edges = G.number_of_edges()
    
    # Get largest connected component
    cleaned_G = get_largest_connected_component(G)
    
    cleaned_nodes = cleaned_G.number_of_nodes()
    cleaned_edges = cleaned_G.number_of_edges()
    
    # Save cleaned graph
    nx.write_graphml(cleaned_G, output_file)
    
    return original_nodes, original_edges, cleaned_nodes, cleaned_edges


def batch_clean_graphml(input_dir: str, output_dir: str = None):
    """
    Clean all GraphML files in a directory, keeping only the largest connected component.
    
    Args:
        input_dir: Directory containing .graphml files
        output_dir: Output directory for cleaned files (optional, defaults to input_dir/cleaned)
    """
    if output_dir is None:
        output_dir = os.path.join(input_dir, "cleaned")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all GraphML files
    graphml_files = [f for f in os.listdir(input_dir) if f.endswith('.graphml')]
    
    if not graphml_files:
        print(f"No .graphml files found in {input_dir}")
        return
    
    print(f"Found {len(graphml_files)} GraphML files. Cleaning graphs...\n")
    
    total_original_nodes = 0
    total_original_edges = 0
    total_cleaned_nodes = 0
    total_cleaned_edges = 0
    
    for i, filename in enumerate(graphml_files, 1):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        print(f"[{i}/{len(graphml_files)}] Processing {filename}...")
        try:
            orig_nodes, orig_edges, clean_nodes, clean_edges = clean_graphml(
                input_path, output_path
            )
            
            total_original_nodes += orig_nodes
            total_original_edges += orig_edges
            total_cleaned_nodes += clean_nodes
            total_cleaned_edges += clean_edges
            
            reduction_nodes = orig_nodes - clean_nodes
            reduction_edges = orig_edges - clean_edges
            
            print(f"  Original: {orig_nodes} nodes, {orig_edges} edges")
            print(f"  Cleaned:  {clean_nodes} nodes, {clean_edges} edges")
            if reduction_nodes > 0 or reduction_edges > 0:
                print(f"  Removed:  {reduction_nodes} nodes, {reduction_edges} edges")
            else:
                print(f"  ✓ Already fully connected")
            print()
            
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total original: {total_original_nodes} nodes, {total_original_edges} edges")
    print(f"  Total cleaned:  {total_cleaned_nodes} nodes, {total_cleaned_edges} edges")
    print(f"  Total removed:  {total_original_nodes - total_cleaned_nodes} nodes, "
          f"{total_original_edges - total_cleaned_edges} edges")
    print(f"\n✓ All cleaned graphs saved to: {output_dir}")


if __name__ == "__main__":
    input_folder = "/app/processed"
    output_folder = "/app/cleaned"
    batch_clean_graphml(input_folder, output_folder)

