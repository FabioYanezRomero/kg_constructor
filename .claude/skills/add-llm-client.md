# Adding an LLM Client

This skill documents how to add a new LLM client provider to `kgb/clients/`.

## Overview

LLM clients provide the interface between the extraction pipeline and language model APIs. The system provides:
- Factory pattern with `@client()` decorator for auto-registration
- Abstract base class (`BaseLLMClient`) with required methods
- Configuration via `ClientConfig` dataclass
- Provider defaults via JSON config files

## Architecture

```
                          Clients Module
    ┌───────────────────────────────────────────────────────────┐
    │                                                           │
    │  base.py              config.py          factory.py       │
    │  ├─ BaseLLMClient     ├─ ClientConfig    ├─ ClientFactory │
    │  └─ LLMClientError    └─ ClientType      └─ @client()    │
    │                                                           │
    │  defaults.py                                              │
    │  └─ load_provider_defaults()  ← reads configs/*.json      │
    │                                                           │
    │  providers/                                               │
    │  ├─ gemini.py         ← Google Gemini (API-based)         │
    │  ├─ ollama.py         ← Ollama (local, OpenAI-compatible) │
    │  ├─ lmstudio.py       ← LM Studio (local, OpenAI-compat) │
    │  └─ your_provider.py  ← Your new client                  │
    │                                                           │
    │  configs/                                                 │
    │  ├─ gemini.json       ← Provider default values           │
    │  ├─ ollama.json                                           │
    │  ├─ lmstudio.json                                         │
    │  └─ your_provider.json                                    │
    │                                                           │
    └───────────────────────────────────────────────────────────┘

Registration Flow:
  @client("name") on class → ClientFactory.register() → ClientFactory.create(config)
```

## Dependencies

| Component | Library | Purpose |
|-----------|---------|---------|
| LLM framework | `langextract>=0.1` | Structured extraction with source grounding |
| OpenAI-compatible | `openai>=1.0` | API client for local servers |
| HTTP | `requests>=2.28` | Direct API calls |

## ClientConfig Schema

```python
@dataclass
class ClientConfig:
    client_type: ClientType = "gemini"      # str — no Literal constraint
    model_id: str | None = None             # None = use provider default
    temperature: float = 0.0
    max_workers: int | None = None
    max_char_buffer: int = 8000
    show_progress: bool = True
    extraction_passes: int = 1              # langextract passes
    batch_length: int | None = None         # langextract batch size
    api_key: str | None = None              # For API-based clients
    base_url: str | None = None             # For local server clients
    timeout: int = 120
```

## Decision Tree

| Scenario | Pattern | Reference |
|----------|---------|-----------|
| OpenAI-compatible API | `openai` SDK + langextract | `ollama.py`, `lmstudio.py` |
| Native SDK | Provider's SDK + langextract | `gemini.py` |
| REST API (augment) | `requests` or `openai` | All providers' `augment()` |

## Step 1: Understand the Interface

All clients must implement `BaseLLMClient` (defined in `kgb/clients/base.py`):

```python
class BaseLLMClient(ABC):

    @abstractmethod
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
        """Extract with source grounding (char positions via langextract)."""

    @abstractmethod
    def augment(
        self,
        text: str,
        prompt_description: str,
        format_type: type,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Generate inferred triples for graph augmentation.

        Unlike extract(), this does NOT ground in source text (no char positions).
        Used for high-level inference and bridging over an existing graph.
        """

    @classmethod
    @abstractmethod
    def from_config(cls, config: ClientConfig) -> BaseLLMClient:
        """Factory method to create client from configuration."""
```

### extract() vs augment()

| | `extract()` | `augment()` |
|---|---|---|
| **Purpose** | Extract triples grounded in source text | Generate inferred bridging triples |
| **Source grounding** | Yes — char_start/char_end positions | No — no position tracking |
| **Mechanism** | Uses langextract's full pipeline | Direct LLM call (no langextract) |
| **Inference type** | `InferenceType.EXPLICIT` | `InferenceType.CONTEXTUAL` |
| **Called by** | `builder/extraction.py` | `builder/augmentation.py` |

