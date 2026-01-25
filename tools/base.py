"""Base class for MCP tools."""

import logging
from typing import Any

from qdrant_client import QdrantClient

from github_client import GitHubClient
from llm_analyzer import LLMAnalyzer, MockLLMAnalyzer
from pattern_extractor import PatternExtractor
from scaffolder import ProjectScaffolder


class BaseTool:
    """Base class for all MCP tools with shared dependencies."""

    def __init__(
        self, qdrant_client: QdrantClient, collection_name: str, config: dict[str, Any]
    ):
        """
        Initialize the base tool.

        Args:
            qdrant_client: Initialized Qdrant client
            collection_name: Name of the Qdrant collection
            config: Configuration dictionary from config.yaml
        """
        self.client = qdrant_client
        self.collection_name = collection_name
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Lazy-loaded components
        self._github_client: GitHubClient | None = None
        self._llm_analyzer: LLMAnalyzer | None = None
        self._pattern_extractor: PatternExtractor | None = None
        self._scaffolder: ProjectScaffolder | None = None

    def get_github_client(self) -> GitHubClient:
        """Get or create GitHub client with caching configured from config."""
        if self._github_client is None:
            self._github_client = GitHubClient(config=self.config)
        return self._github_client

    def get_llm_analyzer(self) -> LLMAnalyzer:
        """Get or create LLM analyzer."""
        if self._llm_analyzer is None:
            llm_config = self.config.get("llm", {})
            provider = llm_config.get("provider", "gemini")
            if provider == "mock":
                self._llm_analyzer = MockLLMAnalyzer()
            else:
                self._llm_analyzer = LLMAnalyzer(
                    model=llm_config.get("model"),
                    max_retries=llm_config.get("max_retries"),
                    initial_retry_delay=llm_config.get("initial_retry_delay"),
                    max_retry_delay=llm_config.get("max_retry_delay"),
                )
        return self._llm_analyzer

    def get_pattern_extractor(self) -> PatternExtractor:
        """Get or create pattern extractor."""
        if self._pattern_extractor is None:
            self._pattern_extractor = PatternExtractor()
        return self._pattern_extractor

    def get_scaffolder(self) -> ProjectScaffolder:
        """Get or create project scaffolder."""
        if self._scaffolder is None:
            self._scaffolder = ProjectScaffolder(
                self.client, self.collection_name, self.config
            )
        return self._scaffolder
