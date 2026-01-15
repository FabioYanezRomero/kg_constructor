---
name: add-llm-client
description: Adds a new LLM client provider to the clients module. Use when implementing support for a new LLM provider like Anthropic, OpenAI, Groq, or any OpenAI-compatible API.
---

# Add LLM Client: New Provider Implementation

This skill guides you through adding a new LLM client provider to `src/clients`.

## Architecture Overview

```text
src/clients/
├── __init__.py          # ClientFactory registry + exports
├── base.py              # BaseLLMClient ABC + LLMClientError
├── config.py            # ClientConfig dataclass + ClientType
└── providers/
    ├── __init__.py      # Provider exports
    ├── gemini.py        # Google Gemini (native SDK)
    ├── ollama.py        # Ollama (OpenAI-compatible)
    └── lmstudio.py      # LM Studio (OpenAI-compatible)
```

---

## Step 1: Create the Provider File

Create `src/clients/providers/<provider_name>.py`:

```python
"""<ProviderName> client for knowledge graph extraction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..base import BaseLLMClient, LLMClientError

if TYPE_CHECKING:
    from ..config import ClientConfig


class <ProviderName>Client(BaseLLMClient):
    """Client for <ProviderName> LLM service."""

    def __init__(
        self,
        model_id: str = "default-model",
        api_key: str | None = None,
        base_url: str | None = None,
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
        """Extract with source grounding (char positions)."""
        # TODO: Implement with langextract integration
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
        # TODO: Implement JSON generation
        raise NotImplementedError

    def get_model_name(self) -> str:
        return f"<provider>/{self.model_id}"

    def supports_structured_output(self) -> bool:
        return False  # Set True if native JSON schema supported

    @classmethod
    def from_config(cls, config: ClientConfig) -> <ProviderName>Client:
        """Create from ClientConfig with provider-specific defaults."""
        return cls(
            model_id=config.model_id or "default-model",
            api_key=config.api_key,
            base_url=config.base_url or "http://localhost:8000",
            max_workers=config.max_workers if config.max_workers is not None else 5,
            max_char_buffer=config.max_char_buffer,
            show_progress=config.show_progress,
            timeout=config.timeout,
        )


__all__ = ["<ProviderName>Client"]
```

---

## Step 2: Update providers/__init__.py

```python
from .<provider_name> import <ProviderName>Client

__all__ = [
    # ... existing clients
    "<ProviderName>Client",
]
```

---

## Step 3: Register in ClientFactory

Update `src/clients/__init__.py`:

```python
from .providers import <ProviderName>Client

ClientFactory.register("<provider_name>", <ProviderName>Client)
```

---

## Step 4: Update ClientType

Add to `src/clients/config.py`:

```python
ClientType = Literal["gemini", "ollama", "lmstudio", "<provider_name>"]
```

---

## Step 5: Verify Registration

```python
from src.clients import ClientFactory, ClientConfig

# Check available clients
print(ClientFactory.get_available_clients())

# Create via factory
config = ClientConfig(client_type="<provider_name>", model_id="my-model")
client = ClientFactory.create(config)
print(client.get_model_name())
```

---

## Required Abstract Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `extract()` | Source-grounded extraction (char positions) | `list[dict]` |
| `generate_json()` | Structured JSON generation (no grounding) | `list[dict]` |
| `get_model_name()` | Model identifier for logging | `str` |
| `supports_structured_output()` | Native JSON schema support | `bool` |
| `from_config()` | Factory method | `BaseLLMClient` |

> [!NOTE]
> `BaseLLMClient` uses `abc.ABC` with `@abstractmethod`. Missing implementations raise `TypeError` at instantiation.

---

## Decision Tree

| Scenario | Reference Implementation |
|----------|-------------------------|
| OpenAI-compatible API | `ollama.py`, `lmstudio.py` |
| Native SDK | `gemini.py` |
| Needs structured output | Check provider docs for JSON mode |

---

## CLI Integration

Once registered, your client is automatically available in the CLI:

```bash
python -m src.extract_cli extract --input data.jsonl --domain legal --client <provider_name>
```

---

## Error Handling

Always raise `LLMClientError` for API failures:

```python
from ..base import LLMClientError

try:
    response = api.generate(...)
except SomeAPIError as e:
    raise LLMClientError(f"<Provider> API error: {e}") from e
```

---

## Key Principles

1. **`from_config()` handles defaults** - Don't put provider logic in `ClientConfig`
2. **Check None explicitly** - Use `is not None` for optional fields
3. **Raise `LLMClientError`** - Consistent error handling
4. **Document defaults in docstring** - Make clear what defaults are applied
5. **TYPE_CHECKING at top** - Import `ClientConfig` inside `TYPE_CHECKING` block
