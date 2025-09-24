# Knowledge Graph Constructor

This repository automates the generation of knowledge graphs from Hugging Face datasets by orchestrating:
- dataset retrieval through the `datasets` library,
- prompt construction for each record,
- inference against a locally hosted [vLLM](https://github.com/vllm-project/vllm) server, and
- storage of the model's JSON output for every processed example and dataset split.

The output artefacts are written as JSON files under `data/output/<dataset_identifier>/<split>/<record>.json`, where slashes in the dataset name are replaced with double underscores, containing the original record, the raw language model response, and the parsed knowledge graph when available.

## Prerequisites
- Python 3.11+
- A vLLM server exposing the OpenAI-compatible API (for example: `pip install vllm` and `vllm serve pytorch/gemma-3-12b-it-INT4 --dtype bfloat16 --gpu-memory-utilization 0.9`)
- Optional: Docker and Make for containerised execution and handy automation

## Quickstart
```bash
make install            # create a virtual environment and install dependencies
make run ARGS="--dataset <namespace/dataset> --split train --model pytorch/gemma-3-12b-it-INT4"
```

The first execution will download the dataset into the local Hugging Face cache. Ensure the vLLM server is running before invoking the command.

## Command-line usage
You can run the pipeline directly with Python:
```bash
.venv/bin/python -m kg_constructor \
  --dataset namespace/dataset_name \
  --dataset-config optional_config \
  --split train --split validation \
  --sample-size 25 \
  --model pytorch/gemma-3-12b-it-INT4 \
  --prompt-path src/prompts/default_prompt.txt \
  --output-dir data/output \
  --parallelism 4 \
  --inference-url http://localhost:8000 \
  --temperature 0.0 \
  --include-prompt
```

### Key options
- `--dataset / -d`: Hugging Face dataset identifier (required)
- `--dataset-config / -c`: optional dataset configuration (e.g. language)
- `--split / -s`: one or more dataset splits to process (`train` by default)
- `--sample-size`: limit the number of records per split
- `--model / -m`: model identifier as served by vLLM (`pytorch/gemma-3-12b-it-INT4` by default)
- `--inference-url`: base URL of the vLLM server (defaults to `http://localhost:8000`; also reads `VLLM_URL`)
- `--api-key`: optional API key forwarded to the vLLM server
- `--overwrite`: overwrite existing result files instead of skipping them
- `--include-prompt`: persist the rendered prompt alongside the model output
- `--parallelism / -p`: number of concurrent requests issued by the client
- `--system-prompt`: optional system prompt prepended to every request
- `--max-tokens`: cap the number of tokens generated per response (omit to use server settings)
- `--temperature`, `--top-p`, `--top-k`, `--repetition-penalty`: sampling controls forwarded to vLLM
- `--warmup/--no-warmup`: control whether an initial warm-up request is sent before processing

Every invocation produces JSON files such as:
```json
{
  "dataset": "namespace/dataset",
  "dataset_config": null,
  "split": "train",
  "record_id": "row_000001",
  "model": "pytorch/gemma-3-12b-it-INT4",
  "graph": {"nodes": [], "edges": []},
  "raw_response": "{...}",
  "input_record": {"text": "example"}
}
```
The `graph` field contains the parsed JSON object when the model returns valid JSON; otherwise it is `null` and the raw response is preserved for later inspection.

### Post-processing raw responses
Use the post-processing utility once outputs are available to coerce `raw_response` strings into the canonical `nodes`/`edges` structure:

```bash
PYTHONPATH=src python -m kg_constructor.postprocess data/output
```

Add `--force` to overwrite graphs that already exist.

### Exporting to NetworkX
Convert any processed JSON artefact into a NetworkX graph representation:

```bash
PYTHONPATH=src python -m kg_constructor.networkx_export data/output/SetFit__ag_news/train/row_000002.json --format graphml
```

Supported formats: `graphml`, `gpickle`, and `json` (node-link schema). The exporter preserves all node and edge attributes present in the structured graph.

## Docker workflow
```bash
make docker-build
make docker-run ARGS="--dataset <namespace/dataset> --split train"
```
The Docker image exposes `VLLM_URL` (defaulting to `http://localhost:8000`) and mounts `./data/output` into the container to persist results. Ensure your vLLM instance is accessible from inside the container (using `--network host` in the Makefile).

## Project layout
```
├── Dockerfile
├── Makefile
├── README.md
├── requirements.txt
├── src/
│   ├── kg_constructor/
│   │   ├── __main__.py          # Typer CLI entry point
│   │   ├── config.py            # Dataclasses describing runtime configuration
│   │   ├── dataset_loader.py    # Hugging Face dataset loading utilities
│   │   ├── json_utils.py        # Helpers to normalise model JSON outputs
│   │   ├── pipeline.py          # Orchestrates prompt generation and persistence
│   │   ├── vllm_client.py       # Minimal HTTP client for vLLM
│   │   └── prompt_builder.py    # Renders prompts based on template placeholders
│   └── prompts/
│       └── default_prompt.txt   # Default knowledge graph prompt template
└── data/
    └── output/                  # Generated graphs organised by dataset and split
```

## Development notes
- Use `make format` to apply Black formatting.
- Extend or replace `src/prompts/default_prompt.txt` to tailor the instructions for your dataset.
- Set environment variables (e.g. `VLLM_URL`) to target remote or containerised vLLM instances.

## Testing the setup
While this repository does not include automated tests yet, you can validate connectivity by running the CLI with `--sample-size 1` on a small dataset split and confirming that a JSON artefact appears inside `data/output/`.
