"""Pattern extraction from source code using AST parsing."""

import logging
import re
from pathlib import Path

from models import CodeChunk, Language

logger = logging.getLogger(__name__)


class PatternExtractor:
    """Extracts code patterns from source files using various strategies."""

    # Minimum lines for a chunk to be considered meaningful
    MIN_CHUNK_LINES = 5

    # Maximum lines for a single chunk (to avoid overwhelming the LLM)
    MAX_CHUNK_LINES = 150

    def extract_chunks(
        self, content: str, file_path: str, language: Language
    ) -> list[CodeChunk]:
        """
        Extract code chunks from a file.

        Uses language-appropriate parsing strategy.
        Falls back to semantic chunking if AST parsing fails.

        Args:
            content: File content
            file_path: Path to the file
            language: Programming language

        Returns:
            List of CodeChunk objects
        """
        # Try language-specific extraction
        if language == Language.PYTHON:
            chunks = self._extract_python_chunks(content, file_path)
        elif language == Language.JAVA:
            chunks = self._extract_java_chunks(content, file_path)
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            chunks = self._extract_js_chunks(content, file_path, language)
        else:
            chunks = []

        # Fallback to semantic chunking if no chunks found
        if not chunks:
            chunks = self._semantic_chunk(content, file_path, language)

        return chunks

    def _extract_python_chunks(self, content: str, file_path: str) -> list[CodeChunk]:
        """Extract Python classes and functions using regex-based parsing."""
        chunks = []
        lines = content.split("\n")

        # Pattern for class and function definitions
        class_pattern = re.compile(r"^class\s+(\w+)")
        func_pattern = re.compile(r"^(?:async\s+)?def\s+(\w+)")
        re.compile(r"^@\w+")

        # Extract imports for context
        imports = self._extract_python_imports(content)

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Track decorators
            decorator_start = i
            while stripped.startswith("@"):
                i += 1
                if i < len(lines):
                    stripped = lines[i].strip()
                else:
                    break

            # Check for class definition
            class_match = class_pattern.match(stripped)
            if class_match:
                class_name = class_match.group(1)
                end_line = self._find_python_block_end(lines, i)
                chunk_content = "\n".join(lines[decorator_start : end_line + 1])

                if self._is_valid_chunk(chunk_content):
                    chunks.append(
                        CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            language=Language.PYTHON,
                            start_line=decorator_start + 1,
                            end_line=end_line + 1,
                            chunk_type="class",
                            name=class_name,
                            context=imports,
                        )
                    )
                i = end_line + 1
                continue

            # Check for top-level function definition
            func_match = func_pattern.match(stripped)
            if func_match and not line.startswith(" ") and not line.startswith("\t"):
                func_name = func_match.group(1)
                end_line = self._find_python_block_end(lines, i)
                chunk_content = "\n".join(lines[decorator_start : end_line + 1])

                if self._is_valid_chunk(chunk_content):
                    chunks.append(
                        CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            language=Language.PYTHON,
                            start_line=decorator_start + 1,
                            end_line=end_line + 1,
                            chunk_type="function",
                            name=func_name,
                            context=imports,
                        )
                    )
                i = end_line + 1
                continue

            i += 1

        return chunks

    def _extract_python_imports(self, content: str) -> str:
        """Extract import statements from Python code."""
        import_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                import_lines.append(line)
            elif (
                stripped
                and not stripped.startswith("#")
                and import_lines
                and not stripped.startswith("import")
                and not stripped.startswith("from")
            ):
                # Stop at first non-import, non-comment line
                break
        return "\n".join(import_lines)

    def _find_python_block_end(self, lines: list[str], start: int) -> int:
        """Find the end of a Python block (class or function)."""
        if start >= len(lines):
            return start

        # Get the indentation of the definition line
        first_line = lines[start]
        base_indent = len(first_line) - len(first_line.lstrip())

        end = start + 1
        while end < len(lines):
            line = lines[end]

            # Empty lines are part of the block
            if not line.strip():
                end += 1
                continue

            # Check indentation
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent and line.strip():
                # Found a line at same or lower indentation
                break

            end += 1

        # Trim trailing empty lines
        while end > start and not lines[end - 1].strip():
            end -= 1

        return end - 1

    def _extract_java_chunks(self, content: str, file_path: str) -> list[CodeChunk]:
        """Extract Java classes and methods using regex-based parsing."""
        chunks = []
        lines = content.split("\n")

        # Extract package and imports for context
        context = self._extract_java_context(content)

        # Pattern for class definition
        class_pattern = re.compile(
            r"^(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?"
            r"(?:class|interface|enum|record)\s+(\w+)"
        )

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip annotations, collect them
            annotation_start = i
            while stripped.startswith("@"):
                i += 1
                if i < len(lines):
                    stripped = lines[i].strip()
                else:
                    break

            # Check for class definition
            class_match = class_pattern.match(stripped)
            if class_match:
                class_name = class_match.group(1)
                end_line = self._find_brace_block_end(lines, i)
                chunk_content = "\n".join(lines[annotation_start : end_line + 1])

                if self._is_valid_chunk(chunk_content):
                    chunks.append(
                        CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            language=Language.JAVA,
                            start_line=annotation_start + 1,
                            end_line=end_line + 1,
                            chunk_type="class",
                            name=class_name,
                            context=context,
                        )
                    )
                i = end_line + 1
                continue

            i += 1

        return chunks

    def _extract_java_context(self, content: str) -> str:
        """Extract package and import statements from Java code."""
        context_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("package ") or stripped.startswith("import "):
                context_lines.append(line)
        return "\n".join(context_lines)

    def _extract_js_chunks(
        self, content: str, file_path: str, language: Language
    ) -> list[CodeChunk]:
        """Extract JavaScript/TypeScript functions and classes."""
        chunks = []
        lines = content.split("\n")

        # Extract imports for context
        context = self._extract_js_imports(content)

        # Patterns for various JS/TS constructs
        class_pattern = re.compile(r"^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)")
        func_pattern = re.compile(
            r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)|"
            r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\("
        )

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check for class
            class_match = class_pattern.match(stripped)
            if class_match:
                class_name = class_match.group(1)
                end_line = self._find_brace_block_end(lines, i)
                chunk_content = "\n".join(lines[i : end_line + 1])

                if self._is_valid_chunk(chunk_content):
                    chunks.append(
                        CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            language=language,
                            start_line=i + 1,
                            end_line=end_line + 1,
                            chunk_type="class",
                            name=class_name,
                            context=context,
                        )
                    )
                i = end_line + 1
                continue

            # Check for function
            func_match = func_pattern.match(stripped)
            if func_match:
                func_name = func_match.group(1) or func_match.group(2)
                end_line = self._find_brace_block_end(lines, i)
                chunk_content = "\n".join(lines[i : end_line + 1])

                if self._is_valid_chunk(chunk_content):
                    chunks.append(
                        CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            language=language,
                            start_line=i + 1,
                            end_line=end_line + 1,
                            chunk_type="function",
                            name=func_name,
                            context=context,
                        )
                    )
                i = end_line + 1
                continue

            i += 1

        return chunks

    def _extract_js_imports(self, content: str) -> str:
        """Extract import statements from JS/TS code."""
        import_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("require("):
                import_lines.append(line)
        return "\n".join(import_lines)

    def _find_brace_block_end(self, lines: list[str], start: int) -> int:
        """Find the end of a brace-delimited block."""
        brace_count = 0
        found_opening = False

        for i in range(start, len(lines)):
            line = lines[i]

            for char in line:
                if char == "{":
                    brace_count += 1
                    found_opening = True
                elif char == "}":
                    brace_count -= 1

            if found_opening and brace_count == 0:
                return i

        return len(lines) - 1

    def _semantic_chunk(
        self, content: str, file_path: str, language: Language
    ) -> list[CodeChunk]:
        """
        Fallback chunking strategy: split file into logical sections.
        Used when AST-based parsing doesn't find meaningful chunks.
        """
        lines = content.split("\n")

        # If file is small enough, treat it as a single chunk
        if len(lines) <= self.MAX_CHUNK_LINES:
            if self._is_valid_chunk(content):
                return [
                    CodeChunk(
                        content=content,
                        file_path=file_path,
                        language=language,
                        start_line=1,
                        end_line=len(lines),
                        chunk_type="file",
                        name=Path(file_path).stem,
                    )
                ]
            return []

        # Split into chunks of MAX_CHUNK_LINES with some overlap
        chunks = []
        overlap = 10
        i = 0
        chunk_num = 1

        while i < len(lines):
            end = min(i + self.MAX_CHUNK_LINES, len(lines))
            chunk_content = "\n".join(lines[i:end])

            if self._is_valid_chunk(chunk_content):
                chunks.append(
                    CodeChunk(
                        content=chunk_content,
                        file_path=file_path,
                        language=language,
                        start_line=i + 1,
                        end_line=end,
                        chunk_type="file_part",
                        name=f"{Path(file_path).stem}_part{chunk_num}",
                    )
                )
                chunk_num += 1

            i = end - overlap if end < len(lines) else end

        return chunks

    def _is_valid_chunk(self, content: str) -> bool:
        """Check if a chunk is meaningful enough to index."""
        lines = [line for line in content.split("\n") if line.strip()]
        return len(lines) >= self.MIN_CHUNK_LINES
