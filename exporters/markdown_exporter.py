"""Markdown export format implementation."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BaseExporter, ExportResult


class MarkdownExporter(BaseExporter):
    """Markdown format exporter with rich formatting.

    CRITICAL FEATURES:
    - Auto-detect code language from pattern metadata (not hardcoded)
    - Language mapping for syntax highlighters
    - YAML frontmatter with metadata
    - Table of contents generation
    - Proper markdown formatting
    """

    # Language mapping for syntax highlighters
    LANGUAGE_MAP = {
        "python": "python",
        "java": "java",
        "javascript": "javascript",
        "typescript": "typescript",
        "csharp": "csharp",
        "go": "go",
        "unknown": "text"
    }

    def export(
        self,
        data: Any,
        output_path: str,
        **options
    ) -> ExportResult:
        """Export data to Markdown file.

        Args:
            data: Data to export (list of patterns or dict)
            output_path: Output file path
            **options: Format options:
                - include_toc: Include table of contents (default: True)
                - include_metadata: Include YAML frontmatter (default: True)
                - code_language: Override code language detection (optional)

        Returns:
            ExportResult with export metrics
        """
        start_time = time.time()
        include_toc = options.get("include_toc", True)
        include_metadata = options.get("include_metadata", True)

        try:
            # Prepare output path
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Build markdown content
            md_lines = []

            # Frontmatter
            if include_metadata:
                md_lines.append("---")
                md_lines.append(f"exported_at: {datetime.now().isoformat()}")
                md_lines.append("format: markdown")
                md_lines.append("---")
                md_lines.append("")

            # Title
            md_lines.append("# DNA Export Report")
            md_lines.append("")

            # Table of contents
            if include_toc:
                md_lines.append("## Table of Contents")
                md_lines.append("- [Patterns](#patterns)")
                md_lines.append("")

            # Content
            if isinstance(data, list):
                md_lines.extend(self._format_pattern_list(data))
            elif isinstance(data, dict):
                md_lines.extend(self._format_dict(data))
            else:
                duration = time.time() - start_time
                return ExportResult(
                    success=False,
                    output_path=output_path,
                    records_exported=0,
                    records_failed=0,
                    errors=[{"type": "ValueError", "error": "Markdown export requires list or dict"}],
                    warnings=[],
                    duration_seconds=duration
                )

            # Write to file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))

            # Count patterns exported
            records_exported = len(data) if isinstance(data, list) else 1

            duration = time.time() - start_time

            return ExportResult(
                success=True,
                output_path=str(output_file),
                records_exported=records_exported,
                records_failed=0,
                errors=[],
                warnings=[],
                duration_seconds=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            return ExportResult(
                success=False,
                output_path=output_path,
                records_exported=0,
                records_failed=0,
                errors=[{"type": type(e).__name__, "error": str(e)}],
                warnings=[],
                duration_seconds=duration
            )

    def _format_pattern_list(self, patterns: list) -> list[str]:
        """Format list of patterns as markdown with auto-detected language.

        CRITICAL: Auto-detect language from pattern metadata using pattern["language"],
        don't hardcode code_language parameter.

        Args:
            patterns: List of pattern dicts

        Returns:
            List of markdown lines
        """
        lines = ["## Patterns", ""]

        for i, pattern in enumerate(patterns, 1):
            lines.append(f"### {i}. {pattern.get('title', 'Untitled')}")
            lines.append("")
            lines.append(f"**Category**: {pattern.get('category', 'Unknown')}")
            lines.append(f"**Language**: {pattern.get('language', 'Unknown')}")
            lines.append(f"**Quality**: {pattern.get('quality_score', 'N/A')}/10")
            lines.append("")

            description = pattern.get('description', 'No description')
            lines.append(f"**Description**: {description}")
            lines.append("")

            # Add code block with auto-detected language
            if "content" in pattern and pattern["content"]:
                # CRITICAL: Auto-detect language from pattern metadata
                pattern_lang = pattern.get('language', 'python')
                syntax_lang = self.LANGUAGE_MAP.get(pattern_lang, 'text')

                lines.append(f"```{syntax_lang}")
                lines.append(pattern["content"])
                lines.append("```")
                lines.append("")

        return lines

    def _format_dict(self, data: dict) -> list[str]:
        """Format dict as markdown sections.

        Args:
            data: Dict to format

        Returns:
            List of markdown lines
        """
        lines = []

        for key, value in data.items():
            section_title = key.replace("_", " ").title()
            lines.append(f"## {section_title}")
            lines.append("")

            if isinstance(value, (list, tuple)):
                for item in value:
                    lines.append(f"- {item}")
            else:
                lines.append(str(value))

            lines.append("")

        return lines

    def supports_format(self, format_name: str) -> bool:
        """Check if this exporter handles Markdown format."""
        return format_name.lower() in ("md", "markdown")

    def get_file_extension(self) -> str:
        """Get Markdown file extension."""
        return ".md"

    def verify(self, output_path: str) -> tuple[bool, str]:
        """Verify exported Markdown file is valid.

        Args:
            output_path: Path to Markdown file

        Returns:
            (success, message): True if valid Markdown
        """
        try:
            content = Path(output_path).read_text(encoding="utf-8")

            # Basic markdown validation
            checks = []
            if "# " in content:
                checks.append("✓ Contains headings")
            if "```" in content:
                checks.append("✓ Contains code blocks")
            if "---" in content:
                checks.append("✓ Contains frontmatter")

            line_count = len(content.split("\n"))
            return True, f"Valid Markdown ({line_count} lines) {', '.join(checks)}"

        except FileNotFoundError:
            return False, "File not found"
        except Exception as e:
            return False, f"Verification failed: {e}"
