"""Unified command-line interface for knowledge graph extraction.

This CLI supports multiple LLM backends: Gemini API, Ollama, and LM Studio.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .clients import ClientConfig
from .extraction_pipeline import ExtractionPipeline


def main() -> None:
    """Run the knowledge graph extraction pipeline."""
    parser = argparse.ArgumentParser(
        description="Extract knowledge graphs from text using various LLM backends",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Use Gemini API (cloud)
  python -m kg_constructor.extract_cli \\
    --client gemini \\
    --model gemini-2.0-flash-exp \\
    --api-key YOUR_KEY \\
    --csv data/legal/sample_data.csv \\
    --limit 3

  # Use Ollama (local)
  python -m kg_constructor.extract_cli \\
    --client ollama \\
    --model llama3.1 \\
    --base-url http://localhost:11434 \\
    --csv data/legal/sample_data.csv \\
    --limit 3

  # Use LM Studio (local)
  python -m kg_constructor.extract_cli \\
    --client lmstudio \\
    --model local-model \\
    --base-url http://localhost:1234/v1 \\
    --csv data/legal/sample_data.csv \\
    --limit 3

  # Use custom prompt template
  python -m kg_constructor.extract_cli \\
    --client gemini \\
    --csv data/legal/sample_data.csv \\
    --prompt src/prompts/legal_background_prompt.txt \\
    --limit 3

Environment Variables:
  LANGEXTRACT_API_KEY    API key for Gemini
  GOOGLE_API_KEY         Alternative for Gemini API key
        """
    )

    # Client selection
    parser.add_argument(
        "--client",
        type=str,
        choices=["gemini", "ollama", "lmstudio"],
        default="gemini",
        help="LLM client type (default: gemini)"
    )

    # Input/output arguments
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to input CSV file"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/kg_extraction"),
        help="Directory to save all outputs (default: outputs/kg_extraction)"
    )
    parser.add_argument(
        "--text-column",
        type=str,
        default="background",
        help="Name of CSV column containing text (default: background)"
    )
    parser.add_argument(
        "--id-column",
        type=str,
        default="id",
        help="Name of CSV column containing record IDs (default: id)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of records to process (default: all)"
    )

    # Model configuration
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model ID (default: gemini-2.0-flash-exp for Gemini, llama3.1 for Ollama)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for Gemini (can also use LANGEXTRACT_API_KEY env var)"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Base URL for Ollama/LM Studio server"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (default: 0.0 for deterministic)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum parallel workers (default: 10 for Gemini, 5 for local)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Request timeout in seconds for local servers (default: 120)"
    )

    # Prompt configuration
    parser.add_argument(
        "--prompt",
        type=Path,
        default=None,
        help="Path to prompt template file (default: src/prompts/default_prompt.txt)"
    )

    # Pipeline options
    parser.add_argument(
        "--no-visualizations",
        action="store_true",
        help="Skip creating HTML visualizations"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Hide progress bar during extraction"
    )

    args = parser.parse_args()

    # Validate input file
    if not args.csv.exists():
        print(f"Error: CSV file not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    # Validate prompt file if specified
    if args.prompt and not args.prompt.exists():
        print(f"Error: Prompt file not found: {args.prompt}", file=sys.stderr)
        sys.exit(1)

    # Build client configuration
    config_kwargs = {
        "client_type": args.client,
        "temperature": args.temperature,
        "show_progress": not args.no_progress,
    }

    # Set model ID with provider-specific defaults
    if args.model:
        config_kwargs["model_id"] = args.model

    # Add client-specific parameters
    if args.client == "gemini":
        if args.api_key:
            config_kwargs["api_key"] = args.api_key
        if args.max_workers:
            config_kwargs["max_workers"] = args.max_workers
    elif args.client in ["ollama", "lmstudio"]:
        if args.base_url:
            config_kwargs["base_url"] = args.base_url
        if args.max_workers:
            config_kwargs["max_workers"] = args.max_workers
        config_kwargs["timeout"] = args.timeout

    # Create client config (will apply defaults in __post_init__)
    client_config = ClientConfig(**config_kwargs)

    # Initialize pipeline
    try:
        pipeline = ExtractionPipeline(
            output_dir=args.output_dir,
            client_config=client_config,
            prompt_path=args.prompt
        )
    except Exception as e:
        print(f"Error initializing pipeline: {e}", file=sys.stderr)
        sys.exit(1)

    # Run full pipeline
    try:
        results = pipeline.run_full_pipeline(
            csv_path=args.csv,
            text_column=args.text_column,
            id_column=args.id_column,
            limit=args.limit,
            create_visualizations=not args.no_visualizations,
            temperature=args.temperature
        )

        print("\nAll outputs saved successfully!")
        print(f"Model: {results['model']}")
        sys.exit(0)

    except Exception as e:
        print(f"\nError during pipeline execution: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
