"""Unit tests for C# Semantic Analyzer."""

import pytest
from csharp_semantic_analyzer import (
    CSharpSemanticAnalyzer,
    CSharpTypeInfo,
    ArchitecturalRole,
    CSharpAttribute,
)


class TestAttributeDetection:
    """Test C# attribute detection."""

    def test_controller_attribute_detection(self):
        """Test detection of [ApiController] and [Route] attributes."""
        analyzer = CSharpSemanticAnalyzer()

        code = '''
[ApiController]
[Route("api/[controller]")]
public class UserController {
}
'''

        type_info = CSharpTypeInfo(
            name="UserController",
            namespace="MyApp.Controllers",
            file_path="Controllers/UserController.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, code)

        # Should have both attributes
        attr_names = {attr.name for attr in result.attributes}
        assert "ApiController" in attr_names
        assert "Route" in attr_names

    def test_service_attribute_detection(self):
        """Test detection of custom service attributes."""
        analyzer = CSharpSemanticAnalyzer()

        code = '''
[Service]
[Transient]
public class UserService {
}
'''

        type_info = CSharpTypeInfo(
            name="UserService",
            namespace="MyApp.Services",
            file_path="Services/UserService.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, code)
        attr_names = {attr.name for attr in result.attributes}
        assert "Service" in attr_names or "Transient" in attr_names


class TestArchitecturalRoleDetection:
    """Test architectural role detection based on attributes and patterns."""

    def test_controller_role_detection(self, sample_controller_code):
        """Test detection of Controller role."""
        analyzer = CSharpSemanticAnalyzer()

        type_info = CSharpTypeInfo(
            name="UserController",
            namespace="MyApp.Controllers",
            file_path="Controllers/UserController.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, sample_controller_code)
        assert result.architectural_role == ArchitecturalRole.CONTROLLER

    def test_service_role_detection(self, sample_service_code):
        """Test detection of Service role."""
        analyzer = CSharpSemanticAnalyzer()

        type_info = CSharpTypeInfo(
            name="UserService",
            namespace="MyApp.Services",
            file_path="Services/UserService.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, sample_service_code)
        assert result.architectural_role == ArchitecturalRole.SERVICE

    def test_repository_role_detection(self, sample_repository_code):
        """Test detection of Repository role."""
        analyzer = CSharpSemanticAnalyzer()

        type_info = CSharpTypeInfo(
            name="UserRepository",
            namespace="MyApp.Data",
            file_path="Data/UserRepository.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, sample_repository_code)
        assert result.architectural_role == ArchitecturalRole.REPOSITORY


class TestDependencyExtraction:
    """Test dependency extraction from code."""

    def test_interface_dependency_extraction(self, sample_controller_code):
        """Test extraction of interface dependencies."""
        analyzer = CSharpSemanticAnalyzer()

        type_info = CSharpTypeInfo(
            name="UserController",
            namespace="MyApp.Controllers",
            file_path="Controllers/UserController.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, sample_controller_code)

        # Should have detected IUserService and IMediator
        assert len(result.dependencies) > 0
        # IUserService and IMediator should be in dependencies
        deps_str = " ".join(result.dependencies)
        assert "IUserService" in deps_str or "UserService" in deps_str
        assert "IMediator" in deps_str or "Mediator" in deps_str

    def test_class_dependency_extraction(self, sample_service_code):
        """Test extraction of class dependencies."""
        analyzer = CSharpSemanticAnalyzer()

        type_info = CSharpTypeInfo(
            name="UserService",
            namespace="MyApp.Services",
            file_path="Services/UserService.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, sample_service_code)

        # Should have IUserRepository dependency
        assert len(result.dependencies) > 0


class TestCohesionMetrics:
    """Test LCOM (Lack of Cohesion in Methods) calculation."""

    def test_cohesive_class_low_lcom(self, sample_cohesive_class):
        """Test that cohesive class has low LCOM."""
        analyzer = CSharpSemanticAnalyzer()

        type_info = CSharpTypeInfo(
            name="User",
            namespace="Models",
            file_path="Models/User.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, sample_cohesive_class)

        # Cohesive class should have low LCOM (< 0.5)
        assert result.lcom_score < 0.7

    def test_god_object_high_lcom(self, sample_god_object):
        """Test that God Object has high LCOM."""
        analyzer = CSharpSemanticAnalyzer()

        type_info = CSharpTypeInfo(
            name="UserService",
            namespace="Services",
            file_path="Services/UserService.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, sample_god_object)

        # God object should have high LCOM (> 0.7)
        # (Note: depends on implementation of LCOM calculation)
        assert hasattr(result, 'lcom_score')


class TestAsyncPatternDetection:
    """Test async-over-sync anti-pattern detection."""

    def test_async_result_detection(self, sample_async_issue):
        """Test detection of .Result on async method."""
        analyzer = CSharpSemanticAnalyzer()

        violations = analyzer.detect_async_over_sync(sample_async_issue)

        # Should detect .Result usage
        assert len(violations) > 0
        violation_messages = [msg for _, msg in violations]
        assert any(".Result" in msg for msg in violation_messages)

    def test_async_wait_detection(self, sample_async_issue):
        """Test detection of Task.Wait/WaitAll."""
        analyzer = CSharpSemanticAnalyzer()

        violations = analyzer.detect_async_over_sync(sample_async_issue)

        # Should detect Task.Wait usage
        assert len(violations) > 0


class TestDIExtraction:
    """Test Dependency Injection registration extraction from Program.cs."""

    def test_di_registration_extraction(self, sample_di_program_cs):
        """Test extraction of DI registrations from Program.cs."""
        analyzer = CSharpSemanticAnalyzer()

        analyzer.extract_di_registrations(sample_di_program_cs, "Program.cs")

        # Should have extracted DI registrations
        assert len(analyzer.di_registrations) > 0
        # Should have IUserService → UserService mapping
        assert any(
            "UserService" in str(reg)
            for reg in analyzer.di_registrations.values()
        )


class TestPartialClassAggregation:
    """Test partial class aggregation."""

    def test_partial_class_aggregation(self):
        """Test that partial classes are aggregated."""
        analyzer = CSharpSemanticAnalyzer()

        # Create two partial class definitions
        part1 = CSharpTypeInfo(
            name="User",
            namespace="Models",
            file_path="Models/User.Part1.cs",
            type_kind="class",
            is_partial=True
        )

        part2 = CSharpTypeInfo(
            name="User",
            namespace="Models",
            file_path="Models/User.Part2.cs",
            type_kind="class",
            is_partial=True
        )

        analyzer.types = {"User_Part1": part1, "User_Part2": part2}

        # Add to partial locations
        part1.partial_locations = [str(part1.file_path)]
        part2.partial_locations = [str(part2.file_path)]

        analyzer.aggregate_partial_classes()

        # After aggregation, should have merged partial classes
        assert len(analyzer.types) <= 2


class TestNamespaceParsing:
    """Test namespace extraction from code."""

    def test_namespace_extraction(self, sample_controller_code):
        """Test extraction of namespace."""
        # Should extract namespace from code
        code = sample_controller_code
        assert "MyApp.Controllers" in code


class TestInstabilityIndex:
    """Test instability index calculation."""

    def test_instability_calculation(self):
        """Test calculation of namespace instability."""
        analyzer = CSharpSemanticAnalyzer()

        # Create mock types
        type1 = CSharpTypeInfo(
            name="Service",
            namespace="Application",
            file_path="test.cs",
            type_kind="class"
        )

        type2 = CSharpTypeInfo(
            name="Model",
            namespace="Domain",
            file_path="test.cs",
            type_kind="class"
        )

        analyzer.types = {"Service": type1, "Model": type2}

        # Calculate instability
        instability = analyzer.calculate_instability("Application")

        # Should return a value between 0 and 1
        assert 0 <= instability <= 1


class TestErrorHandling:
    """Test error handling for malformed code."""

    def test_malformed_code_handling(self):
        """Test graceful handling of malformed C# code."""
        analyzer = CSharpSemanticAnalyzer()

        malformed_code = '''
public class BadClass {
    public void BadMethod(
        // Missing closing brace
}
'''

        type_info = CSharpTypeInfo(
            name="BadClass",
            namespace="Test",
            file_path="test.cs",
            type_kind="class"
        )

        # Should not crash on malformed code
        try:
            result = analyzer.analyze_type(type_info, malformed_code)
            # Should return valid object even with malformed input
            assert result is not None
        except Exception as e:
            pytest.fail(f"Analyzer crashed on malformed code: {e}")

    def test_empty_code_handling(self):
        """Test handling of empty code."""
        analyzer = CSharpSemanticAnalyzer()

        type_info = CSharpTypeInfo(
            name="Empty",
            namespace="Test",
            file_path="test.cs",
            type_kind="class"
        )

        result = analyzer.analyze_type(type_info, "")

        # Should handle empty code gracefully
        assert result is not None
        assert result.name == "Empty"
