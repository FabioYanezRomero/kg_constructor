# Adding a New LLM Client Provider

This skill documents how to add a new LLM client provider to the `src/clients` module.

## Overview

The clients module uses a registry-based factory pattern. Each client:
1. Inherits from `BaseLLMClient` (which uses `abc.ABC` with `@abstractmethod` decorators)
2. Implements required abstract methods
3. Provides a `from_config()` classmethod for factory instantiation
4. Gets registered in `__init__.py`

## File Structure

```
src/clients/
├── __init__.py           # Registration happens here
├── base.py               # BaseLLMClient abstract class (uses abc.ABC)
├── config.py             # ClientConfig dataclass
├── factory.py            # ClientFactory class
└── providers/            # All client implementations
    ├── __init__.py       # Re-exports client classes
    ├── gemini.py         # Example: Gemini client
    ├── ollama.py         # Example: Ollama client
    └── your_provider.py  # NEW: Your client
```

## Step 1: Create Provider File

Create `src/clients/providers/your_provider.py`:

```python
"""Your Provider client for knowledge graph extraction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..base import BaseLLMClient, LLMClientError

if TYPE_CHECKING:
    from ..config import ClientConfig


class YourProviderClient(BaseLLMClient):
    """Client for YourProvider LLM service."""

    def __init__(
        self,
        model_id: str = "default-model",
        api_key: str | None = None,
        base_url: str = "http://localhost:8000",
        max_workers: int = 5,
        max_char_buffer: int = 8000,
        show_progress: bool = True,
        timeout: int = 120,
    ) -> None:
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url
        self.max_workers = max_workers
        self.max_char_buffer = max_char_buffer
        self.show_progress = show_progress
        self.timeout = timeout

    def extract(
        self,
        text: str,
        prompt_description: str,
        examples: list[Any] | None = None,
        format_type: type | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Extract structured information with source grounding."""
        # Implementation here
        raise NotImplementedError

    def generate_json(
        self,
        text: str,
        prompt_description: str,
        format_type: type,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Generate JSON without source grounding."""
        # Implementation here
        raise NotImplementedError

    def get_model_name(self) -> str:
        """Return the model identifier."""
        return f"yourprovider/{self.model_id}"

    def supports_structured_output(self) -> bool:
        """Whether this client supports native JSON schema."""
        return False

    @classmethod
    def from_config(cls, config: ClientConfig) -> YourProviderClient:
        """Create client from a ClientConfig.
        
        Apply provider-specific defaults for unset values.
        """
        return cls(
            model_id=config.model_id or "default-model",
            api_key=config.api_key,
            base_url=config.base_url or "http://localhost:8000",
            max_workers=config.max_workers if config.max_workers is not None else 5,
            max_char_buffer=config.max_char_buffer,
            show_progress=config.show_progress,
            timeout=config.timeout,
        )


__all__ = ["YourProviderClient"]
```

## Step 2: Update providers/__init__.py

Add your client to the re-exports:

```python
from .gemini import GeminiClient
from .ollama import OllamaClient
from .lmstudio import LMStudioClient
from .your_provider import YourProviderClient  # Add this

__all__ = [
    "GeminiClient",
    "OllamaClient", 
    "LMStudioClient",
    "YourProviderClient",  # Add this
]
```

## Step 3: Register in clients/__init__.py

Add registration line:

```python
from .providers import GeminiClient, OllamaClient, LMStudioClient, YourProviderClient

# Register all client types
ClientFactory.register("gemini", GeminiClient)
ClientFactory.register("ollama", OllamaClient)
ClientFactory.register("lmstudio", LMStudioClient)
ClientFactory.register("yourprovider", YourProviderClient)  # Add this

__all__ = [
    # ... existing exports
    "YourProviderClient",  # Add this
]
```

## Step 4: Update config.py ClientType

Add your provider to the ClientType literal:

```python
ClientType = Literal["gemini", "ollama", "lmstudio", "yourprovider"]
```

## Required Abstract Methods

Your client MUST implement these methods from `BaseLLMClient`:

| Method | Purpose |
|--------|---------|
| `extract()` | Extract with source grounding (char positions) |
| `generate_json()` | Generate JSON without source grounding |
| `get_model_name()` | Return model identifier string |
| `supports_structured_output()` | Return True if native JSON schema supported |
| `from_config()` | Class method to create from ClientConfig |

> **Note:** `BaseLLMClient` uses Python's `abc.ABC` with `@abstractmethod` decorators to enforce implementation. Your code will fail at instantiation if any abstract method is missing.

## Testing Your Client

After implementing your client, verify it works:

```python
# Test 1: Verify registration
from src.clients import ClientFactory
print(ClientFactory.get_available_clients())
# Should include 'yourprovider'

# Test 2: Create via factory
from src.clients import ClientConfig, ClientFactory
config = ClientConfig(client_type="yourprovider")
client = ClientFactory.create(config)
print(client.get_model_name())

# Test 3: Direct instantiation
from src.clients import YourProviderClient
client = YourProviderClient(model_id="my-model", api_key="test")
print(client.get_model_name())
```

## Example Usage

```python
from src.clients import ClientFactory, ClientConfig

# Create config
config = ClientConfig(
    client_type="yourprovider",
    model_id="my-model",
    api_key="your-api-key"
)

# Create client via factory
client = ClientFactory.create(config)

# Use client
results = client.extract(
    text="Your input text here...",
    prompt_description="Extract entities and relationships"
)
```

## Key Principles

1. **from_config() handles defaults**: Don't put provider-specific logic in ClientConfig
2. **Use None for optional config fields**: Check `is not None` before applying defaults
3. **Consistent error handling**: Raise `LLMClientError` for client errors
4. **Document defaults in docstring**: Make clear what defaults are applied
5. **TYPE_CHECKING at top**: Place the `if TYPE_CHECKING:` block at the top with other imports
