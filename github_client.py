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

logger = logging.getLogger(__name__)


class GitHubClient:
    """Handles GitHub API authentication and repository operations."""

    # File extensions to include when fetching code
    CODE_EXTENSIONS = {".py", ".java", ".js", ".ts", ".tsx", ".jsx", ".go", ".cs"}

    # Directories to skip
    IGNORED_DIRS = {
        ".git", "node_modules", "venv", "__pycache__",
        "dist", "build", "target", ".idea", ".vscode",
        "vendor", "deps", ".gradle", "bin", "obj"
    }

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub client.
        
        Args:
            token: GitHub personal access token. If not provided,
                   reads from GITHUB_TOKEN environment variable.
        """
        token = token or os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError(
                "GitHub token required. Set GITHUB_TOKEN environment variable "
                "or pass token to constructor."
            )
        self.github = Github(auth=Auth.Token(token))
        self._user = None

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
            excluded_patterns: Optional[list[str]] = None
    ) -> list[RepoInfo]:
        """
        List all repositories accessible to the authenticated user.
        
        Args:
            include_private: Include private repositories
            include_orgs: Include repositories from organizations
            excluded_patterns: Glob patterns for repos to exclude (e.g., "archived-*")
        
        Returns:
            List of RepoInfo objects
        """
        excluded_patterns = excluded_patterns or []
        repos = []

        # Get user's repos
        for repo in self.user.get_repos():
            # Filter by visibility
            if repo.private and not include_private:
                continue

            # Filter by owner (skip org repos if not included)
            if repo.owner.login != self.user.login and not include_orgs:
                continue

            # Check exclusion patterns
            if any(fnmatch.fnmatch(repo.name, pattern) for pattern in excluded_patterns):
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

        return repos

    def get_repository(self, repo_name: str) -> Repository:
        """
        Get a specific repository by name.
        
        Args:
            repo_name: Full repository name (e.g., "username/repo")
        
        Returns:
            GitHub Repository object
        """
        return self.github.get_repo(repo_name)

    def get_file_tree(
            self,
            repo: Repository,
            path: str = "",
            recursive: bool = True
    ) -> list[FileNode]:
        """
        Get the file tree for a repository.
        
        Args:
            repo: GitHub Repository object
            path: Starting path (empty for root)
            recursive: Whether to traverse subdirectories
        
        Returns:
            List of FileNode objects
        """
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
                nodes.extend(self.get_file_tree(repo, content.path, recursive))

        return nodes

    def get_code_files(self, repo: Repository) -> list[FileNode]:
        """
        Get only code files (filtered by extension).
        
        Args:
            repo: GitHub Repository object
        
        Returns:
            List of FileNode objects for code files only
        """
        all_files = self.get_file_tree(repo)
        return [
            f for f in all_files
            if not f.is_dir and Path(f.path).suffix in self.CODE_EXTENSIONS
        ]

    def get_file_content(self, repo: Repository, file_path: str) -> Optional[str]:
        """
        Get the content of a specific file.
        
        Args:
            repo: GitHub Repository object
            file_path: Path to the file within the repository
        
        Returns:
            File content as string, or None if unable to decode
        """
        try:
            content: ContentFile = repo.get_contents(file_path)
            if content.encoding == "base64":
                return content.decoded_content.decode("utf-8")
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
