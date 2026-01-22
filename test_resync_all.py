"""Test script to resync all repositories via the DNA server."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import yaml
from qdrant_client import QdrantClient

from tools import RepositoryTool
from tools.batch_processor import BatchProcessor
from embedding_manager import EmbeddingManager

# Repos to sync
REPOS = [
    "pershai/ai-chat-bot",
    "pershai/ai_chat_bot_container",
    "pershai/architectural-dna",
    "pershai/file-agent",
    "pershai/film-finder",
    "pershai/outbox-pattern-demo",
    "pershai/sso-demo",
]


def main():
    print("=" * 60)
    print("Resync All Repositories Test")
    print("=" * 60)

    # Check for GitHub token
    if not os.getenv("GITHUB_TOKEN"):
        print("[ERROR] GITHUB_TOKEN not set")
        return

    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Initialize embedding manager
    embedding_manager = EmbeddingManager(config)

    # Initialize Qdrant client
    qdrant_url = os.getenv("QDRANT_URL", config["qdrant"]["url"])
    client = QdrantClient(url=qdrant_url)
    embedding_manager.setup_qdrant_client(client)

    collection_name = config["qdrant"]["collection_name"]

    # Ensure collection exists
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=client.get_fastembed_vector_params(),
        )

    # Get initial count
    info = client.get_collection(collection_name)
    initial_count = info.points_count
    print(f"\nInitial pattern count: {initial_count}")

    # Initialize batch processor
    batch_processor = BatchProcessor(client, collection_name, config)

    # Initialize repository tool with batch processor
    repo_tool = RepositoryTool(client, collection_name, config, batch_processor)

    print(f"\nSyncing {len(REPOS)} repositories...")
    print("-" * 60)

    for i, repo in enumerate(REPOS, 1):
        print(f"\n[{i}/{len(REPOS)}] Syncing: {repo}")

        try:
            # This will automatically use batch processing for large repos (>50 files)
            result = repo_tool.sync_github_repo(
                repo_name=repo,
                analyze_patterns=False,  # Skip LLM for faster testing
                min_quality=1
            )

            # Show summary
            if "[OK]" in result:
                # Extract key info from result
                lines = result.split("\n")
                for line in lines:
                    if "Files processed" in line or "Patterns stored" in line or "batch" in line.lower():
                        print(f"  {line.strip()}")
                print(f"  [OK] Done")
            else:
                print(f"  Result: {result[:200]}...")

        except Exception as e:
            print(f"  [ERROR] {e}")

    # Get final count
    info = client.get_collection(collection_name)
    final_count = info.points_count

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Initial patterns: {initial_count}")
    print(f"Final patterns: {final_count}")
    print(f"Change: {final_count - initial_count:+d}")
    print("=" * 60)


if __name__ == "__main__":
    main()
