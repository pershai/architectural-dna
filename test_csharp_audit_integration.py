"""Unit tests for C# Audit Integration."""

import pytest

from csharp_audit_integration import CSharpArchitecturalAuditor
from models import Language


@pytest.fixture
def auditor():
    """Create C# architectural auditor."""
    return CSharpArchitecturalAuditor()


class TestSingleFileAnalysis:
    """Test analysis of single C# file."""

    def test_analyze_single_controller_file(self, auditor, sample_controller_code):
        """Test analysis of single controller file."""
        types = auditor.analyze_csharp_file(
            "Controllers/UserController.cs", sample_controller_code
        )

        # Should extract at least the controller
        assert len(types) > 0
        assert any(t.name == "UserController" for t in types)

    def test_analyze_single_service_file(self, auditor, sample_service_code):
        """Test analysis of single service file."""
        types = auditor.analyze_csharp_file(
            "Services/UserService.cs", sample_service_code
        )

        # Should extract service and interface
        assert len(types) > 0
        type_names = {t.name for t in types}
        assert "UserService" in type_names or "IUserService" in type_names

    def test_analyze_returns_type_info(self, auditor, sample_controller_code):
        """Test that analysis returns proper TypeInfo objects."""
        types = auditor.analyze_csharp_file("test.cs", sample_controller_code)

        for type_info in types:
            # Check required attributes
            assert hasattr(type_info, "name")
            assert hasattr(type_info, "namespace")
            assert hasattr(type_info, "file_path")
            assert hasattr(type_info, "type_kind")


class TestProjectAnalysis:
    """Test analysis of entire C# project."""

    def test_analyze_project_directory(self, tmp_path, auditor):
        """Test analysis of project directory structure."""
        # Create project structure
        project_root = tmp_path / "TestProject"
        project_root.mkdir()

        (project_root / "Controllers").mkdir()
        (project_root / "Services").mkdir()

        # Create sample files
        controller_file = project_root / "Controllers" / "UserController.cs"
        controller_file.write_text("""
using Microsoft.AspNetCore.Mvc;

namespace TestProject.Controllers {
    [ApiController]
    public class UserController {
        public void GetUser(int id) { }
    }
}
""")

        service_file = project_root / "Services" / "UserService.cs"
        service_file.write_text("""
namespace TestProject.Services {
    public class UserService {
        public void GetUser(int id) { }
    }
}
""")

        result = auditor.analyze_csharp_project(str(project_root))

        # Should have analyzed project
        assert "types" in result
        assert len(result["types"]) > 0

    def test_analyze_project_with_patterns(self, tmp_path, auditor):
        """Test project analysis with include patterns."""
        project_root = tmp_path / "TestProject"
        project_root.mkdir()

        # Create files
        (project_root / "good.cs").write_text("""
namespace Test {
    public class GoodClass { }
}
""")

        (project_root / "test.cs").write_text("""
namespace Test {
    public class TestClass { }
}
""")

        # Analyze only non-test files
        result = auditor.analyze_csharp_project(
            str(project_root), include_patterns=["*.cs", "!test*.cs"]
        )

        # Should have types from analysis
        assert "types" in result


class TestAsyncViolationsStorage:
    """Test storage of async violations in type info."""

    def test_async_violations_detected_and_stored(self, auditor, sample_async_issue):
        """Test that async violations are detected and stored."""
        types = auditor.analyze_csharp_file("test.cs", sample_async_issue)

        # Find the service with async violations
        for type_info in types:
            if type_info.async_violations:
                # Should have violations stored
                assert len(type_info.async_violations) > 0
                # Each violation is (line_num, message)
                for line_num, message in type_info.async_violations:
                    assert isinstance(line_num, int)
                    assert isinstance(message, str)
                return

        # Should find at least one violation
        pytest.fail("No async violations detected")

    def test_async_violations_reported_in_audit(self, auditor, sample_async_issue):
        """Test that async violations appear in audit report."""
        types = auditor.analyze_csharp_file("test.cs", sample_async_issue)

        # Store types for audit engine
        auditor.semantic_analyzer.types = {t.name: t for t in types}

        # Run audit
        audit_result = auditor.audit_engine.run_all_audits()

        # Should have async violations in report
        async_violations = [v for v in audit_result.violations if "ASYNC" in v.rule_id]

        if any(t.async_violations for t in types):
            assert len(async_violations) > 0


class TestDIRegistrationExtraction:
    """Test DI registration extraction from Program.cs."""

    def test_di_extraction_from_program_cs(self, auditor, sample_di_program_cs):
        """Test extraction of DI registrations."""
        auditor.semantic_analyzer.extract_di_registrations(
            sample_di_program_cs, "Program.cs"
        )

        # Should have extracted DI registrations
        assert len(auditor.semantic_analyzer.di_registrations) > 0

    def test_di_registrations_linked(self, auditor, sample_di_program_cs):
        """Test that DI registrations are linked."""
        auditor.semantic_analyzer.extract_di_registrations(
            sample_di_program_cs, "Program.cs"
        )

        auditor.semantic_analyzer.link_di_registrations()

        # Should have linked registrations
        di_regs = auditor.semantic_analyzer.di_registrations
        assert len(di_regs) > 0


