"""Integration tests for C# Project Analysis - High Priority Tests."""

import pytest

from csharp_audit_integration import CSharpArchitecturalAuditor
from csharp_semantic_analyzer import ArchitecturalRole, CSharpTypeInfo
from models import PatternCategory


class TestFileAnalysis:
    """Test C# file analysis with various scenarios."""

    def test_analyze_csharp_file_empty_content(self):
        """AnalyzeFile_EmptyContent_ReturnsEmptyList

        Arrange: Empty file content
        Act: Analyze file
        Assert: Should return empty list without error
        """
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_file("empty.cs", "")

        assert result == []

    def test_analyze_csharp_file_whitespace_only(self):
        """AnalyzeFile_WhitespaceOnly_ReturnsEmptyList

        Arrange: File with only whitespace
        Act: Analyze file
        Assert: Should return empty list without error
        """
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_file("whitespace.cs", "   \n\n  \t  ")

        assert result == []

    def test_analyze_csharp_file_valid_controller(self, sample_controller_code):
        """AnalyzeFile_ValidController_ReturnsTypeInfo

        Arrange: Valid controller code
        Act: Analyze file
        Assert: Should extract type info with correct role
        """
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_file(
            "UserController.cs", sample_controller_code
        )

        assert len(result) > 0
        controller_type = result[0]
        assert controller_type.name == "UserController"
        assert controller_type.architectural_role == ArchitecturalRole.CONTROLLER

    def test_analyze_csharp_file_with_async_violations(self, sample_async_issue):
        """AnalyzeFile_AsyncViolations_DetectsAndLogs

        Arrange: Code with async-over-sync
        Act: Analyze file
        Assert: Should detect violations
        """
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_file("BadService.cs", sample_async_issue)

        assert len(result) > 0
        type_info = result[0]
        assert len(type_info.async_violations) > 0

    def test_analyze_csharp_file_extracts_namespace(self):
        """AnalyzeFile_WithNamespace_ExtractsCorrectly

        Arrange: File with explicit namespace
        Act: Analyze file
        Assert: Should extract namespace
        """
        auditor = CSharpArchitecturalAuditor()

        code = """
        namespace MyApp.Services {
            public class TestService {
                public void DoWork() { }
            }
        }
        """

        result = auditor.analyze_csharp_file("TestService.cs", code)

        assert len(result) > 0
        assert result[0].namespace == "MyApp.Services"


class TestProjectAnalysis:
    """Test full C# project analysis."""

    def test_analyze_project_nonexistent_path(self):
        """AnalyzeProject_NonexistentPath_RaisesFileNotFoundError

        Arrange: Invalid project path
        Act: Analyze project
        Assert: Should raise FileNotFoundError
        """
        auditor = CSharpArchitecturalAuditor()

        with pytest.raises(FileNotFoundError):
            auditor.analyze_csharp_project("/nonexistent/path/that/does/not/exist")

    def test_analyze_project_empty_path(self):
        """AnalyzeProject_EmptyPath_RaisesValueError

        Arrange: Empty project path
        Act: Analyze project
        Assert: Should raise ValueError
        """
        auditor = CSharpArchitecturalAuditor()

        with pytest.raises(ValueError, match="project_path cannot be empty"):
            auditor.analyze_csharp_project("")

    def test_analyze_project_no_csharp_files(self, tmp_path):
        """AnalyzeProject_NoCSharpFiles_ReturnsEmptyResult

        Arrange: Directory without .cs files
        Act: Analyze project
        Assert: Should return result with 0 files analyzed
        """
        auditor = CSharpArchitecturalAuditor()

        # Create empty directory
        test_dir = tmp_path / "empty_project"
        test_dir.mkdir()

        result = auditor.analyze_csharp_project(str(test_dir))

        assert result["files_analyzed"] == 0
        assert result["types_analyzed"] == 0
        assert result["audit_result"] is None

    def test_analyze_project_with_program_cs(self, tmp_path, sample_di_program_cs):
        """AnalyzeProject_WithProgramCs_ExtractsDI

        Arrange: Project with Program.cs containing DI registrations
        Act: Analyze project
        Assert: Should extract DI registrations
        """
        auditor = CSharpArchitecturalAuditor()

        # Create Program.cs
        program_file = tmp_path / "Program.cs"
        program_file.write_text(sample_di_program_cs)

        result = auditor.analyze_csharp_project(str(tmp_path))

        assert result["files_analyzed"] == 1
        # DI registrations should be extracted
        assert len(auditor.semantic_analyzer.di_registrations) > 0

    def test_analyze_project_batch_processing(self, tmp_path):
        """AnalyzeProject_LargeProject_ProcessesInBatches

        Arrange: Project with many files
        Act: Analyze with small batch size
        Assert: Should process all files
        """
        auditor = CSharpArchitecturalAuditor()

        # Create 10 files
        for i in range(10):
            file = tmp_path / f"Class{i}.cs"
            file.write_text(f"namespace Test {{ public class Class{i} {{}} }}")

        result = auditor.analyze_csharp_project(str(tmp_path), batch_size=3)

        assert result["files_analyzed"] == 10

    def test_analyze_project_skips_invalid_files(self, tmp_path):
        """AnalyzeProject_InvalidFiles_SkipsAndContinues

        Arrange: Mix of valid and invalid files
        Act: Analyze project
        Assert: Should process valid files and skip invalid ones
        """
        auditor = CSharpArchitecturalAuditor()

        # Create valid file
        valid_file = tmp_path / "Valid.cs"
        valid_file.write_text("namespace Test { public class Valid {} }")

        # Create invalid file (not parseable C#)
        invalid_file = tmp_path / "Invalid.cs"
        invalid_file.write_text("this is not valid C# code @@@@")

        result = auditor.analyze_csharp_project(str(tmp_path))

        # Should process at least the valid file
        assert result["files_analyzed"] >= 1 or result["files_skipped"] >= 1

    def test_analyze_project_with_multiple_files(
        self, tmp_path, sample_controller_code, sample_service_code
    ):
        """AnalyzeProject_MultipleFiles_ProcessesAll

        Arrange: Project with controller and service
        Act: Analyze project
        Assert: Should process both files
        """
        auditor = CSharpArchitecturalAuditor()

        # Create files
        controller_file = tmp_path / "UserController.cs"
        controller_file.write_text(sample_controller_code)

        service_file = tmp_path / "UserService.cs"
        service_file.write_text(sample_service_code)

        result = auditor.analyze_csharp_project(str(tmp_path))

        assert result["files_analyzed"] == 2
        assert result["types_analyzed"] >= 2


