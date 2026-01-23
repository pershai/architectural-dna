"""Tests for GitHub API caching."""

import time
import pytest
from unittest.mock import Mock, patch

from github_cache import (
    GitHubCache,
    CacheEntry,
    make_repo_list_key,
    make_file_tree_key,
    make_file_content_key,
    make_repository_key,
)
from constants import (
    CACHE_TTL_REPO_LIST,
    CACHE_TTL_FILE_TREE,
    CACHE_TTL_FILE_CONTENT,
    DEFAULT_CACHE_MAX_SIZE,
)


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_entry_not_expired(self):
        """Test entry that hasn't expired yet."""
        entry = CacheEntry(value="test", expires_at=time.time() + 100)
        assert not entry.is_expired()

    def test_entry_expired(self):
        """Test entry that has expired."""
        entry = CacheEntry(value="test", expires_at=time.time() - 100)
        assert entry.is_expired()

    def test_entry_just_expired(self):
        """Test entry that just expired."""
        entry = CacheEntry(value="test", expires_at=time.time() - 0.001)
        assert entry.is_expired()


class TestGitHubCache:
    """Tests for GitHubCache class."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance without disk persistence."""
        return GitHubCache(max_size=10, default_ttl=60, cache_dir=None)

    @pytest.fixture
    def cache_with_disk(self, tmp_path):
        """Create a cache instance with disk persistence."""
        cache_dir = tmp_path / "cache"
        return GitHubCache(max_size=10, default_ttl=60, cache_dir=str(cache_dir))

    # ==========================================================================
    # Basic cache operations
    # ==========================================================================

    def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self, cache):
        """Test getting a key that doesn't exist."""
        assert cache.get("nonexistent") is None

    def test_get_expired_entry(self, cache):
        """Test getting an expired entry returns None."""
        cache.set("key1", "value1", ttl=0.001)
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_cache_disabled(self):
        """Test that disabled cache doesn't store or retrieve."""
        cache = GitHubCache(enabled=False)
        cache.set("key1", "value1")
        assert cache.get("key1") is None

    def test_set_with_custom_ttl(self, cache):
        """Test setting with custom TTL."""
        cache.set("key1", "value1", ttl=3600)
        entry = cache._cache.get("key1")
        assert entry is not None
        assert entry.expires_at > time.time() + 3500

    # ==========================================================================
    # LRU eviction
    # ==========================================================================

    def test_lru_eviction(self):
        """Test that LRU eviction works when cache is full."""
        cache = GitHubCache(max_size=3, default_ttl=60, cache_dir=None)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key4, should evict key2 (least recently used)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"  # Still there (recently accessed)
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_respects_max_size(self):
        """Test that cache never exceeds max size."""
        cache = GitHubCache(max_size=5, default_ttl=60, cache_dir=None)

        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        assert len(cache._cache) <= 5

    # ==========================================================================
    # Invalidation
    # ==========================================================================

    def test_invalidate_key(self, cache):
        """Test invalidating a specific key."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.invalidate("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_invalidate_nonexistent_key(self, cache):
        """Test invalidating a key that doesn't exist (no error)."""
        cache.invalidate("nonexistent")  # Should not raise

    def test_invalidate_prefix(self, cache):
        """Test invalidating all keys with a prefix."""
        cache.set("repos:user1:True:True", ["repo1"])
        cache.set("repos:user2:True:False", ["repo2"])
        cache.set("tree:repo1:", [])

        removed = cache.invalidate_prefix("repos")

        assert removed == 2
        assert cache.get("repos:user1:True:True") is None
        assert cache.get("repos:user2:True:False") is None
        assert cache.get("tree:repo1:") == []

    def test_clear(self, cache):
        """Test clearing all cache entries."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert len(cache._cache) == 0

    # ==========================================================================
    # Configuration
    # ==========================================================================

    def test_from_config_default(self):
        """Test creating cache from empty config."""
        cache = GitHubCache.from_config(None)
        assert cache.enabled is True
        assert cache.max_size == DEFAULT_CACHE_MAX_SIZE

    def test_from_config_custom(self):
        """Test creating cache from custom config."""
        config = {
            "github": {
                "cache": {
                    "enabled": True,
                    "max_size": 500,
                    "ttl_repo_list": 600,
                    "cache_dir": ".test_cache"
                }
            }
        }
        cache = GitHubCache.from_config(config)
        assert cache.enabled is True
        assert cache.max_size == 500
        assert cache.default_ttl == 600

    def test_from_config_disabled(self):
        """Test creating disabled cache from config."""
        config = {
            "github": {
                "cache": {
                    "enabled": False
                }
            }
        }
        cache = GitHubCache.from_config(config)
        assert cache.enabled is False

    def test_get_ttl_for_type(self, cache):
        """Test getting TTL for different cache types."""
        assert cache.get_ttl_for_type(GitHubCache.PREFIX_REPO_LIST) == CACHE_TTL_REPO_LIST
        assert cache.get_ttl_for_type(GitHubCache.PREFIX_FILE_TREE) == CACHE_TTL_FILE_TREE
        assert cache.get_ttl_for_type(GitHubCache.PREFIX_FILE_CONTENT) == CACHE_TTL_FILE_CONTENT
        assert cache.get_ttl_for_type("unknown") == cache.default_ttl

    def test_get_ttl_for_type_from_config(self, cache):
        """Test getting TTL from config."""
        config = {
            "github": {
                "cache": {
                    "ttl_repo_list": 100,
                    "ttl_file_tree": 200,
                    "ttl_file_content": 300
                }
            }
        }
        assert cache.get_ttl_for_type(GitHubCache.PREFIX_REPO_LIST, config) == 100
        assert cache.get_ttl_for_type(GitHubCache.PREFIX_FILE_TREE, config) == 200
        assert cache.get_ttl_for_type(GitHubCache.PREFIX_FILE_CONTENT, config) == 300

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def test_stats(self, cache):
        """Test cache statistics."""
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=0.001)
        time.sleep(0.01)

        stats = cache.stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 10
        assert stats["expired_entries"] == 1
        assert stats["enabled"] is True
        assert stats["disk_cache"] is False

    def test_stats_with_disk_cache(self, cache_with_disk):
        """Test stats show disk cache is enabled."""
        stats = cache_with_disk.stats()
        assert stats["disk_cache"] is True

    # ==========================================================================
    # Disk persistence
    # ==========================================================================

    def test_disk_cache_save_and_load(self, cache_with_disk):
        """Test saving and loading from disk."""
        cache_with_disk.set("key1", {"data": "test"})

        # Verify file was created
        cache_files = list(cache_with_disk.cache_dir.glob("*.json"))
        assert len(cache_files) == 1

        # Create new cache and verify it loads from disk
        new_cache = GitHubCache(
            max_size=10,
            default_ttl=60,
            cache_dir=str(cache_with_disk.cache_dir)
        )
        assert new_cache.get("key1") == {"data": "test"}

    def test_disk_cache_removes_expired(self, tmp_path):
        """Test that expired entries are removed from disk on load."""
        cache_dir = tmp_path / "cache"
        cache = GitHubCache(max_size=10, default_ttl=0.001, cache_dir=str(cache_dir))
        cache.set("key1", "value1")

        time.sleep(0.01)

        # Create new cache, should not load expired entry
        new_cache = GitHubCache(max_size=10, default_ttl=60, cache_dir=str(cache_dir))
        assert new_cache.get("key1") is None
        assert len(list(cache_dir.glob("*.json"))) == 0

    def test_disk_cache_clear(self, cache_with_disk):
        """Test clearing disk cache."""
        cache_with_disk.set("key1", "value1")
        cache_with_disk.set("key2", "value2")

        cache_with_disk.clear()

        cache_files = list(cache_with_disk.cache_dir.glob("*.json"))
        assert len(cache_files) == 0

    def test_disk_cache_invalidate(self, cache_with_disk):
        """Test invalidating removes from disk."""
        cache_with_disk.set("key1", "value1")

        cache_with_disk.invalidate("key1")

        cache_files = list(cache_with_disk.cache_dir.glob("*.json"))
        assert len(cache_files) == 0

    # ==========================================================================
    # Key generation helpers
    # ==========================================================================

    def test_make_repo_list_key(self):
        """Test repo list key generation."""
        key = make_repo_list_key("user123", True, False)
        assert key == "repos:user123:True:False"

    def test_make_file_tree_key(self):
        """Test file tree key generation."""
        key = make_file_tree_key("user/repo", "src")
        assert key == "tree:user/repo:src"

        key_root = make_file_tree_key("user/repo", "")
        assert key_root == "tree:user/repo:"

    def test_make_file_content_key(self):
        """Test file content key generation."""
        key = make_file_content_key("user/repo", "src/main.py", "abc123")
        assert key == "content:user/repo:src/main.py:abc123"

    def test_make_repository_key(self):
        """Test repository key generation."""
        key = make_repository_key("user/repo")
        assert key == "repo:user/repo"


class TestGitHubClientCacheIntegration:
    """Tests for GitHubClient cache integration."""

    @pytest.fixture
    def mock_github(self):
        """Create mock GitHub API objects."""
        with patch('github_client.Github') as mock:
            mock_user = Mock()
            mock_user.login = "testuser"
            mock_user.get_repos.return_value = []

            mock_instance = Mock()
            mock_instance.get_user.return_value = mock_user

            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def client_with_cache(self, mock_github):
        """Create a GitHubClient with caching."""
        from github_client import GitHubClient
        cache = GitHubCache(max_size=100, default_ttl=60, cache_dir=None)
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'test-token'}):
            client = GitHubClient(cache=cache)
            return client

    def test_client_creates_default_cache(self, mock_github):
        """Test that client creates a cache if not provided."""
        from github_client import GitHubClient
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'test-token'}):
            client = GitHubClient()
            assert client.cache is not None
            assert isinstance(client.cache, GitHubCache)

    def test_client_uses_provided_cache(self, mock_github):
        """Test that client uses provided cache."""
        from github_client import GitHubClient
        cache = GitHubCache(max_size=50, enabled=False)
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'test-token'}):
            client = GitHubClient(cache=cache)
            assert client.cache is cache
            assert client.cache.max_size == 50

    def test_list_repositories_caches_result(self, client_with_cache, mock_github):
        """Test that list_repositories caches its result."""

        mock_repo = Mock()
        mock_repo.full_name = "testuser/repo1"
        mock_repo.name = "repo1"
        mock_repo.description = "Test repo"
        mock_repo.language = "Python"
        mock_repo.private = False
        mock_repo.default_branch = "main"
        mock_repo.html_url = "https://github.com/testuser/repo1"
        mock_repo.owner.login = "testuser"

        client_with_cache.user.get_repos.return_value = [mock_repo]

        # First call should hit the API
        result1 = client_with_cache.list_repositories()
        assert len(result1) == 1

        # Second call should use cache (API should be called only once)
        result2 = client_with_cache.list_repositories()
        assert len(result2) == 1
        assert client_with_cache.user.get_repos.call_count == 1

    def test_list_repositories_bypasses_cache(self, client_with_cache, mock_github):
        """Test that use_cache=False bypasses cache."""
        mock_repo = Mock()
        mock_repo.full_name = "testuser/repo1"
        mock_repo.name = "repo1"
        mock_repo.description = "Test"
        mock_repo.language = "Python"
        mock_repo.private = False
        mock_repo.default_branch = "main"
        mock_repo.html_url = "https://github.com/testuser/repo1"
        mock_repo.owner.login = "testuser"

        client_with_cache.user.get_repos.return_value = [mock_repo]

        # First call
        client_with_cache.list_repositories(use_cache=False)

        # Second call with cache bypass
        client_with_cache.list_repositories(use_cache=False)

        # API should be called twice
        assert client_with_cache.user.get_repos.call_count == 2

    def test_invalidate_repo_cache(self, client_with_cache):
        """Test invalidating cache for a specific repo."""
        # Pre-populate cache
        client_with_cache.cache.set("tree:user/repo:", [{"path": "test.py"}])
        client_with_cache.cache.set("content:user/repo:test.py:abc123", "code")

        client_with_cache.invalidate_repo_cache("user/repo")

        assert client_with_cache.cache.get("tree:user/repo:") is None
        assert client_with_cache.cache.get("content:user/repo:test.py:abc123") is None

    def test_invalidate_all_cache(self, client_with_cache):
        """Test clearing all cache."""
        client_with_cache.cache.set("key1", "value1")
        client_with_cache.cache.set("key2", "value2")

        client_with_cache.invalidate_all_cache()

        assert client_with_cache.cache.get("key1") is None
        assert client_with_cache.cache.get("key2") is None

    def test_get_cache_stats(self, client_with_cache):
        """Test getting cache stats through client."""
        client_with_cache.cache.set("key1", "value1")

        stats = client_with_cache.get_cache_stats()

        assert stats["size"] == 1
        assert "max_size" in stats
        assert "enabled" in stats
