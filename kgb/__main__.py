"""Unified command-line interface for knowledge graph generation using Typer.

This CLI supports multiple LLM backends: Gemini API, Ollama, and LM Studio.
Supports JSONL (recommended), JSON, and CSV input formats.

Commands:
    extract              - Step 1: Extract triples from text
    augment connectivity - Step 2: Reduce disconnected graph components
    convert              - Convert JSON triples to GraphML
    visualize network    - Show interactive network graph (Plotly)
    visualize extraction - Show entity highlights in source text (langextract)
    list domains         - List available knowledge domains
    list clients         - List available LLM client types

Interactive mode:
    Run `kgb` with no arguments to enter the interactive shell.
"""

from __future__ import annotations

# Suppress absl warnings (e.g., langextract prompt alignment warnings)
import os
os.environ["ABSL_LOGGING_LEVEL"] = "ERROR"
import absl.logging
absl.logging.set_verbosity(absl.logging.ERROR)

import json
import shlex
import sys
from pathlib import Path
from typing import Optional, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import typer
from rich.console import Console
from rich.table import Table

from .clients import ClientConfig, ClientFactory
from .io.readers import load_records
from .io.writers import convert_json_directory
from .visualization import batch_visualize_graphs, EntityVisualizer
from .domains import list_available_domains, ExtractionMode
from .pipeline import PipelineRunner, PipelineContext, get_step

__version__ = "0.1.0"

# Initialize Typer apps
app = typer.Typer(
    help="Knowledge graph generation framework.",
)

augment_app = typer.Typer(
    help="Step 2: Augment the knowledge graph.",
    no_args_is_help=True
)
app.add_typer(augment_app, name="augment")

visualize_app = typer.Typer(
    help="Create interactive HTML visualizations.",
    no_args_is_help=True
)
app.add_typer(visualize_app, name="visualize")

list_app = typer.Typer(
    help="List available resources.",
    no_args_is_help=True
)
app.add_typer(list_app, name="list")

console = Console()

def _available_client_types() -> list[str]:
    """Return the registered client types."""
    return sorted(ClientFactory.get_available_clients())


def _validate_client_type(value: str) -> str:
    """Validate CLI client selection against the factory registry."""
    if ClientFactory.is_registered(value):
        return value
    available = ", ".join(_available_client_types()) or "none"
    raise typer.BadParameter(
        f"Unsupported client type '{value}'. Available types: {available}"
    )


