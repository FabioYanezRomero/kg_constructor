import networkx as nx
import plotly.graph_objects as go
import sys
import os

def visualize_graphml(graphml_file: str, output_html: str = None):
    """
    Visualize a GraphML file with interactive Plotly showing all node and edge attributes on hover.
    
    Args:
        graphml_file: Path to the .graphml file
        output_html: Output HTML file path (optional, defaults to same name as input)
    """
    # Load the graph
    G = nx.read_graphml(graphml_file)
    
    # Generate output filename if not provided
    if output_html is None:
        output_html = graphml_file.replace('.graphml', '_visualization.html')
    
    # Get layout positions
    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
    
    # ====================== EDGES ======================
    edge_trace_list = []
    
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        
        # Get all edge attributes
        edge_attrs = edge[2]
        
        # Build comprehensive hover text with all attributes
        hover_text = f"<b>Edge: {edge[0]} → {edge[1]}</b><br><br>"
        
        if edge_attrs:
            hover_text += "<b>Attributes:</b><br>"
            for key, value in edge_attrs.items():
                # Handle list attributes
                if isinstance(value, list):
                    hover_text += f"<b>{key}:</b><br>"
                    for i, item in enumerate(value, 1):
                        hover_text += f"  {i}. {item}<br>"
                else:
                    hover_text += f"<b>{key}:</b> {value}<br>"
        else:
            hover_text += "<i>No additional attributes</i>"
        
        # Create edge line trace
        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=3, color='#888'),
            hoverinfo='skip',  # Skip hover on line itself
            showlegend=False,
            name=''
        )
        edge_trace_list.append(edge_trace)
        
        # Add invisible marker at midpoint for easier hovering
        mid_x = (x0 + x1) / 2
        mid_y = (y0 + y1) / 2
        
        edge_hover_trace = go.Scatter(
            x=[mid_x],
            y=[mid_y],
            mode='markers',
            marker=dict(
                size=25,  # Larger hover area for easier interaction
                color='rgba(0,0,0,0)',  # Invisible
                line=dict(width=0),
                opacity=0  # Fully transparent
            ),
            hovertext=[hover_text],  # Hover text as list (required for hovertemplate)
            hovertemplate='%{hovertext}<extra></extra>',
            showlegend=False,
            name=''
        )
        edge_trace_list.append(edge_hover_trace)
    
    # ====================== NODES ======================
    node_x = []
    node_y = []
    node_text = []
    node_hover = []
    node_colors = []
    
    for node in G.nodes(data=True):
        x, y = pos[node[0]]
        node_x.append(x)
        node_y.append(y)
        
        # Node label (shown on graph)
        node_text.append(str(node[0]))
        
        # Get all node attributes
        node_attrs = node[1]
        
        # Build comprehensive hover text with all attributes
        hover_text = f"<b>Node: {node[0]}</b><br><br>"
        
        if node_attrs:
            hover_text += "<b>Attributes:</b><br>"
            for key, value in node_attrs.items():
                # Handle list attributes (like relations, inferences)
                if isinstance(value, list):
                    hover_text += f"<b>{key}:</b><br>"
                    for i, item in enumerate(value, 1):
                        hover_text += f"  {i}. {item}<br>"
                else:
                    hover_text += f"<b>{key}:</b> {value}<br>"
        else:
            hover_text += "<i>No additional attributes</i>"
        
        # Add degree information
        degree = G.degree(node[0])
        hover_text += f"<br><b>Connections:</b> {degree}"
        
        node_hover.append(hover_text)
        node_colors.append(degree)  # Color by degree
    
    # Create node trace
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        textfont=dict(size=10, color='black'),
        hovertemplate='%{hovertext}<extra></extra>',
        hovertext=node_hover,
        marker=dict(
            showscale=True,
            colorscale='Viridis',
            color=node_colors,
            size=20,
            colorbar=dict(
                thickness=15,
                title='Node<br>Degree',
                xanchor='left'
            ),
            line=dict(width=2, color='white')
        ),
        showlegend=False
    )
    
    # ====================== CREATE FIGURE ======================
    fig = go.Figure(data=edge_trace_list + [node_trace])
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f'<b>Graph Visualization: {os.path.basename(graphml_file)}</b>',
            x=0.5,
            xanchor='center',
            font=dict(size=16)
        ),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        annotations=[
            dict(
                text=f"Nodes: {G.number_of_nodes()} | Edges: {G.number_of_edges()}",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002
            )
        ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        width=1200,
        height=800
    )
    
    # Save to HTML
    fig.write_html(output_html, auto_open=True)
    print(f"✓ Visualization saved to: {output_html}")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    
    return fig


def batch_visualize_graphml(input_dir: str, output_dir: str = None):
    """
    Visualize all GraphML files in a directory.
    
    Args:
        input_dir: Directory containing .graphml files
        output_dir: Output directory for HTML files (optional, defaults to input_dir/visualizations)
    """
    if output_dir is None:
        output_dir = os.path.join(input_dir, "visualizations")
    
    os.makedirs(output_dir, exist_ok=True)
    
    graphml_files = [f for f in os.listdir(input_dir) if f.endswith('.graphml')]
    
    if not graphml_files:
        print(f"No .graphml files found in {input_dir}")
        return
    
    print(f"Found {len(graphml_files)} GraphML files. Generating visualizations...\n")
    
    for i, filename in enumerate(graphml_files, 1):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename.replace('.graphml', '.html'))
        
        print(f"[{i}/{len(graphml_files)}] Processing {filename}...")
        try:
            visualize_graphml(input_path, output_path)
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
    
    print(f"\n✓ All visualizations saved to: {output_dir}")


if __name__ == "__main__":
    folder = "/app/processed"
    output_folder = "/app/visualizations"
    batch_visualize_graphml(folder, output_folder)
    print(f"All visualizations saved to: {output_folder}")