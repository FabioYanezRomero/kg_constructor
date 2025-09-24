from __future__ import annotations

"""Command-line entry point for the knowledge graph constructor."""

import logging
from pathlib import Path
from typing import List, Optional

import typer

from .config import DatasetConfig, RunConfig
from .pipeline import build_and_save_graphs

app = typer.Typer(help="Generate knowledge graphs with a local vLLM-hosted model.")


@app.command()
def run(
    dataset_name: str = typer.Option(..., "--dataset", "-d", help="Hugging Face dataset identifier."),
    dataset_config: Optional[str] = typer.Option(
        None,
        "--dataset-config",
        "-c",
        help="Optional dataset configuration name (e.g. subset or language).",
    ),
    split: List[str] = typer.Option(
        ["train"],
        "--split",
        "-s",
        help="Dataset split(s) to process. Repeat for multiple splits.",
    ),
    sample_size: Optional[int] = typer.Option(
        None,
        "--sample-size",
        help="Limit the number of samples processed per split.",
    ),
    prompt_path: Path = typer.Option(
        Path("src/prompts/default_prompt.txt"),
        "--prompt-path",
        help="Path to the prompt template file.",
    ),
    output_dir: Path = typer.Option(
        Path("data/output"),
        "--output-dir",
        "-o",
        help="Directory where outputs will be written.",
    ),
    model: str = typer.Option(
        "pytorch/gemma-3-12b-it-INT4",
        "--model",
        "-m",
        help="Model identifier served by vLLM.",
    ),
    inference_url: str = typer.Option(
        "http://localhost:8000",
        "--inference-url",
        envvar="VLLM_URL",
        help="Base URL of the vLLM server (OpenAI compatible).",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        envvar="VLLM_API_KEY",
        help="Optional API key for the vLLM server.",
    ),
    request_timeout: int = typer.Option(
        120,
        "--timeout",
        help="Request timeout for inference interactions in seconds.",
    ),
    parallelism: int = typer.Option(
        1,
        "--parallelism",
        "-p",
        min=1,
        help="Number of concurrent requests issued to the inference server.",
    ),
    warmup: bool = typer.Option(
        True,
        "--warmup/--no-warmup",
        help="Send an initial warm-up request to keep the model loaded.",
    ),
    warmup_prompt: str = typer.Option(
        "Warm up model. Respond with OK.",
        "--warmup-prompt",
        help="Prompt used for the warm-up request.",
    ),
    max_tokens: Optional[int] = typer.Option(
        None,
        "--max-tokens",
        help="Maximum tokens to generate per response (omit to use server default).",
    ),
    temperature: float = typer.Option(
        0.0,
        "--temperature",
        help="Sampling temperature passed to vLLM.",
    ),
    top_p: Optional[float] = typer.Option(
        None,
        "--top-p",
        help="Nucleus sampling top-p parameter.",
    ),
    top_k: Optional[int] = typer.Option(
        None,
        "--top-k",
        help="Top-k sampling parameter.",
    ),
    repetition_penalty: Optional[float] = typer.Option(
        None,
        "--repetition-penalty",
        help="Repetition penalty applied during generation.",
    ),
    system_prompt: Optional[str] = typer.Option(
        None,
        "--system-prompt",
        help="Optional system prompt prepended to every request.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing files instead of skipping them.",
    ),
    include_prompt_in_output: bool = typer.Option(
        False,
        "--include-prompt",
        help="Persist the prompt alongside the model response.",
    ),
) -> None:
    """Execute the end-to-end knowledge graph generation pipeline."""

    dataset_config_obj = DatasetConfig.from_cli(
        dataset_name=dataset_name,
        dataset_config=dataset_config,
        splits=split,
        sample_size=sample_size,
    )

    run_config = RunConfig(
        dataset=dataset_config_obj,
        prompt_path=prompt_path,
        output_dir=output_dir,
        model=model,
        inference_url=inference_url,
        api_key=api_key,
        request_timeout=request_timeout,
        parallelism=parallelism,
        warmup=warmup,
        warmup_prompt=warmup_prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        repetition_penalty=repetition_penalty,
        overwrite=overwrite,
        include_prompt_in_output=include_prompt_in_output,
    )

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    logging.info(
        "Starting knowledge graph construction for dataset %s on splits %s",
        dataset_config_obj.name,
        ", ".join(dataset_config_obj.splits),
    )
    build_and_save_graphs(run_config)


if __name__ == "__main__":
    app()