## Step 2: Create Provider Defaults

Create `kgb/clients/configs/groq.json`:

```json
{
  "model_id": "llama-3.1-70b-versatile",
  "base_url": "https://api.groq.com/openai/v1",
  "max_workers": 10
}
```

These defaults are loaded by `load_provider_defaults("groq")` when no explicit value is provided.

## Step 3: Implement Your Client

Create `kgb/clients/providers/groq.py`:

```python
"""Groq cloud inference client."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import langextract as lx
from langextract.providers.openai import OpenAILanguageModel

from ..base import BaseLLMClient, LLMClientError
from ..defaults import load_provider_defaults
from ..factory import client

if TYPE_CHECKING:
    from ..config import ClientConfig


@client("groq")
class GroqClient(BaseLLMClient):
    """Client for Groq cloud inference."""

    def __init__(
        self,
        model_id: str = "llama-3.1-70b-versatile",
        api_key: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
        max_workers: int = 10,
        max_char_buffer: int = 8000,
        show_progress: bool = True,
        timeout: int = 60,
        batch_length: int | None = None,
    ) -> None:
        import os

        self.model_id = model_id
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.base_url = base_url
        self.max_workers = max_workers
        self.max_char_buffer = max_char_buffer
        self.show_progress = show_progress
        self.timeout = timeout
        self.batch_length = batch_length

        if not self.api_key:
            raise LLMClientError("Groq API key required (set GROQ_API_KEY)")

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
        """Extract with source grounding using langextract."""
        try:
            groq_model = OpenAILanguageModel(
                model_id=self.model_id,
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )

            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt_description,
                examples=examples or [],
                model=groq_model,
                temperature=temperature or 0.0,
                max_workers=self.max_workers,
                max_char_buffer=self.max_char_buffer,
                show_progress=self.show_progress,
            )

            items = []
            if hasattr(result, 'extractions'):
                for extraction in result.extractions:
                    if extraction.attributes:
                        item = dict(extraction.attributes)
                        if extraction.char_interval:
                            item["char_start"] = extraction.char_interval.start_pos
                            item["char_end"] = extraction.char_interval.end_pos
                        items.append(item)

            return items

        except Exception as e:
            raise LLMClientError(f"Groq extraction failed: {e}") from e

    def augment(
        self,
        text: str,
        prompt_description: str,
        format_type: type,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Generate inferred triples without source grounding."""
        try:
            from openai import OpenAI

            oai = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )

            response = oai.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": prompt_description},
                    {"role": "user", "content": text}
                ],
                temperature=temperature or 0.0,
                response_format={"type": "json_object"}
            )

            raw = response.choices[0].message.content
            data = json.loads(raw)

            # Handle both list and nested object responses
            if isinstance(data, list):
                return data
            # Search for a list value in the response
            for value in data.values():
                if isinstance(value, list):
                    return value
            return [data]

        except Exception as e:
            raise LLMClientError(f"Groq augmentation failed: {e}") from e

    @classmethod
    def from_config(cls, config: "ClientConfig") -> "GroqClient":
        defaults = load_provider_defaults("groq")
        return cls(
            model_id=config.model_id or defaults.get("model_id", "llama-3.1-70b-versatile"),
            api_key=config.api_key,
            base_url=config.base_url or defaults.get("base_url", "https://api.groq.com/openai/v1"),
            max_workers=config.max_workers or defaults.get("max_workers", 10),
            max_char_buffer=config.max_char_buffer,
            show_progress=config.show_progress,
            timeout=config.timeout,
            batch_length=config.batch_length or defaults.get("batch_length"),
        )
```

## Step 4: Register Client

Import your provider in `kgb/clients/providers/__init__.py`:

```python
from .gemini import GeminiClient
from .ollama import OllamaClient
from .lmstudio import LMStudioClient
from .groq import GroqClient  # Add this

__all__ = [
    "GeminiClient",
    "OllamaClient",
    "LMStudioClient",
    "GroqClient",  # Add this
]
```

