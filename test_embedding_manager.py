"""Tests for EmbeddingManager."""

from unittest.mock import Mock, patch

import pytest

from embedding_manager import EmbeddingManager


class TestEmbeddingManager:
    """Tests for EmbeddingManager class."""

    @pytest.fixture
    def basic_config(self):
        return {
            "embeddings": {
                "provider": "fastembed",
                "model": "BAAI/bge-small-en-v1.5",
                "preprocessing": {
                    "normalize_whitespace": True,
                    "remove_empty_lines": False,
                    "include_comments": True,
                    "include_docstrings": True,
                },
                "chunking": {
                    "enabled": True,
                    "max_chunk_size": 512,
                    "chunk_overlap": 50,
                    "strategy": "smart",
                },
            }
        }

    @pytest.fixture
    def manager(self, basic_config):
        return EmbeddingManager(basic_config)

    # ==========================================================================
    # Initialization tests
    # ==========================================================================

    def test_initialization_with_config(self, basic_config):
        """Test initialization with config."""
        manager = EmbeddingManager(basic_config)

        assert manager.provider == "fastembed"
        assert manager.model == "BAAI/bge-small-en-v1.5"

    def test_initialization_defaults(self):
        """Test initialization with empty config uses defaults."""
        manager = EmbeddingManager({})

        assert manager.provider == "fastembed"
        assert manager.model == "BAAI/bge-small-en-v1.5"

    def test_initialization_unsupported_model_warns(self, basic_config):
        """Test warning for unsupported model."""
        basic_config["embeddings"]["model"] = "unknown/model"

        with patch("embedding_manager.logger") as mock_logger:
            EmbeddingManager(basic_config)
            mock_logger.warning.assert_called()

    # ==========================================================================
    # Vector size tests
    # ==========================================================================

    def test_get_vector_size_known_model(self, manager):
        """Test vector size for known model."""
        assert manager.get_vector_size() == 384  # bge-small-en-v1.5

    def test_get_vector_size_override(self, basic_config):
        """Test vector size with override."""
        basic_config["embeddings"]["vector_size"] = 1024
        manager = EmbeddingManager(basic_config)

        assert manager.get_vector_size() == 1024

    def test_get_vector_size_different_models(self):
        """Test vector sizes for different models."""
        models = {
            "BAAI/bge-small-en-v1.5": 384,
            "BAAI/bge-base-en-v1.5": 768,
            "jinaai/jina-embeddings-v2-base-code": 768,
        }

        for model, expected_size in models.items():
            config = {"embeddings": {"model": model}}
            manager = EmbeddingManager(config)
            assert manager.get_vector_size() == expected_size

    # ==========================================================================
    # Qdrant client setup tests
    # ==========================================================================

    def test_setup_qdrant_client_fastembed(self, manager):
        """Test Qdrant client setup with fastembed."""
        mock_client = Mock()

        manager.setup_qdrant_client(mock_client)

        mock_client.set_model.assert_called_once_with("BAAI/bge-small-en-v1.5")

    def test_setup_qdrant_client_unsupported_provider(self, basic_config):
        """Test Qdrant client setup with unsupported provider."""
        basic_config["embeddings"]["provider"] = "openai"
        manager = EmbeddingManager(basic_config)
        mock_client = Mock()

        with patch("embedding_manager.logger") as mock_logger:
            manager.setup_qdrant_client(mock_client)
            mock_logger.warning.assert_called()
            mock_client.set_model.assert_not_called()

    # ==========================================================================
    # Preprocessing tests
    # ==========================================================================

    def test_preprocess_code_empty(self, manager):
        """Test preprocessing empty code."""
        assert manager.preprocess_code("") == ""
        assert manager.preprocess_code(None) is None

    def test_preprocess_normalize_whitespace(self, basic_config):
        """Test whitespace normalization."""
        basic_config["embeddings"]["preprocessing"]["normalize_whitespace"] = True
        manager = EmbeddingManager(basic_config)

        code = "def foo():  \r\n    x = 1"
        result = manager.preprocess_code(code)

        assert "  " not in result  # Multiple spaces removed
        assert "\r\n" not in result  # CRLF normalized

    def test_preprocess_remove_empty_lines(self, basic_config):
        """Test empty line removal."""
        basic_config["embeddings"]["preprocessing"]["remove_empty_lines"] = True
        manager = EmbeddingManager(basic_config)

        code = "line1\n\nline2\n\n\nline3"
        result = manager.preprocess_code(code)

        assert result == "line1\nline2\nline3"

    def test_preprocess_remove_comments(self, basic_config):
        """Test comment removal."""
        basic_config["embeddings"]["preprocessing"]["include_comments"] = False
        manager = EmbeddingManager(basic_config)

        code = """x = 1  // inline comment
y = 2  # python comment
/* block
comment */
z = 3"""
        result = manager.preprocess_code(code)

        assert "inline comment" not in result
        assert "python comment" not in result
        assert "block" not in result

    def test_preprocess_remove_docstrings(self, basic_config):
        """Test docstring removal."""
        basic_config["embeddings"]["preprocessing"]["include_docstrings"] = False
        manager = EmbeddingManager(basic_config)

        code = '''def foo():
    """This is a docstring."""
    return 1

def bar():
    \'\'\'Another docstring.\'\'\'
    return 2'''
        result = manager.preprocess_code(code)

        assert "This is a docstring" not in result
        assert "Another docstring" not in result

    def test_preprocess_keep_comments(self, basic_config):
        """Test keeping comments when configured."""
        basic_config["embeddings"]["preprocessing"]["include_comments"] = True
        manager = EmbeddingManager(basic_config)

        code = "x = 1  # keep this comment"
        result = manager.preprocess_code(code)

        assert "keep this comment" in result

    # ==========================================================================
    # Chunking tests
    # ==========================================================================

    def test_should_chunk_small_code(self, manager):
        """Test that small code doesn't need chunking."""
        small_code = "x = 1\ny = 2"
        assert not manager.should_chunk(small_code)

    def test_should_chunk_large_code(self, manager):
        """Test that large code needs chunking."""
        large_code = "x = 1\n" * 1000  # Many lines
        assert manager.should_chunk(large_code)

    def test_should_chunk_disabled(self, basic_config):
        """Test chunking disabled."""
        basic_config["embeddings"]["chunking"]["enabled"] = False
        manager = EmbeddingManager(basic_config)

        large_code = "x = 1\n" * 1000
        assert not manager.should_chunk(large_code)

    def test_chunk_code_no_chunking_needed(self, manager):
        """Test chunking when not needed."""
        code = "x = 1\ny = 2"
        chunks = manager.chunk_code(code)

        assert len(chunks) == 1
        assert chunks[0][0] == code
        assert chunks[0][1]["chunk_index"] == 0
        assert chunks[0][1]["total_chunks"] == 1

    def test_simple_chunk(self, basic_config):
        """Test simple chunking strategy."""
        basic_config["embeddings"]["chunking"]["strategy"] = "simple"
        basic_config["embeddings"]["chunking"]["max_chunk_size"] = (
            20  # Very small for testing
        )
        manager = EmbeddingManager(basic_config)

        code = "a" * 500  # 500 chars
        chunks = manager._simple_chunk(code, 20, 5)

        assert len(chunks) > 1
        for i, (_chunk_text, metadata) in enumerate(chunks):
            assert metadata["chunk_index"] == i
            assert metadata["total_chunks"] == len(chunks)

    def test_smart_chunk(self, basic_config):
        """Test smart chunking strategy."""
        basic_config["embeddings"]["chunking"]["max_chunk_size"] = (
            50  # Small for testing
        )
        manager = EmbeddingManager(basic_config)

        code = "\n".join([f"line {i}" for i in range(100)])
        chunks = manager._smart_chunk(code, 50, 10, "test.py")

        assert len(chunks) > 1
        # Verify metadata
        total = len(chunks)
        for _chunk_text, metadata in chunks:
            assert metadata["total_chunks"] == total

    # ==========================================================================
    # Model info tests
    # ==========================================================================

    def test_get_model_info(self, manager):
        """Test getting model info."""
        info = manager.get_model_info()

        assert info["provider"] == "fastembed"
        assert info["model"] == "BAAI/bge-small-en-v1.5"
        assert info["vector_size"] == 384
        assert "chunking_enabled" in info
        assert "preprocessing" in info

    # ==========================================================================
    # Supported models
    # ==========================================================================

    def test_supported_models_exist(self):
        """Test that supported models are defined."""
        assert len(EmbeddingManager.SUPPORTED_MODELS) > 0
        assert "BAAI/bge-small-en-v1.5" in EmbeddingManager.SUPPORTED_MODELS
        assert "BAAI/bge-base-en-v1.5" in EmbeddingManager.SUPPORTED_MODELS
