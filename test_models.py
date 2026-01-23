"""Tests for data models."""

import pytest
from pydantic import ValidationError

from models import (
    Language,
    PatternCategory,
    ScaffoldProjectInput,
    SearchDNAInput,
    StorePatternInput,
    SyncGitHubRepoInput,
)


class TestPatternCategory:
    """Tests for PatternCategory enum."""

    def test_valid_categories(self):
        """Test that all categories are accessible."""
        assert PatternCategory.ARCHITECTURE == "architecture"
        assert PatternCategory.SECURITY == "security"
        assert PatternCategory.UTILITIES == "utilities"

    def test_category_from_string(self):
        """Test creating category from string."""
        cat = PatternCategory("security")
        assert cat == PatternCategory.SECURITY


class TestLanguage:
    """Tests for Language enum."""

    def test_valid_languages(self):
        """Test that all languages are accessible."""
        assert Language.PYTHON == "python"
        assert Language.JAVA == "java"
        assert Language.TYPESCRIPT == "typescript"

    def test_from_extension(self):
        """Test Language.from_extension method."""
        assert Language.from_extension(".py") == Language.PYTHON
        assert Language.from_extension(".java") == Language.JAVA
        assert Language.from_extension(".ts") == Language.TYPESCRIPT
        assert Language.from_extension(".tsx") == Language.TYPESCRIPT
        assert Language.from_extension(".js") == Language.JAVASCRIPT
        assert Language.from_extension(".unknown") == Language.UNKNOWN


class TestStorePatternInput:
    """Tests for StorePatternInput validation."""

    def test_valid_input(self):
        """Test that valid input passes validation."""
        data = StorePatternInput(
            content="def hello(): pass",
            title="Test Pattern",
            description="A test pattern",
            category="utilities",
            language="python",
            quality_score=8,
        )
        assert data.content == "def hello(): pass"
        assert data.quality_score == 8

    def test_content_too_short(self):
        """Test that content must be at least 10 characters."""
        with pytest.raises(ValidationError):
            StorePatternInput(
                content="short",
                title="Test",
                description="Description here",
                category="utilities",
                language="python",
            )

    def test_title_too_short(self):
        """Test that title must be at least 3 characters."""
        with pytest.raises(ValidationError):
            StorePatternInput(
                content="def hello(): pass",
                title="ab",
                description="Description here",
                category="utilities",
                language="python",
            )

    def test_invalid_category(self):
        """Test that invalid category raises error."""
        with pytest.raises(ValidationError):
            StorePatternInput(
                content="def hello(): pass",
                title="Test Pattern",
                description="A test pattern",
                category="invalid_category",
                language="python",
            )

    def test_invalid_language(self):
        """Test that invalid language raises error."""
        with pytest.raises(ValidationError):
            StorePatternInput(
                content="def hello(): pass",
                title="Test Pattern",
                description="A test pattern",
                category="utilities",
                language="invalid_lang",
            )

    def test_quality_score_bounds(self):
        """Test that quality score must be between 1 and 10."""
        with pytest.raises(ValidationError):
            StorePatternInput(
                content="def hello(): pass",
                title="Test Pattern",
                description="A test pattern",
                category="utilities",
                language="python",
                quality_score=11,
            )

        with pytest.raises(ValidationError):
            StorePatternInput(
                content="def hello(): pass",
                title="Test Pattern",
                description="A test pattern",
                category="utilities",
                language="python",
                quality_score=0,
            )


class TestSearchDNAInput:
    """Tests for SearchDNAInput validation."""

    def test_valid_input(self):
        """Test that valid input passes validation."""
        data = SearchDNAInput(
            query="authentication patterns",
            limit=5,
            min_quality=7,
            language="python",
            category="security",
        )
        assert data.query == "authentication patterns"
        assert data.limit == 5

    def test_query_too_short(self):
        """Test that query must be at least 3 characters."""
        with pytest.raises(ValidationError):
            SearchDNAInput(query="ab")

    def test_limit_bounds(self):
        """Test that limit must be between 1 and 100."""
        with pytest.raises(ValidationError):
            SearchDNAInput(query="test", limit=0)

        with pytest.raises(ValidationError):
            SearchDNAInput(query="test", limit=101)

    def test_optional_filters(self):
        """Test that language and category are optional."""
        data = SearchDNAInput(query="test patterns")
        assert data.language is None
        assert data.category is None


class TestSyncGitHubRepoInput:
    """Tests for SyncGitHubRepoInput validation."""

    def test_valid_input(self):
        """Test that valid repo name passes validation."""
        data = SyncGitHubRepoInput(repo_name="owner/repo")
        assert data.repo_name == "owner/repo"
        assert data.analyze is True

    def test_invalid_repo_format(self):
        """Test that invalid repo format raises error."""
        with pytest.raises(ValidationError):
            SyncGitHubRepoInput(repo_name="invalid-format")

        with pytest.raises(ValidationError):
            SyncGitHubRepoInput(repo_name="owner/repo/extra")


class TestScaffoldProjectInput:
    """Tests for ScaffoldProjectInput validation."""

    def test_valid_input(self):
        """Test that valid input passes validation."""
        data = ScaffoldProjectInput(
            project_name="my-new-project",
            project_type="REST API",
            tech_stack="Python, FastAPI",
        )
        assert data.project_name == "my-new-project"

    def test_invalid_project_name(self):
        """Test that invalid characters in project name raise error."""
        with pytest.raises(ValidationError):
            ScaffoldProjectInput(
                project_name="invalid name!", project_type="API", tech_stack="Python"
            )

        with pytest.raises(ValidationError):
            ScaffoldProjectInput(
                project_name="project@name", project_type="API", tech_stack="Python"
            )
