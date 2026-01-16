# Adding an LLM Client

This skill documents how to add a new LLM client provider to `src/clients/`.

## Overview

LLM clients provide the interface between the extraction pipeline and language model APIs. The system provides:
- Factory pattern for client registration
- Abstract base class with required methods
- Configuration via `ClientConfig` dataclass

## Architecture

```
                          Clients Module
    ┌───────────────────────────────────────────────────────────┐
    │                                                           │
    │  __init__.py          base.py            config.py        │
    │  ├─ ClientFactory     ├─ BaseLLMClient   ├─ ClientConfig  │
    │  └─ get_client()      ├─ LLMClientError  └─ ClientType    │
    │                       └─ (ABC methods)                    │
    │                                                           │
    │  providers/                                               │
    │  ├─ gemini.py         ← Native SDK                        │
    │  ├─ ollama.py         ← OpenAI-compatible                 │
    │  └─ your_provider.py  ← Your new client                   │
    │                                                           │
    └───────────────────────────────────────────────────────────┘

Registration Flow:
  ClientFactory.register("name", YourClient) → ClientFactory.create(config)
```

## Dependencies

| Component | Library | Purpose |
|-----------|---------|---------|
| LLM framework | `langextract>=0.1` | Structured extraction |
| OpenAI-compatible | `openai>=1.0` | API client |
| HTTP | `requests>=2.28` | API calls |

## ClientConfig Schema

```python
@dataclass
class ClientConfig:
    client_type: ClientType = "gemini"
    model_id: str | None = None
    temperature: float = 0.0
    max_workers: int | None = None
    batch_length: int | None = None  # Chunks per batch
    max_char_buffer: int = 8000
    show_progress: bool = True
    api_key: str | None = None
    base_url: str | None = None
    timeout: int = 120
```

## Decision Tree

| Scenario | Pattern | Reference |
|----------|---------|-----------|
| OpenAI-compatible API | `openai` SDK | `ollama.py` |
| Native SDK | Provider's SDK | `gemini.py` |
| REST API only | `requests` | `ollama.py` |

## Step 1: Understand the Interface

All clients must implement `BaseLLMClient`:

```python
class BaseLLMClient(ABC):
    
    @abstractmethod
    def extract(self, text, prompt_description, examples=None, ...) -> list[dict]:
        """Extract with source grounding (char positions)."""
    
    @abstractmethod
    def generate_json(self, text, prompt_description, format_type, ...) -> list[dict]:
        """Generate JSON without char positions."""
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return model identifier."""
    
    @abstractmethod
    def supports_structured_output(self) -> bool:
        """Check if provider supports JSON mode."""
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: ClientConfig) -> BaseLLMClient:
        """Factory method."""
```

## Step 2: Implement Your Client

Create `src/clients/providers/groq.py`:

```python
"""Groq cloud inference client."""

from __future__ import annotations
import json
from typing import TYPE_CHECKING, Any
import langextract as lx
from langextract.providers.openai import OpenAILanguageModel
from ..base import BaseLLMClient, LLMClientError

if TYPE_CHECKING:
    from ..config import ClientConfig


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
    ) -> None:
        import os
        
        self.model_id = model_id
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.base_url = base_url
        self.max_workers = max_workers
        self.max_char_buffer = max_char_buffer
        self.show_progress = show_progress
        self.timeout = timeout
        
        if not self.api_key:
            raise LLMClientError("Groq API key required")
    
    def extract(
        self,
        text: str,
        prompt_description: str,
        examples: list[Any] | None = None,
        format_type: type | None = None,
        temperature: float = 0.0,
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
                temperature=temperature,
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
    
    def generate_json(
        self,
        text: str,
        prompt_description: str,
        format_type: type,
        temperature: float | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Generate JSON without char positions."""
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            
            response = client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": prompt_description},
                    {"role": "user", "content": text}
                ],
                temperature=temperature or 0.0,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(response.choices[0].message.content)
            return data if isinstance(data, list) else [data]
            
        except Exception as e:
            raise LLMClientError(f"Groq generation failed: {e}") from e
    
    def get_model_name(self) -> str:
        return f"groq/{self.model_id}"
    
    def supports_structured_output(self) -> bool:
        return True
    
    @classmethod
    def from_config(cls, config: "ClientConfig") -> "GroqClient":
        return cls(
            model_id=config.model_id or "llama-3.1-70b-versatile",
            api_key=config.api_key,
            base_url=config.base_url or "https://api.groq.com/openai/v1",
            max_workers=config.max_workers or 10,
            max_char_buffer=config.max_char_buffer,
            show_progress=config.show_progress,
            timeout=config.timeout,
        )
```

## Step 3: Register Client

Update `src/clients/__init__.py`:

```python
from .providers.groq import GroqClient
ClientFactory.register("groq", GroqClient)
```

Update `src/clients/config.py`:

```python
ClientType = Literal["gemini", "ollama", "lmstudio", "groq"]
```

## Step 4: Verify

### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.clients.providers.groq import GroqClient
from src.clients.base import LLMClientError


def test_client_from_config():
    from src.clients import ClientConfig
    
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


def test_get_model_name():
    client = GroqClient(api_key="test")
    assert client.get_model_name() == "groq/llama-3.1-70b-versatile"


@patch('src.clients.providers.groq.OpenAI')
def test_generate_json_success(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_response = Mock(choices=[Mock(message=Mock(content='{"head": "A"}'))])
    mock_client.chat.completions.create.return_value = mock_response
    
    client = GroqClient(api_key="test")
    result = client.generate_json("text", "desc", dict)
    
    assert result == [{"head": "A"}]


@patch('src.clients.providers.groq.OpenAI')
def test_generate_json_error(mock_openai):
    mock_openai.return_value.chat.completions.create.side_effect = Exception("API error")
    
    client = GroqClient(api_key="test")
    with pytest.raises(LLMClientError, match="failed"):
        client.generate_json("text", "desc", dict)
```

## Input/Output Examples

### Extract (with char positions)

```python
client.extract(
    text="PharmaCorp developed X-123.",
    prompt_description="Extract relationships"
)
# Output:
[{"head": "PharmaCorp", "relation": "developed", "tail": "X-123", 
  "char_start": 0, "char_end": 26}]
```

### Generate JSON (without char positions)

```python
client.generate_json(
    text="Alice knows Bob.",
    prompt_description="Generate bridging triples",
    format_type=Triple
)
# Output:
[{"head": "Alice", "relation": "connected_to", "tail": "Acme"}]
```

## CLI Usage

```bash
python -m src extract --input data.jsonl --domain legal --client groq
python -m src extract --input data.jsonl --client groq --model mixtral-8x7b
```

## Key Principles

| Principle | Implementation |
|-----------|---------------|
| **Exception Wrapping** | `raise LLMClientError(...) from e` |
| **Lazy Dependencies** | Import SDKs inside methods |
| **Provider Defaults** | Apply in `from_config()` |

## Verification Checklist

- [ ] Inherits from `BaseLLMClient`
- [ ] Implements all 5 abstract methods
- [ ] `from_config()` applies provider defaults
- [ ] All errors wrapped in `LLMClientError`
- [ ] Registered in `ClientFactory`
- [ ] Added to `ClientType` literal
- [ ] Tests cover factory, defaults, errors
