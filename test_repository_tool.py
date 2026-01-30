"""Tests for RepositoryTool."""

from unittest.mock import Mock, patch

import pytest

from constants import LARGE_REPO_THRESHOLD
from models import Language, PatternCategory
from tools.repository_tool import RepositoryTool


class TestRepositoryTool:
    """Tests for RepositoryTool class."""

    @pytest.fixture
    def mock_qdrant_client(self):
        return Mock()

    @pytest.fixture
    def test_config(self):
        return {
            "github": {"excluded_repos": ["test/excluded"]},
            "llm": {"min_quality_score": 5},
        }

    @pytest.fixture
    def tool(self, mock_qdrant_client, test_config):
        return RepositoryTool(mock_qdrant_client, "test_collection", test_config)

    @pytest.fixture
    def tool_with_batch(self, mock_qdrant_client, test_config):
        mock_batch = Mock()
        return RepositoryTool(
            mock_qdrant_client, "test_collection", test_config, mock_batch
        )

    # ==========================================================================
    # list_my_repos tests
    # ==========================================================================

    def test_list_my_repos_success(self, tool):
        """Test listing repositories successfully."""
        mock_repo1 = Mock()
        mock_repo1.full_name = "user/repo1"
        mock_repo1.is_private = False
        mock_repo1.language = "Python"
        mock_repo1.default_branch = "main"
        mock_repo1.description = "Test repo 1"

        mock_repo2 = Mock()
        mock_repo2.full_name = "user/repo2"
        mock_repo2.is_private = True
        mock_repo2.language = "Java"
        mock_repo2.default_branch = "master"
        mock_repo2.description = None

        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.list_repositories.return_value = [mock_repo1, mock_repo2]
            mock_gh.return_value = mock_client

            result = tool.list_my_repos()

            assert "Found 2 repositories" in result
            assert "user/repo1" in result
            assert "[PUBLIC]" in result
            assert "user/repo2" in result
            assert "[PRIVATE]" in result
            assert "Python" in result
            assert "Java" in result

    def test_list_my_repos_empty(self, tool):
        """Test listing when no repositories found."""
        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.list_repositories.return_value = []
            mock_gh.return_value = mock_client

            result = tool.list_my_repos()

            assert "No repositories found" in result

    def test_list_my_repos_auth_error(self, tool):
        """Test handling authentication errors."""
        with patch.object(tool, "get_github_client") as mock_gh:
            mock_gh.side_effect = ValueError("Invalid token")

            result = tool.list_my_repos()

            assert "[ERROR]" in result
            assert "authentication failed" in result

    def test_list_my_repos_general_error(self, tool):
        """Test handling general errors."""
        with patch.object(tool, "get_github_client") as mock_gh:
            mock_gh.side_effect = Exception("Network error")

            result = tool.list_my_repos()

            assert "[ERROR]" in result
            assert "Error listing repositories" in result

    def test_list_my_repos_with_filters(self, tool):
        """Test listing with include filters."""
        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.list_repositories.return_value = []
            mock_gh.return_value = mock_client

            tool.list_my_repos(include_private=False, include_orgs=False)

            mock_client.list_repositories.assert_called_once_with(
                include_private=False,
                include_orgs=False,
                excluded_patterns=["test/excluded"],
            )

    # ==========================================================================
    # sync_github_repo tests
    # ==========================================================================

    def test_sync_github_repo_no_code_files(self, tool):
        """Test syncing repo with no code files."""
        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = []
            mock_gh.return_value = mock_client

            result = tool.sync_github_repo("user/repo")

            assert "No code files found" in result

    def test_sync_github_repo_no_chunks_extracted(self, tool):
        """Test syncing repo with files but no extractable chunks."""
        mock_file = Mock()
        mock_file.path = "test.py"

        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = [mock_file]
            mock_client.get_file_content.return_value = "x = 1"  # Too short
            mock_client.get_language.return_value = Language.PYTHON
            mock_gh.return_value = mock_client

            with patch.object(tool, "get_pattern_extractor") as mock_extractor:
                mock_ext = Mock()
                mock_ext.extract_chunks.return_value = []
                mock_extractor.return_value = mock_ext

                result = tool.sync_github_repo("user/repo")

                assert "No code patterns extracted" in result

    def test_sync_github_repo_without_llm(self, tool, mock_qdrant_client):
        """Test syncing repo without LLM analysis."""
        mock_file = Mock()
        mock_file.path = "test.py"

        mock_chunk = Mock()
        mock_chunk.content = "def test(): pass"
        mock_chunk.file_path = "test.py"
        mock_chunk.language = Language.PYTHON
        mock_chunk.chunk_type = "function"
        mock_chunk.name = "test"

        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = [mock_file]
            mock_client.get_file_content.return_value = "def test(): pass"
            mock_client.get_language.return_value = Language.PYTHON
            mock_gh.return_value = mock_client

            with patch.object(tool, "get_pattern_extractor") as mock_extractor:
                mock_ext = Mock()
                mock_ext.extract_chunks.return_value = [mock_chunk]
                mock_extractor.return_value = mock_ext

                result = tool.sync_github_repo("user/repo", analyze_patterns=False)

                assert "[OK]" in result
                assert "Successfully synced" in result
                assert "LLM analysis: No" in result
                mock_qdrant_client.add.assert_called()

    def test_sync_github_repo_with_llm(self, tool, mock_qdrant_client):
        """Test syncing repo with LLM analysis."""
        mock_file = Mock()
        mock_file.path = "service.py"

        mock_chunk = Mock()
        mock_chunk.content = "class UserService: pass"
        mock_chunk.file_path = "service.py"
        mock_chunk.language = Language.PYTHON
        mock_chunk.chunk_type = "class"
        mock_chunk.name = "UserService"

        mock_analysis = Mock()
        mock_analysis.title = "User Service Pattern"
        mock_analysis.description = "A service for users"
        mock_analysis.category = PatternCategory.ARCHITECTURE
        mock_analysis.quality_score = 8
        mock_analysis.use_cases = ["User management"]

        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = [mock_file]
            mock_client.get_file_content.return_value = "class UserService: pass"
            mock_client.get_language.return_value = Language.PYTHON
            mock_gh.return_value = mock_client

            with patch.object(tool, "get_pattern_extractor") as mock_extractor:
                mock_ext = Mock()
                mock_ext.extract_chunks.return_value = [mock_chunk]
                mock_extractor.return_value = mock_ext

                with patch.object(tool, "get_llm_analyzer") as mock_llm:
                    mock_analyzer = Mock()
                    mock_analyzer.analyze_chunks.return_value = [
                        (mock_chunk, mock_analysis)
                    ]
                    mock_llm.return_value = mock_analyzer

                    result = tool.sync_github_repo("user/repo", analyze_patterns=True)

                    assert "[OK]" in result
                    assert "LLM analysis: Yes" in result

    def test_sync_github_repo_llm_fallback_on_error(self, tool, mock_qdrant_client):
        """Test fallback to non-LLM when LLM fails."""
        mock_file = Mock()
        mock_file.path = "test.py"

        mock_chunk = Mock()
        mock_chunk.content = "def test(): pass"
        mock_chunk.file_path = "test.py"
        mock_chunk.language = Language.PYTHON
        mock_chunk.chunk_type = "function"
        mock_chunk.name = "test"

        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = [mock_file]
            mock_client.get_file_content.return_value = "def test(): pass"
            mock_client.get_language.return_value = Language.PYTHON
            mock_gh.return_value = mock_client

            with patch.object(tool, "get_pattern_extractor") as mock_extractor:
                mock_ext = Mock()
                mock_ext.extract_chunks.return_value = [mock_chunk]
                mock_extractor.return_value = mock_ext

                with patch.object(tool, "get_llm_analyzer") as mock_llm:
                    mock_llm.side_effect = Exception("LLM API error")

                    result = tool.sync_github_repo("user/repo", analyze_patterns=True)

                    assert "[OK]" in result
                    assert "LLM analysis: No" in result

    def test_sync_github_repo_auth_error(self, tool):
        """Test sync with authentication error."""
        with patch.object(tool, "get_github_client") as mock_gh:
            mock_gh.side_effect = ValueError("Invalid token")

            result = tool.sync_github_repo("user/repo")

            assert "[ERROR]" in result
            assert "authentication failed" in result

    def test_sync_github_repo_general_error(self, tool):
        """Test sync with general error."""
        with patch.object(tool, "get_github_client") as mock_gh:
            mock_gh.side_effect = Exception("Network error")

            result = tool.sync_github_repo("user/repo")

            assert "[ERROR]" in result
            assert "Error syncing repository" in result

    def test_sync_github_repo_store_pattern_error(self, tool, mock_qdrant_client):
        """Test handling store errors for individual patterns."""
        mock_file = Mock()
        mock_file.path = "test.py"

        mock_chunk = Mock()
        mock_chunk.content = "def test(): pass"
        mock_chunk.file_path = "test.py"
        mock_chunk.language = Language.PYTHON
        mock_chunk.chunk_type = "function"
        mock_chunk.name = "test"

        # First call succeeds, second fails
        mock_qdrant_client.add.side_effect = [None, Exception("Store error")]

        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = [mock_file, mock_file]
            mock_client.get_file_content.return_value = "def test(): pass"
            mock_client.get_language.return_value = Language.PYTHON
            mock_gh.return_value = mock_client

            with patch.object(tool, "get_pattern_extractor") as mock_extractor:
                mock_ext = Mock()
                mock_ext.extract_chunks.return_value = [mock_chunk]
                mock_extractor.return_value = mock_ext

                result = tool.sync_github_repo("user/repo", analyze_patterns=False)

                # Should continue despite one error
                assert "[OK]" in result

    def test_sync_github_repo_empty_file_content(self, tool):
        """Test sync with empty file content."""
        mock_file = Mock()
        mock_file.path = "empty.py"

        with patch.object(tool, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = [mock_file]
            mock_client.get_file_content.return_value = None  # Empty content
            mock_gh.return_value = mock_client

            with patch.object(tool, "get_pattern_extractor") as mock_extractor:
                mock_ext = Mock()
                mock_ext.extract_chunks.return_value = []
                mock_extractor.return_value = mock_ext

                result = tool.sync_github_repo("user/repo")

                assert "No code patterns extracted" in result

    # ==========================================================================
    # Batch processor auto-delegation tests
    # ==========================================================================

    def test_sync_large_repo_uses_batch_processor(self, tool_with_batch):
        """Test that large repos automatically use batch processor."""
        # Create more files than the threshold
        mock_files = [
            Mock(path=f"file{i}.py") for i in range(LARGE_REPO_THRESHOLD + 10)
        ]

        with patch.object(tool_with_batch, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = mock_files
            mock_gh.return_value = mock_client

            # Mock batch processor
            mock_config = Mock()
            tool_with_batch._batch_processor._get_default_batch_config.return_value = (
                mock_config
            )
            tool_with_batch._batch_processor.batch_sync_repo.return_value = (
                "[OK] Batch synced"
            )

            result = tool_with_batch.sync_github_repo("user/large-repo")

            # Should have delegated to batch processor
            tool_with_batch._batch_processor.batch_sync_repo.assert_called_once()
            assert "[OK]" in result

    def test_sync_small_repo_does_not_use_batch(
        self, tool_with_batch, mock_qdrant_client
    ):
        """Test that small repos don't use batch processor."""
        # Create fewer files than the threshold
        mock_files = [Mock(path=f"file{i}.py") for i in range(5)]

        mock_chunk = Mock()
        mock_chunk.content = "def test(): pass\n" * 10
        mock_chunk.file_path = "test.py"
        mock_chunk.language = Language.PYTHON
        mock_chunk.chunk_type = "function"
        mock_chunk.name = "test"

        with patch.object(tool_with_batch, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = mock_files
            mock_client.get_file_content.return_value = "def test(): pass\n" * 10
            mock_client.get_language.return_value = Language.PYTHON
            mock_gh.return_value = mock_client

            with patch.object(tool_with_batch, "get_pattern_extractor") as mock_ext:
                mock_extractor = Mock()
                mock_extractor.extract_chunks.return_value = [mock_chunk]
                mock_ext.return_value = mock_extractor

                result = tool_with_batch.sync_github_repo(
                    "user/small-repo", analyze_patterns=False
                )

                # Should NOT have called batch processor
                tool_with_batch._batch_processor.batch_sync_repo.assert_not_called()
                assert "[OK]" in result

    def test_set_batch_processor(self, tool):
        """Test setting batch processor after init."""
        assert tool._batch_processor is None

        mock_batch = Mock()
        tool.set_batch_processor(mock_batch)

        assert tool._batch_processor == mock_batch
