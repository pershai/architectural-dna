"""Tests for LanguageRegistry lazy loading and caching behavior."""

import pytest

from language_registry import ExtractionMethod, LanguageConfig, LanguageRegistry
from models import Language


class TestLanguageRegistry:
    """Test suite for LanguageRegistry functionality."""

    def test_registry_initialization(self):
        """Test that registry initializes with default languages."""
        registry = LanguageRegistry()

        # Check that default languages are registered
        config_python = registry.get_config(Language.PYTHON)
        assert config_python is not None
        assert config_python.language == Language.PYTHON
        assert config_python.parser_module == "tree_sitter_python"

        config_java = registry.get_config(Language.JAVA)
        assert config_java is not None
        assert config_java.language == Language.JAVA

        config_js = registry.get_config(Language.JAVASCRIPT)
        assert config_js is not None
        assert config_js.language == Language.JAVASCRIPT

        config_ts = registry.get_config(Language.TYPESCRIPT)
        assert config_ts is not None
        assert config_ts.language == Language.TYPESCRIPT

        config_csharp = registry.get_config(Language.CSHARP)
        assert config_csharp is not None
        assert config_csharp.language == Language.CSHARP

    def test_registry_lazy_loading(self):
        """Test that parsers are loaded lazily on first use."""
        registry = LanguageRegistry()

        # First call should load the parser
        registry.get_parser(Language.PYTHON)
        # Parser might be None if tree-sitter not available, but that's OK
        # The important thing is that the language is now in initialized set
        assert Language.PYTHON in registry._initialized

    def test_registry_caching(self):
        """Test that loaded parsers are cached and reused."""
        registry = LanguageRegistry()

        # Get parser twice
        parser1 = registry.get_parser(Language.PYTHON)
        parser2 = registry.get_parser(Language.PYTHON)

        # Both calls should return the same object (cached)
        assert parser1 is parser2

    def test_registry_supports_ast(self):
        """Test supports_ast method for different languages."""
        registry = LanguageRegistry()

        # Get support status for each language
        python_support = registry.supports_ast(Language.PYTHON)
        java_support = registry.supports_ast(Language.JAVA)
        js_support = registry.supports_ast(Language.JAVASCRIPT)
        csharp_support = registry.supports_ast(Language.CSHARP)

        # All should return boolean (either True or False depending on tree-sitter availability)
        assert isinstance(python_support, bool)
        assert isinstance(java_support, bool)
        assert isinstance(js_support, bool)
        assert isinstance(csharp_support, bool)

    def test_registry_get_config(self):
        """Test getting language configuration."""
        registry = LanguageRegistry()

        # Get config for registered language
        config = registry.get_config(Language.PYTHON)
        assert config is not None
        assert config.language == Language.PYTHON
        assert config.parser_module == "tree_sitter_python"
        assert "class_definition" in config.type_declarations
        assert "function_definition" in config.type_declarations

        # Get config for Go (now registered with pseudo-AST support)
        config_go = registry.get_config(Language.GO)
        assert config_go is not None
        assert config_go.language == Language.GO
        assert config_go.parser_module == "tree_sitter_go"

    def test_registry_unsupported_language(self):
        """Test handling of unsupported languages."""
        registry = LanguageRegistry()

        # Attempt to get parser for unsupported language
        parser = registry.get_parser(Language.GO)
        assert parser is None

        # Check that language is marked as initialized but parser is None
        assert Language.GO in registry._initialized
        assert registry._parsers[Language.GO] is None

    def test_registry_get_supported_languages(self):
        """Test getting list of supported languages."""
        registry = LanguageRegistry()

        supported = registry.get_supported_languages()

        # Should return a list
        assert isinstance(supported, list)

        # List might be empty if tree-sitter not available, but should be iterable
        assert isinstance(supported, list)

    def test_registry_register_custom_language(self):
        """Test registering a new custom language."""
        registry = LanguageRegistry()

        # Create custom config
        custom_config = LanguageConfig(
            language=Language.GO,
            parser_module="tree_sitter_go",
            type_declarations={
                "type_declaration": "type",
                "function_declaration": "function",
            },
            query_strategy="recursive",
        )

        # Register it
        registry.register(custom_config)

        # Check that it's registered
        registered_config = registry.get_config(Language.GO)
        assert registered_config is not None
        assert registered_config.language == Language.GO
        assert registered_config.parser_module == "tree_sitter_go"

    def test_extraction_method_enum(self):
        """Test ExtractionMethod enum values."""
        assert ExtractionMethod.AST.value == "ast"
        assert ExtractionMethod.REGEX.value == "regex"
        assert ExtractionMethod.PSEUDO_AST.value == "pseudo_ast"
        assert ExtractionMethod.SEMANTIC.value == "semantic"

        # Check all values are string enum
        assert isinstance(ExtractionMethod.AST, str)
        assert isinstance(ExtractionMethod.REGEX, str)

    def test_language_config_validation(self):
        """Test LanguageConfig validation."""
        # Valid config should not raise
        config = LanguageConfig(
            language=Language.PYTHON,
            parser_module="tree_sitter_python",
            type_declarations={"class_definition": "class"},
            query_strategy="recursive",
        )
        assert config is not None

        # Invalid query_strategy should raise
        with pytest.raises(ValueError, match="Invalid query_strategy"):
            LanguageConfig(
                language=Language.PYTHON,
                parser_module="tree_sitter_python",
                type_declarations={"class_definition": "class"},
                query_strategy="invalid_strategy",
            )

        # Missing language should raise ValueError in __post_init__
        with pytest.raises(ValueError, match="language is required"):
            LanguageConfig(
                language=None,  # type: ignore
                parser_module="tree_sitter_python",
            )


class TestLanguageConfigDataclass:
    """Test LanguageConfig dataclass behavior."""

    def test_language_config_defaults(self):
        """Test default values for LanguageConfig fields."""
        config = LanguageConfig(
            language=Language.PYTHON,
            parser_module="tree_sitter_python",
        )

        assert config.query_strategy == "recursive"
        assert config.type_declarations == {}
        assert config.node_type_docs == {}

    def test_language_config_with_node_docs(self):
        """Test LanguageConfig with node documentation."""
        docs = {
            "class_definition": "Top-level class: class Name:",
            "function_definition": "Function or method: def name():",
        }

        config = LanguageConfig(
            language=Language.PYTHON,
            parser_module="tree_sitter_python",
            type_declarations={"class_definition": "class"},
            node_type_docs=docs,
        )

        assert config.node_type_docs == docs
        assert (
            config.node_type_docs["class_definition"] == "Top-level class: class Name:"
        )
