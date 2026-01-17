---
name: add-llm-client
description: Adds a new LLM client provider to the clients module. Use when implementing support for a new LLM provider like Anthropic, OpenAI, Groq, or any OpenAI-compatible API.
---

# Add LLM Client: New Provider

This skill guides you through adding a new LLM client provider to `src/clients/`.

## Architecture Overview

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
    │  ├─ gemini.py         ← Native SDK (google-generativeai)  │
    │  ├─ ollama.py         ← OpenAI-compatible local           │
    │  ├─ lmstudio.py       ← OpenAI-compatible local           │
    │  └─ your_provider.py  ← Your new client                   │
    │                                                           │
    └───────────────────────────────────────────────────────────┘

Registration Flow:
  ClientFactory.register("name", YourClient) → ClientFactory.create(config)
```

**Key Files:**
- [base.py](file:///app/src/clients/base.py) - Abstract base class and exceptions
- [config.py](file:///app/src/clients/config.py) - ClientConfig dataclass
- [__init__.py](file:///app/src/clients/__init__.py) - ClientFactory registry

## Dependencies

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Base client | `abc` (stdlib) | - | Abstract base class |
| LLM framework | `langextract>=0.1` | Latest | Structured extraction |
| OpenAI-compatible | `openai>=1.0` | Latest | API client |
| Gemini | `google-generativeai>=0.3` | Latest | Google SDK |
| HTTP | `requests>=2.28` | Latest | API calls |
| Progress | `tqdm>=4.60` | Latest | Progress bars |

---

## ClientConfig Schema

The configuration dataclass used by all clients:

```python
@dataclass
class ClientConfig:
    """Configuration for LLM clients.
    
    Attributes:
        client_type: Provider identifier ("gemini", "ollama", "lmstudio")
        model_id: Model identifier (provider-specific, None = use default)
        api_key: API key for authenticated providers
        base_url: Base URL for local servers
        max_workers: Concurrent request limit
        batch_length: Chunks per batch (lower for local models)
        max_char_buffer: Maximum text chunk size
        show_progress: Display progress bars
        timeout: Request timeout in seconds
    """
    client_type: ClientType = "gemini"
    model_id: str | None = None
    temperature: float = 0.0
    max_workers: int | None = None
    batch_length: int | None = None
    max_char_buffer: int = 8000
    show_progress: bool = True
    api_key: str | None = None
    base_url: str | None = None
    timeout: int = 120
```

---

## Decision Tree

| Scenario | Use This Pattern | Reference |
|----------|-----------------|-----------|
| OpenAI-compatible API (Ollama, LM Studio, vLLM) | `openai` SDK | `ollama.py` |
| Native SDK (Gemini, Anthropic, Cohere) | Provider's Python SDK | `gemini.py` |
| REST API only | `requests` library | `ollama.py` (generate_json) |

---

## Step 1: Understand the Interface

All clients must implement `BaseLLMClient`:

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
        """Extract with source grounding (char positions)."""
        pass
    
    @abstractmethod
    def generate_json(
        self,
        text: str,
        prompt_description: str,
        format_type: type,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Generate JSON without char positions (for augmentation)."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return model identifier (e.g., 'ollama/llama3.1')."""
        pass
    
    @abstractmethod
    def supports_structured_output(self) -> bool:
        """Check if provider supports JSON mode."""
        pass
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: ClientConfig) -> BaseLLMClient:
        """Factory method for CLI integration."""
        pass
```

---

## Step 2: Implement Your Client

Create `src/clients/providers/groq.py`:

```python
"""Groq cloud inference client implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import langextract as lx
from langextract.providers.openai import OpenAILanguageModel

from ..base import BaseLLMClient, LLMClientError

if TYPE_CHECKING:
    from ..config import ClientConfig


class GroqClient(BaseLLMClient):
    """Client for Groq cloud inference.
    
    Groq provides ultra-fast inference for open models like Llama and Mixtral.
    Uses OpenAI-compatible API.
    """
    
    def __init__(
        self,
        model_id: str = "llama-3.1-70b-versatile",
        api_key: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
        max_workers: int = 10,
        batch_length: int = 10,
        max_char_buffer: int = 8000,
        show_progress: bool = True,
        timeout: int = 60,
    ) -> None:
        """Initialize Groq client.
        
        Args:
            model_id: Groq model name (e.g., "llama-3.1-70b-versatile")
            api_key: Groq API key (GROQ_API_KEY env var)
            base_url: Groq API base URL
            max_workers: Parallel workers (higher for cloud)
            batch_length: Chunks per batch
            max_char_buffer: Maximum characters per chunk
            show_progress: Display progress bars
            timeout: Request timeout seconds
        """
        import os
        
        self.model_id = model_id
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.base_url = base_url
        self.max_workers = max_workers
        self.batch_length = batch_length
        self.max_char_buffer = max_char_buffer
        self.show_progress = show_progress
        self.timeout = timeout
        
        if not self.api_key:
            raise LLMClientError(
                "Groq API key required. Set GROQ_API_KEY env var or pass api_key."
            )
    
    def extract(
        self,
        text: str,
        prompt_description: str,
        examples: list[Any] | None = None,
        format_type: type | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Extract with source grounding using langextract.
        
        Args:
            text: Input text to analyze
            prompt_description: Extraction instructions
            examples: Few-shot examples (lx.ExampleData format)
            format_type: Pydantic model for schema
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum output tokens
            
        Returns:
            List of extracted items with char_start/char_end positions
            
        Raises:
            LLMClientError: If extraction fails
        """
        try:
            # Create langextract language model
            groq_model = OpenAILanguageModel(
                model_id=self.model_id,
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            
            # Configure langextract extraction
            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt_description,
                examples=examples or [],
                model=groq_model,
                temperature=temperature,
                max_workers=self.max_workers,
                batch_length=self.batch_length,
                max_char_buffer=self.max_char_buffer,
                show_progress=self.show_progress,
                use_schema_constraints=False,
                fence_output=False,  # Groq supports JSON mode
                fetch_urls=False,
            )
            
            # Extract items from result
            items = []
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    attrs = extraction.attributes
                    if attrs is None:
                        continue
                    
                    item = dict(attrs)
                    
                    # Add source grounding
                    if extraction.char_interval:
                        item["char_start"] = extraction.char_interval.start_pos
                        item["char_end"] = extraction.char_interval.end_pos
                    else:
                        item["char_start"] = None
                        item["char_end"] = None
                    
                    item["extraction_text"] = str(extraction.extraction_text)
                    
                    # Validate required fields present
                    if all(k in item for k in ('head', 'relation', 'tail')):
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
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Generate JSON without char positions.
        
        Used for augmentation step where source grounding isn't needed.
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            
            schema_json = format_type.model_json_schema()
            
            response = client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system",
                        "content": f"{prompt_description}\n\nReturn JSON matching: {json.dumps(schema_json)}"
                    },
                    {"role": "user", "content": text}
                ],
                temperature=temperature or 0.0,
                max_tokens=max_tokens or 4000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Normalize to list
            if isinstance(data, dict):
                for key in ["items", "triples", "results"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
            
            return data if isinstance(data, list) else []
            
        except Exception as e:
            raise LLMClientError(f"Groq generation failed: {e}") from e
    
    def get_model_name(self) -> str:
        return f"groq/{self.model_id}"
    
    def supports_structured_output(self) -> bool:
        return True  # Groq supports JSON mode
    
    @classmethod
    def from_config(cls, config: "ClientConfig") -> "GroqClient":
        """Create from ClientConfig.
        
        Applies Groq-specific defaults:
        - model_id: "llama-3.1-70b-versatile"
        - max_workers: 10 (cloud can handle more)
        """
        return cls(
            model_id=config.model_id or "llama-3.1-70b-versatile",
            api_key=config.api_key,
            base_url=config.base_url or "https://api.groq.com/openai/v1",
            max_workers=config.max_workers if config.max_workers is not None else 10,
            batch_length=config.batch_length if config.batch_length is not None else 10,
            max_char_buffer=config.max_char_buffer,
            show_progress=config.show_progress,
            timeout=config.timeout,
        )


__all__ = ["GroqClient"]
```

---

## Step 3: Register in ClientFactory

Update `src/clients/__init__.py`:

```python
from .providers.groq import GroqClient

# Register new client
ClientFactory.register("groq", GroqClient)
```

Update `src/clients/config.py` to add the type:

```python
ClientType = Literal["gemini", "ollama", "lmstudio", "groq"]
```

---

## Step 4: Verification

### 4.1 Check Registration

```bash
python -c "from src.clients import ClientFactory; print(ClientFactory.get_available_clients())"
# Output: ['gemini', 'ollama', 'lmstudio', 'groq']
```

### 4.2 Unit Tests

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.clients import ClientFactory, ClientConfig
from src.clients.providers.groq import GroqClient
from src.clients.base import LLMClientError


def test_client_registered():
    """Verify client appears in registry."""
    assert "groq" in ClientFactory.get_available_clients()


def test_client_from_config():
    """Test factory method creates client correctly."""
    config = ClientConfig(
        client_type="groq",
        model_id="mixtral-8x7b-32768",
        api_key="test-key",
        timeout=30
    )
    
    client = GroqClient.from_config(config)
    
    assert client.model_id == "mixtral-8x7b-32768"
    assert client.api_key == "test-key"
    assert client.timeout == 30


