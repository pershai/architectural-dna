"""Unit tests for BatchProcessor with mocks."""

import tempfile
from unittest.mock import Mock, patch

import pytest

from models import Language
from tools.batch_processor import BatchConfig, BatchProcessor, BatchProgress


class TestBatchProgress:
    """Tests for BatchProgress dataclass."""

    def test_progress_percent_zero_files(self):
        """Test progress percentage with zero total files."""
        progress = BatchProgress(repo_name="test/repo")
        assert progress.progress_percent == 0.0

    def test_progress_percent_calculation(self):
        """Test progress percentage calculation."""
        progress = BatchProgress(repo_name="test/repo")
        progress.total_files = 100
        progress.processed_files = 25
        assert progress.progress_percent == 25.0

    def test_elapsed_seconds(self):
        """Test elapsed seconds calculation."""
        progress = BatchProgress(repo_name="test/repo")
        # Should be small since just created
        assert progress.elapsed_seconds >= 0

    def test_estimated_remaining_zero_processed(self):
        """Test estimated remaining with zero processed."""
        progress = BatchProgress(repo_name="test/repo")
        progress.total_files = 100
        progress.processed_files = 0
        assert progress.estimated_remaining_seconds == 0.0

    def test_estimated_remaining_calculation(self):
        """Test estimated remaining calculation."""
        progress = BatchProgress(repo_name="test/repo")
        progress.total_files = 100
        progress.processed_files = 50
        # Should return a positive estimate
        remaining = progress.estimated_remaining_seconds
        assert remaining >= 0

    def test_to_dict_serialization(self):
        """Test serialization to dict."""
        progress = BatchProgress(repo_name="test/repo")
        progress.total_files = 100
        progress.processed_files = 25
        progress.total_chunks = 50
        progress.stored_patterns = 10
        progress.failed_files = ["file1.py"]
        progress.current_file = "file2.py"

        data = progress.to_dict()

        assert data["repo_name"] == "test/repo"
        assert data["total_files"] == 100
        assert data["processed_files"] == 25
        assert data["total_chunks"] == 50
        assert data["stored_patterns"] == 10
        assert data["failed_files"] == ["file1.py"]
        assert data["current_file"] == "file2.py"
        assert "progress_percent" in data
        assert "elapsed_seconds" in data
        assert "started_at" in data
        assert "last_updated" in data

    def test_from_dict_deserialization(self):
        """Test deserialization from dict."""
        data = {
            "repo_name": "user/repo",
            "total_files": 50,
            "processed_files": 20,
            "total_chunks": 30,
            "stored_patterns": 15,
            "failed_files": ["bad.py"],
            "current_file": "good.py",
            "started_at": "2024-01-15T10:00:00",
            "last_updated": "2024-01-15T10:05:00",
        }

        progress = BatchProgress.from_dict(data)

        assert progress.repo_name == "user/repo"
        assert progress.total_files == 50
        assert progress.processed_files == 20
        assert progress.total_chunks == 30
        assert progress.stored_patterns == 15
        assert progress.failed_files == ["bad.py"]
        assert progress.current_file == "good.py"

    def test_from_dict_minimal(self):
        """Test deserialization with minimal data."""
        data = {"repo_name": "minimal/repo"}

        progress = BatchProgress.from_dict(data)

        assert progress.repo_name == "minimal/repo"
        assert progress.total_files == 0
        assert progress.processed_files == 0


class TestBatchConfig:
    """Tests for BatchConfig dataclass."""

    def test_default_values(self):
        """Test default config values."""
        config = BatchConfig()

        assert config.batch_size == 10
        assert config.delay_between_batches == 0.5
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.save_progress is True
        assert config.progress_dir == ".batch_progress"
        assert config.analyze_patterns is True
        assert config.min_quality == 5

    def test_custom_values(self):
        """Test custom config values."""
        config = BatchConfig(
            batch_size=20,
            delay_between_batches=1.0,
            max_retries=5,
            analyze_patterns=False,
            min_quality=3,
        )

        assert config.batch_size == 20
        assert config.delay_between_batches == 1.0
        assert config.max_retries == 5
        assert config.analyze_patterns is False
        assert config.min_quality == 3


