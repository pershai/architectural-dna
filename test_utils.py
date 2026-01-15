"""Tests for utility functions."""

import pytest
from utils import parse_json_from_llm_response


class TestParseJsonFromLLMResponse:
    """Tests for JSON parsing from LLM responses."""

    def test_parse_plain_json(self):
        """Test parsing plain JSON without markdown."""
        response = '{"key": "value", "number": 42}'
        result = parse_json_from_llm_response(response)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_markdown_fences(self):
        """Test parsing JSON wrapped in markdown code fences."""
        response = '```json\n{"key": "value"}\n```'
        result = parse_json_from_llm_response(response)
        assert result == {"key": "value"}

    def test_parse_json_with_uppercase_json_marker(self):
        """Test parsing JSON with uppercase JSON marker."""
        response = '```JSON\n{"key": "value"}\n```'
        result = parse_json_from_llm_response(response)
        assert result == {"key": "value"}

    def test_parse_json_without_language_marker(self):
        """Test parsing JSON in code fences without language marker."""
        response = '```\n{"key": "value"}\n```'
        result = parse_json_from_llm_response(response)
        assert result == {"key": "value"}

    def test_parse_complex_json(self):
        """Test parsing complex nested JSON."""
        response = '''```json
        {
            "is_pattern": true,
            "title": "Test Pattern",
            "category": "architecture",
            "quality_score": 8,
            "use_cases": ["case1", "case2"]
        }
        ```'''
        result = parse_json_from_llm_response(response)
        assert result["is_pattern"] is True
        assert result["title"] == "Test Pattern"
        assert result["category"] == "architecture"
        assert result["quality_score"] == 8
        assert len(result["use_cases"]) == 2

    def test_parse_invalid_json_returns_none(self):
        """Test that invalid JSON returns None."""
        response = '{"key": invalid}'
        result = parse_json_from_llm_response(response)
        assert result is None

    def test_parse_empty_string_returns_none(self):
        """Test that empty string returns None."""
        response = ''
        result = parse_json_from_llm_response(response)
        assert result is None

    def test_parse_non_json_returns_none(self):
        """Test that non-JSON text returns None."""
        response = 'This is not JSON at all'
        result = parse_json_from_llm_response(response)
        assert result is None

    def test_parse_json_with_whitespace(self):
        """Test parsing JSON with extra whitespace."""
        response = '''

        ```json
        {"key": "value"}
        ```

        '''
        result = parse_json_from_llm_response(response)
        assert result == {"key": "value"}
