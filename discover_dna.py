import os
from pathlib import Path

import yaml
from qdrant_client import QdrantClient

# Load configuration
with open(Path(__file__).parent / "config.yaml") as f:
    config = yaml.safe_load(f)

# Initialize client with config
client = QdrantClient(url=config["qdrant"]["url"])
COLLECTION_NAME = config["qdrant"]["collection_name"]
IGNORED_DIRS = set(config["discovery"]["ignored_dirs"])
SUPPORTED_EXTENSIONS = set(config["discovery"]["supported_extensions"])


def get_code_chunks(root_dir):
    """Walks the directory and yields file content with metadata."""
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                file_path = os.path.join(root, file)
                with open(file_path, encoding="utf-8") as f:
                    yield f.read(), file_path


def discover_and_index(directory_path):
    print(f"[*] Starting discovery in: {directory_path}")

    for content, path in get_code_chunks(directory_path):
        # In a real scenario, you'd send a small snippet to an LLM here:
        # "Is this snippet a reusable pattern? If yes, provide a 1-sentence summary."

        # For now, we index the file with its path as the description
        description = f"Pattern found in {os.path.relpath(path, directory_path)}"

        print(f"[+] Indexing: {path}")
        client.add(
            collection_name=COLLECTION_NAME,
            documents=[content],
            metadata=[{"path": path, "description": description}],
        )


if __name__ == "__main__":
    # Point this to your current project folder
    project_to_crawl = "./src"
    discover_and_index(project_to_crawl)
