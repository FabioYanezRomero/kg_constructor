"""LM Studio client using langextract for knowledge graph extraction."""

from __future__ import annotations

import dataclasses
from typing import Any

import langextract as lx
from langextract.providers.openai import OpenAILanguageModel
from langextract.core import types as core_types
from langextract.core import exceptions

from .base import BaseLLMClient, LLMClientError


@dataclasses.dataclass(init=False)
class LMStudioLanguageModel(OpenAILanguageModel):
    """Custom OpenAI-compatible model for LM Studio that doesn't use response_format.
    
    LM Studio rejects the response_format: json_object parameter that langextract's
    OpenAI provider sends. This subclass overrides the prompt processing to remove
    that parameter while keeping all other langextract functionality.
    """
    
    # Additional field for LM Studio
    timeout: int = 120

    def __init__(
        self,
        model_id: str = 'local-model',
        api_key: str | None = None,
        base_url: str | None = None,
        organization: str | None = None,
        temperature: float | None = None,
        max_workers: int = 5,
        timeout: int = 120,
        **kwargs,
    ) -> None:
        """Initialize LM Studio language model with JSON format type."""
        from langextract.core.data import FormatType
        
        # Initialize parent with JSON format type 
        super().__init__(
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            organization=organization,
            format_type=FormatType.JSON,
            temperature=temperature,
            max_workers=max_workers,
            **kwargs,
        )
        self.timeout = timeout

    @property
    def requires_fence_output(self) -> bool:
        """LM Studio doesn't use structured output, so we expect fenced JSON."""
        return True

    def _process_single_prompt(
        self, prompt: str, config: dict
    ) -> core_types.ScoredOutput:
        """Process a single prompt without sending response_format parameter."""
        try:
            normalized_config = self._normalize_reasoning_params(config)

            # System message for JSON output (without using response_format API param)
            system_message = (
                "You are a helpful assistant that extracts information into structured JSON. "
                "Follow the format shown in the examples precisely. "
                "Do not include any preamble or extra explanations."
            )

            messages = [{'role': 'user', 'content': prompt}]
            messages.insert(0, {'role': 'system', 'content': system_message})

            api_params = {
                'model': self.model_id,
                'messages': messages,
                'n': 1,
            }

            temp = normalized_config.get('temperature', self.temperature)
            if temp is not None:
                api_params['temperature'] = temp

            # DO NOT add response_format - LM Studio doesn't support it properly
            # The system message and fence_output will handle JSON parsing

            if (v := normalized_config.get('max_output_tokens')) is not None:
                api_params['max_tokens'] = v
            if (v := normalized_config.get('top_p')) is not None:
                api_params['top_p'] = v
            for key in [
                'frequency_penalty',
                'presence_penalty',
                'seed',
                'stop',
                'logprobs',
                'top_logprobs',
                'reasoning',
                # Explicitly exclude 'response_format' from being passed
            ]:
                if (v := normalized_config.get(key)) is not None:
                    api_params[key] = v

            response = self._client.chat.completions.create(**api_params)
            output_text = response.choices[0].message.content

            return core_types.ScoredOutput(score=1.0, output=output_text)

        except Exception as e:
            raise exceptions.InferenceRuntimeError(
                f'LM Studio API error: {str(e)}', original=e
            ) from e


