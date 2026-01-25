"""Data models for Architectural DNA."""

import hashlib
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field, field_validator


def generate_pattern_id(repo_name: str, file_path: str, content: str) -> str:
    """
    Generate a deterministic ID for a pattern.

    The ID is based on repo + file path + content hash, ensuring:
    - Same code in same location = same ID (enables upsert/deduplication)
    - Code changes = new ID (new version gets stored)
    - Same code in different repos = different IDs (allows cross-repo patterns)

    Args:
        repo_name: Repository name (e.g., "owner/repo")
        file_path: Path to the file within the repo
        content: The actual code content

    Returns:
        A 32-character hex string ID
    """
    # Include content hash to handle file changes
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    unique_str = f"{repo_name}:{file_path}:{content_hash}"
    return hashlib.md5(unique_str.encode()).hexdigest()


class PatternCategory(str, Enum):
    """Categories for code patterns."""

    ARCHITECTURE = "architecture"
    ERROR_HANDLING = "error_handling"
    CONFIGURATION = "configuration"
    TESTING = "testing"
    API_DESIGN = "api_design"
    DATA_ACCESS = "data_access"
    SECURITY = "security"
    LOGGING = "logging"
    UTILITIES = "utilities"
    OTHER = "other"


class Language(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    CSHARP = "csharp"
    GO = "go"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, ext: str) -> "Language":
        """Get language from file extension."""
        mapping = {
            ".py": cls.PYTHON,
            ".java": cls.JAVA,
            ".js": cls.JAVASCRIPT,
            ".ts": cls.TYPESCRIPT,
            ".tsx": cls.TYPESCRIPT,
            ".jsx": cls.JAVASCRIPT,
            ".cs": cls.CSHARP,
            ".go": cls.GO,
        }
        return mapping.get(ext.lower(), cls.UNKNOWN)


@dataclass
class CodeChunk:
    """A chunk of code extracted from a file."""

    content: str
    file_path: str
    language: Language
    start_line: int
    end_line: int
    chunk_type: str  # "class", "function", "file", etc.
    name: str | None = None  # Class/function name if applicable
    context: str | None = None  # Imports, class hierarchy, etc.


@dataclass
class PatternAnalysis:
    """LLM analysis result for a code chunk."""

    is_pattern: bool
    title: str
    description: str
    category: PatternCategory
    quality_score: int  # 1-10
    use_cases: list[str] = field(default_factory=list)


@dataclass
class Pattern:
    """A code pattern ready for storage in the DNA bank."""

    content: str
    title: str
    description: str
    category: PatternCategory
    language: Language
    quality_score: int
    source_repo: str
    source_path: str
    use_cases: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict:
        """Convert to metadata dict for Qdrant storage."""
        return {
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "language": self.language.value,
            "quality_score": self.quality_score,
            "source_repo": self.source_repo,
            "source_path": self.source_path,
            "use_cases": self.use_cases,
        }

    def generate_id(self) -> str:
        """Generate deterministic ID for this pattern."""
        return generate_pattern_id(self.source_repo, self.source_path, self.content)


@dataclass
class RepoInfo:
    """Information about a GitHub repository."""

    full_name: str
    name: str
    description: str | None
    language: str | None
    is_private: bool
    default_branch: str
    url: str


@dataclass
class FileNode:
    """A file or directory in a repository."""

    path: str
    name: str
    is_dir: bool
    size: int = 0
    sha: str | None = None


@dataclass
class ProjectStructure:
    """Structure for a scaffolded project."""

    name: str
    directories: list[str]
    files: dict[str, str]  # path -> content


# Pydantic models for input validation


class StorePatternInput(BaseModel):
    """Input validation for store_pattern tool."""

    content: str = Field(..., min_length=10, description="The code content")
    title: str = Field(..., min_length=3, max_length=200, description="Pattern title")
    description: str = Field(..., min_length=10, description="Pattern description")
    category: str = Field(..., description="Pattern category")
    language: str = Field(..., description="Programming language")
    quality_score: int = Field(5, ge=1, le=10, description="Quality score 1-10")
    source_repo: str = Field("manual", description="Source repository")
    source_path: str = Field("", description="Source file path")
    use_cases: list[str] = Field(default_factory=list, description="Use cases")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is in allowed values."""
        try:
            PatternCategory(v.lower())
            return v.lower()
        except ValueError:
            valid = [c.value for c in PatternCategory]
            raise ValueError(
                f"Invalid category '{v}'. Must be one of: {', '.join(valid)}"
            ) from None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language is supported."""
        try:
            Language(v.lower())
            return v.lower()
        except ValueError:
            valid = [lang.value for lang in Language if lang != Language.UNKNOWN]
            raise ValueError(
                f"Invalid language '{v}'. Must be one of: {', '.join(valid)}"
            ) from None


class SearchDNAInput(BaseModel):
    """Input validation for search_dna tool."""

    query: str = Field(..., min_length=3, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Max results to return")
    min_quality: int = Field(5, ge=1, le=10, description="Minimum quality score")
    language: str | None = Field(None, description="Filter by language")
    category: str | None = Field(None, description="Filter by category")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        """Validate language if provided."""
        if v is None:
            return v
        try:
            Language(v.lower())
            return v.lower()
        except ValueError:
            valid = [lang.value for lang in Language if lang != Language.UNKNOWN]
            raise ValueError(
                f"Invalid language '{v}'. Must be one of: {', '.join(valid)}"
            ) from None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Validate category if provided."""
        if v is None:
            return v
        try:
            PatternCategory(v.lower())
            return v.lower()
        except ValueError:
            valid = [c.value for c in PatternCategory]
            raise ValueError(
                f"Invalid category '{v}'. Must be one of: {', '.join(valid)}"
            ) from None


class SyncGitHubRepoInput(BaseModel):
    """Input validation for sync_github_repo tool."""

    repo_name: str = Field(
        ...,
        pattern=r"^[\w\-\.]+/[\w\-\.]+$",
        description="Repository in format 'owner/repo'",
    )
    analyze: bool = Field(True, description="Whether to analyze patterns with LLM")
    min_quality: int = Field(
        5, ge=1, le=10, description="Minimum quality score for patterns"
    )


class ScaffoldProjectInput(BaseModel):
    """Input validation for scaffold_project tool."""

    project_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9\-_]+$",
        description="Project name (alphanumeric, hyphens, underscores)",
    )
    project_type: str = Field(..., min_length=3, description="Type of project")
    tech_stack: str = Field(..., min_length=3, description="Technologies to use")
