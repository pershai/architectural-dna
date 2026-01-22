"""Caching layer for GitHub API responses.

This module provides an LRU cache with TTL (time-to-live) support for
GitHub API responses. It helps reduce API calls and improves performance
when repeatedly accessing the same data.
"""

import contextlib
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from constants import (
    CACHE_TTL_FILE_CONTENT,
    CACHE_TTL_FILE_TREE,
    CACHE_TTL_REPO_LIST,
    DEFAULT_CACHE_DIR,
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_CACHE_TTL,
)

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A single cache entry with value and expiration time."""

    value: Any
    expires_at: float

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() > self.expires_at


class GitHubCache:
    """LRU cache with TTL support for GitHub API responses.

    Features:
    - In-memory LRU cache with configurable max size
    - Per-entry TTL (time-to-live)
    - Optional disk persistence for cross-session caching
    - Thread-safe operations

    Usage:
        cache = GitHubCache(max_size=1000, cache_dir=".github_cache")

        # Store a value with default TTL
        cache.set("repos:user123", repo_list)

        # Store with custom TTL
        cache.set("file:sha123", content, ttl=3600)

        # Retrieve (returns None if expired or missing)
        repos = cache.get("repos:user123")

        # Invalidate specific key
        cache.invalidate("repos:user123")

        # Clear all cache
        cache.clear()
    """

    # Cache key prefixes for different data types
    PREFIX_REPO_LIST = "repos"
    PREFIX_FILE_TREE = "tree"
    PREFIX_FILE_CONTENT = "content"
    PREFIX_REPOSITORY = "repo"

    def __init__(
        self,
        max_size: int = DEFAULT_CACHE_MAX_SIZE,
        default_ttl: float = DEFAULT_CACHE_TTL,
        cache_dir: str | None = None,
        enabled: bool = True,
    ):
        """Initialize the cache.

        Args:
            max_size: Maximum number of entries in the cache
            default_ttl: Default time-to-live in seconds
            cache_dir: Directory for persistent cache (None to disable)
            enabled: Whether caching is enabled
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.enabled = enabled

        self._cache: dict[str, CacheEntry] = {}
        self._access_order: list[str] = []  # For LRU tracking
        self._lock = Lock()

        # Create cache directory if persistent caching is enabled
        if self.cache_dir and self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_persistent_cache()

    @classmethod
    def from_config(cls, config: dict | None = None) -> "GitHubCache":
        """Create a cache instance from configuration.

        Args:
            config: Configuration dictionary with github.cache section

        Returns:
            Configured GitHubCache instance
        """
        if config is None:
            return cls()

        cache_config = config.get("github", {}).get("cache", {})

        return cls(
            max_size=cache_config.get("max_size", DEFAULT_CACHE_MAX_SIZE),
            default_ttl=cache_config.get("ttl_repo_list", DEFAULT_CACHE_TTL),
            cache_dir=cache_config.get("cache_dir", DEFAULT_CACHE_DIR),
            enabled=cache_config.get("enabled", True),
        )

    def get_ttl_for_type(self, cache_type: str, config: dict | None = None) -> float:
        """Get the TTL for a specific cache type.

        Args:
            cache_type: One of PREFIX_REPO_LIST, PREFIX_FILE_TREE, PREFIX_FILE_CONTENT
            config: Optional config dictionary

        Returns:
            TTL in seconds
        """
        cache_config = {}
        if config:
            cache_config = config.get("github", {}).get("cache", {})

        ttl_map = {
            self.PREFIX_REPO_LIST: cache_config.get(
                "ttl_repo_list", CACHE_TTL_REPO_LIST
            ),
            self.PREFIX_FILE_TREE: cache_config.get(
                "ttl_file_tree", CACHE_TTL_FILE_TREE
            ),
            self.PREFIX_FILE_CONTENT: cache_config.get(
                "ttl_file_content", CACHE_TTL_FILE_CONTENT
            ),
            self.PREFIX_REPOSITORY: cache_config.get(
                "ttl_repo_list", CACHE_TTL_REPO_LIST
            ),
        }

        return ttl_map.get(cache_type, self.default_ttl)

    def _make_key(self, prefix: str, *args) -> str:
        """Create a cache key from prefix and arguments.

        Args:
            prefix: Key prefix (e.g., "repos", "tree")
            *args: Additional key components

        Returns:
            Cache key string
        """
        parts = [prefix] + [str(arg) for arg in args]
        return ":".join(parts)

    def _get_disk_path(self, key: str) -> Path | None:
        """Get the disk path for a cache key.

        Args:
            key: Cache key

        Returns:
            Path to the cache file, or None if disk caching is disabled
        """
        if not self.cache_dir:
            return None

        # Hash the key for safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value, or None if not found or expired
        """
        if not self.enabled:
            return None

        with self._lock:
            # Check in-memory cache first
            entry = self._cache.get(key)

            if entry is not None:
                if entry.is_expired():
                    self._remove_entry(key)
                    return None

                # Update access order for LRU
                self._update_access_order(key)
                return entry.value

            # Try disk cache if available
            disk_value = self._load_from_disk(key)
            if disk_value is not None:
                return disk_value

            return None

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (uses default if None)
        """
        if not self.enabled:
            return

        if ttl is None:
            ttl = self.default_ttl

        expires_at = time.time() + ttl
        entry = CacheEntry(value=value, expires_at=expires_at)

        with self._lock:
            # Evict if at capacity
            while len(self._cache) >= self.max_size:
                self._evict_oldest()

            self._cache[key] = entry
            self._update_access_order(key)

            # Save to disk if enabled
            self._save_to_disk(key, entry)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from the cache.

        Args:
            key: Cache key to invalidate
        """
        with self._lock:
            self._remove_entry(key)

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys with the given prefix.

        Args:
            prefix: Key prefix to match

        Returns:
            Number of entries removed
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix + ":")]
            for key in keys_to_remove:
                self._remove_entry(key)
            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

            # Clear disk cache
            if self.cache_dir and self.cache_dir.exists():
                for cache_file in self.cache_dir.glob("*.json"):
                    with contextlib.suppress(OSError):
                        cache_file.unlink()

    def stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            expired_count = sum(1 for e in self._cache.values() if e.is_expired())
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "expired_entries": expired_count,
                "enabled": self.enabled,
                "disk_cache": self.cache_dir is not None,
            }

    def _update_access_order(self, key: str) -> None:
        """Update the access order for LRU tracking."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def _evict_oldest(self) -> None:
        """Evict the least recently used entry."""
        if self._access_order:
            oldest_key = self._access_order[0]
            self._remove_entry(oldest_key)

    def _remove_entry(self, key: str) -> None:
        """Remove an entry from both memory and disk."""
        self._cache.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)

        # Remove from disk
        disk_path = self._get_disk_path(key)
        if disk_path and disk_path.exists():
            with contextlib.suppress(OSError):
                disk_path.unlink()

    def _save_to_disk(self, key: str, entry: CacheEntry) -> None:
        """Save a cache entry to disk."""
        disk_path = self._get_disk_path(key)
        if not disk_path:
            return

        try:
            data = {
                "key": key,
                "value": entry.value,
                "expires_at": entry.expires_at,
            }
            disk_path.write_text(json.dumps(data, default=str))
        except (OSError, TypeError) as e:
            logger.debug(f"Failed to save cache entry to disk: {e}")

    def _load_from_disk(self, key: str) -> Any | None:
        """Load a cache entry from disk."""
        disk_path = self._get_disk_path(key)
        if not disk_path or not disk_path.exists():
            return None

        try:
            data = json.loads(disk_path.read_text())
            expires_at = data.get("expires_at", 0)

            if time.time() > expires_at:
                # Expired, remove from disk
                disk_path.unlink()
                return None

            # Add to in-memory cache
            entry = CacheEntry(value=data["value"], expires_at=expires_at)
            self._cache[key] = entry
            self._update_access_order(key)

            return entry.value
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Failed to load cache entry from disk: {e}")
            return None

    def _load_persistent_cache(self) -> None:
        """Load all valid cache entries from disk on startup."""
        if not self.cache_dir or not self.cache_dir.exists():
            return

        loaded_count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(cache_file.read_text())
                expires_at = data.get("expires_at", 0)

                if time.time() > expires_at:
                    # Expired, remove
                    cache_file.unlink()
                    continue

                key = data.get("key")
                if key and len(self._cache) < self.max_size:
                    entry = CacheEntry(value=data["value"], expires_at=expires_at)
                    self._cache[key] = entry
                    self._access_order.append(key)
                    loaded_count += 1
            except (OSError, json.JSONDecodeError, KeyError):
                # Remove corrupted cache files
                with contextlib.suppress(OSError):
                    cache_file.unlink()

        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} cache entries from disk")


# Convenience functions for common cache operations


def make_repo_list_key(user: str, include_private: bool, include_orgs: bool) -> str:
    """Create cache key for repository list."""
    return f"{GitHubCache.PREFIX_REPO_LIST}:{user}:{include_private}:{include_orgs}"


def make_file_tree_key(repo_name: str, path: str = "") -> str:
    """Create cache key for file tree."""
    return f"{GitHubCache.PREFIX_FILE_TREE}:{repo_name}:{path}"


def make_file_content_key(repo_name: str, file_path: str, sha: str) -> str:
    """Create cache key for file content."""
    return f"{GitHubCache.PREFIX_FILE_CONTENT}:{repo_name}:{file_path}:{sha}"


def make_repository_key(repo_name: str) -> str:
    """Create cache key for repository metadata."""
    return f"{GitHubCache.PREFIX_REPOSITORY}:{repo_name}"