class LMStudioClient(BaseLLMClient):
    """Client for LM Studio local models via langextract.

    LM Studio provides an OpenAI-compatible API, so we use langextract's
    OpenAI provider with a custom base URL.
    """

    def __init__(
        self,
        model_id: str = "local-model",
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        max_workers: int = 5,
        batch_length: int = 5,
        max_char_buffer: int = 8000,
        show_progress: bool = True,
        timeout: int = 120
    ) -> None:
        """Initialize LM Studio client.

        Args:
            model_id: Model identifier (use the model name from LM Studio)
            base_url: LM Studio server URL (default: http://localhost:1234/v1)
            api_key: API key (LM Studio uses "lm-studio" by default)
            max_workers: Maximum parallel workers (keep lower for local models)
            batch_length: Number of chunks per batch (keep lower for local)
            max_char_buffer: Maximum characters for inference
            show_progress: Whether to show progress bar
            timeout: Request timeout in seconds
        """
        self.model_id = model_id
        self.base_url = base_url
        self.api_key = api_key
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
        """Extract knowledge graph triples using LM Studio via langextract.

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
            # Use our custom LMStudioLanguageModel that removes response_format parameter
            lmstudio_model = LMStudioLanguageModel(
                model_id=self.model_id,
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )

            # Prepare langextract kwargs
            # LM Studio has limited OpenAI API compatibility
            langextract_kwargs = {
                "model": lmstudio_model,
                "temperature": temperature,
                "max_workers": self.max_workers,
                "batch_length": self.batch_length,
                "max_char_buffer": self.max_char_buffer,
                "show_progress": self.show_progress,
                "use_schema_constraints": False,  # LM Studio doesn't support JSON schema
                "fence_output": True,  # Expect JSON in code fences
                "fetch_urls": False,
            }

            if max_tokens:
                langextract_kwargs["language_model_params"] = {"max_tokens": max_tokens}

            langextract_kwargs.update(kwargs)

            # Perform extraction
            # Note: Don't pass format_type here - the `format_type` parameter we receive is a Pydantic model
            # for structured output, not the FormatType enum that langextract expects.
            # Our LMStudioLanguageModel already has format_type=FormatType.JSON configured.
            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt_description,
                examples=examples or [],
                **langextract_kwargs
            )

            # Extract triples from result
            triples = []
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if extraction.attributes:
                        # Start with attributes (contains head, relation, tail, interpretation/inference)
                        triple = dict(extraction.attributes)
                        
                        # Add source grounding information from langextract
                        if extraction.char_interval:
                            triple["char_start"] = extraction.char_interval.start_pos
                            triple["char_end"] = extraction.char_interval.end_pos
                        else:
                            triple["char_start"] = None
                            triple["char_end"] = None

                        # Add extraction metadata
                        triple["extraction_text"] = extraction.extraction_text
                        triple["extraction_class"] = extraction.extraction_class
                        
                        triples.append(triple)

            return triples

        except Exception as e:
            raise LLMClientError(f"LM Studio extraction failed: {e}") from e

    def get_model_name(self) -> str:
        """Return the LM Studio model identifier."""
        return f"lmstudio/{self.model_id}"

    def generate_json(
        self,
        text: str,
        prompt_description: str,
        format_type: type,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Generate structured JSON items directly using LM Studio.

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
        import re
        import requests

        try:
            # Build the prompt with schema
            schema_json = format_type.schema_json()
            full_prompt = f"""
{prompt_description}

Return the results as a JSON array of objects matching this schema:
{schema_json}

Input Text:
{text}

IMPORTANT: Respond with ONLY a valid JSON array. No markdown code blocks, no explanation, just the JSON array starting with [ and ending with ].
"""

            # Build request payload - don't use response_format as it's not universally supported
            payload = {
                "model": self.model_id,
                "messages": [
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": temperature if temperature is not None else 0.1,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens

            # Call LM Studio's OpenAI-compatible API
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not response_text:
                return []

            # Try to extract JSON from the response (handle markdown code blocks, etc.)
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                # Extract content between code blocks
                match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
                if match:
                    response_text = match.group(1).strip()
            
            # Find JSON array or object in the response
            json_match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', response_text)
            if json_match:
                response_text = json_match.group(1)

            # Parse the JSON response
            try:
                data = json.loads(response_text)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    # Some models might return {"items": [...]} or {"triples": [...]}
                    for key in ["items", "triples", "data", "results", "extractions"]:
                        if key in data and isinstance(data[key], list):
                            return data[key]
                    # Return as single-item list
                    return [data]
                return []
            except json.JSONDecodeError as e:
                raise LLMClientError(f"Failed to parse JSON response: {e}\nResponse text: {response_text[:500]}")

        except requests.RequestException as e:
            raise LLMClientError(f"LM Studio request failed: {e}") from e
        except Exception as e:
            raise LLMClientError(f"LM Studio JSON generation failed: {e}") from e

    def supports_structured_output(self) -> bool:
        """LM Studio generally doesn't support native structured output."""
        return False


__all__ = ["LMStudioClient"]
