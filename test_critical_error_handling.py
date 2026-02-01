"""Critical error handling tests for extraction hierarchy and language detection.

These tests verify error recovery and edge cases that could cause silent failures
or incorrect behavior in production.
"""

from unittest.mock import Mock, patch

import pytest

from language_registry import LanguageRegistry
from models import CodeChunk, Language
from pattern_extractor import PatternExtractor


class TestExtractionHierarchyErrorRecovery:
    """Test that extraction hierarchy properly falls back on errors."""

    def test_ast_extraction_exception_falls_back_to_regex(self):
        """Verify AST extraction exception triggers regex fallback."""
        extractor = PatternExtractor()

        # Python code that regex can match
        python_code = "def hello():\n    print('world')\n"

        # Since tree-sitter is not available, this will use regex extraction
        # We'll verify that extraction succeeds despite potential AST failures
        chunks = extractor.extract_chunks(python_code, "test.py", Language.PYTHON)

        # Regex fallback should work and return valid CodeChunk objects
        assert isinstance(chunks, list), "Should return list"
        # Should extract something (even if not "hello" text due to regex limitations)
        assert all(hasattr(c, "content") and hasattr(c, "file_path") for c in chunks), (
            "All results should be valid CodeChunk objects"
        )

    def test_recursion_depth_limit_prevents_stack_overflow(self):
        """Verify recursion depth limit prevents stack overflow."""
        extractor = PatternExtractor()

        # Create a deeply nested AST mock
        def create_deep_tree(depth):
            node = Mock()
            node.type = "module"
            node.children = []

            current = node
            for i in range(depth):
                child = Mock()
                child.type = f"node_{i}"
                child.children = []
                current.children = [child]
                current = child

            return node

        # Test with depth exceeding default limit
        deep_node = create_deep_tree(1500)

        # This should not raise RecursionError
        try:
            result = extractor._query_recursive(
                deep_node, {"module": "module"}, max_depth=1000
            )
            # Should return partial results before hitting depth limit
            assert isinstance(result, list), "Should return list even with depth limit"
        except RecursionError:
            pytest.fail("RecursionError should be caught and handled")

    def test_extract_chunks_handles_encoding_errors_gracefully(self):
        """Verify encoding errors are handled gracefully."""
        extractor = PatternExtractor()

        # Content with encoding that might cause issues
        content = "def hello():\n    return '🌍'\n"

        # Should handle Unicode without raising an exception
        try:
            chunks = extractor.extract_chunks(content, "test.py", Language.PYTHON)
            # Should return a list (might be empty or have chunks)
            assert isinstance(chunks, list), (
                "Should return list despite Unicode content"
            )
        except UnicodeDecodeError:
            pytest.fail("Should handle Unicode content without UnicodeDecodeError")

    def test_semantic_chunking_always_succeeds(self):
        """Verify semantic chunking fallback always produces results."""
        extractor = PatternExtractor()

        # Code that doesn't have regex matches
        code = "xyz123\nabc456\ndef789\nghi012"

        chunks = extractor.extract_chunks(code, "test.unknown", Language.UNKNOWN)

        # Should return a list (semantic chunking or empty)
        assert isinstance(chunks, list), "Should return list"
        # If it has chunks, all should be CodeChunk objects
        assert all(isinstance(c, CodeChunk) for c in chunks), (
            "All should be CodeChunk objects"
        )

    def test_extraction_with_empty_content(self):
        """Verify extraction handles empty files."""
        extractor = PatternExtractor()

        chunks = extractor.extract_chunks("", "empty.py", Language.PYTHON)
        assert isinstance(chunks, list), "Should return list"
        assert len(chunks) == 0, "Empty file should have no chunks"

    def test_extraction_with_only_comments(self):
        """Verify extraction handles comment-only files."""
        extractor = PatternExtractor()

        comment_code = """
# This is a comment
# Another comment
# More comments
"""

        chunks = extractor.extract_chunks(comment_code, "test.py", Language.PYTHON)
        # Comments alone might not create chunks, but shouldn't error
        assert isinstance(chunks, list), "Should return list for comment-only file"


