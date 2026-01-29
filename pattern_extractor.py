"""Pattern extraction from source code using AST parsing."""

import logging
import re
from pathlib import Path

from models import CodeChunk, Language

logger = logging.getLogger(__name__)

# Tree-sitter imports - lazy loaded for optional functionality
_tree_sitter_available = False
try:
    from tree_sitter import Parser

    _tree_sitter_available = True
except ImportError:
    logger.debug("tree-sitter not available, using regex-based extraction")


class PatternExtractor:
    """Extracts code patterns from source files using various strategies."""

    # Minimum lines for a chunk to be considered meaningful
    MIN_CHUNK_LINES = 5

    # Maximum lines for a single chunk (to avoid overwhelming the LLM)
    MAX_CHUNK_LINES = 150

    def __init__(self):
        """Initialize PatternExtractor with optional tree-sitter support."""
        self._ts_parser = None
        self._ts_csharp_lang = None
        self._init_treesitter()

    def _init_treesitter(self) -> None:
        """Initialize tree-sitter parser and C# language support.

        Gracefully handles missing tree-sitter or language bindings.
        """
        if not _tree_sitter_available:
            return

        try:
            # Build C# language library
            from tree_sitter_c_sharp import language

            self._ts_csharp_lang = language()
            self._ts_parser = Parser()
            self._ts_parser.set_language(self._ts_csharp_lang)
            logger.info("Tree-sitter C# parser initialized successfully")
        except ImportError as e:
            logger.warning(
                f"Tree-sitter C# language not available: {e}. "
                "Falling back to regex extraction."
            )
            self._ts_parser = None
            self._ts_csharp_lang = None
        except Exception as e:
            logger.error(f"Failed to initialize tree-sitter: {e}")
            self._ts_parser = None
            self._ts_csharp_lang = None

    def __init__(self):
        """Initialize PatternExtractor with optional tree-sitter support."""
        self._ts_parser = None
        self._ts_csharp_lang = None
        self._init_treesitter()

    def _init_treesitter(self) -> None:
        """Initialize tree-sitter parser and C# language support.

        Gracefully handles missing tree-sitter or language bindings.
        """
        if not _tree_sitter_available:
            return

        try:
            # Build C# language library
            from tree_sitter_c_sharp import language

            self._ts_csharp_lang = language()
            self._ts_parser = Parser()
            self._ts_parser.set_language(self._ts_csharp_lang)
            logger.info("Tree-sitter C# parser initialized successfully")
        except ImportError as e:
            logger.warning(
                f"Tree-sitter C# language not available: {e}. "
                "Falling back to regex extraction."
            )
            self._ts_parser = None
            self._ts_csharp_lang = None
        except Exception as e:
            logger.error(f"Failed to initialize tree-sitter: {e}")
            self._ts_parser = None
            self._ts_csharp_lang = None

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
        elif language == Language.CSHARP:
            # Try AST-based extraction first, fall back to regex
            chunks = self._extract_csharp_ast_chunks(content, file_path)
            if not chunks:
                chunks = self._extract_csharp_chunks(content, file_path)
            # Try AST-based extraction first, fall back to regex
            chunks = self._extract_csharp_ast_chunks(content, file_path)
            if not chunks:
                chunks = self._extract_csharp_chunks(content, file_path)
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

    def _extract_csharp_ast_chunks(
        self, content: str, file_path: str
    ) -> list[CodeChunk]:
        """Extract C# chunks using tree-sitter AST parsing.

        Falls back to empty list if tree-sitter is not available.
        The regex-based extraction will be used as fallback.

        Args:
            content: C# source code
            file_path: Path to the file

        Returns:
            List of CodeChunk objects extracted via AST
        """
        if not self._ts_parser or not self._ts_csharp_lang:
            return []

        try:
            chunks = []
            lines = content.split("\n")
            context = self._extract_csharp_context(content)

            # Parse the code
            tree = self._ts_parser.parse(content.encode("utf-8"))
            root = tree.root_node

            # Query for type declarations (class, interface, struct, record, enum)
            chunk_nodes = self._query_csharp_types(root, content)

            for node_info in chunk_nodes:
                node, chunk_type = node_info
                start_line = node.start_point[0]
                end_line = node.end_point[0]

                # Get type name
                type_name = self._extract_type_name(node, content)
                if not type_name:
                    continue

                # Extract chunk content, including attributes
                attribute_start = self._find_leading_attributes(lines, start_line)
                chunk_content = "\n".join(lines[attribute_start : end_line + 1])

                if self._is_valid_chunk(chunk_content):
                    chunks.append(
                        CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            language=Language.CSHARP,
                            start_line=attribute_start + 1,
                            end_line=end_line + 1,
                            chunk_type=chunk_type,
                            name=type_name,
                            context=context,
                        )
                    )

            return chunks

        except Exception as e:
            logger.warning(
                f"Tree-sitter AST extraction failed for {file_path}: {e}. "
                "Falling back to regex extraction."
            )
            return []

    def _query_csharp_types(self, root_node, content: str) -> list[tuple]:
        """Query tree-sitter AST for C# type declarations.

        Args:
            root_node: Root node of the parsed AST
            content: Source code (for reference)

        Returns:
            List of (node, chunk_type) tuples for type declarations
        """
        type_map = {
            "class_declaration": "class",
            "interface_declaration": "interface",
            "struct_declaration": "struct",
            "record_declaration": "record",
            "enum_declaration": "enum",
        }

        chunks = []

        def traverse(node):
            """Recursively traverse AST nodes."""
            if node.type in type_map:
                chunks.append((node, type_map[node.type]))

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return chunks

    def _extract_type_name(self, node, content: str) -> str | None:
        """Extract the name of a C# type from its AST node.

        Args:
            node: AST node representing a type
            content: Source code

        Returns:
            Type name or None if not found
        """
        # The type name is usually the first identifier child after modifiers
        for child in node.children:
            if child.type == "identifier":
                return content[child.start_byte : child.end_byte].decode("utf-8")

        return None

    def _find_leading_attributes(self, lines: list[str], type_start: int) -> int:
        """Find the start of attributes preceding a type declaration.

        Args:
            lines: Source code lines
            type_start: Starting line of type declaration

        Returns:
            Starting line including attributes
        """
        start = type_start
        i = type_start - 1

        while i >= 0:
            stripped = lines[i].strip()
            if stripped.startswith("[") or stripped.startswith("//") or not stripped:
                start = i
                i -= 1
            else:
                break

        return start

    def _extract_csharp_chunks(self, content: str, file_path: str) -> list[CodeChunk]:
        """Extract C# classes, interfaces, structs, and methods using regex-based parsing."""
        chunks = []
        lines = content.split("\n")

        # Extract using statements and namespace for context
        context = self._extract_csharp_context(content)

        # Patterns for C# type definitions
        # Matches: class, interface, struct, record, enum with modifiers
        type_pattern = re.compile(
            r"^(?:\s*(?:public|private|protected|internal|sealed|abstract|static|partial)\s+)*"
            r"(?:class|interface|struct|record|enum)\s+(\w+)"
        )

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip attributes, collect them
            attribute_start = i
            while stripped.startswith("["):
                i += 1
                if i < len(lines):
                    stripped = lines[i].strip()
                else:
                    break

            # Check for type definition
            type_match = type_pattern.match(stripped)
            if type_match:
                type_name = type_match.group(1)
                end_line = self._find_brace_block_end(lines, i)
                chunk_content = "\n".join(lines[attribute_start : end_line + 1])

                if self._is_valid_chunk(chunk_content):
                    # Determine chunk type based on keyword
                    chunk_type_map = {
                        "interface": "interface",
                        "struct": "struct",
                        "record": "record",
                        "enum": "enum",
                    }

                    chunk_type = "class"
                    for keyword, ctype in chunk_type_map.items():
                        if keyword in stripped:
                            chunk_type = ctype
                            break

                    chunks.append(
                        CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            language=Language.CSHARP,
                            start_line=attribute_start + 1,
                            end_line=end_line + 1,
                            chunk_type=chunk_type,
                            name=type_name,
                            context=context,
                        )
                    )
                i = end_line + 1
                continue

            i += 1

        return chunks

    def _extract_csharp_context(self, content: str) -> str:
        """Extract using statements and namespace from C# code."""
        context_lines = []
        namespace_line = None

        for line in content.split("\n"):
            stripped = line.strip()

            # Collect using statements
            if stripped.startswith("using ") and not stripped.startswith("using ("):
                context_lines.append(line)

            # Collect namespace declaration (both classic and file-scoped)
            elif stripped.startswith("namespace "):
                namespace_line = line

        # Add namespace at the beginning if found
        if namespace_line:
            context_lines.insert(0, namespace_line)

        return "\n".join(context_lines)

    def _find_brace_block_end(self, lines: list[str], start: int) -> int:
        """Find the end of a brace-delimited block using shared utility.

        Args:
            lines: Source code split into lines
            start: Starting line number

        Returns:
            End line number
        """
        from csharp_code_parser import BraceFindMode, CSharpCodeParser

        result = CSharpCodeParser.find_block_end(
            content=lines, start=start, mode=BraceFindMode.IMMEDIATE
        )

        if not result.success:
            logger.warning(f"Brace block end search failed: {result.reason}")

        return result.end_position

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
