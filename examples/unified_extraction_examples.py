"""Examples demonstrating the unified knowledge graph extraction system.

This script shows how to use the new modular architecture to extract
knowledge graphs using different LLM backends (Gemini, Ollama, LM Studio).

New Architecture:
    - src.clients: LLM client abstraction (GeminiClient, OllamaClient, LMStudioClient)
    - src.domains: Knowledge domains with prompts and examples
    - src.builder: Extraction and augmentation logic
    - src.converters: Output format converters (GraphML, etc.)
    - src.visualization: Interactive visualizations
"""

from pathlib import Path

# Import from the new modular structure
from src.clients import ClientConfig, ClientFactory, GeminiClient
from src.domains import get_domain, list_available_domains, Triple
from src.builder import extract_from_text, extract_connected_graph, list_strategies


def example_gemini_api():
    """Example 1: Extract using Gemini API."""
    print("=" * 80)
    print("EXAMPLE 1: Gemini API Extraction")
    print("=" * 80)

    # Configure Gemini client
    config = ClientConfig(
        client_type="gemini",
        model_id="gemini-2.0-flash",
        # api_key will be read from LANGEXTRACT_API_KEY or GOOGLE_API_KEY env var
        temperature=0.0,
        max_workers=10
    )

    # Create client using factory
    client = ClientFactory.create(config)

    # Get legal domain (provides prompts and few-shot examples)
    domain = get_domain("legal", extraction_mode="open")

    # Sample legal text
    text = """The appellant was convicted of murder. The main evidence against him
    was a confession made during police interview. The appellant argued that the
    confession was obtained through improper means and should have been excluded
    under section 76 of the Police and Criminal Evidence Act 1984."""

    # Extract triples using the builder module
    triples = extract_from_text(
        client=client,
        domain=domain,
        text=text,
        record_id="example-gemini"
    )

    print(f"\nExtracted {len(triples)} triples using {client.get_model_name()}:")
    for i, triple in enumerate(triples, 1):
        print(f"\n{i}. {triple.head} --[{triple.relation}]--> {triple.tail}")
        print(f"   Inference: {triple.inference}")

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

    # Create client
    client = ClientFactory.create(config)

    # Use default domain
    domain = get_domain("default", extraction_mode="open")

    # Sample text
    text = """The company announced a merger with its competitor. The CEO stated
    that the merger would create significant value for shareholders. Regulatory
    approval is expected within six months."""

    print(f"Using model: {client.get_model_name()}")
    print("Note: This example requires Ollama to be running locally")
    print("Start Ollama: ollama serve")
    print("Pull model: ollama pull llama3.1\n")

    # Uncomment to run (requires Ollama server):
    # triples = extract_from_text(client=client, domain=domain, text=text, record_id="example-ollama")
    # for triple in triples:
    #     print(f"{triple.head} -> {triple.relation} -> {triple.tail}")

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

    # Create client
    client = ClientFactory.create(config)

    print(f"Using model: {client.get_model_name()}")
    print("Note: This example requires LM Studio server running")
    print("1. Start LM Studio")
    print("2. Load a model in the UI")
    print("3. Enable server mode\n")

    # Uncomment to run (requires LM Studio server):
    # domain = get_domain("default")
    # text = "Sample text here..."
    # triples = extract_from_text(client=client, domain=domain, text=text)

    return []


def example_direct_client_usage():
    """Example 4: Using client directly without builder module."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Direct Client Usage")
    print("=" * 80)

    # Create Gemini client directly (bypassing factory)
    client = GeminiClient(
        model_id="gemini-2.0-flash",
        # api_key from env var
        max_workers=10
    )

    print(f"Using client: {client.get_model_name()}")
    print(f"Supports structured output: {client.supports_structured_output()}")

    # You can use the client directly for extraction with langextract
    # The extract() method accepts text, prompt, examples, and format_type
    
    # Uncomment to run:
    # triples = client.extract(
    #     text="The court ruled in favor of the plaintiff.",
    #     prompt_description="Extract all (head, relation, tail) triples from the text.",
    #     format_type=Triple,
    #     temperature=0.0
    # )

    return []


def example_connected_graph_extraction():
    """Example 5: Two-step extraction with connectivity augmentation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Connected Graph Extraction (Two-Step)")
    print("=" * 80)

    # Configure client
    config = ClientConfig(
        client_type="gemini",
        model_id="gemini-2.0-flash",
        temperature=0.0
    )
    client = ClientFactory.create(config)

    # Get legal domain
    domain = get_domain("legal", extraction_mode="open")

    # Sample text with multiple entities that might form disconnected components
    text = """H is a three-year-old child. GB is the maternal grandmother. 
    GB was granted a residence order in respect of H. The local authority applied 
    for a care order. The court considered the child's welfare as paramount. 
    Section 31 of the Children Act 1989 sets out the threshold criteria."""

    # Extract with connectivity augmentation
    # This will:
    # 1. Extract initial triples
    # 2. Iteratively add bridging triples to reduce disconnected components
    triples, metadata = extract_connected_graph(
        client=client,
        domain=domain,
        text=text,
        record_id="example-connected",
        max_disconnected=1,  # Target: at most 1 disconnected component (fully connected)
        max_iterations=3     # Try up to 3 refinement iterations
    )

    print(f"\nExtracted {len(triples)} triples")
    print(f"Final components: {metadata['final_components']}")
    print(f"Iterations used: {len(metadata['iterations'])}")

    print("\nTriples:")
    for i, triple in enumerate(triples, 1):
        print(f"  {i}. {triple.head} --[{triple.relation}]--> {triple.tail}")

    return triples, metadata


