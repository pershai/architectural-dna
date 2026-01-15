"""
Architectural DNA MCP Server

An MCP server that:
1. Connects to your GitHub repositories
2. Extracts code patterns using LLM analysis
3. Stores patterns in a Qdrant vector database
4. Enables RAG-powered project scaffolding

Usage:
    python dna_server.py         # stdio mode (local)
    python dna_server.py --sse   # SSE mode (Docker/remote)

Environment variables can be set via:
    - .env file
    - Docker environment
    - MCP client headers (X-GITHUB-TOKEN, X-GEMINI-API-KEY, X-QDRANT-URL)
"""

import os
import logging

# Disable FastMCP banner and logging to prevent stdout pollution
os.environ["FASTMCP_SHOW_CLI_BANNER"] = "false"
os.environ["FASTMCP_LOG_ENABLED"] = "false"

from pathlib import Path
from typing import Optional
from contextvars import ContextVar

import yaml
from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from qdrant_client import QdrantClient

from tools import PatternTool, RepositoryTool, ScaffoldTool, StatsTool
from embedding_manager import EmbeddingManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dna_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (can be overridden by headers)
load_dotenv()


def get_env_or_header(key: str, header_key: str, default: str = None) -> str:
    """Get value from environment variable, with header override support.

    Priority: Environment variable > Default
    Headers are handled at request time via middleware.
    """
    return os.getenv(key, default)

# Load configuration
CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Initialize MCP server
mcp = FastMCP("Architectural DNA")

# Initialize embedding manager
embedding_manager = EmbeddingManager(config)
logger.info(f"Embedding model: {embedding_manager.model} ({embedding_manager.get_vector_size()} dimensions)")

# Initialize Qdrant client with configured embeddings
qdrant_url = os.getenv("QDRANT_URL", config["qdrant"]["url"])
client = QdrantClient(url=qdrant_url)
COLLECTION_NAME = config["qdrant"]["collection_name"]

# Set up the embedding model and ensure collection exists
embedding_manager.setup_qdrant_client(client)
if not client.collection_exists(COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=client.get_fastembed_vector_params(),
    )

# Initialize tool classes
pattern_tool = PatternTool(client, COLLECTION_NAME, config)
repository_tool = RepositoryTool(client, COLLECTION_NAME, config)
scaffold_tool = ScaffoldTool(client, COLLECTION_NAME, config)
stats_tool = StatsTool(client, COLLECTION_NAME, config)


# ==============================================================================
# MCP Tool Registrations
# ==============================================================================

@mcp.tool()
def store_pattern(
        content: str,
        title: str,
        description: str,
        category: str,
        language: str = "python",
        quality_score: int = 5,
        source_repo: str = "manual",
        source_path: str = "",
        use_cases: list[str] = None
) -> str:
    """
    Stores a high-quality code snippet or architectural pattern in the DNA bank.

    Args:
        content: The code content to store (min 10 chars)
        title: Pattern title (3-200 chars)
        description: A detailed description (min 10 chars)
        category: Pattern category (architecture, error_handling, configuration, etc.)
        language: Programming language (python, java, typescript, go)
        quality_score: Quality rating 1-10 (default: 5)
        source_repo: Source repository name (default: "manual")
        source_path: Source file path (default: "")
        use_cases: List of use case descriptions (default: [])

    Returns:
        Confirmation message
    """
    return pattern_tool.store_pattern(
        content=content,
        title=title,
        description=description,
        category=category,
        language=language,
        quality_score=quality_score,
        source_repo=source_repo,
        source_path=source_path,
        use_cases=use_cases
    )


@mcp.tool()
def search_dna(
        query: str,
        language: Optional[str] = None,
        category: Optional[str] = None,
        min_quality: int = 5,
        limit: int = 10
) -> str:
    """
    Searches the DNA bank for best practices matching the query.

    Args:
        query: Natural language description (min 3 chars)
        language: Filter by programming language (python, java, typescript, go)
        category: Filter by pattern category (architecture, error_handling, etc.)
        min_quality: Minimum quality score 1-10 (default: 5)
        limit: Maximum results to return 1-100 (default: 10)

    Returns:
        Formatted list of matching patterns with their code
    """
    return pattern_tool.search_dna(
        query=query,
        language=language,
        category=category,
        min_quality=min_quality,
        limit=limit
    )


@mcp.tool()
def list_my_repos(include_private: bool = True, include_orgs: bool = True) -> str:
    """
    Lists all your GitHub repositories available for DNA extraction.

    Args:
        include_private: Include private repositories
        include_orgs: Include repositories from organizations you belong to

    Returns:
        Formatted list of repositories with their details
    """
    return repository_tool.list_my_repos(
        include_private=include_private,
        include_orgs=include_orgs
    )


