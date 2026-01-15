"""Unified pipeline for knowledge graph extraction and export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .clients import BaseLLMClient, ClientConfig, ClientFactory
from .extractor import KnowledgeGraphExtractor
from .visualizer import EntityVisualizer
from .domains import KnowledgeDomain


class ExtractionPipeline:
    """Orchestrates knowledge graph extraction, conversion, and visualization.

    This pipeline provides a unified interface for:
    1. Extracting triples from text using any LLM backend
    2. Converting to GraphML format (reusing existing code)
    3. Creating interactive visualizations (reusing existing code)
    """

    def __init__(
        self,
        output_dir: Path,
        client: BaseLLMClient | None = None,
        client_config: ClientConfig | None = None,
        domain: KnowledgeDomain | str | None = None,
        extraction_mode: str = "open",
        augmentation_strategy: str = "connectivity",
        # Overrides
        prompt_path: Path | str | None = None,
        augmentation_prompt_path: Path | str | None = None,
        enable_entity_viz: bool = True
    ) -> None:
        """Initialize the pipeline.

        Args:
            output_dir: Directory to save all outputs
            client: Pre-configured LLM client (takes precedence)
            client_config: Configuration for creating a client
            domain: KnowledgeDomain instance or domain name
            extraction_mode: 'open' or 'constrained'
            augmentation_strategy: Augmentation strategy (default: 'connectivity')
            prompt_path: Optional override for extraction prompt file
            augmentation_prompt_path: Optional override for augmentation prompt file
            enable_entity_viz: Whether to create entity highlighting visualizations
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store strategy for reference
        self.augmentation_strategy = augmentation_strategy

        # Initialize extractor with client
        self.extractor = KnowledgeGraphExtractor(
            client=client,
            client_config=client_config,
            domain=domain,
            extraction_mode=extraction_mode,
            augmentation_strategy=augmentation_strategy,
            prompt_path=prompt_path,
            augmentation_prompt_path=augmentation_prompt_path
        )

        # Initialize entity visualizer
        self.entity_visualizer = EntityVisualizer() if enable_entity_viz else None

    def process_csv(
        self,
        csv_path: Path,
        text_column: str = "background",
        id_column: str = "id",
        limit: int | None = None,
        output_subdir: str = "json",
        temperature: float = 0.0,
        save_texts: bool = True,
        run_extraction: bool = True,
        run_augmentation: bool = True,
        max_disconnected: int = 3,
        max_iterations: int = 2,
    ) -> dict[str, Any]:
        """Process a CSV file and save triples as JSON files.

        Args:
            csv_path: Path to CSV file
            text_column: Name of column containing text
            id_column: Name of column containing record IDs
            limit: Optional limit on number of records
            output_subdir: Subdirectory within output_dir for JSON files
            temperature: Sampling temperature
            save_texts: Whether to save original texts for entity visualization

        Returns:
            Dictionary with:
                - 'output_files': mapping record IDs to JSON file paths
                - 'texts': mapping record IDs to original texts (if save_texts=True)
        """
        print(f"Processing CSV: {csv_path}")
        print(f"Using model: {self.extractor.get_model_name()}")
        print(f"Text column: {text_column}, ID column: {id_column}")

        if limit:
            print(f"Limiting to {limit} records")

        # Load CSV to extract both texts and triples
        import pandas as pd
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        if limit:
            df = df.head(limit)

        save_dir = self.output_dir / output_subdir
        save_dir.mkdir(parents=True, exist_ok=True)

        output_files = {}
        all_metadata = {}
        texts_map = {} if save_texts else None

        for _, row in df.iterrows():
            record_id = str(row[id_column])
            text = str(row[text_column])
            output_path = save_dir / f"{record_id}.json"
            
            existing_triples = None
            if not run_extraction:
                if output_path.exists():
                    print(f"Loading existing triples for {record_id} from {output_path}")
                    with open(output_path, "r", encoding="utf-8") as f:
                        existing_triples = json.load(f)
                else:
                    print(f"Extraction skipped, and no existing file found for {record_id} at {output_path}")
                    continue
            
            if run_augmentation:
                print(f"Running extraction + augmentation for {record_id}")
                triples, metadata = self.extractor.extract_connected_graph(
                    text=text,
                    record_id=record_id,
                    initial_triples=existing_triples,
                    temperature=temperature,
                    max_disconnected=max_disconnected,
                    max_iterations=max_iterations
                )
                all_metadata[record_id] = metadata
            elif run_extraction:
                print(f"Running extraction for {record_id}")
                triples = self.extractor.extract_from_text(text, record_id, temperature)
            else:
                # Both false? Should not happen with current CLI, but if so:
                triples = existing_triples

            # Save results
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(triples, f, ensure_ascii=False, indent=2)

            output_files[record_id] = output_path

            # Store original text
            if save_texts:
                texts_map[record_id] = text

            print(f"Saved {len(triples)} triples for {record_id} to {output_path}")

        print(f"\nProcessed {len(output_files)} records")

        result = {'output_files': output_files}
        if save_texts:
            result['texts'] = texts_map

        return result

    def process_single_text(
        self,
        text: str,
        record_id: str,
        output_subdir: str = "json",
        temperature: float = 0.0
    ) -> Path:
        """Process a single text and save triples as JSON.

        Args:
            text: The text to analyze
            record_id: Identifier for this record
            output_subdir: Subdirectory within output_dir
            temperature: Sampling temperature

        Returns:
            Path to the output JSON file
        """
        print(f"Processing record: {record_id}")
        print(f"Using model: {self.extractor.get_model_name()}")

        # Extract triples
        triples = self.extractor.extract_from_text(text, record_id, temperature)

        # Save to JSON
        save_dir = self.output_dir / output_subdir
        save_dir.mkdir(parents=True, exist_ok=True)

        output_path = save_dir / f"{record_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(triples, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(triples)} triples to {output_path}")
        return output_path

    def export_to_graphml(
        self,
        json_input_dir: Path,
        graphml_output_dir: Path
    ) -> list[Path]:
        """Convert JSON triples to GraphML format.

        This method reuses the existing convert_from_JSON.py code to ensure
        compatibility with all downstream tools.

        Args:
            json_input_dir: Directory containing JSON files with triples
            graphml_output_dir: Directory to save GraphML files

        Returns:
            List of paths to created GraphML files
        """
        from postprocessing.networkX.convert_from_JSON import convert_from_JSON

        print(f"\nConverting JSON to GraphML")
        print(f"Input: {json_input_dir}")
        print(f"Output: {graphml_output_dir}")

        # Use existing conversion function
        convert_from_JSON(
            input_dir=str(json_input_dir),
            output_dir=str(graphml_output_dir)
        )

        # Return list of created files
        graphml_files = list(Path(graphml_output_dir).glob("*.graphml"))
        print(f"Created {len(graphml_files)} GraphML files")
        return graphml_files

    def visualize_graphs(
        self,
        graphml_dir: Path,
        viz_output_dir: Path
    ) -> list[Path]:
        """Create interactive graph visualizations (nodes and edges) from GraphML files.

        This method reuses the existing visualisation.py code to create Plotly
        network visualizations showing entities as nodes and relations as edges.

        Args:
            graphml_dir: Directory containing GraphML files
            viz_output_dir: Directory to save HTML visualizations

        Returns:
            List of paths to created HTML files
        """
        from postprocessing.networkX.visualisation import batch_visualize_graphml

        print(f"\nCreating graph visualizations (network view)")
        print(f"Input: {graphml_dir}")
        print(f"Output: {viz_output_dir}")

        # Use existing visualization function
        batch_visualize_graphml(
            input_dir=str(graphml_dir),
            output_dir=str(viz_output_dir)
        )

        # Return list of created files
        html_files = list(Path(viz_output_dir).glob("*.html"))
        print(f"Created {len(html_files)} graph visualizations")
        return html_files

    def visualize_entities(
        self,
        texts: dict[str, str],
        triples: dict[str, list[dict[str, Any]]],
        entity_viz_dir: Path,
        group_by: str = "entity_type"
    ) -> list[Path]:
        """Create entity highlighting visualizations in original text.

        This uses langextract's built-in visualization to highlight entities
        in the original text with animation. This complements the graph
        visualization by showing WHERE entities appear in the source text.

        Args:
            texts: Dictionary mapping record IDs to original texts
            triples: Dictionary mapping record IDs to extracted triples
            entity_viz_dir: Directory to save entity HTML files
            group_by: How to group entities - "entity_type" or "relation"

        Returns:
            List of paths to created HTML files
        """
        if not self.entity_visualizer:
            print("Entity visualizer disabled")
            return []

        print(f"\nCreating entity visualizations (text highlights)")
        print(f"Output: {entity_viz_dir}")

        # Prepare records for batch visualization
        records = {}
        for record_id in texts.keys():
            if record_id in triples:
                records[record_id] = (texts[record_id], triples[record_id])

        # Create visualizations
        html_files = self.entity_visualizer.batch_visualize(
            records=records,
            output_dir=entity_viz_dir,
            group_by=group_by
        )

        print(f"Created {len(html_files)} entity visualizations")
        return html_files

    def run_full_pipeline(
        self,
        csv_path: Path,
        text_column: str = "background",
        id_column: str = "id",
        limit: int | None = None,
        create_graph_viz: bool = True,
        create_entity_viz: bool = True,
        temperature: float = 0.0,
        run_extraction: bool = True,
        run_augmentation: bool = True,
        max_disconnected: int = 3,
        max_iterations: int = 2
    ) -> dict[str, Any]:
        """Run the complete pipeline: extract, convert, visualize.

        This pipeline creates TWO types of visualizations:
        1. Graph visualizations: Network view showing entities (nodes) and relations (edges)
        2. Entity visualizations: Text view highlighting entities in original text

        Args:
            csv_path: Path to input CSV file
            text_column: Name of column containing text
            id_column: Name of column containing record IDs
            limit: Optional limit on number of records
            create_graph_viz: Whether to create graph/network visualizations
            create_entity_viz: Whether to create entity highlighting visualizations
            temperature: Sampling temperature

        Returns:
            Dictionary with paths to all outputs:
                - json_dir: Directory with extracted triples JSON
                - graphml_dir: Directory with GraphML files
                - graph_viz_dir: Directory with network visualizations (optional)
                - entity_viz_dir: Directory with entity highlighting (optional)
        """
        print("=" * 80)
        print("KNOWLEDGE GRAPH EXTRACTION PIPELINE")
        print("=" * 80)
        print(f"Model: {self.extractor.get_model_name()}")
        print(f"Client: {self.extractor.client.__class__.__name__}")
        print("=" * 80)

        # Step 1: Extract triples from CSV (and save original texts)
        extraction_result = self.process_csv(
            csv_path=csv_path,
            text_column=text_column,
            id_column=id_column,
            limit=limit,
            output_subdir="extracted_json",
            temperature=temperature,
            save_texts=create_entity_viz,
            run_extraction=run_extraction,
            run_augmentation=run_augmentation,
            max_disconnected=max_disconnected,
            max_iterations=max_iterations
        )

        json_files = extraction_result['output_files']
        texts = extraction_result.get('texts', {})
        json_dir = self.output_dir / "extracted_json"

        # Load triples for entity visualization
        triples_map = {}
        if create_entity_viz and texts:
            for record_id, json_path in json_files.items():
                with open(json_path, 'r', encoding='utf-8') as f:
                    triples_map[record_id] = json.load(f)

        # Step 2: Convert to GraphML
        graphml_dir = self.output_dir / "graphml"
        graphml_files = self.export_to_graphml(
            json_input_dir=json_dir,
            graphml_output_dir=graphml_dir
        )

        results = {
            "json_dir": json_dir,
            "json_files": json_files,
            "graphml_dir": graphml_dir,
            "graphml_files": graphml_files,
            "model": self.extractor.get_model_name()
        }

        # Step 3a: Create graph/network visualizations (Plotly - shows relations)
        if create_graph_viz:
            graph_viz_dir = self.output_dir / "graph_visualizations"
            graph_html_files = self.visualize_graphs(
                graphml_dir=graphml_dir,
                viz_output_dir=graph_viz_dir
            )
            results["graph_viz_dir"] = graph_viz_dir
            results["graph_html_files"] = graph_html_files

        # Step 3b: Create entity visualizations (langextract - highlights entities in text)
        if create_entity_viz and self.entity_visualizer and texts:
            entity_viz_dir = self.output_dir / "entity_visualizations"
            entity_html_files = self.visualize_entities(
                texts=texts,
                triples=triples_map,
                entity_viz_dir=entity_viz_dir,
                group_by="entity_type"
            )
            results["entity_viz_dir"] = entity_viz_dir
            results["entity_html_files"] = entity_html_files

        print("\n" + "=" * 80)
        print("PIPELINE COMPLETE")
        print("=" * 80)
        print(f"Model used: {self.extractor.get_model_name()}")
        print(f"JSON triples: {json_dir}")
        print(f"GraphML files: {graphml_dir}")
        if create_graph_viz:
            print(f"Graph visualizations (network view): {graph_viz_dir}")
        if create_entity_viz and self.entity_visualizer:
            print(f"Entity visualizations (text highlights): {entity_viz_dir}")

        return results


__all__ = [
    "ExtractionPipeline",
]
