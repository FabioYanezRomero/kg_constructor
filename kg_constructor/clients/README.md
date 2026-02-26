# LLM Clients Module

The `kg_constructor/clients` module provides an abstraction layer over Large Language Model (LLM) backends. It provides a unified interface to execute knowledge graph extraction and general structural generation across different providers, such as Gemini, Ollama, and LM Studio.

## Architecture

The module is built around three core components:

1. **`BaseLLMClient`** (`base.py`)
   An abstract base class that defines the contract all client implementations must follow. Key methods include:
   - `extract()`: For extracting structured information grounded in the source text (provides character positions).
   - `generate_json()`: For general-purpose structured JSON generation without source grounding.
   - `from_config()`: A class method to instantiate the client from a unified configuration object.

2. **`ClientConfig`** (`config.py`)
   A pure data container (`dataclass`) that holds all possible parameters needed to instantiate any supported LLM client (e.g., `client_type`, `model_id`, `temperature`, `api_key`, `base_url`). This keeps the configuration decoupled from specific provider dependencies.

3. **`ClientFactory`** (`factory.py`)
   A factory utilizing the registry pattern to instantiate the correct client based on the `ClientConfig`. Classes register themselves, allowing for dynamic addition of new client types without hardcoding dependencies across the codebase.

## Supported Providers

Currently, the framework supports:
- **Gemini (`gemini`)**: Google's API-based models.
- **Ollama (`ollama`)**: Local open-source model execution.
- **LM Studio (`lmstudio`)**: Local OpenAI-compatible server endpoints.

*(Provider implementations are located in the `kg_constructor/clients/providers/` directory.)*

## Integration and Usage

### Adding a New Provider

To add a new LLM provider to the framework:
1. Create a new module in `kg_constructor/clients/providers/` (e.g., `openai.py`).
2. Implement a class inheriting from `BaseLLMClient`, ensuring you fulfill the required abstract methods (`extract`, `generate_json`, `supports_structured_output`, `get_model_name`, `from_config`).
3. Register the new client in `kg_constructor/clients/__init__.py`:
   ```python
   from .providers import NewProviderClient
   ClientFactory.register("new_provider", NewProviderClient)
   ```

### Effects on CLI Commands

The clients module is tightly integrated with the main Typer CLI (`kg_constructor/__main__.py`), ensuring a seamless user experience.

#### Dynamic Client Listing
Users can see all installed backend providers with the `list clients` wrapper, which polls the `ClientFactory` registry directly:
```bash
kg_constructor list clients
```

#### Shared Execution Arguments
Whether running step 1 (`extract`) or step 2 (`augment connectivity`), the CLI accepts standardized arguments that map directly onto `ClientConfig`:
- `--client` (`-c`): The backend identifier (e.g., `gemini`, `ollama`).
- `--model`: Specific model identifier to override default.
- `--temp`: Adjust the sampling temperature.
- `--api-key`: For remote provider authentication.
- `--base-url`: For local backend endpoints.
- `--timeout`: Inference timeout.

**Under the hood:** The CLI constructs a `ClientConfig` using these flags and calls `ClientFactory.create(config)` to procure a ready-to-use client instance, completely agnostic of the execution logic mapping (extraction vs augmentation).
