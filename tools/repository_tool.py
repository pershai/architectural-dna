"""Repository management tools for GitHub integration."""

from constants import LARGE_REPO_THRESHOLD
from models import Pattern, PatternCategory

from .base import BaseTool


class RepositoryTool(BaseTool):
    """Tool for GitHub repository operations and synchronization."""

    def __init__(
        self,
        qdrant_client,
        collection_name: str,
        config: dict = None,
        batch_processor=None,
    ):
        """
        Initialize repository tool.

        Args:
            qdrant_client: Qdrant client instance
            collection_name: Name of the collection
            config: Configuration dictionary
            batch_processor: Optional BatchProcessor for large repos
        """
        super().__init__(qdrant_client, collection_name, config)
        self._batch_processor = batch_processor

    def set_batch_processor(self, batch_processor):
        """Set the batch processor for large repository handling."""
        self._batch_processor = batch_processor

    def list_my_repos(
        self, include_private: bool = True, include_orgs: bool = True
    ) -> str:
        """
        List all your GitHub repositories available for DNA extraction.

        Args:
            include_private: Include private repositories
            include_orgs: Include repositories from organizations you belong to

        Returns:
            Formatted list of repositories with their details
        """
        try:
            gh = self.get_github_client()
            excluded = self.config.get("github", {}).get("excluded_repos", [])

            repos = gh.list_repositories(
                include_private=include_private,
                include_orgs=include_orgs,
                excluded_patterns=excluded,
            )

            if not repos:
                return "No repositories found."

            output = f"Found {len(repos)} repositories:\n\n"

            for repo in repos:
                visibility = "[PRIVATE]" if repo.is_private else "[PUBLIC]"
                lang = repo.language or "Unknown"
                desc = repo.description or "No description"

                output += f"**{repo.full_name}** ({visibility})\n"
                output += f"  Language: {lang} | Branch: {repo.default_branch}\n"
                output += f"  {desc}\n\n"

            return output

        except ValueError as e:
            return (
                f"[ERROR] GitHub authentication failed: {e}\n\n"
                "Make sure GITHUB_TOKEN is set in your environment."
            )
        except Exception as e:
            return f"[ERROR] Error listing repositories: {e}"

    def sync_github_repo(
        self, repo_name: str, analyze_patterns: bool = True, min_quality: int = 5
    ) -> str:
        """
        Sync a GitHub repository into the DNA bank.

        Fetches code from the repository, extracts patterns, optionally analyzes
        them with LLM, and stores high-quality patterns in the vector database.

        For large repositories (>50 files), automatically uses batch processing
        with progress tracking and resumability.

        Args:
            repo_name: Full repository name (e.g., "username/repo-name")
            analyze_patterns: If True, use LLM to identify and rate patterns
            min_quality: Minimum quality score (1-10) for patterns to store

        Returns:
            Summary of the sync operation
        """
        try:
            gh = self.get_github_client()
            extractor = self.get_pattern_extractor()

            self.logger.info(f"Syncing repository: {repo_name}")

            # Get repository
            repo = gh.get_repository(repo_name)

            # Get code files
            code_files = gh.get_code_files(repo)
            total_files = len(code_files)
            self.logger.info(f"Found {total_files} code files")

            # For large repos, delegate to batch processor if available
            if total_files > LARGE_REPO_THRESHOLD and self._batch_processor:
                self.logger.info(
                    f"Large repo detected ({total_files} files > {LARGE_REPO_THRESHOLD}), "
                    "using batch processing..."
                )
                batch_config = self._batch_processor._get_default_batch_config()
                batch_config.analyze_patterns = analyze_patterns
                batch_config.min_quality = min_quality
                return self._batch_processor.batch_sync_repo(
                    repo_name, batch_config, resume=True
                )

            if not code_files:
                return f"No code files found in {repo_name}"

            # Extract chunks from all files
            all_chunks = []
            for file_node in code_files:
                content = gh.get_file_content(repo, file_node.path)
                if content:
                    language = gh.get_language(file_node.path)
                    chunks = extractor.extract_chunks(content, file_node.path, language)
                    all_chunks.extend(chunks)

            self.logger.info(f"Extracted {len(all_chunks)} code chunks")

            if not all_chunks:
                return f"No code patterns extracted from {repo_name}"

            # Analyze patterns with LLM if requested
            patterns_to_store = []

            if analyze_patterns:
                try:
                    analyzer = self.get_llm_analyzer()
                    min_qual = self.config.get("llm", {}).get(
                        "min_quality_score", min_quality
                    )

                    self.logger.info(
                        f"Analyzing patterns with LLM (min quality: {min_qual})..."
                    )
                    analyzed = analyzer.analyze_chunks(all_chunks, min_quality=min_qual)

                    for chunk, analysis in analyzed:
                        pattern = Pattern(
                            content=chunk.content,
                            title=analysis.title,
                            description=analysis.description,
                            category=analysis.category,
                            language=chunk.language,
                            quality_score=analysis.quality_score,
                            source_repo=repo_name,
                            source_path=chunk.file_path,
                            use_cases=analysis.use_cases,
                        )
                        patterns_to_store.append(pattern)

                except Exception as e:
                    self.logger.warning(
                        f"LLM analysis failed: {e}. Storing chunks without analysis."
                    )
                    analyze_patterns = False

            # Fallback: store chunks without LLM analysis
            if not analyze_patterns:
                for chunk in all_chunks:
                    pattern = Pattern(
                        content=chunk.content,
                        title=chunk.name or f"Pattern from {chunk.file_path}",
                        description=f"Code {chunk.chunk_type} from {chunk.file_path}",
                        category=PatternCategory.OTHER,
                        language=chunk.language,
                        quality_score=5,
                        source_repo=repo_name,
                        source_path=chunk.file_path,
                        use_cases=[],
                    )
                    patterns_to_store.append(pattern)

            # Store patterns in Qdrant using upsert for deduplication
            stored_count = 0
            for pattern in patterns_to_store:
                try:
                    pattern_id = pattern.generate_id()
                    self.client.add(
                        collection_name=self.collection_name,
                        documents=[pattern.content],
                        metadata=[pattern.to_metadata()],
                        ids=[pattern_id],
                    )
                    stored_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to store pattern {pattern.title}: {e}")

            return (
                f"[OK] Successfully synced {repo_name}\n\n"
                f"**Summary:**\n"
                f"- Files processed: {len(code_files)}\n"
                f"- Chunks extracted: {len(all_chunks)}\n"
                f"- Patterns stored: {stored_count}\n"
                f"- LLM analysis: {'Yes' if analyze_patterns else 'No'}"
            )

        except ValueError as e:
            return (
                f"[ERROR] GitHub authentication failed: {e}\n\n"
                "Make sure GITHUB_TOKEN is set."
            )
        except Exception as e:
            return f"[ERROR] Error syncing repository: {e}"
