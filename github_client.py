"""GitHub API client for repository operations."""

import fnmatch
import logging
import os
from pathlib import Path
from typing import Optional

from github import Github, Auth
from github.ContentFile import ContentFile
from github.Repository import Repository

from models import RepoInfo, FileNode, Language
from github_cache import (
    GitHubCache,
    make_repo_list_key,
    make_file_tree_key,
    make_file_content_key,
    make_repository_key,
)
from constants import (
    CACHE_TTL_REPO_LIST,
    CACHE_TTL_FILE_TREE,
    CACHE_TTL_FILE_CONTENT,
)

logger = logging.getLogger(__name__)


class GitHubClient:
    """Handles GitHub API authentication and repository operations."""

    # File extensions to include when fetching code
    CODE_EXTENSIONS = {".py", ".java", ".js", ".ts", ".tsx", ".jsx", ".go"}

    # Directories to skip
    IGNORED_DIRS = {
        ".git", "node_modules", "venv", "__pycache__",
        "dist", "build", "target", ".idea", ".vscode",
        "vendor", "deps", ".gradle", "bin", "obj"
    }

    def __init__(
        self,
        token: Optional[str] = None,
        cache: Optional[GitHubCache] = None,
        config: Optional[dict] = None
    ):
        """
        Initialize the GitHub client.

        Args:
            token: GitHub personal access token. If not provided,
                   reads from GITHUB_TOKEN environment variable.
            cache: Optional GitHubCache instance for caching API responses.
                   If not provided, creates one from config or uses defaults.
            config: Optional configuration dictionary for cache settings.
        """
        token = token or os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError(
                "GitHub token required. Set GITHUB_TOKEN environment variable "
                "or pass token to constructor."
            )
        self.github = Github(auth=Auth.Token(token))
        self._user = None
        self.config = config or {}

        # Initialize cache
        if cache is not None:
            self.cache = cache
        else:
            self.cache = GitHubCache.from_config(config)

    @property
    def user(self):
        """Get the authenticated user (cached)."""
        if self._user is None:
            self._user = self.github.get_user()
        return self._user

    def list_repositories(
            self,
            include_private: bool = True,
            include_orgs: bool = True,
            excluded_patterns: Optional[list[str]] = None,
            use_cache: bool = True
    ) -> list[RepoInfo]:
        """
        List all repositories accessible to the authenticated user.

        Args:
            include_private: Include private repositories
            include_orgs: Include repositories from organizations
            excluded_patterns: Glob patterns for repos to exclude (e.g., "archived-*")
            use_cache: Whether to use cached results if available

        Returns:
            List of RepoInfo objects
        """
        excluded_patterns = excluded_patterns or []

        # Check cache first
        cache_key = make_repo_list_key(self.user.login, include_private, include_orgs)
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for repository list: {cache_key}")
                # Apply exclusion patterns to cached results
                return [
                    r for r in cached
                    if not any(fnmatch.fnmatch(r.name, p) for p in excluded_patterns)
                ]

        repos = []

        # Get user's repos
        for repo in self.user.get_repos():
            # Filter by visibility
            if repo.private and not include_private:
                continue

            # Filter by owner (skip org repos if not included)
            if repo.owner.login != self.user.login and not include_orgs:
                continue

            repos.append(RepoInfo(
                full_name=repo.full_name,
                name=repo.name,
                description=repo.description,
                language=repo.language,
                is_private=repo.private,
                default_branch=repo.default_branch,
                url=repo.html_url
            ))

        # Cache the unfiltered results (exclusion patterns are applied after)
        ttl = self.cache.get_ttl_for_type(GitHubCache.PREFIX_REPO_LIST, self.config)
        self.cache.set(cache_key, repos, ttl=ttl)
        logger.debug(f"Cached repository list: {cache_key} ({len(repos)} repos)")

        # Apply exclusion patterns
        return [
            r for r in repos
            if not any(fnmatch.fnmatch(r.name, p) for p in excluded_patterns)
        ]

    def get_repository(self, repo_name: str, use_cache: bool = True) -> Repository:
        """
        Get a specific repository by name.

        Args:
            repo_name: Full repository name (e.g., "username/repo")
            use_cache: Whether to use cached results if available

        Returns:
            GitHub Repository object

        Note:
            Repository objects themselves are not cached (they contain methods),
            but this method is kept for consistency with the caching interface.
            The actual caching happens at the data level (file trees, content).
        """
        return self.github.get_repo(repo_name)

    def get_file_tree(
            self,
            repo: Repository,
            path: str = "",
            recursive: bool = True,
            use_cache: bool = True
    ) -> list[FileNode]:
        """
        Get the file tree for a repository.

        Args:
            repo: GitHub Repository object
            path: Starting path (empty for root)
            recursive: Whether to traverse subdirectories
            use_cache: Whether to use cached results if available

        Returns:
            List of FileNode objects
        """
        # Only cache complete tree (root path, recursive)
        cache_key = make_file_tree_key(repo.full_name, path)
        if use_cache and path == "" and recursive:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for file tree: {repo.full_name}")
                # Convert cached dicts back to FileNode objects
                return [FileNode(**node) if isinstance(node, dict) else node for node in cached]

        nodes = []

        try:
            contents = repo.get_contents(path)
        except Exception:
            return nodes

        # Handle single file case
        if not isinstance(contents, list):
            contents = [contents]

        for content in contents:
            # Skip ignored directories
            if content.type == "dir" and content.name in self.IGNORED_DIRS:
                continue

            node = FileNode(
                path=content.path,
                name=content.name,
                is_dir=(content.type == "dir"),
                size=content.size or 0,
                sha=content.sha
            )
            nodes.append(node)

            # Recurse into directories
            if recursive and content.type == "dir":
                nodes.extend(self.get_file_tree(repo, content.path, recursive, use_cache=False))

        # Cache the complete tree
        if path == "" and recursive:
            ttl = self.cache.get_ttl_for_type(GitHubCache.PREFIX_FILE_TREE, self.config)
            # Convert FileNode objects to dicts for JSON serialization
            cacheable_nodes = [
                {"path": n.path, "name": n.name, "is_dir": n.is_dir, "size": n.size, "sha": n.sha}
                for n in nodes
            ]
            self.cache.set(cache_key, cacheable_nodes, ttl=ttl)
            logger.debug(f"Cached file tree: {repo.full_name} ({len(nodes)} files)")

        return nodes

    def get_code_files(self, repo: Repository, use_cache: bool = True) -> list[FileNode]:
        """
        Get only code files (filtered by extension).

        Args:
            repo: GitHub Repository object
            use_cache: Whether to use cached results if available

        Returns:
            List of FileNode objects for code files only
        """
        all_files = self.get_file_tree(repo, use_cache=use_cache)
        return [
            f for f in all_files
            if not f.is_dir and Path(f.path).suffix in self.CODE_EXTENSIONS
        ]

    def get_file_content(
            self,
            repo: Repository,
            file_path: str,
            sha: Optional[str] = None,
            use_cache: bool = True
    ) -> Optional[str]:
        """
        Get the content of a specific file.

        Args:
            repo: GitHub Repository object
            file_path: Path to the file within the repository
            sha: Optional SHA of the file (for cache key - content is immutable by SHA)
            use_cache: Whether to use cached results if available

        Returns:
            File content as string, or None if unable to decode
        """
        try:
            # Check cache if SHA is provided (content is immutable for a given SHA)
            if use_cache and sha:
                cache_key = make_file_content_key(repo.full_name, file_path, sha)
                cached = self.cache.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for file content: {file_path}")
                    return cached

            content: ContentFile = repo.get_contents(file_path)
            if content.encoding == "base64":
                decoded = content.decoded_content.decode("utf-8")

                # Cache using the actual SHA from the content
                if use_cache:
                    actual_sha = sha or content.sha
                    cache_key = make_file_content_key(repo.full_name, file_path, actual_sha)
                    ttl = self.cache.get_ttl_for_type(GitHubCache.PREFIX_FILE_CONTENT, self.config)
                    self.cache.set(cache_key, decoded, ttl=ttl)
                    logger.debug(f"Cached file content: {file_path}")

                return decoded
            return None
        except UnicodeDecodeError as e:
            logger.warning(f"Unable to decode file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {file_path}: {e}")
            return None

    def get_language(self, file_path: str) -> Language:
        """Get the programming language for a file path."""
        ext = Path(file_path).suffix
        return Language.from_extension(ext)

    def invalidate_repo_cache(self, repo_name: str) -> None:
        """Invalidate all cached data for a specific repository.

        Args:
            repo_name: Full repository name (e.g., "username/repo")
        """
        # Invalidate file tree cache
        self.cache.invalidate(make_file_tree_key(repo_name, ""))

        # Invalidate all file content caches for this repo
        self.cache.invalidate_prefix(f"{GitHubCache.PREFIX_FILE_CONTENT}:{repo_name}")

        logger.info(f"Invalidated cache for repository: {repo_name}")

    def invalidate_all_cache(self) -> None:
        """Clear all cached GitHub API responses."""
        self.cache.clear()
        logger.info("Cleared all GitHub API cache")

    def get_cache_stats(self) -> dict:
        """Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        return self.cache.stats()
