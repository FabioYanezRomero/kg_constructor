---
name: add-llm-client
description: Adds a new LLM client provider to the clients module. Use when implementing support for a new LLM provider like Anthropic, OpenAI, Groq, or any OpenAI-compatible API.
---

# Add LLM Client Skill

This skill guides you through adding a new LLM client provider to the `src/clients` module.

## When to use this skill

- Adding support for a new LLM provider (e.g., Anthropic, OpenAI, Groq)
- Implementing a new local model server client
- Creating a wrapper for an OpenAI-compatible API

## Overview

The clients module uses a registry-based factory pattern:
1. Each client inherits from `BaseLLMClient` (which uses `abc.ABC` with `@abstractmethod`)
2. Implements required abstract methods
3. Provides `from_config()` classmethod for factory instantiation
4. Gets registered in `__init__.py`

## Step-by-step guide

### Step 1: Create the provider file

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
        # TODO: Implement extraction logic
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

### Step 2: Update providers/__init__.py

```python
from .<provider_name> import <ProviderName>Client
# Add to __all__ list
```

### Step 3: Register in clients/__init__.py

```python
from .providers import <ProviderName>Client
ClientFactory.register("<provider_name>", <ProviderName>Client)
# Add to __all__ list
```

### Step 4: Update ClientType in config.py

```python
ClientType = Literal["gemini", "ollama", "lmstudio", "<provider_name>"]
```

### Step 5: Test your client

```python
# Verify registration
from src.clients import ClientFactory
print(ClientFactory.get_available_clients())

# Create via factory
from src.clients import ClientConfig, ClientFactory
config = ClientConfig(client_type="<provider_name>")
client = ClientFactory.create(config)
print(client.get_model_name())
```

## Required abstract methods

| Method | Purpose |
|--------|---------|
| `extract()` | Extract with source grounding (char positions) |
| `generate_json()` | Generate structured JSON (no grounding) |
| `get_model_name()` | Return model identifier string |
| `supports_structured_output()` | Whether native JSON schema is supported |
| `from_config()` | Create instance from ClientConfig |

> **Note:** `BaseLLMClient` uses `abc.ABC` with `@abstractmethod` decorators. Missing implementations will raise `TypeError` at instantiation.

## Example usage

```python
from src.clients import ClientFactory, ClientConfig

config = ClientConfig(client_type="yourprovider", model_id="my-model")
client = ClientFactory.create(config)
results = client.extract(text="...", prompt_description="Extract entities")
```

## Key principles

1. **from_config() handles defaults** - Don't put provider logic in ClientConfig
2. **Check None explicitly** - Use `is not None` for optional fields
3. **Raise LLMClientError** - Consistent error handling
4. **Document defaults in docstring** - Make clear what defaults are applied
5. **TYPE_CHECKING at top** - Place import block at top of file, not bottom

## Decision tree

- **OpenAI-compatible API?** → Look at `ollama.py` or `lmstudio.py` for patterns
- **Native SDK available?** → Look at `gemini.py` for patterns
- **Need source grounding?** → Use langextract integration in `extract()`