@mcp.tool()
def sync_github_repo(
        repo_name: str,
        analyze_patterns: bool = True,
        min_quality: int = 5
) -> str:
    """
    Syncs a GitHub repository into the DNA bank.

    Fetches code from the repository, extracts patterns, optionally analyzes
    them with LLM, and stores high-quality patterns in the vector database.

    Args:
        repo_name: Full repository name (e.g., "username/repo-name")
        analyze_patterns: If True, use LLM to identify and rate patterns
        min_quality: Minimum quality score (1-10) for patterns to store

    Returns:
        Summary of the sync operation
    """
    return repository_tool.sync_github_repo(
        repo_name=repo_name,
        analyze_patterns=analyze_patterns,
        min_quality=min_quality
    )


@mcp.tool()
def scaffold_project(
        project_name: str,
        project_type: str,
        tech_stack: str,
        output_dir: Optional[str] = None
) -> str:
    """
    Scaffolds a new project using best practices from the DNA bank.

    Searches for relevant patterns based on the project type and tech stack,
    then generates a complete project structure with files.

    Args:
        project_name: Name for the new project (will be the directory name)
        project_type: Type of project - "api", "cli", "library", or "web-app"
        tech_stack: Comma-separated technologies (e.g., "python, fastapi, postgresql")
        output_dir: Directory to create the project in (defaults to ./generated_projects)

    Returns:
        Path to the created project and summary of what was generated
    """
    return scaffold_tool.scaffold_project(
        project_name=project_name,
        project_type=project_type,
        tech_stack=tech_stack,
        output_dir=output_dir
    )


@mcp.tool()
def get_dna_stats() -> str:
    """
    Get statistics about the DNA bank.

    Returns:
        Statistics including total patterns, languages, categories, and top sources
    """
    return stats_tool.get_dna_stats()


@mcp.tool()
def get_embedding_info() -> str:
    """
    Get information about the current embedding configuration.

    Returns:
        Embedding model details and configuration
    """
    info = embedding_manager.get_model_info()

    output = "[*] **Embedding Configuration**\n\n"
    output += f"**Provider:** {info['provider']}\n"
    output += f"**Model:** {info['model']}\n"
    output += f"**Vector Size:** {info['vector_size']} dimensions\n"
    output += f"**Chunking:** {'Enabled' if info['chunking_enabled'] else 'Disabled'}\n\n"

    output += "**Preprocessing:**\n"
    for key, value in info['preprocessing'].items():
        output += f"  - {key}: {value}\n"

    output += "\n**Supported Models:**\n"
    for model, dims in EmbeddingManager.SUPPORTED_MODELS.items():
        current = " (current)" if model == info['model'] else ""
        output += f"  - {model} ({dims}d){current}\n"

    return output


def apply_header_overrides(headers: dict) -> dict:
    """Apply environment overrides from request headers.

    Supported headers:
        X-GITHUB-TOKEN: Override GITHUB_TOKEN
        X-GEMINI-API-KEY: Override GEMINI_API_KEY
        X-QDRANT-URL: Override QDRANT_URL

    Returns dict of applied overrides for logging.
    """
    overrides = {}

    header_mapping = {
        "x-github-token": "GITHUB_TOKEN",
        "x-gemini-api-key": "GEMINI_API_KEY",
        "x-qdrant-url": "QDRANT_URL",
    }

    for header_name, env_name in header_mapping.items():
        value = headers.get(header_name)
        if value:
            os.environ[env_name] = value
            overrides[env_name] = "***" if "token" in header_name or "key" in header_name else value

    return overrides


if __name__ == "__main__":
    import sys

    # Check for server mode
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8080"))

    logger.info(
        f"Starting Architectural DNA MCP Server "
        f"(Qdrant: {qdrant_url}, Collection: {COLLECTION_NAME})"
    )

    if transport == "sse" or "--sse" in sys.argv:
        # Run as HTTP/SSE server (for Docker/remote access)
        logger.info(f"Running in SSE mode on http://{host}:{port}")
        logger.info("Headers supported: X-GITHUB-TOKEN, X-GEMINI-API-KEY, X-QDRANT-URL")

        # Add middleware to handle header-based auth
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request

        class HeaderAuthMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                # Extract headers and apply overrides
                headers = {k.lower(): v for k, v in request.headers.items()}
                overrides = apply_header_overrides(headers)
                if overrides:
                    logger.info(f"Applied header overrides: {list(overrides.keys())}")
                return await call_next(request)

        # Get the underlying Starlette app and add middleware
        mcp.run(transport="sse", host=host, port=port)
    else:
        # Run in stdio mode (for local MCP clients)
        logger.info("Running in stdio mode")
        mcp.run()
