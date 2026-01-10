"""Ollama client using langextract for knowledge graph extraction."""

from __future__ import annotations

from typing import Any

import langextract as lx
from langextract.providers.ollama import OllamaLanguageModel

from .base import BaseLLMClient, LLMClientError


class OllamaClient(BaseLLMClient):
    """Client for Ollama local models via langextract.

    This client uses langextract's Ollama provider to interact with
    locally hosted models for knowledge graph extraction.
    """

    def __init__(
        self,
        model_id: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        max_workers: int = 5,
        batch_length: int = 5,
        max_char_buffer: int = 8000,
        show_progress: bool = True,
        timeout: int = 120
    ) -> None:
        """Initialize Ollama client.

        Args:
            model_id: Ollama model name (e.g., "llama3.1", "mistral", "phi3")
            base_url: Ollama server URL
            max_workers: Maximum parallel workers (keep lower for local models)
            batch_length: Number of chunks per batch (keep lower for local)
            max_char_buffer: Maximum characters for inference
            show_progress: Whether to show progress bar
            timeout: Request timeout in seconds
        """
        self.model_id = model_id
        self.base_url = base_url
        self.max_workers = max_workers
        self.batch_length = batch_length
        self.max_char_buffer = max_char_buffer
        self.show_progress = show_progress
        self.timeout = timeout

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
        """Extract knowledge graph triples using Ollama via langextract.

        Args:
            text: Input text to analyze
            prompt_description: Extraction instructions
            examples: Few-shot examples (list of lx.ExampleData)
            format_type: Pydantic model for structured output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional langextract parameters

        Returns:
            List of extracted triples

        Raises:
            LLMClientError: If extraction fails
        """
        try:
            # Create Ollama language model
            ollama_model = OllamaLanguageModel(
                model_id=self.model_id,
                base_url=self.base_url,
                timeout=self.timeout
            )

            # Prepare langextract kwargs
            langextract_kwargs = {
                "model": ollama_model,
                "temperature": temperature,
                "max_workers": self.max_workers,
                "batch_length": self.batch_length,
                "max_char_buffer": self.max_char_buffer,
                "show_progress": self.show_progress,
                "use_schema_constraints": False,  # Ollama may not support schema
                "fence_output": True,  # Expect JSON in code fences
                "fetch_urls": False,
            }

            if max_tokens:
                langextract_kwargs["language_model_params"] = {"max_tokens": max_tokens}

            langextract_kwargs.update(kwargs)

            # Perform extraction
            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt_description,
                examples=examples or [],
                format_type=format_type,
                **langextract_kwargs
            )

            # Extract triples from result
            triples = []
            if hasattr(result, 'extractions'):
                for extraction in result.extractions:
                    if hasattr(extraction, 'data') and extraction.data:
                        triple_dict = extraction.data.model_dump()
                        triples.append(triple_dict)

            return triples

        except Exception as e:
            raise LLMClientError(f"Ollama extraction failed: {e}") from e

    def get_model_name(self) -> str:
        """Return the Ollama model identifier."""
        return f"ollama/{self.model_id}"

    def generate_json(
        self,
        text: str,
        prompt_description: str,
        format_type: type,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Generate structured JSON items directly using Ollama.

        This bypasses langextract to allow for unconstrained generation without
        the overhead of character-level source grounding. Used for bridging step.

        Args:
            text: Input text/prompt
            prompt_description: Instructions for generation
            format_type: Pydantic model for schema definition
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            List of dictionaries matching the requested schema
        """
        import json
        import requests

        try:
            # Build the prompt with schema
            schema_json = format_type.schema_json()
            full_prompt = f"""
{prompt_description}

Return the results as a JSON list of objects matching this JSON schema:
{schema_json}

Input Text:
{text}

Respond with ONLY valid JSON, no additional text or markdown.
"""

            # Call Ollama API directly
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_id,
                    "prompt": full_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": temperature if temperature is not None else 0.0,
                        **({"num_predict": max_tokens} if max_tokens else {}),
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            response_text = result.get("response", "")

            if not response_text:
                return []

            # Parse the JSON response with robust extraction
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            import re
            if response_text.startswith("```"):
                match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
                if match:
                    response_text = match.group(1).strip()
            
            # Find JSON array or object 
            json_match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', response_text)
            if json_match:
                response_text = json_match.group(1)
            
            try:
                data = json.loads(response_text)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    # Some models might return {"items": [...]} or {"triples": [...]}
                    for key in ["items", "triples", "data", "results", "extractions"]:
                        if key in data and isinstance(data[key], list):
                            return data[key]
                    return [data]
                return []
            except json.JSONDecodeError as e:
                raise LLMClientError(f"Failed to parse JSON response: {e}\nResponse text: {response_text[:500]}")

        except requests.RequestException as e:
            raise LLMClientError(f"Ollama request failed: {e}") from e
        except Exception as e:
            raise LLMClientError(f"Ollama JSON generation failed: {e}") from e

    def supports_structured_output(self) -> bool:
        """Ollama generally doesn't support native structured output."""
        return False


__all__ = ["OllamaClient"]