class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    @pytest.fixture
    def mock_qdrant_client(self):
        return Mock()

    @pytest.fixture
    def test_config(self):
        return {
            "batch": {
                "batch_size": 10,
                "delay_between_batches": 0.1,
                "max_retries": 2,
                "progress_dir": ".test_batch_progress",
            },
            "llm": {"provider": "mock", "min_quality_score": 5},
        }

    @pytest.fixture
    def processor(self, mock_qdrant_client, test_config):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config["batch"]["progress_dir"] = tmpdir
            yield BatchProcessor(mock_qdrant_client, "test_collection", test_config)

    # ==========================================================================
    # Initialization tests
    # ==========================================================================

    def test_initialization(self, mock_qdrant_client, test_config):
        """Test processor initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config["batch"]["progress_dir"] = tmpdir
            processor = BatchProcessor(
                mock_qdrant_client, "test_collection", test_config
            )

            assert processor.collection_name == "test_collection"
            assert processor.progress_callback is None

    def test_initialization_with_callback(self, mock_qdrant_client, test_config):
        """Test initialization with progress callback."""
        callback = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_config["batch"]["progress_dir"] = tmpdir
            processor = BatchProcessor(
                mock_qdrant_client,
                "test_collection",
                test_config,
                progress_callback=callback,
            )

            assert processor.progress_callback == callback

    # ==========================================================================
    # Config tests
    # ==========================================================================

    def test_get_default_batch_config(self, processor):
        """Test default batch config from yaml settings."""
        config = processor._get_default_batch_config()

        assert isinstance(config, BatchConfig)
        assert config.batch_size == 10
        assert config.analyze_patterns is False  # Because provider is "mock"
        assert config.min_quality == 5

    def test_get_default_batch_config_with_real_llm(self, mock_qdrant_client):
        """Test that analyze_patterns is True with real LLM provider."""
        config = {"batch": {}, "llm": {"provider": "gemini", "min_quality_score": 7}}

        with tempfile.TemporaryDirectory() as tmpdir:
            config["batch"]["progress_dir"] = tmpdir
            processor = BatchProcessor(mock_qdrant_client, "test", config)
            batch_config = processor._get_default_batch_config()

            assert batch_config.analyze_patterns is True
            assert batch_config.min_quality == 7

    # ==========================================================================
    # Progress file management tests
    # ==========================================================================

    def test_get_progress_file_path(self, processor):
        """Test progress file path generation."""
        path = processor._get_progress_file("user/repo")

        assert path.suffix == ".json"
        assert path.exists() is False  # File doesn't exist yet

    def test_get_progress_file_consistent(self, processor):
        """Test that same repo gets same file path."""
        path1 = processor._get_progress_file("user/repo")
        path2 = processor._get_progress_file("user/repo")

        assert path1 == path2

    def test_get_progress_file_different_repos(self, processor):
        """Test different repos get different paths."""
        path1 = processor._get_progress_file("user/repo1")
        path2 = processor._get_progress_file("user/repo2")

        assert path1 != path2

    def test_save_and_load_progress(self, processor):
        """Test saving and loading progress."""
        progress = BatchProgress(repo_name="test/repo")
        progress.total_files = 100
        progress.processed_files = 50
        progress.total_chunks = 75
        progress.stored_patterns = 25

        processor._save_progress(progress)
        loaded = processor._load_progress("test/repo")

        assert loaded is not None
        assert loaded.repo_name == "test/repo"
        assert loaded.total_files == 100
        assert loaded.processed_files == 50

    def test_load_progress_nonexistent(self, processor):
        """Test loading progress for repo without progress file."""
        loaded = processor._load_progress("nonexistent/repo")
        assert loaded is None

    def test_clear_progress(self, processor):
        """Test clearing progress."""
        progress = BatchProgress(repo_name="test/clear")
        progress.total_files = 10

        processor._save_progress(progress)
        assert processor._load_progress("test/clear") is not None

        processor._clear_progress("test/clear")
        assert processor._load_progress("test/clear") is None

    def test_clear_progress_nonexistent(self, processor):
        """Test clearing progress that doesn't exist (no error)."""
        processor._clear_progress("nonexistent/repo")  # Should not raise

    # ==========================================================================
    # Public API tests
    # ==========================================================================

    def test_get_sync_progress_existing(self, processor):
        """Test getting existing sync progress."""
        progress = BatchProgress(repo_name="test/progress")
        progress.total_files = 50
        progress.processed_files = 25
        processor._save_progress(progress)

        result = processor.get_sync_progress("test/progress")

        assert result is not None
        assert result["repo_name"] == "test/progress"
        assert result["total_files"] == 50

    def test_get_sync_progress_nonexistent(self, processor):
        """Test getting progress for repo without progress."""
        result = processor.get_sync_progress("nonexistent/repo")
        assert result is None

    def test_clear_sync_progress(self, processor):
        """Test public clear sync progress method."""
        progress = BatchProgress(repo_name="test/clear2")
        processor._save_progress(progress)

        result = processor.clear_sync_progress("test/clear2")

        assert "cleared" in result.lower()
        assert processor._load_progress("test/clear2") is None

    def test_clear_sync_progress_nonexistent(self, processor):
        """Test clearing nonexistent progress."""
        result = processor.clear_sync_progress("nonexistent/repo")
        # May succeed even if no progress exists
        assert "cleared" in result.lower() or "no progress" in result.lower()

    # ==========================================================================
    # Batch sync tests with mocks
    # ==========================================================================

    def test_batch_sync_no_code_files(self, processor):
        """Test batch sync when repo has no code files."""
        with patch.object(processor, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = []
            mock_gh.return_value = mock_client

            result = processor.batch_sync_repo("user/empty-repo", BatchConfig())

            assert "No code files found" in result

    def test_batch_sync_auth_error(self, processor):
        """Test batch sync with auth error."""
        with patch.object(processor, "get_github_client") as mock_gh:
            mock_gh.side_effect = ValueError("Invalid token")

            result = processor.batch_sync_repo("user/repo", BatchConfig())

            assert "[ERROR]" in result
            assert "authentication" in result.lower()

    def test_batch_sync_general_error(self, processor):
        """Test batch sync with general error."""
        with patch.object(processor, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.side_effect = Exception("Network error")
            mock_gh.return_value = mock_client

            result = processor.batch_sync_repo("user/repo", BatchConfig())

            assert "[ERROR]" in result

    def test_batch_sync_with_progress_callback(self, mock_qdrant_client):
        """Test that progress callback is called during sync."""
        callback = Mock()
        config = {
            "batch": {"progress_dir": tempfile.mkdtemp()},
            "llm": {"provider": "mock"},
        }

        processor = BatchProcessor(
            mock_qdrant_client, "test", config, progress_callback=callback
        )

        mock_file = Mock()
        mock_file.path = "test.py"

        mock_chunk = Mock()
        mock_chunk.content = "def test(): pass\n" * 10
        mock_chunk.file_path = "test.py"
        mock_chunk.language = Language.PYTHON
        mock_chunk.chunk_type = "function"
        mock_chunk.name = "test"

        with patch.object(processor, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = [mock_file]
            mock_client.get_file_content.return_value = "def test(): pass\n" * 10
            mock_client.get_language.return_value = Language.PYTHON
            mock_gh.return_value = mock_client

            with patch.object(processor, "get_pattern_extractor") as mock_ext:
                mock_extractor = Mock()
                mock_extractor.extract_chunks.return_value = [mock_chunk]
                mock_ext.return_value = mock_extractor

                config_obj = BatchConfig(
                    batch_size=5, analyze_patterns=False, save_progress=False
                )

                processor.batch_sync_repo("user/repo", config_obj, resume=False)

                # Callback should have been called
                assert callback.called

    def test_batch_sync_resume_from_progress(self, mock_qdrant_client):
        """Test resuming batch sync from saved progress."""
        config = {
            "batch": {"progress_dir": tempfile.mkdtemp()},
            "llm": {"provider": "mock"},
        }

        processor = BatchProcessor(mock_qdrant_client, "test", config)

        # Save some progress
        progress = BatchProgress(repo_name="user/resume-repo")
        progress.total_files = 10
        progress.processed_files = 5
        progress.total_chunks = 10
        progress.stored_patterns = 5
        processor._save_progress(progress)

        # Mock the file list to include already processed files
        mock_files = [Mock(path=f"file{i}.py") for i in range(10)]

        mock_chunk = Mock()
        mock_chunk.content = "def test(): pass\n" * 10
        mock_chunk.file_path = "test.py"
        mock_chunk.language = Language.PYTHON
        mock_chunk.chunk_type = "function"
        mock_chunk.name = "test"

        with patch.object(processor, "get_github_client") as mock_gh:
            mock_client = Mock()
            mock_client.get_repository.return_value = Mock()
            mock_client.get_code_files.return_value = mock_files
            mock_client.get_file_content.return_value = "def test(): pass\n" * 10
            mock_client.get_language.return_value = Language.PYTHON
            mock_gh.return_value = mock_client

            with patch.object(processor, "get_pattern_extractor") as mock_ext:
                mock_extractor = Mock()
                mock_extractor.extract_chunks.return_value = [mock_chunk]
                mock_ext.return_value = mock_extractor

                config_obj = BatchConfig(analyze_patterns=False)
                result = processor.batch_sync_repo(
                    "user/resume-repo", config_obj, resume=True
                )

                # Should complete successfully
                assert (
                    "[OK]" in result or "No code" in result or "Successfully" in result
                )