def test_client_defaults():
    """Test default values are applied."""
    config = ClientConfig(client_type="groq", api_key="test")
    client = GroqClient.from_config(config)
    
    assert client.model_id == "llama-3.1-70b-versatile"
    assert client.max_workers == 10
    assert client.base_url == "https://api.groq.com/openai/v1"


def test_missing_api_key():
    """Test error when API key missing."""
    with pytest.raises(LLMClientError, match="API key required"):
        GroqClient(api_key=None)


def test_get_model_name():
    """Test model name formatting."""
    client = GroqClient(model_id="llama2", api_key="test")
    assert client.get_model_name() == "groq/llama2"


def test_supports_structured_output():
    """Test structured output detection."""
    client = GroqClient(api_key="test")
    assert client.supports_structured_output() is True


@patch('src.clients.providers.groq.OpenAI')
def test_generate_json_success(mock_openai_class):
    """Test successful JSON generation."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content='{"head": "A", "relation": "r", "tail": "B"}'))]
    mock_client.chat.completions.create.return_value = mock_response
    
    client = GroqClient(api_key="test")
    result = client.generate_json(
        text="Test text",
        prompt_description="Extract",
        format_type=dict
    )
    
    assert result == [{"head": "A", "relation": "r", "tail": "B"}]


@patch('src.clients.providers.groq.OpenAI')
def test_generate_json_api_error(mock_openai_class):
    """Test API error handling."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = Exception("API timeout")
    
    client = GroqClient(api_key="test")
    
    with pytest.raises(LLMClientError, match="generation failed"):
        client.generate_json(
            text="Test",
            prompt_description="Extract",
            format_type=dict
        )
```

---

## Input/Output Examples

### Extract Method (with char positions)

**Input:**
```python
client.extract(
    text="PharmaCorp developed X-123 drug in 2024.",
    prompt_description="Extract company-product relationships",
    examples=[...],  # Few-shot examples
    temperature=0.0
)
```

**Output:**
```python
[
    {
        "head": "PharmaCorp",
        "relation": "developed",
        "tail": "X-123",
        "inference": "explicit",
        "char_start": 0,
        "char_end": 26,
        "extraction_text": "PharmaCorp developed X-123"
    }
]
```

### Generate JSON Method (without char positions)

**Input:**
```python
client.generate_json(
    text="Alice knows Bob. Bob works at Acme.",
    prompt_description="Generate bridging triples",
    format_type=Triple
)
```

**Output:**
```python
[
    {
        "head": "Alice",
        "relation": "connected_to",
        "tail": "Acme",
        "inference": "contextual"
    }
]
```

---

## CLI Usage

```bash
# Use your new client
python -m src extract --input data.jsonl --domain legal --client groq

# With custom model
python -m src extract --input data.jsonl --domain legal --client groq --model mixtral-8x7b-32768

# With API key
python -m src extract --input data.jsonl --domain legal --client groq --api-key sk-xxx
```

---

## Key Principles

| Principle | Implementation | Example |
|-----------|---------------|---------|
| **Exception Wrapping** | Wrap all errors in `LLMClientError` | `raise LLMClientError(...) from e` |
| **Lazy Dependencies** | Import SDKs inside methods | `from openai import OpenAI` |
| **Provider Defaults** | Apply in `from_config()` | `model_id or "llama3.1"` |
| **Model Name Format** | Use `provider/model` pattern | `"groq/llama-3.1-70b"` |

---

## Error Handling Reference

| Exception | When | Action |
|-----------|------|--------|
| `LLMClientError` | API failure, timeout, parse error | Wrap with context |
| `ImportError` | Missing SDK | Catch and raise with install hint |

### Catching Client Errors

```python
from src.clients import ClientFactory, ClientConfig
from src.clients.base import LLMClientError

try:
    config = ClientConfig(client_type="groq", api_key="test")
    client = ClientFactory.create(config)
    result = client.extract(text="...", prompt_description="...")
except LLMClientError as e:
    print(f"Client error: {e}")
    # Handle gracefully
```

---

## Verification Checklist

Before submitting, verify your client:

- [ ] Inherits from `BaseLLMClient`
- [ ] Implements all 5 abstract methods
- [ ] `from_config()` applies provider defaults
- [ ] All errors wrapped in `LLMClientError`
- [ ] Lazy imports for SDK dependencies
- [ ] Registered in `ClientFactory`
- [ ] Added to `ClientType` literal
- [ ] Tests cover factory, defaults, errors
- [ ] CLI works: `python -m src extract --client name`
