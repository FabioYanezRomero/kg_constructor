"""Unified command-line interface for knowledge graph generation using Typer.

This CLI supports multiple LLM backends: Gemini API, Ollama, and LM Studio.
Supports JSONL (recommended), JSON, and CSV input formats.

Commands:
    extract              - Step 1: Extract triples from text
    augment connectivity - Step 2: Reduce disconnected graph components

Full pipeline is achieved by running both commands in sequence:
    python -m src.extract_cli extract --input data.jsonl --domain legal
    python -m src.extract_cli augment connectivity --input data.jsonl --domain legal
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .clients import ClientConfig
from .extraction_pipeline import ExtractionPipeline
from .domains import list_available_domains, ExtractionMode

# Initialize Typer apps
app = typer.Typer(
    help="Knowledge graph generation CLI. Use 'extract' for Step 1, 'augment <strategy>' for Step 2.",
    no_args_is_help=True
)
augment_app = typer.Typer(
    help="Step 2: Augment the knowledge graph. Strategies: connectivity (default)",
    no_args_is_help=True
)
app.add_typer(augment_app, name="augment")

console = Console()


class ClientType(str, Enum):
    """Supported LLM client backends."""
    GEMINI = "gemini"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"


def _build_client_config(
    client: ClientType,
    model: Optional[str],
    api_key: Optional[str],
    base_url: Optional[str],
    temperature: float,
    no_progress: bool,
    max_workers: Optional[int],
    timeout: int
) -> ClientConfig:
    """Build ClientConfig from CLI options."""
    config_kwargs = {
        "client_type": client.value,
        "temperature": temperature,
        "show_progress": not no_progress,
        "timeout": timeout,
    }
    if model:
        config_kwargs["model_id"] = model
    if api_key:
        config_kwargs["api_key"] = api_key
    if base_url:
        config_kwargs["base_url"] = base_url
    if max_workers:
        config_kwargs["max_workers"] = max_workers
    return ClientConfig(**config_kwargs)


def _init_pipeline(
    output_dir: Path,
    client_config: ClientConfig,
    domain: str,
    mode: ExtractionMode,
    prompt_override: Optional[Path]
) -> ExtractionPipeline:
    """Initialize the extraction pipeline."""
    return ExtractionPipeline(
        output_dir=output_dir,
        client_config=client_config,
        domain=domain,
        extraction_mode=mode,
        prompt_path=prompt_override
    )


# =============================================================================
# EXTRACT Command (Step 1)
# =============================================================================

@app.command()
def extract(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to input file (.jsonl, .json, or .csv)", exists=True, file_okay=True, dir_okay=False),
    output_dir: Path = typer.Option("outputs/kg_extraction", "--output-dir", "-o", help="Directory to save all outputs"),
    domain: str = typer.Option(..., "--domain", "-d", help=f"Knowledge domain [required] (Available: {', '.join(list_available_domains())})"),
    mode: ExtractionMode = typer.Option(ExtractionMode.OPEN, "--mode", "-m", help="Extraction mode (open or constrained)"),
    client: ClientType = typer.Option(ClientType.GEMINI, "--client", "-c", help="LLM client type"),
    model: Optional[str] = typer.Option(None, "--model", help="Model ID (e.g., gemini-2.0-flash-exp, llama3.1)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for Gemini (optional if env var set)"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL for Ollama/LM Studio"),
    text_field: str = typer.Option("text", "--text-field", help="Field name containing text"),
    id_field: str = typer.Option("id", "--id-field", help="Field name containing record IDs"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of records to process"),
    temperature: float = typer.Option(0.0, "--temp", help="Sampling temperature"),
    prompt_override: Optional[Path] = typer.Option(None, "--prompt", help="Override extraction prompt file", exists=True),
    no_progress: bool = typer.Option(False, "--no-progress", help="Hide progress bar"),
    max_workers: Optional[int] = typer.Option(None, "--workers", help="Max parallel workers"),
    timeout: int = typer.Option(120, "--timeout", help="Request timeout (seconds) for local servers"),
):
    """Step 1: Extract knowledge graph triples from text.
    
    Supports JSONL (recommended), JSON, and CSV input formats.
    Format is auto-detected from file extension.
    
    \b
    Examples:
        # Extract from JSONL (recommended)
        python -m src.extract_cli extract --input data.jsonl --domain legal
        
        # Extract from JSON array
        python -m src.extract_cli extract --input data.json --domain legal
        
        # Extract from CSV (legacy)
        python -m src.extract_cli extract --input data.csv --domain legal --text-field background
    """
    console.print(f"[bold blue]Step 1: Extraction[/bold blue]")
    console.print(f"Input: [dim]{input_file}[/dim]")
    console.print(f"Domain: [green]{domain}[/green] | Mode: [dim]{mode.value}[/dim]")
    
    client_config = _build_client_config(client, model, api_key, base_url, temperature, no_progress, max_workers, timeout)
    
    try:
        pipeline = _init_pipeline(output_dir, client_config, domain, mode, prompt_override)
        results = pipeline.run_full_pipeline(
            input_path=input_file,
            text_field=text_field,
            id_field=id_field,
            limit=limit,
            temperature=temperature,
            run_extraction=True,
            run_augmentation=False
        )
        
        console.print("\n[bold green]✓ Extraction complete.[/bold green]")
        
        table = Table(title="Extraction Summary")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Model", pipeline.extractor.client.get_model_name())
        table.add_row("Domain", domain)
        table.add_row("Records processed", str(len(results['json_files'])))
        table.add_row("Output directory", str(output_dir))
        console.print(table)
        
        console.print(f"\n[dim]Next step: python -m src.extract_cli augment connectivity --input {input_file} --domain {domain}[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# AUGMENT Subcommands (Step 2)
# =============================================================================

@augment_app.command("connectivity")
def augment_connectivity(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to input file (.jsonl, .json, or .csv)", exists=True, file_okay=True, dir_okay=False),
    output_dir: Path = typer.Option("outputs/kg_extraction", "--output-dir", "-o", help="Directory containing extracted JSON files"),
    domain: str = typer.Option(..., "--domain", "-d", help=f"Knowledge domain [required] (Available: {', '.join(list_available_domains())})"),
    mode: ExtractionMode = typer.Option(ExtractionMode.OPEN, "--mode", "-m", help="Extraction mode (open or constrained)"),
    client: ClientType = typer.Option(ClientType.GEMINI, "--client", "-c", help="LLM client type"),
    model: Optional[str] = typer.Option(None, "--model", help="Model ID"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for Gemini"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL for Ollama/LM Studio"),
    text_field: str = typer.Option("text", "--text-field", help="Field name containing text"),
    id_field: str = typer.Option("id", "--id-field", help="Field name containing record IDs"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of records"),
    temperature: float = typer.Option(0.0, "--temp", help="Sampling temperature"),
    max_disconnected: int = typer.Option(3, "--max-disconnected", help="Target: max allowed disconnected components"),
    max_iterations: int = typer.Option(2, "--max-iterations", help="Max refinement iterations"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Hide progress bar"),
    max_workers: Optional[int] = typer.Option(None, "--workers", help="Max parallel workers"),
    timeout: int = typer.Option(120, "--timeout", help="Request timeout (seconds)"),
):
    """Connectivity augmentation: Reduce disconnected graph components.
    
    This strategy analyzes the extracted knowledge graph, identifies disconnected
    components, and uses the LLM to infer bridging triples that connect them.
    
    Requires: Run 'extract' first to create JSON files in the output directory.
    
    \b
    Examples:
        # Basic connectivity augmentation
        python -m src.extract_cli augment connectivity --input data.jsonl --domain legal
        
        # Aggressive connectivity (target fully connected graph)
        python -m src.extract_cli augment connectivity --input data.jsonl --domain legal --max-disconnected 1
    """
    console.print(f"[bold blue]Step 2: Augmentation (Connectivity Strategy)[/bold blue]")
    console.print(f"Target: ≤ {max_disconnected} disconnected components | Max iterations: {max_iterations}")
    
    client_config = _build_client_config(client, model, api_key, base_url, temperature, no_progress, max_workers, timeout)
    
    try:
        pipeline = _init_pipeline(output_dir, client_config, domain, mode, None)
        results = pipeline.run_full_pipeline(
            input_path=input_file,
            text_field=text_field,
            id_field=id_field,
            limit=limit,
            temperature=temperature,
            run_extraction=False,
            run_augmentation=True,
            max_disconnected=max_disconnected,
            max_iterations=max_iterations
        )
        
        console.print("\n[bold green]✓ Connectivity augmentation complete.[/bold green]")
        
        table = Table(title="Augmentation Summary")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Strategy", "Connectivity")
        table.add_row("Model", pipeline.extractor.client.get_model_name())
        table.add_row("Records processed", str(len(results['json_files'])))
        table.add_row("Output directory", str(output_dir))
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# Default augment command (shows available strategies)
# =============================================================================

@augment_app.callback(invoke_without_command=True)
def augment_default(ctx: typer.Context):
    """Default augmentation strategy is 'connectivity'.
    
    Run 'augment connectivity --help' for options.
    """
    if ctx.invoked_subcommand is None:
        console.print("[yellow]No strategy specified. Available strategies:[/yellow]")
        console.print("  • connectivity - Reduce disconnected graph components")
        console.print("\n[dim]Usage: python -m src.extract_cli augment connectivity --input data.jsonl --domain legal[/dim]")
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
