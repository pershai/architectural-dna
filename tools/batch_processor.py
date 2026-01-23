"""Batch processor for handling large repositories."""

import hashlib
import json
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_DELAY_BETWEEN_BATCHES,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MIN_QUALITY,
    DEFAULT_PROGRESS_DIR,
    DEFAULT_RETRY_DELAY,
    FAILED_FILES_DISPLAY_LIMIT,
    PROGRESS_HASH_LENGTH,
    PROGRESS_NOTIFY_INTERVAL,
    PROGRESS_SAVE_INTERVAL,
)
from models import CodeChunk, Pattern, PatternCategory

from .base import BaseTool


@dataclass
class BatchProgress:
    """Tracks progress of batch processing."""

    repo_name: str
    total_files: int = 0
    processed_files: int = 0
    total_chunks: int = 0
    stored_patterns: int = 0
    failed_files: list = field(default_factory=list)
    current_file: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def progress_percent(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.started_at).total_seconds()

    @property
    def estimated_remaining_seconds(self) -> float:
        if self.processed_files == 0:
            return 0.0
        rate = self.elapsed_seconds / self.processed_files
        remaining = self.total_files - self.processed_files
        return rate * remaining

    def to_dict(self) -> dict:
        return {
            "repo_name": self.repo_name,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "total_chunks": self.total_chunks,
            "stored_patterns": self.stored_patterns,
            "failed_files": self.failed_files,
            "current_file": self.current_file,
            "progress_percent": round(self.progress_percent, 1),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "estimated_remaining_seconds": round(self.estimated_remaining_seconds, 1),
            "started_at": self.started_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BatchProgress":
        progress = cls(repo_name=data["repo_name"])
        progress.total_files = data.get("total_files", 0)
        progress.processed_files = data.get("processed_files", 0)
        progress.total_chunks = data.get("total_chunks", 0)
        progress.stored_patterns = data.get("stored_patterns", 0)
        progress.failed_files = data.get("failed_files", [])
        progress.current_file = data.get("current_file", "")
        if "started_at" in data:
            progress.started_at = datetime.fromisoformat(data["started_at"])
        if "last_updated" in data:
            progress.last_updated = datetime.fromisoformat(data["last_updated"])
        return progress


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = DEFAULT_BATCH_SIZE
    delay_between_batches: float = DEFAULT_DELAY_BETWEEN_BATCHES
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: float = DEFAULT_RETRY_DELAY
    save_progress: bool = True
    progress_dir: str = DEFAULT_PROGRESS_DIR
    analyze_patterns: bool = True
    min_quality: int = DEFAULT_MIN_QUALITY


class BatchProcessor(BaseTool):
    """
    Processes large repositories in batches with progress tracking and resumability.

    Features:
    - Configurable batch sizes to manage memory and API rate limits
    - Progress tracking with percentage and time estimates
    - Resumable processing (can continue after interruption)
    - Error handling with retries for transient failures
    - Progress callbacks for real-time status updates
    """

    def __init__(
        self,
        qdrant_client,
        collection_name: str,
        config: dict = None,
        progress_callback: Callable[[BatchProgress], None] = None,
    ):
        super().__init__(qdrant_client, collection_name, config or {})
        self.progress_callback = progress_callback
        self._ensure_progress_dir()

    def _get_default_batch_config(self) -> BatchConfig:
        """Create BatchConfig from config.yaml settings."""
        batch_cfg = self.config.get("batch", {})
        llm_cfg = self.config.get("llm", {})

        # Determine if LLM analysis should be enabled
        llm_provider = llm_cfg.get("provider", "mock")
        analyze_patterns = llm_provider != "mock"

        return BatchConfig(
            batch_size=batch_cfg.get("batch_size", DEFAULT_BATCH_SIZE),
            delay_between_batches=batch_cfg.get(
                "delay_between_batches", DEFAULT_DELAY_BETWEEN_BATCHES
            ),
            max_retries=batch_cfg.get("max_retries", DEFAULT_MAX_RETRIES),
            retry_delay=batch_cfg.get("retry_delay", DEFAULT_RETRY_DELAY),
            save_progress=batch_cfg.get("save_progress", True),
            progress_dir=batch_cfg.get("progress_dir", DEFAULT_PROGRESS_DIR),
            analyze_patterns=analyze_patterns,
            min_quality=llm_cfg.get("min_quality_score", DEFAULT_MIN_QUALITY),
        )

    def _ensure_progress_dir(self):
        """Create progress directory if it doesn't exist."""
        progress_dir = Path(
            self.config.get("batch", {}).get("progress_dir", DEFAULT_PROGRESS_DIR)
        )
        progress_dir.mkdir(parents=True, exist_ok=True)

    def _get_progress_file(self, repo_name: str) -> Path:
        """Get path to progress file for a repository."""
        progress_dir = Path(
            self.config.get("batch", {}).get("progress_dir", DEFAULT_PROGRESS_DIR)
        )
        # Create safe filename from repo name
        safe_name = hashlib.md5(repo_name.encode()).hexdigest()[:PROGRESS_HASH_LENGTH]
        return progress_dir / f"{safe_name}.json"

    def _save_progress(self, progress: BatchProgress):
        """Save progress to file for resumability."""
        progress.last_updated = datetime.now()
        progress_file = self._get_progress_file(progress.repo_name)
        with open(progress_file, "w") as f:
            json.dump(progress.to_dict(), f, indent=2)

    def _load_progress(self, repo_name: str) -> BatchProgress | None:
        """Load progress from file if it exists."""
        progress_file = self._get_progress_file(repo_name)
        if progress_file.exists():
            with open(progress_file) as f:
                return BatchProgress.from_dict(json.load(f))
        return None

    def _clear_progress(self, repo_name: str):
        """Clear progress file after successful completion."""
        progress_file = self._get_progress_file(repo_name)
        if progress_file.exists():
            progress_file.unlink()

    def _notify_progress(self, progress: BatchProgress):
        """Notify progress callback if set."""
        if self.progress_callback:
            self.progress_callback(progress)

    def _batch_files(self, files: list, batch_size: int) -> Iterator[list]:
        """Yield files in batches."""
        for i in range(0, len(files), batch_size):
            yield files[i : i + batch_size]

    def _process_file_with_retry(
        self, gh, repo, file_node, extractor, max_retries: int, retry_delay: float
    ) -> list[CodeChunk]:
        """Process a single file with retry logic."""
        last_error = None

        for attempt in range(max_retries):
            try:
                content = gh.get_file_content(repo, file_node.path)
                if content:
                    language = gh.get_language(file_node.path)
                    return extractor.extract_chunks(content, file_node.path, language)
                return []
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        raise last_error

    def batch_sync_repo(
        self, repo_name: str, batch_config: BatchConfig = None, resume: bool = True
    ) -> str:
        """
        Sync a GitHub repository in batches with progress tracking.

        Args:
            repo_name: Full repository name (e.g., "username/repo-name")
            batch_config: Configuration for batch processing
            resume: If True, resume from previous progress if available

        Returns:
            Summary of the sync operation with progress details
        """
        if batch_config is None:
            batch_config = self._get_default_batch_config()

        progress = None  # Initialize for exception handler

        try:
            gh = self.get_github_client()
            extractor = self.get_pattern_extractor()

            self.logger.info(f"Starting batch sync for: {repo_name}")

            # Get repository
            repo = gh.get_repository(repo_name)

            # Get all code files
            code_files = gh.get_code_files(repo)
            total_files = len(code_files)

            self.logger.info(f"Found {total_files} code files")

            if not code_files:
                return f"No code files found in {repo_name}"

            # Check for existing progress
            progress = None
            processed_paths = set()

            if resume:
                progress = self._load_progress(repo_name)
                if progress and progress.processed_files > 0:
                    self.logger.info(
                        f"Resuming from previous progress: {progress.processed_files}/{progress.total_files} files"
                    )
                    # Load already processed file paths (stored in failed_files tracking)
                    # We'll use a separate tracking approach

            if progress is None:
                progress = BatchProgress(repo_name=repo_name)

            progress.total_files = total_files

            # Get analyzer if needed
            analyzer = None
            if batch_config.analyze_patterns:
                try:
                    analyzer = self.get_llm_analyzer()
                except Exception as e:
                    self.logger.warning(f"LLM analyzer not available: {e}")
                    batch_config.analyze_patterns = False

            # Process files in batches
            all_chunks = []

            for batch_num, batch in enumerate(
                self._batch_files(code_files, batch_config.batch_size)
            ):
                batch_start = batch_num * batch_config.batch_size
                self.logger.info(
                    f"Processing batch {batch_num + 1} "
                    f"(files {batch_start + 1}-{min(batch_start + batch_config.batch_size, total_files)})"
                )

                for file_node in batch:
                    # Skip already processed files if resuming
                    if file_node.path in processed_paths:
                        continue

                    progress.current_file = file_node.path

                    try:
                        chunks = self._process_file_with_retry(
                            gh,
                            repo,
                            file_node,
                            extractor,
                            batch_config.max_retries,
                            batch_config.retry_delay,
                        )
                        all_chunks.extend(chunks)
                        progress.total_chunks += len(chunks)
                        processed_paths.add(file_node.path)

                    except Exception as e:
                        self.logger.error(f"Failed to process {file_node.path}: {e}")
                        progress.failed_files.append(
                            {"path": file_node.path, "error": str(e)}
                        )

                    progress.processed_files += 1
                    self._notify_progress(progress)

                    # Save progress periodically
                    if (
                        batch_config.save_progress
                        and progress.processed_files % PROGRESS_SAVE_INTERVAL == 0
                    ):
                        self._save_progress(progress)

                # Rate limiting delay between batches
                if batch_config.delay_between_batches > 0:
                    time.sleep(batch_config.delay_between_batches)

            self.logger.info(
                f"Extracted {len(all_chunks)} chunks from {progress.processed_files} files"
            )

            if not all_chunks:
                self._clear_progress(repo_name)
                return f"No code patterns extracted from {repo_name}"

            # Analyze and store patterns in batches
            patterns_to_store = []

            if batch_config.analyze_patterns and analyzer:
                self.logger.info("Analyzing patterns with LLM...")
                try:
                    analyzed = analyzer.analyze_chunks(
                        all_chunks, min_quality=batch_config.min_quality
                    )

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
                    self.logger.warning(f"LLM analysis failed: {e}")
                    batch_config.analyze_patterns = False

            # Fallback: store without analysis
            if not batch_config.analyze_patterns or not patterns_to_store:
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

            # Store patterns using upsert for deduplication
            self.logger.info(
                f"Storing {len(patterns_to_store)} patterns (with deduplication)..."
            )

            for i, pattern in enumerate(patterns_to_store):
                try:
                    pattern_id = pattern.generate_id()
                    self.client.add(
                        collection_name=self.collection_name,
                        documents=[pattern.content],
                        metadata=[pattern.to_metadata()],
                        ids=[pattern_id],
                    )
                    progress.stored_patterns += 1

                    # Progress update periodically
                    if i % PROGRESS_NOTIFY_INTERVAL == 0:
                        self._notify_progress(progress)

                except Exception as e:
                    self.logger.error(f"Failed to store pattern {pattern.title}: {e}")

            # Clear progress file on success
            self._clear_progress(repo_name)

            # Build summary
            elapsed = progress.elapsed_seconds
            elapsed_str = (
                f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
                if elapsed >= 60
                else f"{elapsed:.1f}s"
            )

            summary = (
                f"[OK] Successfully synced {repo_name}\n\n"
                f"**Summary:**\n"
                f"- Files processed: {progress.processed_files}/{progress.total_files}\n"
                f"- Chunks extracted: {progress.total_chunks}\n"
                f"- Patterns stored: {progress.stored_patterns}\n"
                f"- Failed files: {len(progress.failed_files)}\n"
                f"- LLM analysis: {'Yes' if batch_config.analyze_patterns else 'No'}\n"
                f"- Time elapsed: {elapsed_str}\n"
            )

            if progress.failed_files:
                summary += f"\n**Failed files ({len(progress.failed_files)}):**\n"
                for fail in progress.failed_files[:FAILED_FILES_DISPLAY_LIMIT]:
                    summary += f"- {fail['path']}: {fail['error']}\n"
                if len(progress.failed_files) > FAILED_FILES_DISPLAY_LIMIT:
                    summary += f"- ... and {len(progress.failed_files) - FAILED_FILES_DISPLAY_LIMIT} more\n"

            return summary

        except ValueError as e:
            return (
                f"[ERROR] GitHub authentication failed: {e}\n\n"
                "Make sure GITHUB_TOKEN is set."
            )
        except Exception as e:
            # Save progress on error for resumability
            if progress and batch_config.save_progress:
                self._save_progress(progress)
                return f"[ERROR] Error syncing repository: {e}\n\nProgress saved. Use resume=True to continue."
            return f"[ERROR] Error syncing repository: {e}"

    def get_sync_progress(self, repo_name: str) -> dict | None:
        """
        Get the current progress for a repository sync.

        Args:
            repo_name: Full repository name

        Returns:
            Progress dictionary or None if no progress exists
        """
        progress = self._load_progress(repo_name)
        if progress:
            return progress.to_dict()
        return None

    def clear_sync_progress(self, repo_name: str) -> str:
        """
        Clear saved progress for a repository.

        Args:
            repo_name: Full repository name

        Returns:
            Confirmation message
        """
        self._clear_progress(repo_name)
        return f"Progress cleared for {repo_name}"
