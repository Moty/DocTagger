"""LLM integration using Ollama."""

import json
import logging
from typing import Optional

import ollama

from .config import Config, get_config
from .models import TaggingResult

logger = logging.getLogger(__name__)


class LLMTagger:
    """Uses Ollama LLM to tag and categorize documents."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize LLM tagger."""
        self.config = config or get_config()
        self.client = ollama.Client(host=self.config.ollama.url)

    def create_prompt(self, text: str, max_chars: int = 8000) -> str:
        """
        Create a prompt for the LLM.

        Args:
            text: Document text
            max_chars: Maximum characters to include

        Returns:
            Formatted prompt
        """
        # Truncate text if too long
        truncated_text = text[:max_chars] if len(text) > max_chars else text

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
- confidence: Your confidence in this classification (0.0 to 1.0)

Respond ONLY with valid JSON, no additional text."""

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
            # Try to find JSON in the response
            # Sometimes LLMs add extra text around the JSON
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)

            return TaggingResult(**data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Failed to create TaggingResult: {e}")
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
        logger.info("Sending document to LLM for tagging")

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

            response = self.client.generate(
                model=self.config.ollama.model,
                prompt=prompt,
                options={
                    "temperature": self.config.ollama.temperature,
                    "num_predict": 500,  # Limit response length
                },
            )

            response_text = response.get("response", "")
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

        except ollama.ResponseError as e:
            error_msg = f"Ollama API error: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"LLM tagging failed: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def check_availability(self) -> bool:
        """
        Check if Ollama is available and the model exists.

        Returns:
            True if available, False otherwise
        """
        try:
            # Try to list models
            models = self.client.list()
            model_names = [m.get("name", "") for m in models.get("models", [])]

            if self.config.ollama.model not in model_names:
                logger.warning(
                    f"Model {self.config.ollama.model} not found. "
                    f"Available models: {model_names}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False