def _build_client_config(
    client: str,
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
        "client_type": client,
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


# =============================================================================
# LIST Commands
# =============================================================================

@list_app.command("domains")
def list_domains():
    """List available knowledge domains."""
    domains = list_available_domains()
    table = Table(title="Available Knowledge Domains")
    table.add_column("Domain Name", style="cyan")
    for d in domains:
        table.add_row(d)
    console.print(table)


@list_app.command("clients")
def list_clients():
    """List available LLM client types."""
    clients = ClientFactory.get_available_clients()
    table = Table(title="Available LLM Clients")
    table.add_column("Client Type", style="green")
    for c in clients:
        table.add_row(c)
    console.print(table)


# =============================================================================
# PIPELINE Command
# =============================================================================

@app.command("run-pipeline")
def run_pipeline(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to input file (.jsonl, .json, or .csv)", exists=True),
    output_dir: Path = typer.Option("outputs/pipeline_run", "--output-dir", "-o", help="Directory to save pipeline artifacts"),
    domain: str = typer.Option(..., "--domain", "-d", help="Knowledge domain"),
    mode: ExtractionMode = typer.Option(ExtractionMode.OPEN, "--mode", "-m", help="Extraction mode"),
    client: str = typer.Option(
        "gemini",
        "--client",
        "-c",
        help="LLM client type",
        callback=_validate_client_type,
    ),
    model: Optional[str] = typer.Option(None, "--model", help="Model ID"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL"),
    text_field: str = typer.Option("text", "--text-field", help="Field name containing text"),
    id_field: str = typer.Option("id", "--id-field", help="Field name containing record IDs"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of records"),
    temperature: float = typer.Option(0.0, "--temp", help="Sampling temperature"),
    # Logical Pipeline Steps Toggles
    do_extract: bool = typer.Option(False, "--extract", help="Run extraction step"),
    do_augment: bool = typer.Option(False, "--augment", help="Run connectivity augmentation step"),
    do_convert: bool = typer.Option(False, "--convert", help="Convert resulting triples to GraphML"),
    do_visualize: bool = typer.Option(False, "--visualize", help="Create visual HTMLs from triples"),
    # General arguments
    no_progress: bool = typer.Option(False, "--no-progress", help="Hide progress bar"),
    max_workers: Optional[int] = typer.Option(None, "--workers", help="Max parallel workers"),
    timeout: int = typer.Option(120, "--timeout", help="Request timeout (seconds)"),
):
    """Run a dynamically composed pipeline based on provided logical flags.
    
    \b
    Examples:
        kgb run-pipeline --input data.jsonl --domain legal --extract --client ollama
        kgb run-pipeline --input data.jsonl --domain legal --extract --augment --convert --visualize --client ollama
    """
    if not any([do_extract, do_augment, do_convert, do_visualize]):
        console.print("[yellow]Warning: No pipeline steps selected. Use --extract, --augment, --convert, or --visualize.[/yellow]")
        return
        
    console.print(f"[bold blue]Pipeline Orchestrator Launching[/bold blue]")
    
    try:
        # Load records and initialize contexts
        records = load_records(input_file, text_field, id_field, None, limit)
        contexts = [PipelineContext(record_id=str(r["id"]), text=str(r["text"])) for r in records]
        console.print(f"Loaded {len(contexts)} contexts from {input_file.name}")
        
        # Setup cross-cutting utilities
        from .domains import get_domain
        domain_obj = get_domain(domain, extraction_mode=mode)
        config = _build_client_config(client, model, api_key, base_url, temperature, no_progress, max_workers, timeout)
        llm_client = ClientFactory.create(config)
        output_dir = Path(output_dir)
        
        # Assemble Pipeline Steps Sequence
        steps_sequence = []
        
        if do_extract:
            steps_sequence.append(get_step("extract")(client=llm_client, domain=domain_obj, temperature=temperature))
            
        if do_augment:
            steps_sequence.append(get_step("augment")(client=llm_client, domain=domain_obj, temperature=temperature))
            
        if do_extract or do_augment:
            json_dir = output_dir / "extracted_json"
            steps_sequence.append(get_step("export-json")(output_dir=json_dir))
            
        if do_convert:
            graphml_dir = output_dir / "graphml"
            steps_sequence.append(get_step("convert")(output_dir=graphml_dir))
            
        if do_visualize:
            network_dir = output_dir / "visualizations"
            extraction_viz_dir = output_dir / "visualizations_extraction"
            steps_sequence.append(get_step("visualize-network")(output_dir=network_dir))
            steps_sequence.append(get_step("visualize-extraction")(output_dir=extraction_viz_dir))
            
        # Execute Pipeline Sequence
        console.print(f"[bold green]Assembled {len(steps_sequence)} pipeline steps.[/bold green]")
        runner = PipelineRunner(steps=steps_sequence)
        
        results = runner.execute_batch(contexts, max_workers=max_workers, show_progress=not no_progress)
        
        # Determine Success Criteria
        successes = sum(1 for c in results if not c.errors)
        errors = sum(1 for c in results if c.errors)
        
        console.print(f"\n[bold green]✓ Pipeline execution complete.[/bold green]")
        console.print(f"Success: {successes} | Errors: {errors}")
        console.print(f"Artifacts located at: {output_dir}")
        
        if errors > 0:
            console.print("\n[bold red]Errors detail:[/bold red]")
            for c in results:
                if c.errors:
                    console.print(f"  [{c.record_id}]: {c.errors[0]}")
                    
    except Exception as e:
        console.print(f"[bold red]Pipeline Error:[/bold red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# EXTRACT Command (Step 1)
# =============================================================================


@app.command()
def extract(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to input file (.jsonl, .json, or .csv)", exists=True),
    output_dir: Path = typer.Option("outputs/kg_extraction", "--output-dir", "-o", help="Directory to save outputs"),
    domain: str = typer.Option(..., "--domain", "-d", help="Knowledge domain [required] (use 'list domains' to see all)"),
    mode: ExtractionMode = typer.Option(ExtractionMode.OPEN, "--mode", "-m", help="Extraction mode"),
    client: str = typer.Option(
        "gemini",
        "--client",
        "-c",
        help="LLM client type",
        callback=_validate_client_type,
    ),
    model: Optional[str] = typer.Option(None, "--model", help="Model ID"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for Gemini"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL for Ollama/LM Studio"),
    text_field: str = typer.Option("text", "--text-field", help="Field name containing text"),
    id_field: str = typer.Option("id", "--id-field", help="Field name containing record IDs"),
    record_ids: Optional[list[str]] = typer.Option(None, "--record-ids", help="List of record IDs to process"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of records"),
    temperature: float = typer.Option(0.0, "--temp", help="Sampling temperature"),
    prompt_override: Optional[Path] = typer.Option(None, "--prompt", help="Override extraction prompt", exists=True),
    no_progress: bool = typer.Option(False, "--no-progress", help="Hide progress bar"),
    max_workers: Optional[int] = typer.Option(None, "--workers", help="Max parallel workers"),
    timeout: int = typer.Option(120, "--timeout", help="Request timeout (seconds)"),
):
    """Step 1: Extract knowledge graph triples from text.
    
    \b
    Examples:
        kgb extract --input data.jsonl --domain legal
    """
    console.print(f"[bold blue]Step 1: Extraction[/bold blue]")
    console.print(f"Input: [dim]{input_file}[/dim] | Domain: [green]{domain}[/green]")
    
    try:
        # Load records
        records = load_records(input_file, text_field, id_field, record_ids, limit)
        console.print(f"Loaded {len(records)} records")
        
        # Setup domain and client
        from .domains import get_domain
        domain_obj = get_domain(domain, extraction_mode=mode)
        config = _build_client_config(client, model, api_key, base_url, temperature, no_progress, max_workers, timeout)
        llm_client = ClientFactory.create(config)
        
        # Process
        json_dir = output_dir / "extracted_json"
        json_dir.mkdir(parents=True, exist_ok=True)
        
        from .builder import extract_from_text
        
        output_files = {}
        for record in records:
            record_id = str(record["id"])
            text = str(record["text"])
            output_path = json_dir / f"{record_id}.json"
            
            console.print(f"Processing {record_id} (extract only)...")
            triples = extract_from_text(
                client=llm_client,
                domain=domain_obj,
                text=text,
                record_id=record_id,
                temperature=temperature,
                prompt_override=prompt_override.read_text() if prompt_override else None
            )
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump([t.model_dump() for t in triples], f, ensure_ascii=False, indent=2)
            
            output_files[record_id] = output_path
            console.print(f"  → {len(triples)} triples saved")
        
        console.print(f"\n[bold green]✓ Extraction complete.[/bold green]")
        console.print(f"Output: {json_dir} ({len(output_files)} files)")
        console.print(f"\n[dim]Next: kgb augment connectivity --input {input_file} --domain {domain}[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# AUGMENT Subcommands (Step 2)
# =============================================================================

@augment_app.command("connectivity")
def augment_connectivity(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to input file", exists=True),
    output_dir: Path = typer.Option("outputs/kg_extraction", "--output-dir", "-o", help="Directory with extracted JSON"),
    domain: str = typer.Option(..., "--domain", "-d", help="Knowledge domain (use 'list domains' to see all)"),
    mode: ExtractionMode = typer.Option(ExtractionMode.OPEN, "--mode", "-m", help="Extraction mode"),
    client: str = typer.Option(
        "gemini",
        "--client",
        "-c",
        help="LLM client type",
        callback=_validate_client_type,
    ),
    model: Optional[str] = typer.Option(None, "--model", help="Model ID"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL"),
    text_field: str = typer.Option("text", "--text-field", help="Field name containing text"),
    id_field: str = typer.Option("id", "--id-field", help="Field name containing IDs"),
    record_ids: Optional[list[str]] = typer.Option(None, "--record-ids", help="List of record IDs to process"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit records"),
    temperature: float = typer.Option(0.0, "--temp", help="Sampling temperature"),
    max_disconnected: int = typer.Option(3, "--max-disconnected", help="Target max disconnected components"),
    max_iterations: int = typer.Option(2, "--max-iterations", help="Max refinement iterations"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Hide progress bar"),
    max_workers: Optional[int] = typer.Option(None, "--workers", help="Max parallel workers"),
    timeout: int = typer.Option(120, "--timeout", help="Request timeout"),
):
    """Connectivity augmentation: Reduce disconnected graph components.
    
    \b
    Examples:
        kgb augment connectivity --input data.jsonl --domain legal
    """
    console.print(f"[bold blue]Step 2: Augmentation (Connectivity)[/bold blue]")
    console.print(f"Target: ≤ {max_disconnected} components | Max iterations: {max_iterations}")
    
    try:
        records = load_records(input_file, text_field, id_field, record_ids, limit)
        
        from .domains import get_domain
        domain_obj = get_domain(domain, extraction_mode=mode)
        config = _build_client_config(client, model, api_key, base_url, temperature, no_progress, max_workers, timeout)
        llm_client = ClientFactory.create(config)
        
        json_dir = output_dir / "extracted_json"
        json_dir.mkdir(parents=True, exist_ok=True)
        
        from .builder import extract_connected_graph
        
        output_files = {}
        for record in records:
            record_id = str(record["id"])
            text = str(record["text"])
            output_path = json_dir / f"{record_id}.json"
            
            existing_triples = None
            if output_path.exists():
                console.print(f"[dim]Loading existing triples for {record_id}[/dim]")
                with open(output_path, "r", encoding="utf-8") as f:
                    existing_triples = json.load(f)
            
            console.print(f"Processing {record_id} (augment connectivity)...")
            triples, metadata = extract_connected_graph(
                client=llm_client,
                domain=domain_obj,
                text=text,
                record_id=record_id,
                initial_triples=existing_triples,
                temperature=temperature,
                max_disconnected=max_disconnected,
                max_iterations=max_iterations,
                augmentation_strategy="connectivity"
            )
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump([t.model_dump() for t in triples], f, ensure_ascii=False, indent=2)
            
            output_files[record_id] = output_path
            if metadata.get("partial_result"):
                console.print(f"  [yellow]⚠ Partial result saved due to iteration failure.[/yellow]")
            console.print(f"  → {len(triples)} triples saved (Final components: {metadata['final_components']})")
        
        console.print(f"\n[bold green]✓ Augmentation complete.[/bold green]")
        console.print(f"Output: {json_dir} ({len(output_files)} files)")
        console.print(f"\n[dim]Next: kgb convert --input {json_dir}[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@augment_app.callback(invoke_without_command=True)
def augment_default(ctx: typer.Context):
    """Show available augmentation strategies."""
    if ctx.invoked_subcommand is None:
        console.print("[yellow]Available strategies:[/yellow]")
        console.print("  • connectivity - Reduce disconnected graph components")


# =============================================================================
# CONVERT Command
# =============================================================================

@app.command()
def convert(
    input_dir: Path = typer.Option(..., "--input", "-i", help="Directory with JSON triples", exists=True),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for GraphML"),
):
    """Convert JSON triples to GraphML format.
    
    \b
    Examples:
        kgb convert --input outputs/extracted_json
    """
    console.print(f"[bold blue]Converting JSON to GraphML[/bold blue]")
    
    graphml_dir = output_dir or input_dir.parent / "graphml"
    
    try:
        graphml_files = convert_json_directory(input_dir, graphml_dir)
        console.print(f"\n[bold green]✓ Converted {len(graphml_files)} files[/bold green]")
        console.print(f"Output: {graphml_dir}")
        console.print(f"\n[dim]Next: kgb visualize network --input {graphml_dir}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# VISUALIZE Commands
# =============================================================================

@visualize_app.command("network")
def visualize_network(
    input_dir: Path = typer.Option(..., "--input", "-i", help="Directory with GraphML files", exists=True),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for HTML"),
    dark_mode: bool = typer.Option(False, "--dark-mode", help="Enable premium dark mode theme"),
    layout: str = typer.Option("spring", "--layout", help="Graph layout (spring, circular, kamada_kawai, shell)"),
):
    """Create interactive network visualizations from GraphML.
    
    \b
    Examples:
        kgb visualize network --input outputs/graphml --dark-mode
    """
    console.print(f"[bold blue]Creating Network Visualizations[/bold blue]")
    
    viz_dir = output_dir or input_dir.parent / "visualizations"
    
    try:
        html_files = batch_visualize_graphs(input_dir, viz_dir, dark_mode=dark_mode, layout=layout)
        console.print(f"\n[bold green]✓ Created {len(html_files)} network visualizations[/bold green]")
        console.print(f"Output: {viz_dir}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@visualize_app.command("extraction")
def visualize_extraction(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to original text data (.jsonl, .json, or .csv)", exists=True),
    triples_dir: Path = typer.Option(..., "--triples", "-t", help="Directory with extracted JSON triples", exists=True),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for HTML"),
    text_field: str = typer.Option("text", "--text-field", help="Field name containing text"),
    id_field: str = typer.Option("id", "--id-field", help="Field name containing record IDs"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of records"),
    animation_speed: float = typer.Option(1.0, "--speed", help="Animation speed for highlights"),
    group_by: str = typer.Option("entity_type", "--group-by", help="How to group highlights (entity_type, relation)"),
):
    """Create interactive text visualizations with entity highlights.
    
    \b
    Examples:
        kgb visualize extraction --input data.jsonl --triples outputs/extracted_json
    """
    console.print(f"[bold blue]Creating Extraction Visualizations[/bold blue]")
    
    viz_dir = output_dir or triples_dir.parent / "visualizations_extraction"
    
    try:
        records = load_records(input_file, text_field, id_field, limit=limit)
        visualizer = EntityVisualizer(animation_speed=animation_speed)
        
        # Prepare records for batch visualizer
        record_map = {}
        for r in records:
            rid = str(r["id"])
            text = str(r["text"])
            triple_file = triples_dir / f"{rid}.json"
            if triple_file.exists():
                with open(triple_file, "r", encoding="utf-8") as f:
                    triples = json.load(f)
                record_map[rid] = (text, triples)
        
        html_files = visualizer.batch_visualize(record_map, viz_dir, group_by=group_by)
        console.print(f"\n[bold green]✓ Created {len(html_files)} extraction visualizations[/bold green]")
        console.print(f"Output: {viz_dir}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Knowledge graph generation framework."""
    if ctx.invoked_subcommand is None:
        # When called via Typer with no subcommand, show help
        raise typer.Exit()


# =============================================================================
# KGB ASCII Banner & Interactive Shell
# =============================================================================

KGB_BANNER = r"""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║      ◉         ◉    ◉━━━━◉━━━━◉    ◉━━━━◉━━━━◉        ║
    ║      ┃        ╱     ┃              ┃          ╲       ║
    ║      ◉       ◉      ◉              ◉           ◉      ║
    ║      ┃      ╱       ┃              ┃          ╱       ║
    ║      ◉━━━━━◉        ◉    ◉━━━━◉    ◉━━━━◉━━━━◉        ║
    ║      ┃      ╲       ┃         ┃    ┃          ╲       ║
    ║      ◉       ◉      ◉         ◉    ◉           ◉      ║
    ║      ┃        ╲     ┃         ┃    ┃          ╱       ║
    ║      ◉         ◉    ◉━━━━◉━━━━◉    ◉━━━━◉━━━━◉        ║
    ║                                                       ║
    ║     K n o w l e d g e   G r a p h   B u i l d e r     ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
"""


def interactive_shell():
    """Run the interactive KGB shell with REPL."""
    console.print(KGB_BANNER, style="bold green")
    console.print(f"  Knowledge Graph Builder v{__version__}", style="bold white")
    console.print("  Type [bold]help[/bold] for commands, [bold]exit[/bold] to quit.\n")

    while True:
        try:
            line = input("KGB> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!", style="bold green")
            break

        if not line:
            continue

        if line.lower() in ("exit", "quit"):
            console.print("Goodbye!", style="bold green")
            break

        if line.lower() == "help":
            line = "--help"

        try:
            args = shlex.split(line)
        except ValueError as e:
            console.print(f"[red]Parse error:[/red] {e}")
            continue

        try:
            app(args, standalone_mode=False)
        except SystemExit:
            # Typer/Click raises SystemExit on --help and errors; absorb it
            pass
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def main_entry():
    """Console-scripts entry point.

    - With arguments: one-shot mode (delegates to Typer app).
    - Without arguments: launches the interactive KGB shell.
    """
    if len(sys.argv) > 1:
        app()
    else:
        interactive_shell()


if __name__ == "__main__":
    main_entry()
