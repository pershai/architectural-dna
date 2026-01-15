"""Data models for Architectural DNA."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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
    name: Optional[str] = None  # Class/function name if applicable
    context: Optional[str] = None  # Imports, class hierarchy, etc.


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


@dataclass
class RepoInfo:
    """Information about a GitHub repository."""
    full_name: str
    name: str
    description: Optional[str]
    language: Optional[str]
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
    sha: Optional[str] = None


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
            )

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
            )


class SearchDNAInput(BaseModel):
    """Input validation for search_dna tool."""
    query: str = Field(..., min_length=3, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Max results to return")
    min_quality: int = Field(5, ge=1, le=10, description="Minimum quality score")
    language: Optional[str] = Field(None, description="Filter by language")
    category: Optional[str] = Field(None, description="Filter by category")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
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
            )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
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
            )


class SyncGitHubRepoInput(BaseModel):
    """Input validation for sync_github_repo tool."""
    repo_name: str = Field(
        ...,
        pattern=r"^[\w\-\.]+/[\w\-\.]+$",
        description="Repository in format 'owner/repo'"
    )
    analyze: bool = Field(True, description="Whether to analyze patterns with LLM")
    min_quality: int = Field(
        5,
        ge=1,
        le=10,
        description="Minimum quality score for patterns"
    )


class ScaffoldProjectInput(BaseModel):
    """Input validation for scaffold_project tool."""
    project_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9\-_]+$",
        description="Project name (alphanumeric, hyphens, underscores)"
    )
    project_type: str = Field(..., min_length=3, description="Type of project")
    tech_stack: str = Field(..., min_length=3, description="Technologies to use")
