"""Tests for ProjectScaffolder and ScaffoldTool."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from scaffolder import ProjectScaffolder
from tools.scaffold_tool import ScaffoldTool
from models import ProjectStructure


class TestProjectScaffolder:
    """Tests for ProjectScaffolder class."""

    @pytest.fixture
    def mock_qdrant(self):
        return Mock()

    @pytest.fixture
    def scaffolder_no_llm(self, mock_qdrant):
        """Scaffolder without LLM (no API key)."""
        with patch.dict('os.environ', {}, clear=True):
            return ProjectScaffolder(mock_qdrant, "test_collection")

    @pytest.fixture
    def scaffolder_with_llm(self, mock_qdrant):
        """Scaffolder with LLM."""
        with patch('scaffolder.genai') as mock_genai:
            return ProjectScaffolder(mock_qdrant, "test_collection", config=None, gemini_api_key="test-key")

    # ==========================================================================
    # Initialization tests
    # ==========================================================================

    def test_init_without_api_key(self, mock_qdrant):
        """Test initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            scaffolder = ProjectScaffolder(mock_qdrant, "test_collection")

            assert scaffolder.client is None
            assert scaffolder.model is None

    def test_init_with_api_key(self, mock_qdrant):
        """Test initialization with API key."""
        with patch('scaffolder.genai') as mock_genai:
            scaffolder = ProjectScaffolder(mock_qdrant, "test", config=None, gemini_api_key="test-key")

            mock_genai.Client.assert_called_once_with(api_key="test-key")
            assert scaffolder.model == "gemini-2.0-flash"

    def test_init_with_config_model(self, mock_qdrant):
        """Test initialization reads model from config."""
        config = {"llm": {"model": "gemini-1.5-pro"}}
        with patch('scaffolder.genai') as mock_genai:
            scaffolder = ProjectScaffolder(mock_qdrant, "test", config=config, gemini_api_key="test-key")

            assert scaffolder.model == "gemini-1.5-pro"

    def test_init_with_env_api_key(self, mock_qdrant):
        """Test initialization with environment API key."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'env-key'}):
            with patch('scaffolder.genai') as mock_genai:
                scaffolder = ProjectScaffolder(mock_qdrant, "test")

                mock_genai.Client.assert_called_once_with(api_key="env-key")

    # ==========================================================================
    # gather_patterns tests
    # ==========================================================================

    def test_gather_patterns_success(self, scaffolder_no_llm, mock_qdrant):
        """Test gathering patterns from Qdrant."""
        mock_qdrant.query.return_value = [Mock(), Mock()]

        patterns = scaffolder_no_llm.gather_patterns("api", ["python", "fastapi"], limit=5)

        assert len(patterns) == 2
        mock_qdrant.query.assert_called_once()
        call_args = mock_qdrant.query.call_args
        assert "api" in call_args.kwargs['query_text']
        assert "python" in call_args.kwargs['query_text']
        assert call_args.kwargs['limit'] == 5

    def test_gather_patterns_error(self, scaffolder_no_llm, mock_qdrant):
        """Test gather patterns handles errors."""
        mock_qdrant.query.side_effect = Exception("Query error")

        patterns = scaffolder_no_llm.gather_patterns("api", ["python"])

        assert patterns == []

    def test_gather_patterns_type_context(self, scaffolder_no_llm, mock_qdrant):
        """Test that project type adds context to query."""
        mock_qdrant.query.return_value = []

        scaffolder_no_llm.gather_patterns("cli", ["python"])

        call_args = mock_qdrant.query.call_args
        assert "command line" in call_args.kwargs['query_text']

    # ==========================================================================
    # generate_structure tests
    # ==========================================================================

    def test_generate_structure_without_llm(self, scaffolder_no_llm):
        """Test structure generation without LLM falls back to basic."""
        structure = scaffolder_no_llm.generate_structure(
            "my-project", "api", ["python", "fastapi"], []
        )

        assert structure is not None
        assert structure.name == "my-project"
        assert "src" in structure.directories
        assert "README.md" in structure.files

    def test_generate_structure_with_llm(self, mock_qdrant):
        """Test structure generation with LLM."""
        with patch('scaffolder.genai') as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = '{"directories": ["src", "tests"], "files": {"README.md": "# Test"}}'
            mock_client.models.generate_content.return_value = mock_response

            scaffolder = ProjectScaffolder(mock_qdrant, "test", gemini_api_key="key")
            structure = scaffolder.generate_structure("test-proj", "api", ["python"], [])

            assert structure is not None
            assert structure.name == "test-proj"
            assert "src" in structure.directories
            assert "README.md" in structure.files

    def test_generate_structure_llm_error_fallback(self, mock_qdrant):
        """Test LLM error falls back to basic structure."""
        with patch('scaffolder.genai') as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.side_effect = Exception("API error")

            scaffolder = ProjectScaffolder(mock_qdrant, "test", gemini_api_key="key")
            structure = scaffolder.generate_structure("test-proj", "api", ["python"], [])

            # Should fall back to basic structure
            assert structure is not None
            assert structure.name == "test-proj"

    # ==========================================================================
    # _format_patterns tests
    # ==========================================================================

    def test_format_patterns_empty(self, scaffolder_no_llm):
        """Test formatting empty patterns."""
        result = scaffolder_no_llm._format_patterns([])
        assert "No reference patterns" in result

    def test_format_patterns_with_data(self, scaffolder_no_llm):
        """Test formatting patterns with data."""
        mock_pattern = Mock()
        mock_pattern.metadata = {"title": "Test Pattern", "language": "python"}
        mock_pattern.document = "def test(): pass"

        result = scaffolder_no_llm._format_patterns([mock_pattern])

        assert "Test Pattern" in result
        assert "python" in result

    # ==========================================================================
    # _parse_structure tests
    # ==========================================================================

    def test_parse_structure_valid(self, scaffolder_no_llm):
        """Test parsing valid structure response."""
        response = '{"directories": ["src"], "files": {"main.py": "print(1)"}}'

        structure = scaffolder_no_llm._parse_structure("test", response)

        assert structure is not None
        assert structure.name == "test"
        assert "src" in structure.directories
        assert "main.py" in structure.files

    def test_parse_structure_invalid_json(self, scaffolder_no_llm):
        """Test parsing invalid JSON."""
        result = scaffolder_no_llm._parse_structure("test", "not json")
        assert result is None

    def test_parse_structure_missing_fields(self, scaffolder_no_llm):
        """Test parsing with missing fields returns None or empty."""
        response = '{}'

        structure = scaffolder_no_llm._parse_structure("test", response)

        # May return None or empty structure depending on implementation
        if structure is not None:
            assert structure.directories == []
            assert structure.files == {}

    # ==========================================================================
    # Basic structure generation tests
    # ==========================================================================

    def test_python_structure(self, scaffolder_no_llm):
        """Test Python project structure generation."""
        structure = scaffolder_no_llm._python_structure("myapp", "api", ["python"])

        assert "src" in structure.directories
        assert "tests" in structure.directories
        assert "requirements.txt" in structure.files
        assert "setup.py" in structure.files
        assert "src/main.py" in structure.files

    def test_python_fastapi_structure(self, scaffolder_no_llm):
        """Test Python FastAPI project structure."""
        structure = scaffolder_no_llm._python_structure("myapp", "api", ["python", "fastapi"])

        assert "fastapi" in structure.files["requirements.txt"].lower()
        assert "FastAPI" in structure.files["src/main.py"]

    def test_node_structure(self, scaffolder_no_llm):
        """Test Node.js project structure generation."""
        structure = scaffolder_no_llm._node_structure("myapp", "api", ["typescript"])

        assert "src" in structure.directories
        assert "package.json" in structure.files
        assert "src/index.js" in structure.files

    def test_java_structure(self, scaffolder_no_llm):
        """Test Java project structure generation."""
        structure = scaffolder_no_llm._java_structure("my-app", "api", ["java"])

        assert "src/main/java" in structure.directories
        assert "pom.xml" in structure.files
        # Check for Application.java in package path
        java_files = [f for f in structure.files if f.endswith(".java")]
        assert len(java_files) == 1

    def test_generic_structure(self, scaffolder_no_llm):
        """Test generic project structure."""
        structure = scaffolder_no_llm._generic_structure("myapp", "library", ["go"])

        assert "src" in structure.directories
        assert "README.md" in structure.files

    def test_generate_basic_structure_detects_python(self, scaffolder_no_llm):
        """Test basic structure detects Python."""
        structure = scaffolder_no_llm._generate_basic_structure("app", "api", ["python"])
        assert "requirements.txt" in structure.files

    def test_generate_basic_structure_detects_node(self, scaffolder_no_llm):
        """Test basic structure detects Node."""
        structure = scaffolder_no_llm._generate_basic_structure("app", "api", ["typescript"])
        assert "package.json" in structure.files

    def test_generate_basic_structure_detects_java(self, scaffolder_no_llm):
        """Test basic structure detects Java."""
        structure = scaffolder_no_llm._generate_basic_structure("app", "api", ["java"])
        assert "pom.xml" in structure.files

    # ==========================================================================
    # write_project tests
    # ==========================================================================

    def test_write_project(self, scaffolder_no_llm):
        """Test writing project to disk."""
        structure = ProjectStructure(
            name="test-project",
            directories=["src", "tests"],
            files={
                "README.md": "# Test",
                "src/main.py": "print('hello')"
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = scaffolder_no_llm.write_project(Path(tmpdir), structure)

            assert project_path.exists()
            assert (project_path / "src").is_dir()
            assert (project_path / "tests").is_dir()
            assert (project_path / "README.md").exists()
            assert (project_path / "src" / "main.py").exists()

            # Verify content
            readme_content = (project_path / "README.md").read_text()
            assert readme_content == "# Test"


class TestScaffoldTool:
    """Tests for ScaffoldTool class."""

    @pytest.fixture
    def mock_qdrant_client(self):
        return Mock()

    @pytest.fixture
    def test_config(self):
        return {
            "scaffolding": {
                "output_dir": "./generated"
            }
        }

    @pytest.fixture
    def tool(self, mock_qdrant_client, test_config):
        return ScaffoldTool(mock_qdrant_client, "test_collection", test_config)

    def test_scaffold_project_success(self, tool):
        """Test successful project scaffolding."""
        mock_structure = ProjectStructure(
            name="test-proj",
            directories=["src"],
            files={"README.md": "# Test"}
        )

        with patch.object(tool, 'get_scaffolder') as mock_get_scaffolder:
            mock_scaffolder = Mock()
            mock_scaffolder.gather_patterns.return_value = []
            mock_scaffolder.generate_structure.return_value = mock_structure
            mock_scaffolder.write_project.return_value = Path("/tmp/test-proj")
            mock_get_scaffolder.return_value = mock_scaffolder

            result = tool.scaffold_project("test-proj", "api", "python, fastapi")

            assert "[OK]" in result
            assert "test-proj" in result
            mock_scaffolder.gather_patterns.assert_called_once()
            mock_scaffolder.generate_structure.assert_called_once()
            mock_scaffolder.write_project.assert_called_once()

    def test_scaffold_project_custom_output_dir(self, tool):
        """Test scaffolding with custom output directory."""
        mock_structure = ProjectStructure(
            name="test-proj",
            directories=["src"],
            files={"README.md": "# Test"}
        )

        with patch.object(tool, 'get_scaffolder') as mock_get_scaffolder:
            mock_scaffolder = Mock()
            mock_scaffolder.gather_patterns.return_value = []
            mock_scaffolder.generate_structure.return_value = mock_structure
            mock_scaffolder.write_project.return_value = Path("/custom/test-proj")
            mock_get_scaffolder.return_value = mock_scaffolder

            result = tool.scaffold_project("test-proj", "api", "python", output_dir="/custom")

            assert "[OK]" in result
            # Verify write_project was called with custom path
            call_args = mock_scaffolder.write_project.call_args
            assert call_args[0][0] == Path("/custom")

    def test_scaffold_project_generate_failure(self, tool):
        """Test handling structure generation failure."""
        with patch.object(tool, 'get_scaffolder') as mock_get_scaffolder:
            mock_scaffolder = Mock()
            mock_scaffolder.gather_patterns.return_value = []
            mock_scaffolder.generate_structure.return_value = None
            mock_get_scaffolder.return_value = mock_scaffolder

            result = tool.scaffold_project("test-proj", "api", "python")

            assert "[ERROR]" in result
            assert "Failed to generate" in result

    def test_scaffold_project_error(self, tool):
        """Test handling general errors."""
        with patch.object(tool, 'get_scaffolder') as mock_get_scaffolder:
            mock_get_scaffolder.side_effect = Exception("Scaffolder error")

            result = tool.scaffold_project("test-proj", "api", "python")

            assert "[ERROR]" in result
            assert "Error scaffolding" in result

    def test_scaffold_project_parses_tech_stack(self, tool):
        """Test that tech stack is properly parsed."""
        mock_structure = ProjectStructure(
            name="test",
            directories=[],
            files={}
        )

        with patch.object(tool, 'get_scaffolder') as mock_get_scaffolder:
            mock_scaffolder = Mock()
            mock_scaffolder.gather_patterns.return_value = []
            mock_scaffolder.generate_structure.return_value = mock_structure
            mock_scaffolder.write_project.return_value = Path("/tmp/test")
            mock_get_scaffolder.return_value = mock_scaffolder

            tool.scaffold_project("test", "api", "python, fastapi, postgresql")

            # Verify tech stack was parsed correctly
            call_args = mock_scaffolder.generate_structure.call_args
            tech_stack = call_args.kwargs['tech_stack']
            assert tech_stack == ["python", "fastapi", "postgresql"]
