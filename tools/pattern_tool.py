"""Pattern management tools for storing and searching code patterns."""

from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

from hybrid_search import HybridSearcher
from models import SearchDNAInput, StorePatternInput

from .base import BaseTool


class PatternTool(BaseTool):
    """Tool for managing code patterns in the DNA bank."""

    def __init__(self, *args, **kwargs):
        """Initialize PatternTool with hybrid searcher."""
        super().__init__(*args, **kwargs)
        self.hybrid_searcher = HybridSearcher(self.config)

    def store_pattern(
        self,
        content: str,
        title: str,
        description: str,
        category: str,
        language: str = "python",
        quality_score: int = 5,
        source_repo: str = "manual",
        source_path: str = "",
        use_cases: list[str] = None,
    ) -> str:
        """
        Store a high-quality code snippet or architectural pattern in the DNA bank.

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
        try:
            # Validate input using Pydantic
            validated = StorePatternInput(
                content=content,
                title=title,
                description=description,
                category=category,
                language=language,
                quality_score=quality_score,
                source_repo=source_repo,
                source_path=source_path,
                use_cases=use_cases or [],
            )

            # Store pattern
            self.client.add(
                collection_name=self.collection_name,
                documents=[validated.content],
                metadata=[
                    {
                        "title": validated.title,
                        "description": validated.description,
                        "category": validated.category,
                        "language": validated.language,
                        "quality_score": validated.quality_score,
                        "source_repo": validated.source_repo,
                        "source_path": validated.source_path,
                        "use_cases": validated.use_cases,
                    }
                ],
            )
            self.logger.info(f"Stored pattern: {validated.title}")
            return f"[OK] Successfully indexed pattern: {validated.title}"
        except Exception as e:
            error_msg = f"[ERROR] Failed to store pattern: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    def search_dna(
        self,
        query: str,
        language: str | None = None,
        category: str | None = None,
        min_quality: int = 5,
        limit: int = 10,
    ) -> str:
        """
        Search the DNA bank for best practices matching the query.

        Args:
            query: Natural language description (min 3 chars)
            language: Filter by programming language (python, java, typescript, go)
            category: Filter by pattern category (architecture, error_handling, etc.)
            min_quality: Minimum quality score 1-10 (default: 5)
            limit: Maximum results to return 1-100 (default: 10)

        Returns:
            Formatted list of matching patterns with their code
        """
        try:
            # Validate input using Pydantic
            validated = SearchDNAInput(
                query=query,
                language=language,
                category=category,
                min_quality=min_quality,
                limit=limit,
            )

            # Build filter conditions
            filter_conditions = []

            if validated.language:
                filter_conditions.append(
                    {"key": "language", "match": {"value": validated.language}}
                )

            if validated.category:
                filter_conditions.append(
                    {"key": "category", "match": {"value": validated.category}}
                )

            if validated.min_quality > 1:
                filter_conditions.append(
                    {"key": "quality_score", "range": {"gte": validated.min_quality}}
                )

            # Build filter
            query_filter = None
            if filter_conditions:
                conditions = []
                for fc in filter_conditions:
                    if "match" in fc:
                        conditions.append(
                            FieldCondition(
                                key=fc["key"],
                                match=MatchValue(value=fc["match"]["value"]),
                            )
                        )
                    elif "range" in fc:
                        conditions.append(
                            FieldCondition(
                                key=fc["key"], range=Range(gte=fc["range"]["gte"])
                            )
                        )

                if conditions:
                    query_filter = Filter(must=conditions)

            # Perform search (with hybrid reranking if enabled)
            if self.hybrid_searcher.enabled:
                search_results = self.hybrid_searcher.search_with_hybrid(
                    client=self.client,
                    collection_name=self.collection_name,
                    query=validated.query,
                    limit=validated.limit,
                    query_filter=query_filter,
                )
            else:
                search_results = self.client.query(
                    collection_name=self.collection_name,
                    query_text=validated.query,
                    query_filter=query_filter,
                    limit=validated.limit,
                )

            if not search_results:
                return "No matching patterns found in the DNA bank."

            output = "Found the following architectural patterns:\n\n"
            for i, res in enumerate(search_results, 1):
                metadata = res.metadata if hasattr(res, "metadata") else {}
                document = res.document if hasattr(res, "document") else str(res)

                title = metadata.get(
                    "title", metadata.get("description", f"Pattern {i}")
                )
                lang = metadata.get("language", "unknown")
                category_val = metadata.get("category", "")
                quality = metadata.get("quality_score", "N/A")
                source = metadata.get("source_repo", metadata.get("path", ""))

                output += f"### {i}. {title}\n"
                output += f"**Language:** {lang}"
                if category_val:
                    output += f" | **Category:** {category_val}"
                if quality != "N/A":
                    output += f" | **Quality:** {quality}/10"
                if source:
                    output += f"\n**Source:** {source}"
                output += f"\n\n```{lang}\n{document}\n```\n\n---\n\n"

            self.logger.info(
                f"Search completed: {len(search_results)} results for '{validated.query}'"
            )
            return output

        except Exception as e:
            error_msg = f"[ERROR] Search failed: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
