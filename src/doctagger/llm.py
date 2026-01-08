"""LLM integration supporting Ollama and OpenAI-compatible APIs (LM Studio, vLLM, etc.)."""

import json
import logging
from typing import Optional

import ollama
from openai import OpenAI

from .config import Config, LLMProvider, get_config
from .models import TaggingResult

logger = logging.getLogger(__name__)


class LLMTagger:
    """Uses LLM to tag and categorize documents. Supports Ollama and OpenAI-compatible APIs."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize LLM tagger."""
        self.config = config or get_config()
        self._ollama_client: Optional[ollama.Client] = None
        self._openai_client: Optional[OpenAI] = None

    @property
    def ollama_client(self) -> ollama.Client:
        """Lazy-load Ollama client."""
        if self._ollama_client is None:
            self._ollama_client = ollama.Client(host=self.config.llm.ollama_url)
        return self._ollama_client

    @property
    def openai_client(self) -> OpenAI:
        """Lazy-load OpenAI-compatible client (for LM Studio, vLLM, etc.)."""
        if self._openai_client is None:
            self._openai_client = OpenAI(
                base_url=self.config.llm.openai_base_url,
                api_key=self.config.llm.openai_api_key,
                timeout=self.config.llm.timeout,
            )
        return self._openai_client

    def get_default_prompt_template(self) -> str:
        """Get the default prompt template."""
        categories = ", ".join(self.config.tags.custom_categories)
        return f"""Analyze the following document and provide structured information about it.

Document text:
{{text}}

Provide a JSON response with the following fields:
- title: A concise, descriptive title for the document (max 100 chars)
- document_type: The type of document (choose from: {categories}, or "other")
- tags: An array of relevant keywords/tags (max {self.config.tags.max_tags} tags)
- summary: A brief 1-2 sentence summary of the document
- date: Any date mentioned in the document (format: YYYY-MM-DD) or null
- entities: An array of people, organizations, companies, or other named entities mentioned in the document (e.g., sender, recipient, account holder, company names). Include names exactly as they appear.
- confidence: Your confidence in this classification (0.0 to 1.0)

IMPORTANT: Respond ONLY with the raw JSON object. Do NOT wrap it in markdown code fences (```). Do NOT include any text before or after the JSON."""

    def create_prompt(
        self, text: str, max_chars: int = 8000, custom_template: Optional[str] = None
    ) -> str:
        """
        Create a prompt for the LLM.

        Args:
            text: Document text
            max_chars: Maximum characters to include
            custom_template: Optional custom prompt template (use {text} placeholder)

        Returns:
            Formatted prompt
        """
        # Truncate text if too long
        truncated_text = text[:max_chars] if len(text) > max_chars else text

        if custom_template:
            # Use custom template with {text} placeholder
            try:
                return custom_template.format(
                    text=truncated_text,
                    categories=", ".join(self.config.tags.custom_categories),
                    max_tags=self.config.tags.max_tags,
                )
            except KeyError as e:
                logger.warning(f"Invalid placeholder in custom template: {e}, using default")

        # Use default template
        categories = ", ".join(self.config.tags.custom_categories)

        prompt = f"""Analyze the following document and provide structured information about it.

Document text:
{truncated_text}

Provide a JSON response with the following fields:
- title: A concise, descriptive title for the document (max 100 chars)
- document_type: The type of document (choose from: {categories}, or "other")
- tags: An array of relevant keywords/tags (max {self.config.tags.max_tags} tags)
- summary: A brief 1-2 sentence summary of the document
- date: Any date mentioned in the document (format: YYYY-MM-DD) or null
- entities: An array of people, organizations, companies, or other named entities mentioned in the document (e.g., sender, recipient, account holder, company names). Include names exactly as they appear.
- confidence: Your confidence in this classification (0.0 to 1.0)

IMPORTANT: Respond ONLY with the raw JSON object. Do NOT wrap it in markdown code fences (```). Do NOT include any text before or after the JSON."""
- summary: A brief 1-2 sentence summary of the document
- date: Any date mentioned in the document (format: YYYY-MM-DD) or null
- confidence: Your confidence in this classification (0.0 to 1.0)

