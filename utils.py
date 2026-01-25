"""Utility functions for the Architectural DNA system."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_json_from_llm_response(response_text: str) -> dict[str, Any] | None:
    """
    Parse JSON from LLM response, handling markdown code blocks.

    Many LLMs wrap JSON in markdown code blocks like ```json ... ```.
    This function strips those markers and parses the JSON.

    Args:
        response_text: The raw response text from the LLM

    Returns:
        Parsed JSON as a dictionary, or None if parsing fails

    Example:
        >>> parse_json_from_llm_response('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}
    """
    try:
        # Clean up response - remove markdown code blocks if present
        text = response_text.strip()

        # Remove opening code fence
        if text.startswith("```"):
            # Split by ``` and get the middle part
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                # Remove language identifier if present (e.g., "json")
                if text.startswith("json") or text.startswith("JSON"):
                    text = text[4:]

        # Remove closing code fence if still present
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # Parse JSON
        data = json.loads(text)
        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {e}")
        logger.debug(f"Response was: {response_text[:200]}...")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM response: {e}")
        return None
