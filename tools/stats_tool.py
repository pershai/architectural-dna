"""Statistics tool for DNA bank insights."""

from collections import Counter

from constants import STATS_SCROLL_BATCH_SIZE

from .base import BaseTool


class StatsTool(BaseTool):
    """Tool for retrieving DNA bank statistics and insights."""

    def get_dna_stats(self) -> str:
        """
        Get statistics about the DNA bank.

        Returns:
            Statistics including total patterns, languages, categories, and top sources
        """
        try:
            # Get collection info
            collection_info = self.client.get_collection(self.collection_name)
            total_points = collection_info.points_count

            if total_points == 0:
                return (
                    "[*] **DNA Bank is empty**\n\n"
                    "Get started by:\n"
                    "1. Run `list_my_repos()` to see your GitHub repositories\n"
                    "2. Run `sync_github_repo('username/repo')` to index patterns\n"
                    "3. Or use `store_pattern(code, description)` to manually add patterns"
                )

            output = "[*] **DNA Bank Statistics**\n\n"
            output += f"**Total Patterns:** {total_points}\n\n"

            # Scroll through all patterns to get accurate statistics
            try:
                languages = Counter()
                categories = Counter()
                repos = Counter()

                # Use scroll to iterate through all points
                # Only fetch the metadata fields we need (not full code content)
                from qdrant_client.models import PayloadSelectorInclude

                offset = None
                batch_size = STATS_SCROLL_BATCH_SIZE

                while True:
                    results, offset = self.client.scroll(
                        collection_name=self.collection_name,
                        limit=batch_size,
                        offset=offset,
                        with_payload=PayloadSelectorInclude(
                            include=["language", "category", "source_repo"]
                        ),
                        with_vectors=False,
                    )

                    if not results:
                        break

                    for point in results:
                        payload = point.payload or {}
                        if "language" in payload:
                            languages[payload["language"]] += 1
                        if "category" in payload:
                            categories[payload["category"]] += 1
                        if "source_repo" in payload:
                            repos[payload["source_repo"]] += 1

                    if offset is None:
                        break

                if languages:
                    output += "**Languages:**\n"
                    for lang, count in languages.most_common():
                        output += f"  - {lang}: {count}\n"
                    output += "\n"

                if categories:
                    output += "**Categories:**\n"
                    for cat, count in categories.most_common():
                        output += f"  - {cat}: {count}\n"
                    output += "\n"

                if repos:
                    output += "**Source Repos:**\n"
                    for repo, count in repos.most_common():
                        output += f"  - {repo}: {count}\n"

            except Exception as e:
                self.logger.warning(f"Error aggregating stats: {e}")

            return output

        except Exception as e:
            return f"[ERROR] Error getting stats: {e}"
