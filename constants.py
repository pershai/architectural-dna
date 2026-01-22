"""Project-wide constants and magic numbers.

This module centralizes all magic numbers and hardcoded values that are used
across the codebase. Keeping them here makes it easier to find, modify, and
understand the configuration of the system.
"""

# =============================================================================
# Repository Processing
# =============================================================================

# Threshold for automatically switching to batch processing
# Repositories with more files than this will use BatchProcessor
LARGE_REPO_THRESHOLD = 50  # files

# =============================================================================
# Batch Processing
# =============================================================================

# Default values for BatchConfig (can be overridden in config.yaml)
DEFAULT_BATCH_SIZE = 10  # files per batch
DEFAULT_DELAY_BETWEEN_BATCHES = 0.5  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_PROGRESS_DIR = ".batch_progress"
DEFAULT_MIN_QUALITY = 5  # 1-10 scale

# Progress tracking
PROGRESS_SAVE_INTERVAL = 10  # save progress every N files
PROGRESS_NOTIFY_INTERVAL = 50  # notify callback every N patterns
PROGRESS_HASH_LENGTH = 12  # characters for progress file name hash

# Summary display
FAILED_FILES_DISPLAY_LIMIT = 5  # max failed files to show in summary

# =============================================================================
# Statistics
# =============================================================================

# Batch size for scrolling through Qdrant collection
STATS_SCROLL_BATCH_SIZE = 500

# =============================================================================
# Pattern Display
# =============================================================================

# Maximum characters to show when displaying pattern content
PATTERN_PREVIEW_LENGTH = 500

# =============================================================================
# LLM Configuration
# =============================================================================

# Default LLM model when using Gemini
DEFAULT_LLM_MODEL = "gemini-2.0-flash"

# Default number of patterns to gather for scaffolding
DEFAULT_PATTERN_LIMIT = 5

# =============================================================================
# GitHub API Caching
# =============================================================================

# Default TTL (time-to-live) for cached responses in seconds
DEFAULT_CACHE_TTL = 300  # 5 minutes

# TTL for different types of cached data
CACHE_TTL_REPO_LIST = 300  # 5 minutes - repository list changes infrequently
CACHE_TTL_FILE_TREE = 600  # 10 minutes - file structure is relatively stable
CACHE_TTL_FILE_CONTENT = 3600  # 1 hour - file content by SHA is immutable

# Maximum number of entries in the cache
DEFAULT_CACHE_MAX_SIZE = 1000

# Cache directory for persistent caching
DEFAULT_CACHE_DIR = ".github_cache"

# =============================================================================
# Server Configuration
# =============================================================================
# Note: Server host/port are configured via environment variables:
#   MCP_HOST (default: "0.0.0.0")
#   MCP_PORT (default: "8080")
# See dna_server.py for details.
