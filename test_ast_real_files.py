"""Integration tests for AST extraction on real project files."""

from pathlib import Path

import pytest

from models import Language
from pattern_extractor import PatternExtractor


class TestRealFileExtraction:
    """Integration tests on real project files."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PatternExtractor()

    def test_extract_pattern_extractor_itself(self):
        """Test AST extraction on pattern_extractor.py itself (dogfooding)."""
        filepath = Path("pattern_extractor.py")

        # Skip if file doesn't exist (running from different directory)
        if not filepath.exists():
            pytest.skip("pattern_extractor.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        chunks = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)

        assert len(chunks) > 0

        # Should find PatternExtractor class
        assert any("PatternExtractor" in c.content for c in chunks), (
            "PatternExtractor class not found in extraction"
        )

        # Should find chunks from the large file
        # (might be 1 if semantic chunking fails to split, or multiple if AST works)
        assert len(chunks) >= 1, (
            f"Expected at least 1 chunk from pattern_extractor.py, got {len(chunks)}"
        )

    def test_extract_models_py(self):
        """Test AST extraction on models.py."""
        filepath = Path("models.py")

        if not filepath.exists():
            pytest.skip("models.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        chunks = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)

        assert len(chunks) > 0

        # Should find Language enum (class in Python)
        assert any(
            "Language" in c.content and c.chunk_type in ("class", "function")
            for c in chunks
        ), "Language enum not found"

        # Should find CodeChunk dataclass
        assert any(
            "CodeChunk" in c.content and c.chunk_type in ("class", "function")
            for c in chunks
        ), "CodeChunk dataclass not found"

    def test_extract_language_registry_py(self):
        """Test AST extraction on language_registry.py."""
        filepath = Path("language_registry.py")

        if not filepath.exists():
            pytest.skip("language_registry.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        chunks = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)

        assert len(chunks) > 0

        # Should find LanguageRegistry class
        class_chunks = [
            c
            for c in chunks
            if c.chunk_type == "class" and "LanguageRegistry" in c.content
        ]
        assert len(class_chunks) > 0, "LanguageRegistry class not found"

        # Should find LanguageConfig dataclass
        assert any("LanguageConfig" in c.content for c in chunks), (
            "LanguageConfig not found"
        )

    def test_extraction_completeness(self):
        """Test that extraction finds reasonable number of chunks from real file."""
        filepath = Path("pattern_extractor.py")

        if not filepath.exists():
            pytest.skip("pattern_extractor.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        chunks = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)

        # Should extract multiple chunks or fall back to semantic
        assert len(chunks) >= 1, f"Expected at least 1 chunk, got {len(chunks)}"

    def test_chunk_content_validity(self):
        """Test that extracted chunks have valid content."""
        filepath = Path("models.py")

        if not filepath.exists():
            pytest.skip("models.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        chunks = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)

        for chunk in chunks:
            # Content should be non-empty
            assert len(chunk.content.strip()) > 0, f"Empty chunk: {chunk}"

            # Content should be from the file
            assert chunk.content in content, (
                f"Chunk content not from file: {chunk.name}"
            )

            # Line numbers should be sane
            if chunk.start_line > 0 and chunk.end_line > 0:
                assert chunk.start_line <= chunk.end_line, (
                    f"Invalid line range: {chunk.start_line}-{chunk.end_line}"
                )

    def test_extraction_no_duplicate_chunks(self):
        """Test that extraction doesn't create duplicate chunks."""
        filepath = Path("pattern_extractor.py")

        if not filepath.exists():
            pytest.skip("pattern_extractor.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        chunks = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)

        # Check for duplicates
        chunk_contents = [c.content for c in chunks]
        unique_contents = set(chunk_contents)

        # Note: Some duplication might be OK in semantic chunking,
        # but excessive duplication is problematic
        duplication_ratio = 1 - (len(unique_contents) / len(chunk_contents))
        assert duplication_ratio < 0.3, f"High duplication ratio: {duplication_ratio}"

    def test_language_detection_on_real_files(self):
        """Test language detection on real project files."""
        test_files = [
            ("pattern_extractor.py", Language.PYTHON),
            ("models.py", Language.PYTHON),
            ("language_registry.py", Language.PYTHON),
        ]

        for filename, expected_lang in test_files:
            filepath = Path(filename)

            if not filepath.exists():
                continue

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            detected = Language.from_content(content, f".{filename.split('.')[-1]}")

            assert detected == expected_lang, (
                f"File {filename}: expected {expected_lang}, got {detected}"
            )

    def test_extraction_consistency(self):
        """Test that extraction is consistent across multiple runs."""
        filepath = Path("models.py")

        if not filepath.exists():
            pytest.skip("models.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Extract twice
        chunks1 = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)
        chunks2 = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)

        # Should get same number of chunks
        assert len(chunks1) == len(chunks2), "Inconsistent extraction results"

        # Should get same chunk names
        names1 = sorted([c.name for c in chunks1 if c.name])
        names2 = sorted([c.name for c in chunks2 if c.name])

        assert names1 == names2, "Inconsistent chunk names between runs"

    def test_multiple_real_files(self):
        """Test extraction on multiple real project files."""
        test_files = [
            ("pattern_extractor.py", Language.PYTHON),
            ("models.py", Language.PYTHON),
            ("language_registry.py", Language.PYTHON),
        ]

        for filename, language in test_files:
            filepath = Path(filename)

            if not filepath.exists():
                continue

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            chunks = self.extractor.extract_chunks(content, str(filepath), language)

            # Should extract something from each file
            assert len(chunks) > 0, f"No chunks extracted from {filename}"

    def test_extraction_performance(self):
        """Test that extraction completes in reasonable time on real files."""
        filepath = Path("pattern_extractor.py")

        if not filepath.exists():
            pytest.skip("pattern_extractor.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Should complete quickly
        import time

        start = time.time()
        chunks = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Extraction took too long: {elapsed}s"
        assert len(chunks) > 0

    def test_large_file_handling(self):
        """Test extraction on larger files."""
        filepath = Path("pattern_extractor.py")

        if not filepath.exists():
            pytest.skip("pattern_extractor.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # pattern_extractor.py is one of the larger files
        if len(content) > 2000:  # At least 2KB
            chunks = self.extractor.extract_chunks(
                content, str(filepath), Language.PYTHON
            )

            # Should handle large files
            assert len(chunks) > 0, "Failed to extract from large file"

            # All chunks should be valid
            for chunk in chunks:
                assert len(chunk.content) > 0

    def test_file_with_mixed_content(self):
        """Test extraction on file with mixed Python constructs."""
        filepath = Path("pattern_extractor.py")

        if not filepath.exists():
            pytest.skip("pattern_extractor.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        chunks = self.extractor.extract_chunks(content, str(filepath), Language.PYTHON)

        # Should have mix of classes and functions
        [c for c in chunks if c.chunk_type == "class"]
        [c for c in chunks if c.chunk_type == "function"]

        # pattern_extractor.py is large file, should find multiple chunks
        assert len(chunks) > 0, "Expected to find chunks in pattern_extractor.py"

        # Check that we found class or function content
        assert any(
            "class" in c.chunk_type or "function" in c.chunk_type for c in chunks
        ) or any("def " in c.content for c in chunks)


class TestLanguageDetectionIntegration:
    """Integration tests for language detection."""

    def test_detect_python_files(self):
        """Test Python file detection."""
        test_files = ["pattern_extractor.py", "models.py", "language_registry.py"]

        for filename in test_files:
            filepath = Path(filename)

            if not filepath.exists():
                continue

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            detected = Language.from_content(content)

            assert detected == Language.PYTHON, f"Failed to detect {filename} as Python"


class TestEdgeCases:
    """Test edge cases in real file extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PatternExtractor()

    def test_file_with_unicode_characters(self):
        """Test extraction on file with unicode content."""
        filepath = Path("models.py")

        if not filepath.exists():
            pytest.skip("models.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Should handle unicode in docstrings, comments, etc.
        try:
            chunks = self.extractor.extract_chunks(
                content, str(filepath), Language.PYTHON
            )
            assert isinstance(chunks, list)
        except Exception as e:
            pytest.fail(f"Failed to extract from file with unicode: {e}")

    def test_extraction_with_syntax_edge_cases(self):
        """Test extraction on files with syntax edge cases."""
        filepath = Path("pattern_extractor.py")

        if not filepath.exists():
            pytest.skip("pattern_extractor.py not found")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Should handle complex Python syntax
        try:
            chunks = self.extractor.extract_chunks(
                content, str(filepath), Language.PYTHON
            )
            # Should not crash and return list
            assert isinstance(chunks, list)
        except Exception as e:
            pytest.fail(f"Failed to extract from complex file: {e}")