IMPORTANT: Respond ONLY with the raw JSON object. Do NOT wrap it in markdown code fences (```). Do NOT include any text before or after the JSON."""

        return prompt

    def parse_response(self, response_text: str) -> TaggingResult:
        """
        Parse LLM response into TaggingResult.

        Args:
            response_text: Raw response from LLM

        Returns:
            Parsed TaggingResult

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Clean up the response text
            cleaned = response_text.strip()
            
            # Remove markdown code fences if present (```json ... ``` or ``` ... ```)
            import re
            # Match ```json or ``` at start and ``` at end
            code_fence_pattern = r'^```(?:json)?\s*\n?(.*?)\n?```\s*$'
            match = re.match(code_fence_pattern, cleaned, re.DOTALL | re.IGNORECASE)
            if match:
                cleaned = match.group(1).strip()
            
            # Also handle case where there's text before/after code fences
            if '```' in cleaned:
                # Extract content between first ``` and last ```
                fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, re.DOTALL | re.IGNORECASE)
                if fence_match:
                    cleaned = fence_match.group(1).strip()
            
            # Try to find JSON in the response
            # Sometimes LLMs add extra text around the JSON
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                logger.error(f"No JSON object found in response: {response_text[:500]}")
                raise ValueError("No JSON found in response")

            json_str = cleaned[start_idx:end_idx]
            
            # Try to parse the JSON
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix common JSON issues
                # Remove trailing commas before } or ]
                fixed_json = re.sub(r',\s*([}\]])', r'\1', json_str)
                # Replace single quotes with double quotes (some LLMs do this)
                # Only if the JSON still fails to parse
                try:
                    data = json.loads(fixed_json)
                except json.JSONDecodeError:
                    # Last resort: try replacing single quotes
                    fixed_json = fixed_json.replace("'", '"')
                    data = json.loads(fixed_json)

            return TaggingResult(**data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text[:1000]}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Failed to create TaggingResult: {e}")
            logger.error(f"Response text: {response_text[:1000]}")
            raise ValueError(f"Invalid response format: {e}")

    def tag(self, text: str) -> TaggingResult:
        """
        Tag a document using the LLM.

        Args:
            text: Document text to analyze

        Returns:
            TaggingResult with extracted information

        Raises:
            RuntimeError: If tagging fails
        """
        logger.info(f"Sending document to LLM for tagging (provider: {self.config.llm.provider})")

        if not text.strip():
            logger.warning("Empty text provided for tagging")
            return TaggingResult(
                title="Untitled Document",
                document_type="other",
                tags=[],
                confidence=0.0,
            )

        try:
            prompt = self.create_prompt(text)

            if self.config.llm.provider == LLMProvider.OLLAMA:
                response_text = self._call_ollama(prompt)
            else:
                response_text = self._call_openai(prompt)

            logger.debug(f"LLM response: {response_text}")

            result = self.parse_response(response_text)

            # Filter tags based on confidence
            if result.confidence < self.config.tags.min_confidence:
                logger.warning(
                    f"Low confidence result: {result.confidence}, "
                    f"using fallback values"
                )

            logger.info(
                f"Tagging completed: {result.title} ({result.document_type}), "
                f"{len(result.tags)} tags"
            )

            return result

        except Exception as e:
            error_msg = f"LLM tagging failed: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API."""
        try:
            response = self.ollama_client.generate(
                model=self.config.llm.model,
                prompt=prompt,
                options={
                    "temperature": self.config.llm.temperature,
                    "num_predict": self.config.llm.max_tokens,
                },
            )
            return response.get("response", "")
        except ollama.ResponseError as e:
            raise RuntimeError(f"Ollama API error: {e}")

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI-compatible API (LM Studio, vLLM, etc.)."""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.llm.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a document analysis assistant. You MUST respond with valid JSON only. Never use markdown code fences (```). Never add explanatory text before or after the JSON.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
                response_format={"type": "text"},
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI-compatible API error: {e}")

    def check_availability(self) -> bool:
        """
        Check if the configured LLM provider is available.

        Returns:
            True if available, False otherwise
        """
        if self.config.llm.provider == LLMProvider.OLLAMA:
            return self._check_ollama_availability()
        else:
            return self._check_openai_availability()

    def _check_ollama_availability(self) -> bool:
        """Check if Ollama is available and the model exists."""
        try:
            models = self.ollama_client.list()
            model_names = [m.get("name", "") for m in models.get("models", [])]

            if self.config.llm.model not in model_names:
                logger.warning(
                    f"Model {self.config.llm.model} not found. "
                    f"Available models: {model_names}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False

    def _check_openai_availability(self) -> bool:
        """Check if OpenAI-compatible API (LM Studio) is available."""
        try:
            # Try to list models - LM Studio supports this endpoint
            models = self.openai_client.models.list()
            model_ids = [m.id for m in models.data]
            logger.info(f"Available models: {model_ids}")

            # Check if the configured model is available
            if model_ids and self.config.llm.model not in model_ids:
                logger.warning(
                    f"Model {self.config.llm.model} not in list. "
                    f"Available: {model_ids}. Will try anyway."
                )

            return True

        except Exception as e:
            logger.error(f"Failed to connect to OpenAI-compatible API: {e}")
            return False
