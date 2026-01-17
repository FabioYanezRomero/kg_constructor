"""Examples demonstrating the unified knowledge graph extraction system.

This script shows how to use the new client abstraction layer to extract
knowledge graphs using different LLM backends (Gemini, Ollama, LM Studio).
"""

from pathlib import Path

from kg_constructor.clients import ClientConfig, create_client, GeminiClient
from kg_constructor.extractor import KnowledgeGraphExtractor
from kg_constructor.extraction_pipeline import ExtractionPipeline


def example_gemini_api():
    """Example 1: Extract using Gemini API."""
    print("=" * 80)
    print("EXAMPLE 1: Gemini API Extraction")
    print("=" * 80)

    # Configure Gemini client
    config = ClientConfig(
        client_type="gemini",
        model_id="gemini-2.0-flash-exp",
        # api_key will be read from LANGEXTRACT_API_KEY env var
        temperature=0.0,
        max_workers=10
    )

    # Create extractor
    extractor = KnowledgeGraphExtractor(
        client_config=config,
        prompt_path=Path("src/prompts/legal_background_prompt.txt")
    )

    # Sample legal text
    text = """The appellant was convicted of murder. The main evidence against him
    was a confession made during police interview. The appellant argued that the
    confession was obtained through improper means and should have been excluded
    under section 76 of the Police and Criminal Evidence Act 1984."""

    # Extract triples
    triples = extractor.extract_from_text(text, record_id="example-gemini")

    print(f"\nExtracted {len(triples)} triples using {extractor.get_model_name()}:")
    for i, triple in enumerate(triples, 1):
        print(f"\n{i}. {triple['head']} --[{triple['relation']}]--> {triple['tail']}")
        print(f"   Inference: {triple['inference']}")

    return triples


def example_ollama_local():
    """Example 2: Extract using Ollama (local model)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Ollama Local Model Extraction")
    print("=" * 80)

    # Configure Ollama client
    config = ClientConfig(
        client_type="ollama",
        model_id="llama3.1",
        base_url="http://localhost:11434",
        temperature=0.0,
        max_workers=5,  # Lower for local models
        timeout=120
    )

    # Create extractor
    extractor = KnowledgeGraphExtractor(
        client_config=config,
        prompt_path=Path("src/prompts/default_prompt.txt")
    )

    # Sample text
    text = """The company announced a merger with its competitor. The CEO stated
    that the merger would create significant value for shareholders. Regulatory
    approval is expected within six months."""

    # Extract triples
    print(f"Using model: {extractor.get_model_name()}")
    print("Note: This example requires Ollama to be running locally")
    print("Start Ollama: ollama serve")
    print("Pull model: ollama pull llama3.1\n")

    # Uncomment to run (requires Ollama server):
    # triples = extractor.extract_from_text(text, record_id="example-ollama")
    # for triple in triples:
    #     print(f"{triple['head']} -> {triple['relation']} -> {triple['tail']}")

    return []


def example_lmstudio_local():
    """Example 3: Extract using LM Studio (local model)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: LM Studio Local Model Extraction")
    print("=" * 80)

    # Configure LM Studio client
    config = ClientConfig(
        client_type="lmstudio",
        model_id="local-model",
        base_url="http://localhost:1234/v1",
        temperature=0.0,
        max_workers=5
    )

    # Create extractor
    extractor = KnowledgeGraphExtractor(client_config=config)

    print(f"Using model: {extractor.get_model_name()}")
    print("Note: This example requires LM Studio server running")
    print("1. Start LM Studio")
    print("2. Load a model in the UI")
    print("3. Enable server mode\n")

    # Uncomment to run (requires LM Studio server):
    # text = "Sample text here..."
    # triples = extractor.extract_from_text(text)

    return []


