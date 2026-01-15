#!/bin/bash
# Docker entrypoint script for Architectural DNA

set -e

echo "========================================"
echo "Architectural DNA - Starting Up"
echo "========================================"

# Wait for Qdrant to be ready
echo "Waiting for Qdrant to be ready..."
until curl -sf http://qdrant:6333/healthz > /dev/null 2>&1; do
    echo "  Qdrant not ready yet, waiting..."
    sleep 2
done
echo "✓ Qdrant is ready"

# Check environment variables
echo ""
echo "Checking configuration..."
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  WARNING: GITHUB_TOKEN not set"
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  WARNING: GEMINI_API_KEY not set"
fi

echo "✓ Environment configured"

# Display embedding configuration
echo ""
echo "Embedding Configuration:"
python -c "
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    print(f\"  • Model: {config['embeddings']['model']}\")
    print(f\"  • Hybrid Search: {config['search']['hybrid_enabled']}\")
"

# Initialize collection if needed
echo ""
echo "Initializing Qdrant collection..."
python - <<EOF
import os
import yaml
from qdrant_client import QdrantClient
from embedding_manager import EmbeddingManager

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

client = QdrantClient(url=os.getenv('QDRANT_URL', 'http://qdrant:6333'))
collection_name = config['qdrant']['collection_name']

if not client.collection_exists(collection_name):
    print(f"  Creating collection '{collection_name}'...")
    embedding_manager = EmbeddingManager(config)
    embedding_manager.setup_qdrant_client(client)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=client.get_fastembed_vector_params(),
    )
    print(f"  ✓ Collection '{collection_name}' created")
else:
    collection_info = client.get_collection(collection_name)
    print(f"  ✓ Collection '{collection_name}' exists ({collection_info.points_count} patterns)")
EOF

echo ""
echo "========================================"
echo "Starting MCP Server..."
echo "========================================"
echo ""

# Execute the main command
exec "$@"
