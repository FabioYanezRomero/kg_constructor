"""Command-line interface for langextract-based knowledge graph construction."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from kg_constructor.langextract_extractor import ExtractionConfig
from kg_constructor.langextract_pipeline import LangExtractPipeline


def main() -> None:
    """Run the langextract knowledge graph pipeline."""
    parser = argparse.ArgumentParser(
        description="Extract knowledge graphs from legal text using langextract",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process sample legal data with default settings
  python -m kg_constructor.langextract_cli \\
    --csv data/legal/sample_data.csv \\
    --output-dir outputs/langextract_results \\
    --limit 3

  # Use a specific Gemini model with custom settings
  python -m kg_constructor.langextract_cli \\
    --csv data/legal/sample_data.csv \\
    --output-dir outputs/langextract_results \\
    --model gemini-2.0-flash-exp \\
    --temperature 0.0 \\
    --max-workers 5

  # Process without creating visualizations
  python -m kg_constructor.langextract_cli \\
    --csv data/legal/sample_data.csv \\
    --output-dir outputs/langextract_results \\
    --no-visualizations

Environment Variables:
  LANGEXTRACT_API_KEY    API key for Gemini or other LLM services
  GOOGLE_API_KEY         Alternative environment variable for Gemini API key
        """
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
        default=Path("outputs/langextract_results"),
        help="Directory to save all outputs (default: outputs/langextract_results)"
    )
    parser.add_argument(
        "--text-column",
        type=str,
        default="background",
        help="Name of CSV column containing text to analyze (default: background)"
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
        help="Limit number of records to process (default: process all)"
    )

    # Model configuration
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.0-flash-exp",
        help="Model ID to use for extraction (default: gemini-2.0-flash-exp)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for LLM service (can also use LANGEXTRACT_API_KEY or GOOGLE_API_KEY env var)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for generation (default: 0.0 for deterministic)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum parallel workers for concurrent processing (default: 10)"
    )
    parser.add_argument(
        "--batch-length",
        type=int,
        default=10,
        help="Number of text chunks processed per batch (default: 10)"
    )
    parser.add_argument(
        "--max-char-buffer",
        type=int,
        default=8000,
        help="Max number of characters for inference (default: 8000)"
    )

    # Pipeline options
    parser.add_argument(
        "--no-visualizations",
        action="store_true",
        help="Skip creating HTML visualizations"
    )
    parser.add_argument(
        "--no-schema-constraints",
        action="store_true",
        help="Disable schema constraints for structured outputs"
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

    # Get API key from args or environment
    api_key = args.api_key or os.getenv("LANGEXTRACT_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(
            "Error: No API key provided. Set --api-key, LANGEXTRACT_API_KEY, or GOOGLE_API_KEY",
            file=sys.stderr
        )
        sys.exit(1)

    # Create extraction config
    extraction_config = ExtractionConfig(
        model_id=args.model,
        api_key=api_key,
        temperature=args.temperature,
        max_workers=args.max_workers,
        batch_length=args.batch_length,
        max_char_buffer=args.max_char_buffer,
        use_schema_constraints=not args.no_schema_constraints,
        show_progress=not args.no_progress
    )

    # Initialize pipeline
    pipeline = LangExtractPipeline(
        output_dir=args.output_dir,
        extraction_config=extraction_config
    )

    # Run full pipeline
    try:
        results = pipeline.run_full_pipeline(
            csv_path=args.csv,
            text_column=args.text_column,
            id_column=args.id_column,
            limit=args.limit,
            create_visualizations=not args.no_visualizations
        )

        print("\nAll outputs saved successfully!")
        sys.exit(0)

    except Exception as e:
        print(f"\nError during pipeline execution: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
