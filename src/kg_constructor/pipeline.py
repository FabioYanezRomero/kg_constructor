from __future__ import annotations

"""Workflow orchestration for building knowledge graphs from a dataset."""

import json
import logging
import re
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Dict

from tqdm import tqdm

from .config import RunConfig, build_generation_parameters, expand_output_dir
from .dataset_loader import DatasetLoader, Example
from .json_utils import try_parse_json
from .vllm_client import VLLMClient, VLLMClientError
from .prompt_builder import PromptBuilder, PromptContext

logger = logging.getLogger(__name__)


def build_and_save_graphs(config: RunConfig) -> None:
    """Run the pipeline end-to-end for all configured dataset splits."""

    output_root = expand_output_dir(config.output_dir, config.dataset)
    output_root.mkdir(parents=True, exist_ok=True)

    loader = DatasetLoader(config.dataset)
    client = VLLMClient(
        base_url=config.inference_url,
        timeout=config.request_timeout,
        api_key=config.api_key,
    )
    prompt_builder = PromptBuilder(config.prompt_path)

    generation_params = build_generation_parameters(config)
    params_payload = generation_params or None

    if config.warmup:
        try:
            logger.info("Warming up model %s", config.model)
            client.generate(
                prompt=config.warmup_prompt,
                model=config.model,
                params=params_payload,
                system_prompt=config.system_prompt,
            )
        except VLLMClientError as exc:
            logger.warning("Warm-up request failed: %s", exc)

    for split in config.dataset.splits:
        dataset = loader.load_split(split)
        total = loader.estimate_length(dataset)
        split_dir = output_root / sanitize_path_component(split)
        split_dir.mkdir(parents=True, exist_ok=True)

        progress = tqdm(
            total=total,
            desc=f"Processing {split}",
            unit="record",
            leave=False,
        )

        def handle_example(example: Example) -> None:
            record_id = sanitize_path_component(example.example_id)
            context = PromptContext(
                dataset_name=config.dataset.name,
                dataset_config=config.dataset.config,
                split=split,
                record_id=record_id,
                model_name=config.model,
            )
            prompt = prompt_builder.build(example.payload, context)

            try:
                response_text = client.generate(
                    prompt=prompt,
                    model=config.model,
                    params=params_payload,
                    system_prompt=config.system_prompt,
                )
            except VLLMClientError as exc:
                logger.error("Generation failed for %s/%s: %s", split, record_id, exc)
                return

            graph = try_parse_json(response_text)
            document: Dict[str, Any] = {
                "dataset": config.dataset.name,
                "dataset_config": config.dataset.config,
                "split": split,
                "record_id": example.example_id,
                "model": config.model,
                "graph": graph,
                "raw_response": response_text,
                "input_record": example.payload,
            }
            if config.include_prompt_in_output:
                document["prompt"] = prompt

            output_path = split_dir / f"{record_id}.json"
            if output_path.exists() and not config.overwrite:
                logger.info("Skipping existing file %s", output_path)
                return

            with output_path.open("w", encoding="utf-8") as file_pointer:
                json.dump(document, file_pointer, ensure_ascii=False, indent=2)

        max_inflight = max(1, config.parallelism * 4)
        with ThreadPoolExecutor(max_workers=config.parallelism) as executor:
            inflight = set()
            for example in loader.iter_split(split, dataset=dataset):
                future = executor.submit(handle_example, example)
                inflight.add(future)
                if len(inflight) >= max_inflight:
                    done, inflight = wait(inflight, return_when=FIRST_COMPLETED)
                    for completed in done:
                        try:
                            completed.result()
                        except Exception as exc:  # noqa: BLE001
                            logger.exception("Task failed while processing split %s: %s", split, exc)
                        finally:
                            progress.update()

            while inflight:
                done, inflight = wait(inflight, return_when=FIRST_COMPLETED)
                for completed in done:
                    try:
                        completed.result()
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Task failed while processing split %s: %s", split, exc)
                    finally:
                        progress.update()

        progress.close()


def sanitize_path_component(value: str) -> str:
    """Return a filesystem-friendly representation of the provided string."""

    safe = re.sub(r"[^A-Za-z0-9_.-]", "-", value)
    return safe.strip("-") or "record"


__all__ = [
    "build_and_save_graphs",
]