class TestDNAPatternConversion:
    """Test conversion from C# types to DNA patterns."""

    def test_convert_to_dna_patterns_empty_list(self):
        """ConvertToPatterns_EmptyList_ReturnsEmpty

        Arrange: Empty types list
        Act: Convert to DNA patterns
        Assert: Should return empty list
        """
        auditor = CSharpArchitecturalAuditor()

        patterns = auditor.convert_to_dna_patterns([])

        assert patterns == []

    def test_convert_to_dna_patterns_invalid_type(self):
        """ConvertToPatterns_InvalidType_RaisesTypeError

        Arrange: Non-list argument
        Act: Convert
        Assert: Should raise TypeError
        """
        auditor = CSharpArchitecturalAuditor()

        with pytest.raises(TypeError):
            auditor.convert_to_dna_patterns("not a list")

    def test_convert_to_dna_patterns_filters_god_objects(self):
        """ConvertToPatterns_GodObject_FiltersOut

        Arrange: Type with LCOM > 0.8
        Act: Convert to patterns
        Assert: Should not include God Objects
        """
        auditor = CSharpArchitecturalAuditor()

        god_object = CSharpTypeInfo(
            name="GodClass",
            namespace="Services",
            file_path="GodClass.cs",
            type_kind="class",
            lcom_score=0.9,
        )

        patterns = auditor.convert_to_dna_patterns([god_object])

        # God Objects should be filtered out
        assert len(patterns) == 0

    def test_convert_to_dna_patterns_maps_categories_correctly(self):
        """ConvertToPatterns_VariousRoles_MapsCategoriesCorrectly

        Arrange: Types with different architectural roles
        Act: Convert to patterns
        Assert: Should map to correct PatternCategory
        """
        auditor = CSharpArchitecturalAuditor()

        controller = CSharpTypeInfo(
            name="UserController",
            namespace="Controllers",
            file_path="UserController.cs",
            type_kind="class",
            architectural_role=ArchitecturalRole.CONTROLLER,
            lcom_score=0.3,
        )

        repository = CSharpTypeInfo(
            name="UserRepository",
            namespace="Data",
            file_path="UserRepository.cs",
            type_kind="class",
            architectural_role=ArchitecturalRole.REPOSITORY,
            lcom_score=0.3,
        )

        patterns = auditor.convert_to_dna_patterns([controller, repository])

        assert len(patterns) == 2

        controller_pattern = next(p for p in patterns if "Controller" in p.title)
        assert controller_pattern.category == PatternCategory.API_DESIGN

        repo_pattern = next(p for p in patterns if "Repository" in p.title)
        assert repo_pattern.category == PatternCategory.DATA_ACCESS

    def test_convert_to_dna_patterns_calculates_quality_score(self):
        """ConvertToPatterns_VariousMetrics_CalculatesQualityScore

        Arrange: Types with different metrics
        Act: Convert
        Assert: Quality scores should reflect metrics
        """
        auditor = CSharpArchitecturalAuditor()

        # Good class: low LCOM, low complexity, few dependencies
        good_class = CSharpTypeInfo(
            name="GoodService",
            namespace="Services",
            file_path="GoodService.cs",
            type_kind="class",
            architectural_role=ArchitecturalRole.SERVICE,
            lcom_score=0.2,
            cyclomatic_complexity=5,
            lines_of_code=150,
        )
        good_class.dependencies = {"IRepository", "ILogger"}

        # Bad class: high LCOM, high complexity, many dependencies
        bad_class = CSharpTypeInfo(
            name="BadService",
            namespace="Services",
            file_path="BadService.cs",
            type_kind="class",
            architectural_role=ArchitecturalRole.SERVICE,
            lcom_score=0.7,
            cyclomatic_complexity=60,
            lines_of_code=550,
        )
        bad_class.dependencies = {f"Dep{i}" for i in range(16)}

        patterns = auditor.convert_to_dna_patterns([good_class, bad_class])

        good_pattern = next(p for p in patterns if "GoodService" in p.title)
        bad_pattern = next(p for p in patterns if "BadService" in p.title)

        assert good_pattern.quality_score > bad_pattern.quality_score

    def test_convert_to_dna_patterns_includes_metadata(self):
        """ConvertToPatterns_ValidType_IncludesMetadata

        Arrange: Type with full metadata
        Act: Convert to pattern
        Assert: Pattern should include use_cases and quality_score
        """
        auditor = CSharpArchitecturalAuditor()

        type_info = CSharpTypeInfo(
            name="UserService",
            namespace="Services",
            file_path="UserService.cs",
            type_kind="class",
            architectural_role=ArchitecturalRole.SERVICE,
            lcom_score=0.3,
            cyclomatic_complexity=10,
            lines_of_code=200,
        )
        type_info.dependencies = {"IUserRepository"}

        patterns = auditor.convert_to_dna_patterns([type_info])

        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.quality_score >= 1
        assert pattern.quality_score <= 10
        assert len(pattern.use_cases) > 0


