#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migration script to recreate Qdrant collection with new embedding model."""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from embedding_manager import EmbeddingManager

# Load environment
load_dotenv()

# Load config
CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

print("=" * 70)
print("QDRANT COLLECTION MIGRATION")
print("=" * 70)

# Initialize
qdrant_url = os.getenv("QDRANT_URL", config["qdrant"]["url"])
COLLECTION_NAME = config["qdrant"]["collection_name"]

client = QdrantClient(url=qdrant_url)
embedding_manager = EmbeddingManager(config)

print(f"\nTarget configuration:")
print(f"  • Qdrant URL: {qdrant_url}")
print(f"  • Collection: {COLLECTION_NAME}")
print(f"  • New model: {embedding_manager.model}")
print(f"  • Vector size: {embedding_manager.get_vector_size()} dimensions")

# Check if collection exists
if client.collection_exists(COLLECTION_NAME):
    collection_info = client.get_collection(COLLECTION_NAME)
    print(f"\nCurrent collection info:")
    print(f"  • Points count: {collection_info.points_count}")
    print(f"  • Vector config: {collection_info.config.params.vectors}")

    # Ask user
    print(f"\n⚠️  WARNING: This will DELETE the existing collection and recreate it.")
    print(f"    All {collection_info.points_count} patterns will be LOST.")
    print(f"\nOptions:")
    print(f"  1. Recreate collection (delete all data)")
    print(f"  2. Cancel and keep existing collection")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "1":
        print(f"\nDeleting collection '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)
        print("✓ Collection deleted")
    else:
        print("\nCancelled. No changes made.")
        print("\nTo use the existing collection, update config.yaml to use the old model:")
        print("  embeddings:")
        print("    model: \"BAAI/bge-small-en-v1.5\"")
        sys.exit(0)
else:
    print(f"\nCollection '{COLLECTION_NAME}' does not exist yet.")

# Create collection with new embedding model
print(f"\nCreating collection with new embedding model...")
embedding_manager.setup_qdrant_client(client)

client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=client.get_fastembed_vector_params(),
)

collection_info = client.get_collection(COLLECTION_NAME)
print(f"✓ Collection created successfully")
print(f"  • Vector config: {collection_info.config.params.vectors}")

print("\n" + "=" * 70)
print("MIGRATION COMPLETE ✓")
print("=" * 70)

print(f"\nThe collection '{COLLECTION_NAME}' is now configured for:")
print(f"  • Model: {embedding_manager.model}")
print(f"  • Dimensions: {embedding_manager.get_vector_size()}")
print(f"\nYou can now:")
print(f"  1. Run 'python test_embeddings.py' to verify")
print(f"  2. Run 'python dna_server.py' to start the server")
print(f"  3. Use 'sync_github_repo()' to re-index your repositories")
