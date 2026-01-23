"""LLM-powered code pattern analysis using Google Gemini."""

import logging
import os
import time

from google import genai
from google.genai import errors as genai_errors

from models import CodeChunk, PatternAnalysis, PatternCategory
from utils import parse_json_from_llm_response

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """Uses LLM to identify and describe code patterns."""

    ANALYSIS_PROMPT = """Analyze this code snippet and determine if it represents a reusable architectural pattern or best practice.

```{language}
{code}
```

Context (imports/package):
```
{context}
```

Source file: {file_path}

Respond with a JSON object (no markdown, just raw JSON):
{{
    "is_pattern": true or false,
    "title": "Short descriptive title (e.g., 'Repository Pattern with Caching')",
    "description": "1-2 sentences explaining what this pattern does and when to use it",
    "category": "architecture|error_handling|configuration|testing|api_design|data_access|security|logging|utilities|other",
    "quality_score": 1-10 (10 being production-ready, well-documented code),
    "use_cases": ["List of 2-3 specific scenarios where this pattern is useful"]
}}

Guidelines for determining if something is a pattern:
- IS a pattern: Reusable service classes, error handlers, configuration loaders, decorators, middleware, data access layers, test fixtures, utility functions with broad applicability
- NOT a pattern: Simple data classes/DTOs with no logic, trivial getters/setters, highly application-specific code, incomplete fragments

Be strict with quality_score:
- 1-3: Works but has issues (no docs, poor naming, anti-patterns)
- 4-6: Decent code that could be improved
- 7-8: Good, clean code with some documentation
- 9-10: Excellent, production-ready with good docs and error handling"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
        initial_retry_delay: float | None = None,
        max_retry_delay: float | None = None,
    ):
        """
        Initialize the LLM analyzer.

        Args:
            api_key: Gemini API key. If not provided, reads from GEMINI_API_KEY env var.
            model: Gemini model to use. If not provided, reads from GEMINI_MODEL env var
                   or defaults to gemini-2.0-flash.
            max_retries: Maximum number of retries for rate-limited requests.
            initial_retry_delay: Initial delay in seconds before first retry.
            max_retry_delay: Maximum delay in seconds between retries.
        """
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY environment variable "
                "or pass api_key to constructor."
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.max_retries = max_retries if max_retries is not None else 5
        self.initial_retry_delay = initial_retry_delay if initial_retry_delay is not None else 1.0
        self.max_retry_delay = max_retry_delay if max_retry_delay is not None else 60.0

    def analyze_chunk(self, chunk: CodeChunk) -> PatternAnalysis | None:
        """
        Analyze a code chunk to determine if it's a reusable pattern.

        Args:
            chunk: CodeChunk to analyze

        Returns:
            PatternAnalysis if analysis successful, None otherwise
        """
        prompt = self.ANALYSIS_PROMPT.format(
            language=chunk.language.value,
            code=chunk.content,
            context=chunk.context or "N/A",
            file_path=chunk.file_path,
        )

        delay = self.initial_retry_delay
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt
                )
                result = self._parse_response(response.text)
                return result
            except genai_errors.ClientError as e:
                # Check for rate limit errors (429)
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    last_error = e
                    if attempt < self.max_retries:
                        logger.warning(
                            "Rate limited (attempt %d/%d), waiting %.1fs before retry...",
                            attempt + 1,
                            self.max_retries + 1,
                            delay,
                        )
                        time.sleep(delay)
                        # Exponential backoff with cap
                        delay = min(delay * 2, self.max_retry_delay)
                        continue
                    else:
                        logger.error(
                            "Rate limit exceeded after %d attempts for chunk %s: %s",
                            self.max_retries + 1,
                            chunk.name,
                            e,
                        )
                        return None
                else:
                    # Non-rate-limit client error
                    logger.error(
                        "API client error analyzing chunk %s: %s", chunk.name, e
                    )
                    return None
            except Exception as e:
                logger.error("Error analyzing chunk %s: %s", chunk.name, e)
                return None

        # Should not reach here, but just in case
        logger.error(
            "Failed to analyze chunk %s after retries: %s", chunk.name, last_error
        )
        return None

    def analyze_chunks(
        self, chunks: list[CodeChunk], min_quality: int = 5
    ) -> list[tuple[CodeChunk, PatternAnalysis]]:
        """
        Analyze multiple chunks and filter by quality.

        Args:
            chunks: List of CodeChunks to analyze
            min_quality: Minimum quality score to include (1-10)

        Returns:
            List of (chunk, analysis) tuples for chunks that are patterns
        """
        results = []

        for i, chunk in enumerate(chunks):
            logger.debug(
                f"Analyzing chunk {i + 1}/{len(chunks)}: {chunk.name or 'unnamed'}..."
            )

            analysis = self.analyze_chunk(chunk)

            if (
                analysis
                and analysis.is_pattern
                and analysis.quality_score >= min_quality
            ):
                results.append((chunk, analysis))
                logger.info(
                    f"Found pattern: {analysis.title} (score: {analysis.quality_score})"
                )
            elif analysis:
                logger.debug(
                    f"Not a pattern or low quality (score: {analysis.quality_score})"
                )
            else:
                logger.warning(f"Analysis failed for chunk: {chunk.name or 'unnamed'}")

        return results

    def _parse_response(self, response_text: str) -> PatternAnalysis | None:
        """Parse the LLM response into a PatternAnalysis object."""
        data = parse_json_from_llm_response(response_text)
        if not data:
            return None

        try:
            # Map category string to enum
            category_str = data.get("category", "other").lower()
            try:
                category = PatternCategory(category_str)
            except ValueError:
                category = PatternCategory.OTHER

            return PatternAnalysis(
                is_pattern=data.get("is_pattern", False),
                title=data.get("title", "Untitled Pattern"),
                description=data.get("description", ""),
                category=category,
                quality_score=min(10, max(1, int(data.get("quality_score", 5)))),
                use_cases=data.get("use_cases", []),
            )
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to construct PatternAnalysis from data: {e}")
            return None


class MockLLMAnalyzer:
    """Mock analyzer for testing without API calls."""

    def analyze_chunk(self, chunk: CodeChunk) -> PatternAnalysis:
        """Return a mock analysis based on chunk characteristics."""
        # Simple heuristics for testing
        is_pattern = len(chunk.content) > 200 and chunk.chunk_type in (
            "class",
            "function",
        )

        return PatternAnalysis(
            is_pattern=is_pattern,
            title=f"Pattern from {chunk.name or 'code'}",
            description=f"A {chunk.chunk_type} extracted from {chunk.file_path}",
            category=PatternCategory.OTHER,
            quality_score=6 if is_pattern else 3,
            use_cases=["General use"],
        )

    def analyze_chunks(
        self, chunks: list[CodeChunk], min_quality: int = 5
    ) -> list[tuple[CodeChunk, PatternAnalysis]]:
        """Analyze chunks using mock logic."""
        results = []
        for chunk in chunks:
            analysis = self.analyze_chunk(chunk)
            if analysis.is_pattern and analysis.quality_score >= min_quality:
                results.append((chunk, analysis))
        return results
