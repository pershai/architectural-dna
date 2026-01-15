"""Tests for tool classes."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from tools import PatternTool, RepositoryTool, ScaffoldTool, StatsTool


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = Mock()
    client.add = Mock(return_value=None)
    client.query = Mock(return_value=[])
    client.get_collection = Mock()
    return client


@pytest.fixture
def test_config():
    """Create test configuration."""
    return {
        "llm": {
            "provider": "mock",
            "min_quality_score": 5
        },
        "github": {
            "excluded_repos": []
        },
        "scaffolding": {
            "output_dir": "./test_projects"
        }
    }


class TestPatternTool:
    """Tests for PatternTool class."""

    def test_initialization(self, mock_qdrant_client, test_config):
        """Test that PatternTool initializes correctly."""
        tool = PatternTool(mock_qdrant_client, "test_collection", test_config)
        assert tool.client == mock_qdrant_client
        assert tool.collection_name == "test_collection"
        assert tool.config == test_config

    def test_store_pattern_success(self, mock_qdrant_client, test_config):
        """Test storing a pattern successfully."""
        tool = PatternTool(mock_qdrant_client, "test_collection", test_config)

        result = tool.store_pattern(
            content="def hello(): pass",
            title="Test Pattern",
            description="A test pattern",
            category="utilities",
            language="python",
            quality_score=8
        )

        assert "[OK]" in result
        assert "Test Pattern" in result
        mock_qdrant_client.add.assert_called_once()

    def test_store_pattern_validation_error(self, mock_qdrant_client, test_config):
        """Test that invalid input returns error."""
        tool = PatternTool(mock_qdrant_client, "test_collection", test_config)

        result = tool.store_pattern(
            content="short",  # Too short
            title="Test",
            description="Description",
            category="utilities",
            language="python"
        )

        assert "[ERROR]" in result

    def test_search_dna_empty_results(self, mock_qdrant_client, test_config):
        """Test search with no results."""
        mock_qdrant_client.query.return_value = []
        tool = PatternTool(mock_qdrant_client, "test_collection", test_config)

        result = tool.search_dna(query="test query")

        assert "No matching patterns found" in result

    def test_search_dna_with_results(self, mock_qdrant_client, test_config):
        """Test search with results."""
        mock_result = Mock()
        mock_result.metadata = {
            "title": "Test Pattern",
            "language": "python",
            "category": "utilities",
            "quality_score": 8
        }
        mock_result.document = "def test(): pass"

        mock_qdrant_client.query.return_value = [mock_result]
        tool = PatternTool(mock_qdrant_client, "test_collection", test_config)

        result = tool.search_dna(query="test query")

        assert "Test Pattern" in result
        assert "python" in result


class TestRepositoryTool:
    """Tests for RepositoryTool class."""

    def test_initialization(self, mock_qdrant_client, test_config):
        """Test that RepositoryTool initializes correctly."""
        tool = RepositoryTool(mock_qdrant_client, "test_collection", test_config)
        assert tool.client == mock_qdrant_client

    @patch('tools.repository_tool.RepositoryTool.get_github_client')
    def test_list_my_repos_success(
            self,
            mock_get_client,
            mock_qdrant_client,
            test_config
    ):
        """Test listing repositories."""
        mock_repo = Mock()
        mock_repo.full_name = "user/repo"
        mock_repo.is_private = False
        mock_repo.language = "Python"
        mock_repo.default_branch = "main"
        mock_repo.description = "Test repo"

        mock_client = Mock()
        mock_client.list_repositories.return_value = [mock_repo]
        mock_get_client.return_value = mock_client

        tool = RepositoryTool(mock_qdrant_client, "test_collection", test_config)
        result = tool.list_my_repos()

        assert "user/repo" in result
        assert "Python" in result


class TestScaffoldTool:
    """Tests for ScaffoldTool class."""

    def test_initialization(self, mock_qdrant_client, test_config):
        """Test that ScaffoldTool initializes correctly."""
        tool = ScaffoldTool(mock_qdrant_client, "test_collection", test_config)
        assert tool.client == mock_qdrant_client


class TestStatsTool:
    """Tests for StatsTool class."""

    def test_initialization(self, mock_qdrant_client, test_config):
        """Test that StatsTool initializes correctly."""
        tool = StatsTool(mock_qdrant_client, "test_collection", test_config)
        assert tool.client == mock_qdrant_client

    def test_get_dna_stats_empty(self, mock_qdrant_client, test_config):
        """Test stats with empty DNA bank."""
        mock_info = Mock()
        mock_info.points_count = 0
        mock_qdrant_client.get_collection.return_value = mock_info

        tool = StatsTool(mock_qdrant_client, "test_collection", test_config)
        result = tool.get_dna_stats()

        assert "empty" in result.lower()
        assert "Get started" in result

    def test_get_dna_stats_with_data(self, mock_qdrant_client, test_config):
        """Test stats with populated DNA bank."""
        mock_info = Mock()
        mock_info.points_count = 42
        mock_qdrant_client.get_collection.return_value = mock_info

        mock_result = Mock()
        mock_result.metadata = {
            "language": "python",
            "category": "utilities",
            "source_repo": "user/repo"
        }
        mock_qdrant_client.query.return_value = [mock_result]

        tool = StatsTool(mock_qdrant_client, "test_collection", test_config)
        result = tool.get_dna_stats()

        assert "42" in result
        assert "python" in result


class TestBaseTool:
    """Tests for BaseTool dependency management."""

    def test_lazy_loading_github_client(self, mock_qdrant_client, test_config):
        """Test that GitHub client is lazy-loaded."""
        tool = PatternTool(mock_qdrant_client, "test_collection", test_config)
        assert tool._github_client is None

        # First call creates it
        with patch('tools.base.GitHubClient') as mock_gh:
            client1 = tool.get_github_client()
            assert mock_gh.called

            # Second call reuses it
            mock_gh.reset_mock()
            client2 = tool.get_github_client()
            assert not mock_gh.called
            assert client1 is client2

    def test_lazy_loading_llm_analyzer(self, mock_qdrant_client, test_config):
        """Test that LLM analyzer is lazy-loaded."""
        tool = PatternTool(mock_qdrant_client, "test_collection", test_config)
        assert tool._llm_analyzer is None

        with patch('tools.base.MockLLMAnalyzer') as mock_llm:
            analyzer = tool.get_llm_analyzer()
            assert mock_llm.called