def example_list_resources():
    """Example 6: List available domains and strategies."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: List Available Resources")
    print("=" * 80)

    # List available domains
    print("\nAvailable Knowledge Domains:")
    for domain_name in list_available_domains():
        print(f"  • {domain_name}")

    # List available augmentation strategies
    print("\nAvailable Augmentation Strategies:")
    for strategy_name in list_strategies():
        print(f"  • {strategy_name}")

    # List available LLM clients
    print("\nAvailable LLM Clients:")
    for client_name in ClientFactory.get_available_clients():
        print(f"  • {client_name}")


def example_compare_clients():
    """Example 7: Compare extraction from different clients."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Compare Clients")
    print("=" * 80)

    sample_text = """The Supreme Court ruled unanimously in favor of the appellant.
    The lower court's decision was overturned. The case will be remanded for
    further proceedings."""

    domain = get_domain("legal", extraction_mode="open")

    # Gemini extraction
    print("\n--- Gemini Extraction ---")
    gemini_config = ClientConfig(client_type="gemini")
    gemini_client = ClientFactory.create(gemini_config)
    gemini_triples = extract_from_text(
        client=gemini_client,
        domain=domain,
        text=sample_text,
        record_id="compare-gemini"
    )

    print(f"Gemini extracted {len(gemini_triples)} triples")
    for triple in gemini_triples[:3]:  # Show first 3
        print(f"  {triple.head} -> {triple.relation} -> {triple.tail}")

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
    """Example 8: Using custom prompt override."""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Custom Prompt Override")
    print("=" * 80)

    config = ClientConfig(client_type="gemini")
    client = ClientFactory.create(config)

    # Get domain but override the prompt
    domain = get_domain("legal", extraction_mode="open")

    # Custom prompt template (must include {{record_json}} placeholder)
    custom_prompt = """You are an expert legal analyst. Extract all relationships from the following legal text.

Focus on:
- Party relationships (appellant, respondent, court)
- Legal provisions cited
- Decisions and their effects

{{record_json}}

Extract triples in the form (head, relation, tail) with inference type."""

    text = """H is a three year old child. GB is the maternal grandmother.
    GB was granted a residence order in respect of H."""

    triples = extract_from_text(
        client=client,
        domain=domain,
        text=text,
        record_id="custom-prompt-example",
        prompt_override=custom_prompt
    )

    print(f"\nExtracted {len(triples)} triples with custom prompt:")
    for triple in triples:
        print(f"  {triple.head} -> {triple.relation} -> {triple.tail}")

    return triples


def main():
    """Run all examples."""
    print("UNIFIED KNOWLEDGE GRAPH EXTRACTION EXAMPLES")
    print("=" * 80)
    print("\nNew Modular Architecture:")
    print("  • src.clients - LLM client abstraction layer")
    print("  • src.domains - Knowledge domains with prompts/examples")
    print("  • src.builder - Extraction and augmentation logic")
    print("  • src.converters - Output format converters")
    print("  • src.visualization - Interactive visualizations")
    print("\n")

    try:
        # Example 1: Gemini API (only one that runs without local server)
        example_gemini_api()

        # Example 2: Ollama (info only, requires server)
        example_ollama_local()

        # Example 3: LM Studio (info only, requires server)
        example_lmstudio_local()

        # Example 4: Direct client usage
        example_direct_client_usage()

        # Example 5: Connected graph extraction (two-step)
        example_connected_graph_extraction()

        # Example 6: List resources
        example_list_resources()

        # Example 7: Compare clients
        example_compare_clients()

        # Example 8: Custom prompt
        example_custom_prompt()

        print("\n" + "=" * 80)
        print("EXAMPLES COMPLETED")
        print("=" * 80)
        print("\nNote: Local model examples (Ollama, LM Studio) require")
        print("running servers and are shown for reference only.")
        print("\nCLI Usage:")
        print("  python -m src extract --help")
        print("  python -m src list domains")
        print("  python -m src list clients")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
