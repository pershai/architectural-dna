"""Tests for LLMAnalyzer and MockLLMAnalyzer."""

from unittest.mock import MagicMock, patch

import pytest

from llm_analyzer import LLMAnalyzer, MockLLMAnalyzer
from models import CodeChunk, Language, PatternAnalysis, PatternCategory


class TestMockLLMAnalyzer:
    """Tests for MockLLMAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        return MockLLMAnalyzer()

    @pytest.fixture
    def class_chunk(self):
        return CodeChunk(
            content='''class UserService:
    """Service for user operations."""

    def __init__(self, repository):
        self.repository = repository

    def get_user(self, user_id):
        return self.repository.find_by_id(user_id)

    def create_user(self, data):
        user = User(**data)
        return self.repository.save(user)
''',
            file_path="services/user_service.py",
            language=Language.PYTHON,
            start_line=1,
            end_line=15,
            chunk_type="class",
            name="UserService",
        )

    @pytest.fixture
    def small_chunk(self):
        return CodeChunk(
            content="x = 1",
            file_path="small.py",
            language=Language.PYTHON,
            start_line=1,
            end_line=1,
            chunk_type="statement",
            name="assignment",
        )

    def test_analyze_chunk_class_is_pattern(self, analyzer, class_chunk):
        """Test that a class chunk is identified as a pattern."""
        analysis = analyzer.analyze_chunk(class_chunk)

        assert analysis is not None
        assert analysis.is_pattern is True
        assert analysis.quality_score >= 5
        assert "UserService" in analysis.title

    def test_analyze_chunk_small_not_pattern(self, analyzer, small_chunk):
        """Test that a small chunk is not a pattern."""
        analysis = analyzer.analyze_chunk(small_chunk)

        assert analysis is not None
        assert analysis.is_pattern is False
        assert analysis.quality_score < 5

    def test_analyze_chunks_filters_by_quality(
        self, analyzer, class_chunk, small_chunk
    ):
        """Test that analyze_chunks filters by quality."""
        chunks = [class_chunk, small_chunk]

        results = analyzer.analyze_chunks(chunks, min_quality=5)

        # Only the class chunk should pass
        assert len(results) == 1
        chunk, analysis = results[0]
        assert chunk.name == "UserService"

    def test_analyze_chunks_empty_list(self, analyzer):
        """Test analyzing empty list."""
        results = analyzer.analyze_chunks([])
        assert results == []

    def test_analyze_chunk_returns_pattern_analysis(self, analyzer, class_chunk):
        """Test that analyze_chunk returns PatternAnalysis."""
        analysis = analyzer.analyze_chunk(class_chunk)

        assert isinstance(analysis, PatternAnalysis)
        assert analysis.category == PatternCategory.OTHER
        assert len(analysis.use_cases) > 0


class TestLLMAnalyzer:
    """Tests for LLMAnalyzer class."""

    def test_init_requires_api_key(self):
        """Test that initialization requires API key."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="Gemini API key required"),
        ):
            LLMAnalyzer()

    def test_init_with_api_key_param(self):
        """Test initialization with API key parameter."""
        with patch("llm_analyzer.genai") as mock_genai:
            analyzer = LLMAnalyzer(api_key="test-key")

            mock_genai.Client.assert_called_once_with(api_key="test-key")
            assert analyzer.model == "gemini-2.0-flash"

    def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": "env-key"}),
            patch("llm_analyzer.genai") as mock_genai,
        ):
            LLMAnalyzer()

            mock_genai.Client.assert_called_once_with(api_key="env-key")

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        with patch("llm_analyzer.genai"):
            analyzer = LLMAnalyzer(api_key="test-key", model="gemini-1.5-pro")

            assert analyzer.model == "gemini-1.5-pro"

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        with patch("llm_analyzer.genai"):
            analyzer = LLMAnalyzer(api_key="test-key")

        response = """{
    "is_pattern": true,
    "title": "Repository Pattern",
    "description": "Data access abstraction layer",
    "category": "data_access",
    "quality_score": 8,
    "use_cases": ["Database operations", "Testing"]
}"""
        result = analyzer._parse_response(response)

        assert result is not None
        assert result.is_pattern is True
        assert result.title == "Repository Pattern"
        assert result.category == PatternCategory.DATA_ACCESS
        assert result.quality_score == 8
        assert len(result.use_cases) == 2

    def test_parse_response_with_markdown(self):
        """Test parsing JSON wrapped in markdown."""
        with patch("llm_analyzer.genai"):
            analyzer = LLMAnalyzer(api_key="test-key")

        response = """```json
{
    "is_pattern": true,
    "title": "Service Pattern",
    "description": "Business logic encapsulation",
    "category": "architecture",
    "quality_score": 7,
    "use_cases": ["Service layer"]
}
```"""
        result = analyzer._parse_response(response)

        assert result is not None
        assert result.title == "Service Pattern"
        assert result.category == PatternCategory.ARCHITECTURE

    def test_parse_response_invalid_json(self):
        """Test parsing invalid JSON."""
        with patch("llm_analyzer.genai"):
            analyzer = LLMAnalyzer(api_key="test-key")

        result = analyzer._parse_response("not valid json")

        assert result is None

    def test_parse_response_unknown_category(self):
        """Test parsing response with unknown category."""
        with patch("llm_analyzer.genai"):
            analyzer = LLMAnalyzer(api_key="test-key")

        response = """{
    "is_pattern": true,
    "title": "Test Pattern",
    "description": "Test",
    "category": "unknown_category",
    "quality_score": 5,
    "use_cases": []
}"""
        result = analyzer._parse_response(response)

        assert result is not None
        assert result.category == PatternCategory.OTHER

    def test_parse_response_clamps_quality_score(self):
        """Test that quality score is clamped to 1-10."""
        with patch("llm_analyzer.genai"):
            analyzer = LLMAnalyzer(api_key="test-key")

        # Test high score
        response_high = '{"is_pattern": true, "title": "T", "description": "D", "category": "other", "quality_score": 100, "use_cases": []}'
        result = analyzer._parse_response(response_high)
        assert result.quality_score == 10

        # Test low score
        response_low = '{"is_pattern": true, "title": "T", "description": "D", "category": "other", "quality_score": -5, "use_cases": []}'
        result = analyzer._parse_response(response_low)
        assert result.quality_score == 1

    def test_analyze_chunk_success(self):
        """Test successful chunk analysis."""
        with patch("llm_analyzer.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = '{"is_pattern": true, "title": "Test", "description": "Desc", "category": "utilities", "quality_score": 7, "use_cases": ["Use"]}'
            mock_client.models.generate_content.return_value = mock_response

            analyzer = LLMAnalyzer(api_key="test-key")
            chunk = CodeChunk(
                content="def test(): pass",
                file_path="test.py",
                language=Language.PYTHON,
                start_line=1,
                end_line=1,
                chunk_type="function",
                name="test",
            )

            result = analyzer.analyze_chunk(chunk)

            assert result is not None
            assert result.title == "Test"
            mock_client.models.generate_content.assert_called_once()

    def test_analyze_chunk_api_error(self):
        """Test chunk analysis handles API errors."""
        with patch("llm_analyzer.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.side_effect = Exception("API Error")

            analyzer = LLMAnalyzer(api_key="test-key")
            chunk = CodeChunk(
                content="def test(): pass",
                file_path="test.py",
                language=Language.PYTHON,
                start_line=1,
                end_line=1,
                chunk_type="function",
                name="test",
            )

            result = analyzer.analyze_chunk(chunk)

            assert result is None

    def test_analyze_chunks_filters_results(self):
        """Test analyze_chunks filters by pattern and quality."""
        with patch("llm_analyzer.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            # Different responses for different calls
            responses = [
                '{"is_pattern": true, "title": "Good", "description": "D", "category": "utilities", "quality_score": 8, "use_cases": []}',
                '{"is_pattern": false, "title": "Not Pattern", "description": "D", "category": "other", "quality_score": 5, "use_cases": []}',
                '{"is_pattern": true, "title": "Low Quality", "description": "D", "category": "other", "quality_score": 3, "use_cases": []}',
            ]
            mock_responses = [MagicMock(text=r) for r in responses]
            mock_client.models.generate_content.side_effect = mock_responses

            analyzer = LLMAnalyzer(api_key="test-key")
            chunks = [
                CodeChunk(
                    content="code1",
                    file_path="a.py",
                    language=Language.PYTHON,
                    start_line=1,
                    end_line=1,
                    chunk_type="function",
                    name="a",
                ),
                CodeChunk(
                    content="code2",
                    file_path="b.py",
                    language=Language.PYTHON,
                    start_line=1,
                    end_line=1,
                    chunk_type="function",
                    name="b",
                ),
                CodeChunk(
                    content="code3",
                    file_path="c.py",
                    language=Language.PYTHON,
                    start_line=1,
                    end_line=1,
                    chunk_type="function",
                    name="c",
                ),
            ]

            results = analyzer.analyze_chunks(chunks, min_quality=5)

            # Only the first chunk should pass (is_pattern=true and quality >= 5)
            assert len(results) == 1
            assert results[0][1].title == "Good"

    def test_analysis_prompt_format(self):
        """Test that analysis prompt is properly formatted."""
        with patch("llm_analyzer.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = '{"is_pattern": false, "title": "T", "description": "D", "category": "other", "quality_score": 5, "use_cases": []}'
            mock_client.models.generate_content.return_value = mock_response

            analyzer = LLMAnalyzer(api_key="test-key")
            chunk = CodeChunk(
                content="def test(): pass",
                file_path="myfile.py",
                language=Language.PYTHON,
                start_line=1,
                end_line=1,
                chunk_type="function",
                name="test",
                context="import os",
            )

            analyzer.analyze_chunk(chunk)

            # Verify the prompt was constructed correctly
            call_args = mock_client.models.generate_content.call_args
            prompt = call_args.kwargs["contents"]

            assert "python" in prompt
            assert "def test(): pass" in prompt
            assert "myfile.py" in prompt
            assert "import os" in prompt