def example_direct_client_usage():
    """Example 4: Using client directly without extractor."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Direct Client Usage")
    print("=" * 80)

    # Create Gemini client directly
    client = GeminiClient(
        model_id="gemini-2.0-flash-exp",
        # api_key from env var
        max_workers=10
    )

    # Use client directly for extraction
    text = """{"text": "The court ruled in favor of the plaintiff. The defendant
    was ordered to pay damages of $1 million."}"""

    prompt = """Extract all (head, relation, tail) triples from the text.
    Mark each triple as "inference": "explicit"."""

    print(f"Using client: {client.get_model_name()}")
    print(f"Supports structured output: {client.supports_structured_output()}")

    # Uncomment to run:
    # from kg_constructor.extractor import Triple
    # triples = client.extract(
    #     text=text,
    #     prompt_description=prompt,
    #     format_type=Triple,
    #     temperature=0.0
    # )

    return []


def example_full_pipeline_gemini():
    """Example 5: Full pipeline with Gemini."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Full Pipeline with Gemini")
    print("=" * 80)

    csv_path = Path("data/legal/sample_data.csv")
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        print("Skipping this example.")
        return None

    # Configure Gemini
    config = ClientConfig(
        client_type="gemini",
        model_id="gemini-2.0-flash-exp",
        temperature=0.0
    )

    # Create pipeline
    pipeline = ExtractionPipeline(
        output_dir=Path("outputs/unified_gemini"),
        client_config=config,
        prompt_path=Path("src/prompts/legal_background_prompt.txt")
    )

    # Run full pipeline (limit to 2 records for demo)
    results = pipeline.run_full_pipeline(
        csv_path=csv_path,
        text_column="background",
        id_column="id",
        limit=2,
        create_visualizations=True
    )

    print("\n" + "=" * 80)
    print("Pipeline Results:")
    print("=" * 80)
    print(f"Model: {results['model']}")
    print(f"JSON files: {len(results['json_files'])}")
    print(f"GraphML files: {len(results['graphml_files'])}")
    print(f"Visualizations: {len(results.get('html_files', []))}")

    return results


def example_compare_clients():
    """Example 6: Compare extraction from different clients."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Compare Clients")
    print("=" * 80)

    sample_text = """The Supreme Court ruled unanimously in favor of the appellant.
    The lower court's decision was overturned. The case will be remanded for
    further proceedings."""

    # Gemini extraction
    print("\n--- Gemini Extraction ---")
    gemini_config = ClientConfig(client_type="gemini")
    gemini_extractor = KnowledgeGraphExtractor(client_config=gemini_config)
    gemini_triples = gemini_extractor.extract_from_text(sample_text)

    print(f"Gemini extracted {len(gemini_triples)} triples")
    for triple in gemini_triples[:3]:  # Show first 3
        print(f"  {triple['head']} -> {triple['relation']} -> {triple['tail']}")

    # Ollama extraction (requires server)
    print("\n--- Ollama Extraction (Requires Server) ---")
    print("Run: ollama serve && ollama pull llama3.1")

    # LM Studio extraction (requires server)
    print("\n--- LM Studio Extraction (Requires Server) ---")
    print("Start LM Studio and load a model")

    return {
        "gemini": gemini_triples,
        "ollama": [],  # Requires server
        "lmstudio": []  # Requires server
    }


def example_custom_prompt():
    """Example 7: Using custom prompt template."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Custom Prompt Template")
    print("=" * 80)

    # Use the legal-specific prompt
    config = ClientConfig(client_type="gemini")

    extractor = KnowledgeGraphExtractor(
        client_config=config,
        prompt_path=Path("src/prompts/legal_background_prompt.txt")
    )

    text = """H is a three year old child. GB is the maternal grandmother.
    GB was granted a residence order in respect of H."""

    triples = extractor.extract_from_text(text, record_id="custom-prompt-example")

    print(f"\nExtracted {len(triples)} triples with legal-specific prompt:")
    for triple in triples:
        print(f"  {triple['head']} -> {triple['relation']} -> {triple['tail']}")

    return triples


def main():
    """Run all examples."""
    print("UNIFIED KNOWLEDGE GRAPH EXTRACTION EXAMPLES")
    print("=" * 80)
    print("\nThese examples demonstrate the new client abstraction layer")
    print("supporting Gemini API, Ollama, and LM Studio backends.\n")

    try:
        # Example 1: Gemini API (only one that runs without local server)
        example_gemini_api()

        # Example 2: Ollama (info only, requires server)
        example_ollama_local()

        # Example 3: LM Studio (info only, requires server)
        example_lmstudio_local()

        # Example 4: Direct client usage
        example_direct_client_usage()

        # Example 5: Full pipeline with Gemini
        example_full_pipeline_gemini()

        # Example 6: Compare clients
        example_compare_clients()

        # Example 7: Custom prompt
        example_custom_prompt()

        print("\n" + "=" * 80)
        print("EXAMPLES COMPLETED")
        print("=" * 80)
        print("\nNote: Local model examples (Ollama, LM Studio) require")
        print("running servers and are shown for reference only.")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
