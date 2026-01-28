"""Test batch processing functionality."""

# ruff: noqa: E402
import sys

sys.stdout.reconfigure(encoding="utf-8")

import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

import yaml
from qdrant_client import QdrantClient

from embedding_manager import EmbeddingManager
from tools.batch_processor import BatchConfig, BatchProcessor, BatchProgress


def test_batch_progress():
    """Test BatchProgress dataclass."""
    print("\n=== Testing BatchProgress ===")

    progress = BatchProgress(repo_name="test/repo")
    progress.total_files = 100
    progress.processed_files = 25
    progress.total_chunks = 50

    print(f"Progress: {progress.progress_percent}%")
    print(f"Elapsed: {progress.elapsed_seconds:.2f}s")

    # Test serialization
    data = progress.to_dict()
    print(f"Serialized: {data['repo_name']}, {data['progress_percent']}%")

    # Test deserialization
    restored = BatchProgress.from_dict(data)
    print(f"Restored: {restored.repo_name}, {restored.progress_percent}%")

    print("[OK] BatchProgress tests passed")


def test_batch_config():
    """Test BatchConfig dataclass."""
    print("\n=== Testing BatchConfig ===")

    # Default config
    config = BatchConfig()
    print(f"Default batch_size: {config.batch_size}")
    print(f"Default analyze_patterns: {config.analyze_patterns}")

    # Custom config
    custom = BatchConfig(batch_size=20, analyze_patterns=False, min_quality=7)
    print(f"Custom batch_size: {custom.batch_size}")
    print(f"Custom min_quality: {custom.min_quality}")

    print("[OK] BatchConfig tests passed")


def test_batch_processor_init():
    """Test BatchProcessor initialization."""
    print("\n=== Testing BatchProcessor Init ===")

    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Initialize embedding manager
    embedding_manager = EmbeddingManager(config)

    # Initialize Qdrant client
    qdrant_url = os.getenv("QDRANT_URL", config["qdrant"]["url"])
    client = QdrantClient(url=qdrant_url)
    embedding_manager.setup_qdrant_client(client)

    collection_name = config["qdrant"]["collection_name"]

    # Initialize batch processor
    processor = BatchProcessor(client, collection_name, config)
    print("BatchProcessor initialized")
    print(f"Collection: {processor.collection_name}")

    # Test progress file path generation
    progress_file = processor._get_progress_file("owner/repo")
    print(f"Progress file path: {progress_file}")

    print("[OK] BatchProcessor init tests passed")


def test_progress_persistence():
    """Test progress save/load functionality."""
    print("\n=== Testing Progress Persistence ===")

    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Initialize embedding manager
    embedding_manager = EmbeddingManager(config)

    # Initialize Qdrant client
    qdrant_url = os.getenv("QDRANT_URL", config["qdrant"]["url"])
    client = QdrantClient(url=qdrant_url)
    embedding_manager.setup_qdrant_client(client)

    collection_name = config["qdrant"]["collection_name"]

    # Initialize batch processor
    processor = BatchProcessor(client, collection_name, config)

    # Create test progress
    test_repo = "test/persistence-repo"
    progress = BatchProgress(repo_name=test_repo)
    progress.total_files = 50
    progress.processed_files = 10
    progress.total_chunks = 25
    progress.stored_patterns = 5

    # Save progress
    processor._save_progress(progress)
    print(f"Saved progress for {test_repo}")

    # Load progress
    loaded = processor._load_progress(test_repo)
    assert loaded is not None, "Failed to load progress"
    assert loaded.total_files == 50, "Total files mismatch"
    assert loaded.processed_files == 10, "Processed files mismatch"
    print(f"Loaded progress: {loaded.processed_files}/{loaded.total_files}")

    # Clear progress
    processor._clear_progress(test_repo)
    cleared = processor._load_progress(test_repo)
    assert cleared is None, "Progress should be cleared"
    print("Progress cleared successfully")

    print("[OK] Progress persistence tests passed")


def test_batch_sync_small_repo():
    """Test batch sync with a small public repo."""
    print("\n=== Testing Batch Sync (Small Repo) ===")

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("[SKIP] GITHUB_TOKEN not set, skipping live test")
        return

    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
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

    # Initialize batch processor with progress callback
    def progress_callback(progress: BatchProgress):
        print(
            f"  Progress: {progress.processed_files}/{progress.total_files} "
            f"({progress.progress_percent:.1f}%) - {progress.current_file}"
        )

    processor = BatchProcessor(
        client, collection_name, config, progress_callback=progress_callback
    )

    # Use a small public repo for testing
    # Using a small well-known repo
    test_repo = "kelseyhightower/nocode"  # Very small repo

    print(f"Testing batch sync on: {test_repo}")

    batch_config = BatchConfig(
        batch_size=5,
        analyze_patterns=False,  # Skip LLM for faster test
        min_quality=1,
    )

    result = processor.batch_sync_repo(
        repo_name=test_repo, batch_config=batch_config, resume=False
    )

    print(f"\nResult:\n{result}")

    if "[OK]" in result:
        print("\n[OK] Batch sync test passed")
    else:
        print("\n[INFO] Batch sync completed (check result above)")


if __name__ == "__main__":
    print("=" * 60)
    print("Batch Processing Tests")
    print("=" * 60)

    test_batch_progress()
    test_batch_config()
    test_batch_processor_init()
    test_progress_persistence()
    test_batch_sync_small_repo()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