class TestPartialClassHandling:
    """Test handling of partial classes."""

    def test_partial_class_aggregation(self, auditor, sample_partial_class):
        """Test aggregation of partial classes."""
        file1_types = auditor.analyze_csharp_file(
            "User.Part1.cs", sample_partial_class[0]
        )
        file2_types = auditor.analyze_csharp_file(
            "User.Part2.cs", sample_partial_class[1]
        )

        # Should detect partial classes
        for type_info in file1_types + file2_types:
            if type_info.name == "User":
                assert type_info.is_partial

    def test_partial_class_locations_tracked(self, auditor, sample_partial_class):
        """Test that partial class locations are tracked."""
        types1 = auditor.analyze_csharp_file("User.Part1.cs", sample_partial_class[0])
        types2 = auditor.analyze_csharp_file("User.Part2.cs", sample_partial_class[1])

        for type_info in types1 + types2:
            if type_info.is_partial:
                assert len(type_info.partial_locations) > 0


class TestPatternConversion:
    """Test conversion of types to DNA patterns."""

    def test_convert_controller_to_pattern(self, auditor, sample_controller_code):
        """Test conversion of controller to pattern."""
        types = auditor.analyze_csharp_file("test.cs", sample_controller_code)
        auditor.semantic_analyzer.types = {t.name: t for t in types}

        patterns = auditor.convert_to_dna_patterns(
            [t for t in types if t.name == "UserController"], "test-repo"
        )

        # Should convert to patterns
        assert len(patterns) > 0
        pattern = patterns[0]

        # Check pattern fields
        assert pattern.title
        assert pattern.description
        assert pattern.language == Language.CSHARP
        assert pattern.source_repo == "test-repo"
        assert pattern.quality_score > 0

    def test_convert_multiple_types_to_patterns(self, auditor):
        """Test conversion of multiple types to patterns."""
        from csharp_semantic_analyzer import ArchitecturalRole, CSharpTypeInfo

        type1 = CSharpTypeInfo(
            name="UserController",
            namespace="Controllers",
            file_path="test.cs",
            type_kind="class",
            architectural_role=ArchitecturalRole.CONTROLLER,
        )

        type2 = CSharpTypeInfo(
            name="UserService",
            namespace="Services",
            file_path="test.cs",
            type_kind="class",
            architectural_role=ArchitecturalRole.SERVICE,
        )

        auditor.semantic_analyzer.types = {
            "UserController": type1,
            "UserService": type2,
        }

        patterns = auditor.convert_to_dna_patterns([type1, type2], "repo")

        assert len(patterns) == 2
        assert any("Controller" in p.title for p in patterns)
        assert any("Service" in p.title for p in patterns)


class TestErrorHandling:
    """Test error handling in analysis."""

    def test_malformed_code_handling(self, auditor):
        """Test graceful handling of malformed C# code."""
        malformed_code = """
public class BadClass {
    public void BadMethod(
        // Missing closing brace
}
"""

        # Should not crash
        try:
            types = auditor.analyze_csharp_file("bad.cs", malformed_code)
            # Should return empty or partial result
            assert isinstance(types, list)
        except Exception as e:
            pytest.fail(f"Analyzer crashed on malformed code: {e}")

    def test_empty_file_handling(self, auditor):
        """Test handling of empty C# file."""
        types = auditor.analyze_csharp_file("empty.cs", "")

        # Should return empty list
        assert isinstance(types, list)
        assert len(types) == 0

    def test_file_encoding_error_handling(self, tmp_path, auditor):
        """Test handling of file with unsupported encoding."""
        project_root = tmp_path / "Project"
        project_root.mkdir()

        # Create file with Windows-1252 encoding
        test_file = project_root / "test.cs"
        test_file.write_text("public class Test { }", encoding="windows-1252")

        # Should handle gracefully even if encoding issues
        try:
            result = auditor.analyze_csharp_project(str(project_root))
            assert "types" in result
        except UnicodeDecodeError:
            pytest.fail("Should handle encoding errors gracefully")


class TestNamespaceExtraction:
    """Test namespace extraction from code."""

    def test_namespace_extraction_from_code(self, auditor, sample_controller_code):
        """Test extraction of namespace."""
        types = auditor.analyze_csharp_file("test.cs", sample_controller_code)

        # Should extract namespace
        for type_info in types:
            assert type_info.namespace is not None
            assert "MyApp" in type_info.namespace


class TestCompleteAnalysisFlow:
    """Test complete analysis workflow."""

    def test_end_to_end_analysis_flow(self, tmp_path, auditor):
        """Test complete analysis from project to patterns."""
        # Setup
        project_root = tmp_path / "MyProject"
        project_root.mkdir()
        (project_root / "Controllers").mkdir()
        (project_root / "Services").mkdir()

        # Create files
        (project_root / "Controllers" / "UserController.cs").write_text("""
using Microsoft.AspNetCore.Mvc;
namespace MyProject.Controllers {
    [ApiController]
    public class UserController {
        private readonly IUserService service;
        public UserController(IUserService s) { service = s; }
    }
}
""")

        (project_root / "Services" / "UserService.cs").write_text("""
namespace MyProject.Services {
    public interface IUserService { }
    public class UserService : IUserService { }
}
""")

        # Analyze
        result = auditor.analyze_csharp_project(str(project_root))

        # Verify
        assert result["total_types"] > 0
        assert len(result["types"]) > 0

        # Convert to patterns
        patterns = result.get("patterns", [])
        if patterns:
            assert all(hasattr(p, "language") for p in patterns)
            assert all(p.language == Language.CSHARP for p in patterns)
