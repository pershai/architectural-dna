"""Maintenance tools for DNA bank operations."""

import time

from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSelectorInclude,
)

from models import CodeChunk, Language, PatternCategory

from .base import BaseTool


class MaintenanceTool(BaseTool):
    """Tool for maintenance operations on the DNA bank."""

    def recategorize_patterns(
        self,
        from_category: str | None = "other",
        batch_size: int = 10,
        delay_between_batches: float = 1.0,
        dry_run: bool = False,
    ) -> str:
        """
        Re-categorize patterns using LLM analysis.

        Args:
            from_category: Category to re-analyze. Options:
                - "other" (default): Only patterns with category 'other'
                - "all": All patterns regardless of current category
                - Any valid category name: Only patterns with that category
            batch_size: Number of patterns to process per batch
            delay_between_batches: Seconds to wait between batches (rate limiting)
            dry_run: If True, only show what would be changed without updating

        Returns:
            Summary of recategorization results
        """
        try:
            analyzer = self.get_llm_analyzer()
        except Exception as e:
            return f"[ERROR] Could not initialize LLM analyzer: {e}"

        # Validate from_category
        valid_categories = [c.value for c in PatternCategory]
        if from_category and from_category != "all" and from_category not in valid_categories:
            return (
                f"[ERROR] Invalid category '{from_category}'. "
                f"Valid options: 'all', {', '.join(valid_categories)}"
            )

        # Build filter based on from_category
        scroll_filter = None
        filter_desc = "all patterns"

        if from_category and from_category != "all":
            scroll_filter = Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=from_category))]
            )
            filter_desc = f"patterns with category '{from_category}'"

        # Get count first
        try:
            total_patterns = 0
            offset = None
            while True:
                results, offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=scroll_filter,
                    limit=100,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False,
                )
                total_patterns += len(results)
                if offset is None:
                    break

            if total_patterns == 0:
                return f"[OK] No {filter_desc} found. Nothing to recategorize."

            self.logger.info(f"Found {total_patterns} {filter_desc}")

        except Exception as e:
            return f"[ERROR] Failed to query patterns: {e}"

        # Process in batches
        processed = 0
        updated = 0
        failed = 0
        skipped = 0
        unchanged = 0
        category_changes = {}  # "from -> to": count

        offset = None
        batch_num = 0

        while True:
            # Fetch batch of patterns with full payload (includes document)
            results, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=batch_size,
                offset=offset,
                with_payload=True,  # Get all payload including document
                with_vectors=False,
            )

            if not results:
                break

            batch_num += 1
            self.logger.info(
                f"Processing batch {batch_num} ({len(results)} patterns)..."
            )

            for point in results:
                processed += 1
                point_id = point.id
                payload = point.payload or {}
                old_category = payload.get("category", "unknown")

                try:
                    # Document is stored in payload by fastembed
                    document = payload.get("document", "")

                    if not document:
                        self.logger.warning(f"No document content for point {point_id}")
                        skipped += 1
                        continue

                    # Create a CodeChunk for analysis
                    language_str = payload.get("language", "unknown")
                    try:
                        language = Language(language_str)
                    except ValueError:
                        language = Language.UNKNOWN

                    chunk = CodeChunk(
                        content=document,
                        file_path=payload.get("source_path", "unknown"),
                        language=language,
                        start_line=0,
                        end_line=0,
                        chunk_type="unknown",
                        name=payload.get("title", ""),
                        context=payload.get("description", ""),
                    )

                    # Analyze with LLM
                    analysis = analyzer.analyze_chunk(chunk)

                    if analysis is None:
                        self.logger.warning(
                            f"LLM analysis returned None for point {point_id}"
                        )
                        failed += 1
                        continue

                    new_category = analysis.category.value

                    # Skip if category unchanged
                    if new_category == old_category:
                        unchanged += 1
                        continue

                    # Track category changes
                    change_key = f"{old_category} -> {new_category}"
                    category_changes[change_key] = category_changes.get(change_key, 0) + 1

                    if dry_run:
                        self.logger.info(
                            f"[DRY RUN] Would update {point_id}: {change_key}"
                        )
                        updated += 1
                    else:
                        # Update the payload with new category and other analysis results
                        new_payload = {
                            "category": new_category,
                            "title": analysis.title or payload.get("title"),
                            "description": analysis.description
                            or payload.get("description"),
                            "quality_score": analysis.quality_score
                            or payload.get("quality_score", 5),
                            "use_cases": analysis.use_cases
                            or payload.get("use_cases", []),
                        }

                        self.client.set_payload(
                            collection_name=self.collection_name,
                            payload=new_payload,
                            points=[point_id],
                        )
                        updated += 1
                        self.logger.info(f"Updated {point_id}: {change_key}")

                except Exception as e:
                    self.logger.error(f"Error processing point {point_id}: {e}")
                    failed += 1

            # Rate limiting
            if offset is not None and delay_between_batches > 0:
                time.sleep(delay_between_batches)

            if offset is None:
                break

        # Build summary
        mode = "[DRY RUN] " if dry_run else ""
        summary = (
            f"{mode}Recategorization complete\n\n"
            f"**Filter:** {filter_desc}\n\n"
            f"**Summary:**\n"
            f"- Total patterns: {total_patterns}\n"
            f"- Processed: {processed}\n"
            f"- Updated: {updated}\n"
            f"- Unchanged: {unchanged}\n"
            f"- Skipped (no content): {skipped}\n"
            f"- Failed: {failed}\n"
        )

        if category_changes:
            summary += "\n**Category changes:**\n"
            for change, count in sorted(
                category_changes.items(), key=lambda x: x[1], reverse=True
            ):
                summary += f"  - {change}: {count}\n"

        return summary

    def get_category_stats(self) -> str:
        """
        Get statistics about pattern categories.

        Returns:
            Category distribution statistics
        """
        from collections import Counter

        categories = Counter()

        try:
            offset = None
            while True:
                results, offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=500,
                    offset=offset,
                    with_payload=PayloadSelectorInclude(include=["category"]),
                    with_vectors=False,
                )

                if not results:
                    break

                for point in results:
                    payload = point.payload or {}
                    cat = payload.get("category", "unknown")
                    categories[cat] += 1

                if offset is None:
                    break

            if not categories:
                return "[*] No patterns found in DNA bank."

            total = sum(categories.values())
            output = f"[*] **Category Distribution** (Total: {total})\n\n"

            for cat, count in categories.most_common():
                pct = (count / total) * 100
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                output += f"  {cat:20s} {bar} {count:4d} ({pct:5.1f}%)\n"

            return output

        except Exception as e:
            return f"[ERROR] Failed to get category stats: {e}"
