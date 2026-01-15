"""Statistics tool for DNA bank insights."""

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

            # Try to get a sample to show variety
            try:
                sample = self.client.query(
                    collection_name=self.collection_name,
                    query_text="code pattern",
                    limit=10
                )

                languages = set()
                categories = set()
                repos = set()

                for res in sample:
                    metadata = res.metadata if hasattr(res, 'metadata') else {}
                    if 'language' in metadata:
                        languages.add(metadata['language'])
                    if 'category' in metadata:
                        categories.add(metadata['category'])
                    if 'source_repo' in metadata:
                        repos.add(metadata['source_repo'])

                if languages:
                    output += f"**Languages:** {', '.join(sorted(languages))}\n"
                if categories:
                    output += f"**Categories:** {', '.join(sorted(categories))}\n"
                if repos:
                    output += f"**Source Repos:** {', '.join(sorted(repos))}\n"

            except Exception:
                pass

            return output

        except Exception as e:
            return f"[ERROR] Error getting stats: {e}"
