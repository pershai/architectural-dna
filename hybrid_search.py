"""Hybrid search combining semantic (dense) and keyword (sparse) search."""

import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


class HybridSearcher:
    """Implements hybrid search combining semantic and keyword matching."""

    def __init__(self, config: dict[str, Any]):
        """
        Initialize hybrid searcher.

        Args:
            config: Configuration dictionary
        """
        self.config = config.get("search", {})
        self.enabled = self.config.get("hybrid_enabled", True)
        self.semantic_weight = self.config.get("semantic_weight", 0.7)
        self.keyword_weight = self.config.get("keyword_weight", 0.3)

    def extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        """
        Extract important keywords from text.

        Args:
            text: Text to extract keywords from
            top_n: Number of top keywords to return

        Returns:
            List of keywords
        """
        # Tokenize: split by non-alphanumeric, keep underscores for identifiers
        tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", text.lower())

        # Remove common programming keywords and short words
        stop_words = {
            "def",
            "class",
            "if",
            "else",
            "for",
            "while",
            "return",
            "import",
            "from",
            "as",
            "try",
            "except",
            "with",
            "in",
            "is",
            "not",
            "and",
            "or",
            "the",
            "a",
            "an",
            "to",
            "of",
            "it",
            "be",
            "at",
            "by",
            "on",
        }
        tokens = [t for t in tokens if t not in stop_words and len(t) > 2]

        # Count frequency
        counter = Counter(tokens)

        # Return top N
        return [word for word, count in counter.most_common(top_n)]

    def compute_keyword_score(
        self, query_keywords: list[str], document_text: str
    ) -> float:
        """
        Compute keyword match score between query and document.

        Uses TF-IDF-like scoring.

        Args:
            query_keywords: Keywords from query
            document_text: Document text to score

        Returns:
            Keyword match score (0-1)
        """
        if not query_keywords:
            return 0.0

        doc_lower = document_text.lower()
        matches = 0
        total_weight = 0.0

        for keyword in query_keywords:
            # Count occurrences
            count = doc_lower.count(keyword.lower())
            if count > 0:
                matches += 1
                # Diminishing returns for multiple occurrences
                total_weight += min(1.0, count * 0.3)

        # Normalize by number of keywords
        score = total_weight / len(query_keywords)
        return min(1.0, score)

    def rerank_results(
        self, query: str, results: list[Any], semantic_scores: list[float]
    ) -> list[tuple[Any, float]]:
        """
        Rerank search results using hybrid scoring.

        Args:
            query: Search query
            results: List of search result objects
            semantic_scores: Semantic similarity scores from vector search

        Returns:
            List of (result, hybrid_score) tuples, sorted by score
        """
        if not self.enabled or not results:
            # Return results with original scores
            return list(zip(results, semantic_scores, strict=False))

        # Extract keywords from query
        query_keywords = self.extract_keywords(query)
        logger.debug(f"Query keywords: {query_keywords}")

        reranked = []
        for result, semantic_score in zip(results, semantic_scores, strict=False):
            # Get document text
            document = result.document if hasattr(result, "document") else str(result)

            # Compute keyword score
            keyword_score = self.compute_keyword_score(query_keywords, document)

            # Combine scores
            hybrid_score = (
                self.semantic_weight * semantic_score
                + self.keyword_weight * keyword_score
            )

            reranked.append((result, hybrid_score))
            logger.debug(
                f"Reranked: semantic={semantic_score:.3f}, "
                f"keyword={keyword_score:.3f}, "
                f"hybrid={hybrid_score:.3f}"
            )

        # Sort by hybrid score
        reranked.sort(key=lambda x: x[1], reverse=True)

        return reranked

    def search_with_hybrid(
        self,
        client: Any,
        collection_name: str,
        query: str,
        limit: int = 10,
        query_filter: Any | None = None,
    ) -> list[Any]:
        """
        Perform hybrid search on Qdrant collection.

        Args:
            client: Qdrant client
            collection_name: Collection name
            query: Search query
            limit: Number of results (will retrieve more for reranking)
            query_filter: Optional Qdrant filter

        Returns:
            Reranked search results
        """
        # Fetch more results than needed for better reranking
        fetch_limit = min(limit * 3, 50)

        # Perform semantic search
        results = client.query(
            collection_name=collection_name,
            query_text=query,
            query_filter=query_filter,
            limit=fetch_limit,
        )

        if not results:
            return []

        # Extract semantic scores (Qdrant returns them as scores)
        semantic_scores = []
        for res in results:
            # Qdrant query returns results with scores
            score = res.score if hasattr(res, "score") else 1.0
            semantic_scores.append(score)

        # Rerank with hybrid scoring
        reranked = self.rerank_results(query, results, semantic_scores)

        # Return top N after reranking
        return [result for result, score in reranked[:limit]]

    def get_config_info(self) -> dict[str, Any]:
        """
        Get hybrid search configuration info.

        Returns:
            Configuration dictionary
        """
        return {
            "enabled": self.enabled,
            "semantic_weight": self.semantic_weight,
            "keyword_weight": self.keyword_weight,
        }
