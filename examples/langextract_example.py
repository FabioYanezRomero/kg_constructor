"""Example usage of the langextract knowledge graph extraction module.

This script demonstrates how to use the langextract module to extract
entities and relations from legal case text and convert them to GraphML.
"""

from pathlib import Path

from kg_constructor.langextract_extractor import ExtractionConfig, LangExtractExtractor
from kg_constructor.langextract_pipeline import LangExtractPipeline


def example_single_text_extraction():
    """Example: Extract triples from a single text."""
    print("=" * 80)
    print("EXAMPLE 1: Single Text Extraction")
    print("=" * 80)

    # Sample legal text
    text = """H is a three year old child whose parents separated before his birth.
    From the date of his birth until very recently, H has lived with his maternal
    grandmother, GB. H's mother, GLB, lived with her mother and H intermittently
    at GB's home from the time he was born until July 2006. She left GB's home
    then and has not returned. In November 2006, GB was granted, by consent, a
    residence order in respect of H."""

    # Create extractor with custom config
    config = ExtractionConfig(
        model_id="gemini-2.0-flash-exp",
        temperature=0.0,
        max_workers=5,
        show_progress=True
    )
    extractor = LangExtractExtractor(config)

    # Extract triples
    triples = extractor.extract_from_text(text, record_id="example-001")

    # Display results
    print(f"\nExtracted {len(triples)} triples:")
    for i, triple in enumerate(triples, 1):
        print(f"\n{i}. {triple['head']} --[{triple['relation']}]--> {triple['tail']}")
        print(f"   Inference: {triple['inference']}")
        if triple.get('justification'):
            print(f"   Justification: {triple['justification']}")

    return triples


def example_csv_processing():
    """Example: Process CSV file and create GraphML visualizations."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: CSV Processing with Full Pipeline")
    print("=" * 80)

    # Setup paths
    csv_path = Path("data/legal/sample_data.csv")
    output_dir = Path("outputs/langextract_example")

    # Check if CSV exists
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        print("Skipping this example.")
        return None

    # Create extraction config
    config = ExtractionConfig(
        model_id="gemini-2.0-flash-exp",
        temperature=0.0,
        max_workers=10,
        show_progress=True
    )

    # Initialize pipeline
    pipeline = LangExtractPipeline(
        output_dir=output_dir,
        extraction_config=config
    )

    # Run full pipeline (limit to 3 records for demo)
    results = pipeline.run_full_pipeline(
        csv_path=csv_path,
        text_column="background",
        id_column="id",
        limit=3,
        create_visualizations=True
    )

    print("\n" + "=" * 80)
    print("Pipeline Results:")
    print("=" * 80)
    print(f"JSON files: {len(results['json_files'])} created")
    print(f"GraphML files: {len(results['graphml_files'])} created")
    if 'html_files' in results:
        print(f"Visualizations: {len(results['html_files'])} created")

    return results


def example_step_by_step():
    """Example: Step-by-step pipeline execution with custom processing."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Step-by-Step Pipeline")
    print("=" * 80)

    csv_path = Path("data/legal/sample_data.csv")
    output_dir = Path("outputs/langextract_stepwise")

    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        print("Skipping this example.")
        return None

    # Step 1: Initialize components
    config = ExtractionConfig(
        model_id="gemini-2.0-flash-exp",
        temperature=0.0,
        show_progress=True
    )
    pipeline = LangExtractPipeline(output_dir, config)

    # Step 2: Extract triples and save as JSON
    print("\nStep 1: Extracting triples from CSV...")
    json_files = pipeline.process_csv(
        csv_path=csv_path,
        text_column="background",
        id_column="id",
        limit=2,
        output_subdir="json"
    )
    print(f"Created {len(json_files)} JSON files")

    # Step 3: Convert to GraphML
    print("\nStep 2: Converting JSON to GraphML...")
    json_dir = output_dir / "json"
    graphml_dir = output_dir / "graphml"
    graphml_files = pipeline.export_to_graphml(json_dir, graphml_dir)
    print(f"Created {len(graphml_files)} GraphML files")

    # Step 4: Create visualizations
    print("\nStep 3: Creating visualizations...")
    viz_dir = output_dir / "visualizations"
    html_files = pipeline.visualize_graphs(graphml_dir, viz_dir)
    print(f"Created {len(html_files)} HTML visualizations")

    return {
        "json_files": json_files,
        "graphml_files": graphml_files,
        "html_files": html_files
    }


def example_dataset_record():
    """Example: Extract from a dataset record format."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Dataset Record Extraction")
    print("=" * 80)

    # Sample record in dataset format
    record = {
        "id": "UKSC-2009-0001",
        "text": """The appellant was convicted of murder. The main evidence
        against him was a confession made during police interview. The appellant
        argued that the confession was obtained through improper means and should
        have been excluded under section 76 of the Police and Criminal Evidence
        Act 1984.""",
        "title": "Example v. State",
        "decision_label": "dismiss"
    }

    # Create extractor
    extractor = LangExtractExtractor()

    # Extract from record
    triples = extractor.extract_from_dataset_record(record)

    # Display results
    print(f"\nExtracted {len(triples)} triples from record '{record['id']}':")
    for triple in triples:
        print(f"  {triple['head']} -> {triple['relation']} -> {triple['tail']}")

    return triples


def main():
    """Run all examples."""
    print("LANGEXTRACT KNOWLEDGE GRAPH EXTRACTION EXAMPLES")
    print("=" * 80)
    print("\nThese examples demonstrate various ways to use the langextract module")
    print("for extracting knowledge graphs from legal text.\n")

    # Run examples
    try:
        # Example 1: Single text
        example_single_text_extraction()

        # Example 2: Full pipeline
        example_csv_processing()

        # Example 3: Step-by-step
        example_step_by_step()

        # Example 4: Dataset record
        example_dataset_record()

        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