class TestReportGeneration:
    """Test audit report generation."""

    def test_generate_reports_creates_all_formats(self, tmp_path):
        """GenerateReports_ValidResult_CreatesAllFormats

        Arrange: Valid analysis result
        Act: Generate reports
        Assert: Should create JSON, Markdown, SARIF files
        """
        auditor = CSharpArchitecturalAuditor()

        # Create minimal analysis result
        from csharp_audit_engine import AuditResult

        analysis_result = {
            "project_path": str(tmp_path),
            "files_analyzed": 1,
            "types_analyzed": 1,
            "types": {},
            "audit_result": AuditResult(
                total_types=1,
                total_violations=0,
                violations_by_severity={},
                violations_by_rule={},
                violations=[],
                metrics={},
            ),
        }

        output_dir = tmp_path / "reports"
        auditor.generate_reports(analysis_result, str(output_dir))

        # Check all report files exist
        assert (output_dir / "audit_report.json").exists()
        assert (output_dir / "audit_report.md").exists()
        assert (output_dir / "audit_report.sarif").exists()

    def test_generate_reports_creates_output_directory(self, tmp_path):
        """GenerateReports_NonexistentOutputDir_CreatesDirectory

        Arrange: Output directory doesn't exist
        Act: Generate reports
        Assert: Should create directory
        """
        auditor = CSharpArchitecturalAuditor()

        from csharp_audit_engine import AuditResult

        analysis_result = {
            "project_path": str(tmp_path),
            "files_analyzed": 0,
            "types_analyzed": 0,
            "types": {},
            "audit_result": AuditResult(
                total_types=0,
                total_violations=0,
                violations_by_severity={},
                violations_by_rule={},
                violations=[],
                metrics={},
            ),
        }

        output_dir = tmp_path / "nonexistent" / "nested" / "reports"
        auditor.generate_reports(analysis_result, str(output_dir))

        assert output_dir.exists()
        assert output_dir.is_dir()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_analyze_project_with_file_path_instead_of_directory(self, tmp_path):
        """AnalyzeProject_FilePath_UsesParentDirectory

        Arrange: Path to a .cs file instead of directory
        Act: Analyze project
        Assert: Should use parent directory
        """
        auditor = CSharpArchitecturalAuditor()

        # Create a single file
        cs_file = tmp_path / "Test.cs"
        cs_file.write_text("namespace Test { public class Test {} }")

        # Pass file path instead of directory
        result = auditor.analyze_csharp_project(str(cs_file))

        # Should process the file from parent directory
        assert result["files_analyzed"] >= 1

    def test_analyze_file_with_null_bytes(self):
        """AnalyzeFile_NullBytes_HandlesGracefully

        Arrange: Code with null bytes
        Act: Analyze file
        Assert: Should handle without crashing
        """
        auditor = CSharpArchitecturalAuditor()

        # Code with null byte
        code = "public class Test { \x00 }"

        # Should not crash
        result = auditor.analyze_csharp_file("test.cs", code)

        # Result may be empty or have extracted what it could
        assert isinstance(result, list)

    def test_convert_patterns_with_none_values_in_type_info(self):
        """ConvertPatterns_NoneValues_HandlesGracefully

        Arrange: TypeInfo with None in some fields
        Act: Convert to patterns
        Assert: Should handle without crashing
        """
        auditor = CSharpArchitecturalAuditor()

        type_info = CSharpTypeInfo(
            name="TestClass",
            namespace="",  # Empty namespace
            file_path="test.cs",
            type_kind="class",
            lcom_score=0.5,
        )

        patterns = auditor.convert_to_dna_patterns([type_info])

        # Should not crash and produce valid pattern
        assert isinstance(patterns, list)
        if len(patterns) > 0:
            assert patterns[0].title is not None
            assert patterns[0].description is not None
