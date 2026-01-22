"""Embedding manager for configurable embedding models and preprocessing."""

import logging
import re
from typing import Any

from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages embedding models and preprocessing for code patterns."""

    # Supported embedding models and their dimensions
    SUPPORTED_MODELS = {
        # Code-optimized models
        "jinaai/jina-embeddings-v2-base-code": 768,
        "BAAI/bge-base-en-v1.5": 768,
        # Lightweight models
        "BAAI/bge-small-en-v1.5": 384,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        # High quality models
        "nomic-ai/nomic-embed-text-v1.5": 768,
    }

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the embedding manager.

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config.get("embeddings", {})
        self.provider = self.config.get("provider", "fastembed")
        self.model = self.config.get("model", "BAAI/bge-small-en-v1.5")
        self.preprocessing = self.config.get("preprocessing", {})
        self.chunking = self.config.get("chunking", {})

        # Validate model
        if self.model not in self.SUPPORTED_MODELS:
            logger.warning(
                f"Model {self.model} not in supported list. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )

        logger.info(f"Initialized EmbeddingManager with model: {self.model}")

    def get_vector_size(self) -> int:
        """
        Get the vector dimension size for the current model.

        Returns:
            Vector dimension size
        """
        # Check if override is specified in config
        if "vector_size" in self.config:
            return self.config["vector_size"]

        # Auto-detect from supported models
        return self.SUPPORTED_MODELS.get(self.model, 384)

    def setup_qdrant_client(self, client: QdrantClient) -> None:
        """
        Configure Qdrant client with the embedding model.

        Args:
            client: Qdrant client instance
        """
        if self.provider == "fastembed":
            client.set_model(self.model)
            logger.info(f"Qdrant client configured with FastEmbed model: {self.model}")
        else:
            logger.warning(f"Provider {self.provider} not yet implemented")

    def preprocess_code(self, code: str) -> str:
        """
        Preprocess code before embedding.

        Applies normalization and cleaning based on configuration.

        Args:
            code: Raw code string

        Returns:
            Preprocessed code string
        """
        if not code:
            return code

        processed = code

        # Normalize whitespace
        if self.preprocessing.get("normalize_whitespace", True):
            # Replace multiple spaces with single space
            processed = re.sub(r" +", " ", processed)
            # Normalize line endings
            processed = processed.replace("\r\n", "\n")

        # Remove empty lines
        if self.preprocessing.get("remove_empty_lines", False):
            lines = processed.split("\n")
            lines = [line for line in lines if line.strip()]
            processed = "\n".join(lines)

        # Handle comments
        if not self.preprocessing.get("include_comments", True):
            # This is language-specific, basic implementation
            processed = self._remove_comments(processed)

        # Handle docstrings (Python-specific for now)
        if not self.preprocessing.get("include_docstrings", True):
            processed = self._remove_docstrings(processed)

        return processed

    def _remove_comments(self, code: str) -> str:
        """
        Remove comments from code (basic implementation).

        Args:
            code: Code string

        Returns:
            Code without comments
        """
        # Remove single-line comments (// and #)
        code = re.sub(r"//.*?$", "", code, flags=re.MULTILINE)
        code = re.sub(r"#.*?$", "", code, flags=re.MULTILINE)
        # Remove multi-line comments (/* */ and """ """)
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        return code

    def _remove_docstrings(self, code: str) -> str:
        """
        Remove Python docstrings from code.

        Args:
            code: Python code string

        Returns:
            Code without docstrings
        """
        # Remove triple-quoted strings (basic implementation)
        code = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", "", code, flags=re.DOTALL)
        return code

    def should_chunk(self, code: str) -> bool:
        """
        Determine if code should be chunked based on size.

        Args:
            code: Code string

        Returns:
            True if code should be chunked
        """
        if not self.chunking.get("enabled", True):
            return False

        max_size = self.chunking.get("max_chunk_size", 512)

        # Rough token estimation: ~4 chars per token
        estimated_tokens = len(code) / 4

        return estimated_tokens > max_size

    def chunk_code(self, code: str, file_path: str = "") -> list[tuple[str, dict]]:
        """
        Split large code into chunks.

        Args:
            code: Code string to chunk
            file_path: File path for context

        Returns:
            List of (chunk_text, metadata) tuples
        """
        if not self.should_chunk(code):
            return [(code, {"chunk_index": 0, "total_chunks": 1})]

        strategy = self.chunking.get("strategy", "smart")
        max_size = self.chunking.get("max_chunk_size", 512)
        overlap = self.chunking.get("chunk_overlap", 50)

        if strategy == "smart":
            return self._smart_chunk(code, max_size, overlap, file_path)
        else:
            return self._simple_chunk(code, max_size, overlap)

    def _simple_chunk(
        self, code: str, max_size: int, overlap: int
    ) -> list[tuple[str, dict]]:
        """
        Simple character-based chunking.

        Args:
            code: Code to chunk
            max_size: Maximum chunk size in tokens
            overlap: Overlap between chunks in tokens

        Returns:
            List of (chunk, metadata) tuples
        """
        # Convert tokens to characters (rough: 4 chars per token)
        max_chars = max_size * 4
        overlap_chars = overlap * 4

        chunks = []
        start = 0
        chunk_idx = 0

        while start < len(code):
            end = start + max_chars
            chunk = code[start:end]

            chunks.append(
                (
                    chunk,
                    {
                        "chunk_index": chunk_idx,
                        "total_chunks": -1,  # Will be updated
                        "start_char": start,
                        "end_char": end,
                    },
                )
            )

            start = end - overlap_chars
            chunk_idx += 1

        # Update total chunks
        total = len(chunks)
        for _chunk_text, metadata in chunks:
            metadata["total_chunks"] = total

        return chunks

    def _smart_chunk(
        self, code: str, max_size: int, overlap: int, file_path: str
    ) -> list[tuple[str, dict]]:
        """
        Smart chunking that respects code structure (functions, classes).

        Args:
            code: Code to chunk
            max_size: Maximum chunk size in tokens
            overlap: Overlap between chunks in tokens
            file_path: File path for language detection

        Returns:
            List of (chunk, metadata) tuples
        """
        # For now, fall back to line-based chunking that tries to keep functions together
        lines = code.split("\n")
        max(10, max_size // 20)  # Rough estimate

        chunks = []
        current_chunk = []
        current_size = 0
        chunk_idx = 0

        for line in lines:
            line_size = len(line) / 4  # Token estimate

            # If adding this line would exceed max, start new chunk
            if current_size + line_size > max_size and current_chunk:
                chunk_text = "\n".join(current_chunk)
                chunks.append(
                    (
                        chunk_text,
                        {
                            "chunk_index": chunk_idx,
                            "total_chunks": -1,
                            "lines": len(current_chunk),
                        },
                    )
                )
                chunk_idx += 1

                # Keep overlap lines
                overlap_lines = max(1, overlap // 20)
                current_chunk = current_chunk[-overlap_lines:]
                current_size = sum(len(line_text) / 4 for line_text in current_chunk)

            current_chunk.append(line)
            current_size += line_size

        # Add final chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                (
                    chunk_text,
                    {
                        "chunk_index": chunk_idx,
                        "total_chunks": -1,
                        "lines": len(current_chunk),
                    },
                )
            )

        # Update total chunks
        total = len(chunks)
        for _, metadata in chunks:
            metadata["total_chunks"] = total

        logger.info(f"Split code into {total} chunks (smart strategy)")
        return chunks

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the current embedding configuration.

        Returns:
            Dictionary with model information
        """
        return {
            "provider": self.provider,
            "model": self.model,
            "vector_size": self.get_vector_size(),
            "chunking_enabled": self.chunking.get("enabled", True),
            "preprocessing": self.preprocessing,
        }
