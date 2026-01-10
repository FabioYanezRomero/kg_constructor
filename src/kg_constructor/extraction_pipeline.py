"""Unified pipeline for knowledge graph extraction and export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kg_constructor.clients import BaseLLMClient, ClientConfig, create_client
from kg_constructor.extractor import KnowledgeGraphExtractor


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
        prompt_path: Path | str | None = None
    ) -> None:
        """Initialize the pipeline.

        Args:
            output_dir: Directory to save all outputs
            client: Pre-configured LLM client (takes precedence)
            client_config: Configuration for creating a client
            prompt_path: Path to prompt template file
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize extractor with client
        self.extractor = KnowledgeGraphExtractor(
            client=client,
            client_config=client_config,
            prompt_path=prompt_path
        )

    def process_csv(
        self,
        csv_path: Path,
        text_column: str = "background",
        id_column: str = "id",
        limit: int | None = None,
        output_subdir: str = "json",
        temperature: float = 0.0
    ) -> dict[str, Path]:
        """Process a CSV file and save triples as JSON files.

        Args:
            csv_path: Path to CSV file
            text_column: Name of column containing text
            id_column: Name of column containing record IDs
            limit: Optional limit on number of records
            output_subdir: Subdirectory within output_dir for JSON files
            temperature: Sampling temperature

        Returns:
            Dictionary mapping record IDs to output file paths
        """
        print(f"Processing CSV: {csv_path}")
        print(f"Using model: {self.extractor.get_model_name()}")
        print(f"Text column: {text_column}, ID column: {id_column}")

        if limit:
            print(f"Limiting to {limit} records")

        # Extract triples from all records
        results = self.extractor.extract_from_csv(
            csv_path=csv_path,
            text_column=text_column,
            id_column=id_column,
            limit=limit,
            temperature=temperature
        )

        # Save results
        save_dir = self.output_dir / output_subdir
        save_dir.mkdir(parents=True, exist_ok=True)

        output_files = {}
        for record_id, triples in results.items():
            output_path = save_dir / f"{record_id}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(triples, f, ensure_ascii=False, indent=2)

            output_files[record_id] = output_path
            print(f"Saved {len(triples)} triples for {record_id} to {output_path}")

        print(f"\nProcessed {len(output_files)} records")
        return output_files

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
        """Create interactive visualizations of GraphML files.

        This method reuses the existing visualisation.py code to ensure
        consistent visualization across all pipelines.

        Args:
            graphml_dir: Directory containing GraphML files
            viz_output_dir: Directory to save HTML visualizations

        Returns:
            List of paths to created HTML files
        """
        from postprocessing.networkX.visualisation import batch_visualize_graphml

        print(f"\nCreating visualizations")
        print(f"Input: {graphml_dir}")
        print(f"Output: {viz_output_dir}")

        # Use existing visualization function
        batch_visualize_graphml(
            graphml_dir=str(graphml_dir),
            output_dir=str(viz_output_dir)
        )

        # Return list of created files
        html_files = list(Path(viz_output_dir).glob("*.html"))
        print(f"Created {len(html_files)} HTML visualizations")
        return html_files

    def run_full_pipeline(
        self,
        csv_path: Path,
        text_column: str = "background",
        id_column: str = "id",
        limit: int | None = None,
        create_visualizations: bool = True,
        temperature: float = 0.0
    ) -> dict[str, Any]:
        """Run the complete pipeline: extract, convert, visualize.

        Args:
            csv_path: Path to input CSV file
            text_column: Name of column containing text
            id_column: Name of column containing record IDs
            limit: Optional limit on number of records
            create_visualizations: Whether to create HTML visualizations
            temperature: Sampling temperature

        Returns:
            Dictionary with paths to all outputs
        """
        print("=" * 80)
        print("KNOWLEDGE GRAPH EXTRACTION PIPELINE")
        print("=" * 80)
        print(f"Model: {self.extractor.get_model_name()}")
        print(f"Client: {self.extractor.client.__class__.__name__}")
        print("=" * 80)

        # Step 1: Extract triples from CSV
        json_files = self.process_csv(
            csv_path=csv_path,
            text_column=text_column,
            id_column=id_column,
            limit=limit,
            output_subdir="extracted_json",
            temperature=temperature
        )

        json_dir = self.output_dir / "extracted_json"

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

        # Step 3: Visualize (optional)
        if create_visualizations:
            viz_dir = self.output_dir / "visualizations"
            html_files = self.visualize_graphs(
                graphml_dir=graphml_dir,
                viz_output_dir=viz_dir
            )
            results["visualization_dir"] = viz_dir
            results["html_files"] = html_files

        print("\n" + "=" * 80)
        print("PIPELINE COMPLETE")
        print("=" * 80)
        print(f"Model used: {self.extractor.get_model_name()}")
        print(f"JSON triples: {json_dir}")
        print(f"GraphML files: {graphml_dir}")
        if create_visualizations:
            print(f"Visualizations: {viz_dir}")

        return results


__all__ = [
    "ExtractionPipeline",
]