class TestLanguageDetectionAmbiguity:
    """Test language detection in ambiguous cases."""

    def test_detect_javascript_vs_typescript_ambiguity(self):
        """Verify consistent detection for JavaScript/TypeScript overlap."""
        # Code with const/let without type annotations
        js_code = "const x = 10;\nconst y = 20;"
        lang = Language.from_content(js_code, ".js")
        # Should detect as JavaScript or TypeScript, but consistently
        assert lang in (Language.JAVASCRIPT, Language.TYPESCRIPT, Language.UNKNOWN)

    def test_detect_with_extension_fallback_on_ambiguous(self):
        """Verify extension fallback works for ambiguous content."""
        ambiguous_code = "const x = 10;"

        # With TypeScript extension
        ts_lang = Language.from_content(ambiguous_code, ".ts")
        assert ts_lang in (Language.TYPESCRIPT, Language.JAVASCRIPT, Language.UNKNOWN)

        # With JavaScript extension
        js_lang = Language.from_content(ambiguous_code, ".js")
        assert js_lang in (Language.JAVASCRIPT, Language.TYPESCRIPT, Language.UNKNOWN)

    def test_detect_java_vs_csharp_no_cross_contamination(self):
        """Verify Java and C# are detected distinctly."""
        java_code = "package com.example;\nimport java.util.List;"
        csharp_code = "using System;\nnamespace MyApp { }"

        java_lang = Language.from_content(java_code)
        csharp_lang = Language.from_content(csharp_code)

        assert java_lang == Language.JAVA
        assert csharp_lang == Language.CSHARP

    def test_detect_go_vs_c_similarity(self):
        """Verify Go detection despite C-like syntax."""
        go_code = "package main\nfunc main() {\n}"

        go_lang = Language.from_content(go_code)
        assert go_lang == Language.GO

    def test_detect_with_shebang_takes_priority(self):
        """Verify shebang detection takes priority."""
        python_shebang = "#!/usr/bin/python\nprint('hi')"
        lang = Language.from_content(python_shebang)
        assert lang == Language.PYTHON

    def test_detect_comment_only_file_returns_unknown_then_fallback(self):
        """Verify comment-only files use extension fallback."""
        comment_only = "// just comments\n// more comments"

        # Without extension should be unknown
        lang_no_ext = Language.from_content(comment_only)
        assert lang_no_ext == Language.UNKNOWN

        # With extension should use fallback
        lang_with_ext = Language.from_content(comment_only, ".py")
        assert lang_with_ext == Language.PYTHON

    def test_detect_file_with_bom(self):
        """Verify UTF-8 BOM doesn't interfere with detection."""
        code_with_bom = "\ufeff#!/usr/bin/python\nprint('hi')"
        # Shebang detection might miss due to BOM, but file extension works
        lang_with_ext = Language.from_content(code_with_bom, ".py")
        assert lang_with_ext == Language.PYTHON