The `@client("groq")` decorator on the class handles factory registration automatically when the module is imported.

## Step 5: Verify

### Check Registration

```bash
python -c "from kgb.clients import ClientFactory; print(ClientFactory.get_available_clients())"
# Output: ['gemini', 'ollama', 'lmstudio', 'groq']
```

### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from kgb.clients.providers.groq import GroqClient
from kgb.clients.base import LLMClientError


def test_client_from_config():
    from kgb.clients import ClientConfig

    config = ClientConfig(
        client_type="groq",
        model_id="mixtral-8x7b",
        api_key="test-key"
    )
    client = GroqClient.from_config(config)

    assert client.model_id == "mixtral-8x7b"
    assert client.api_key == "test-key"


def test_missing_api_key():
    with pytest.raises(LLMClientError, match="API key required"):
        GroqClient(api_key=None)


def test_factory_creates_groq():
    from kgb.clients import ClientFactory, ClientConfig

    config = ClientConfig(client_type="groq", api_key="test-key")
    client = ClientFactory.create(config)
    assert isinstance(client, GroqClient)


@patch('kgb.clients.providers.groq.OpenAI')
def test_augment_success(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_response = Mock(choices=[Mock(message=Mock(content='[{"head": "A", "relation": "r", "tail": "B"}]'))])
    mock_client.chat.completions.create.return_value = mock_response

    client = GroqClient(api_key="test")
    result = client.augment("text", "desc", dict)

    assert result == [{"head": "A", "relation": "r", "tail": "B"}]


@patch('kgb.clients.providers.groq.OpenAI')
def test_augment_error(mock_openai):
    mock_openai.return_value.chat.completions.create.side_effect = Exception("API error")

    client = GroqClient(api_key="test")
    with pytest.raises(LLMClientError, match="failed"):
        client.augment("text", "desc", dict)
```

## Input/Output Examples

### extract() — with char positions (source grounded)

```python
client.extract(
    text="PharmaCorp developed X-123.",
    prompt_description="Extract relationships"
)
# Output:
[{"head": "PharmaCorp", "relation": "developed", "tail": "X-123",
  "char_start": 0, "char_end": 26}]
```

### augment() — without char positions (inferred)

```python
client.augment(
    text="<augmentation prompt with components>",
    prompt_description="Generate bridging triples to connect disconnected components",
    format_type=Triple
)
# Output:
[{"head": "Alice", "relation": "connected_to", "tail": "Acme",
  "inference": "contextual", "justification": "..."}]
```

## CLI Usage

```bash
kgb extract --input data.jsonl --domain legal --client groq
kgb extract --input data.jsonl --client groq --model mixtral-8x7b
kgb augment connectivity --input data.jsonl --domain legal --client groq
```

## Key Principles

| Principle | Implementation |
|-----------|---------------|
| **Exception Wrapping** | `raise LLMClientError(...) from e` |
| **Lazy Dependencies** | Import SDKs inside methods |
| **Provider Defaults** | JSON file in `configs/` + `load_provider_defaults()` |
| **Registration** | `@client("name")` decorator auto-registers with factory |

## Files to Create/Modify

| File | Action |
|------|--------|
| `kgb/clients/providers/groq.py` | Create — client implementation |
| `kgb/clients/configs/groq.json` | Create — provider defaults |
| `kgb/clients/providers/__init__.py` | Modify — add import |

## Verification Checklist

- [ ] Inherits from `BaseLLMClient`
- [ ] Implements `extract()`, `augment()`, `from_config()`
- [ ] Decorated with `@client("name")`
- [ ] Provider defaults JSON in `configs/`
- [ ] `from_config()` uses `load_provider_defaults()`
- [ ] All errors wrapped in `LLMClientError`
- [ ] Imported in `kgb/clients/providers/__init__.py`
- [ ] `augment()` handles varied JSON response structures
- [ ] Tests cover factory creation, defaults, errors