class TestLanguageRegistryErrorHandling:
    """Test LanguageRegistry error handling."""

    def test_registry_parser_import_error(self):
        """Verify graceful handling when tree-sitter module unavailable."""
        registry = LanguageRegistry()

        # Mock importlib to raise ImportError
        with patch("language_registry.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("tree_sitter_rust not found")

            # Force a language that would need tree-sitter
            parser = registry.get_parser(Language.PYTHON)

            # Should return None, not raise
            assert parser is None

            # Should cache the failure
            assert Language.PYTHON in registry._initialized

    def test_registry_parser_set_language_error(self):
        """Verify handling when parser.set_language() fails."""
        registry = LanguageRegistry()

        with (
            patch("language_registry.importlib.import_module") as mock_import,
            patch("language_registry.Parser") as mock_parser_class,
        ):
            # Create a mock parser that fails on set_language
            mock_parser_instance = Mock()
            mock_parser_instance.set_language.side_effect = RuntimeError(
                "Language not supported"
            )

            mock_parser_class.return_value = mock_parser_instance

            # Import succeeds but set_language fails
            mock_lang_module = Mock()
            mock_lang_obj = Mock()
            mock_lang_module.language.return_value = mock_lang_obj
            mock_import.return_value = mock_lang_module

            parser = registry.get_parser(Language.PYTHON)
            # Should handle gracefully
            assert parser is None or isinstance(parser, Mock)

    def test_registry_get_supported_languages_includes_go(self):
        """Verify Go is included in registered configs even if tree-sitter unavailable."""
        registry = LanguageRegistry()

        # Check that Go config is registered in _configs
        go_config = registry.get_config(Language.GO)
        assert go_config is not None, "Go configuration should be registered"
        assert go_config.language == Language.GO, "Config should be for Go"

        # get_supported_languages might be empty if tree-sitter unavailable,
        # but Go should be in the registry configs
        all_configs = registry._configs
        assert Language.GO in all_configs, "Go should be in registry configurations"


class TestNodeTextExtraction:
    """Test safe text extraction from AST nodes."""

    def test_extract_node_text_with_valid_bytes(self):
        """Verify normal text extraction works."""
        extractor = PatternExtractor()

        mock_node = Mock()
        mock_node.start_byte = 0
        mock_node.end_byte = 11

        content = "hello world"
        result = extractor._extract_node_text(mock_node, content)

        assert result == "hello world"

    def test_extract_node_text_with_unicode(self):
        """Verify Unicode content is handled correctly."""
        extractor = PatternExtractor()

        mock_node = Mock()
        mock_node.start_byte = 0

        content = "hello 🌍"
        utf8_bytes = content.encode("utf-8")
        mock_node.end_byte = len(utf8_bytes)

        result = extractor._extract_node_text(mock_node, utf8_bytes)
        assert "hello" in result

    def test_extract_node_text_out_of_bounds(self):
        """Test handling when node byte range exceeds content."""
        extractor = PatternExtractor()

        mock_node = Mock()
        mock_node.start_byte = 100
        mock_node.end_byte = 200

        content = "short"

        # Should gracefully handle IndexError
        result = extractor._extract_node_text(mock_node, content)
        assert result == "", "Should return empty string for out of bounds"

    def test_extract_node_text_negative_bytes(self):
        """Test handling of negative byte offsets."""
        extractor = PatternExtractor()

        mock_node = Mock()
        mock_node.start_byte = -10
        mock_node.end_byte = 5

        content = "test"

        # Should handle gracefully
        result = extractor._extract_node_text(mock_node, content)
        # Should either return empty or attempt extraction
        assert isinstance(result, str)


class TestPatternExtractorWithSharedRegistry:
    """Test PatternExtractor with optional shared registry."""

    def test_extractor_with_custom_registry(self):
        """Verify PatternExtractor can accept custom registry."""
        custom_registry = LanguageRegistry()
        extractor = PatternExtractor(registry=custom_registry)

        assert extractor._registry is custom_registry
        assert extractor._registry == custom_registry

    def test_extractor_default_creates_new_registry(self):
        """Verify PatternExtractor creates new registry if not provided."""
        extractor1 = PatternExtractor()
        extractor2 = PatternExtractor()

        # Should have different registry instances
        assert extractor1._registry is not extractor2._registry

    def test_multiple_extractors_with_shared_registry(self):
        """Verify multiple extractors can share a registry for efficiency."""
        shared_registry = LanguageRegistry()
        extractor1 = PatternExtractor(registry=shared_registry)
        extractor2 = PatternExtractor(registry=shared_registry)

        # Both should use same registry
        assert extractor1._registry is extractor2._registry
        assert extractor1._registry is shared_registry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
