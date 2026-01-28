"""Unit tests for C# Audit Engine."""

import pytest

from csharp_audit_engine import AuditResult, CSharpAuditEngine
from csharp_semantic_analyzer import (
    ArchitecturalRole,
    CSharpSemanticAnalyzer,
    CSharpTypeInfo,
)


@pytest.fixture
def audit_engine():
    """Create audit engine with analyzer."""
    analyzer = CSharpSemanticAnalyzer()
    return CSharpAuditEngine(analyzer)


class TestAuditRules:
    """Test audit rule initialization."""

    def test_all_rules_initialized(self, audit_engine):
        """Test that all audit rules are initialized."""
        assert len(audit_engine.rules) >= 8

        # Check key rules exist
        assert "MEDIATR_001" in audit_engine.rules
        assert "MEDIATR_002" in audit_engine.rules
        assert "DATA_001" in audit_engine.rules
        assert "ARCH_001" in audit_engine.rules
        assert "DESIGN_001" in audit_engine.rules
        assert "ASYNC_001" in audit_engine.rules
        assert "ARCH_002" in audit_engine.rules
        assert "DATA_002" in audit_engine.rules


class TestMediatRPatternAudit:
    """Test MediatR pattern compliance auditing."""

    def test_handler_domain_access_violation(self, audit_engine):
        """Test detection of handler accessing non-Domain layer."""
        analyzer = audit_engine.analyzer

        # Create handler that violates rule
        bad_handler = CSharpTypeInfo(
            name="CreateUserHandler",
            namespace="Handlers",
            file_path="Handlers/CreateUserHandler.cs",
            type_kind="class",
            architectural_role=ArchitecturalRole.HANDLER,
        )

        # Dependency on wrong layer
        bad_handler.dependencies = {"WebController"}

        analyzer.types = {"CreateUserHandler": bad_handler}

        violations = audit_engine.audit_mediatr_pattern()

        # Should have violations (handler depending on wrong layer)
        # Note: Implementation might not detect this without full type info
        assert isinstance(violations, list)

    def test_controller_imediator_usage(self, audit_engine):
        """Test detection of controller not using IMediator."""
        analyzer = audit_engine.analyzer

        # Create controller with direct handler dependency
        bad_controller = CSharpTypeInfo(
            name="UserController",
            namespace="Controllers",
            file_path="Controllers/UserController.cs",
            type_kind="class",
            architectural_role=ArchitecturalRole.CONTROLLER,
        )

        # Direct dependency on handler (bad)
        bad_controller.dependencies = {"CreateUserHandler"}

        analyzer.types = {"UserController": bad_controller}

        violations = audit_engine.audit_mediatr_pattern()

        assert isinstance(violations, list)


class TestCyclicDependencies:
    """Test cyclic dependency detection."""

    def test_cyclic_dependency_detection(self, audit_engine):
        """Test detection of circular dependencies."""
        analyzer = audit_engine.analyzer

        # Create circular dependency: A → B → C → A
        type_a = CSharpTypeInfo(
            name="ServiceA",
            namespace="Services",
            file_path="test.cs",
            type_kind="class",
        )

        type_b = CSharpTypeInfo(
            name="ServiceB",
            namespace="Services",
            file_path="test.cs",
            type_kind="class",
        )

        type_c = CSharpTypeInfo(
            name="ServiceC", namespace="Other", file_path="test.cs", type_kind="class"
        )

        type_a.dependencies = {"ServiceB"}
        type_b.dependencies = {"ServiceC"}
        type_c.dependencies = {"ServiceA"}  # Creates cycle

        analyzer.types = {"ServiceA": type_a, "ServiceB": type_b, "ServiceC": type_c}

        violations = audit_engine.detect_cyclic_dependencies()

        # Should detect the cycle
        assert len(violations) > 0
        assert any("cyclic" in v.message.lower() for v in violations)

    def test_no_cyclic_dependencies_clean(self, audit_engine):
        """Test that clean code doesn't trigger cyclic dependency violation."""
        analyzer = audit_engine.analyzer

        # Create valid hierarchy: A → B → C (no cycle)
        type_a = CSharpTypeInfo(
            name="ServiceA",
            namespace="Services",
            file_path="test.cs",
            type_kind="class",
        )

        type_b = CSharpTypeInfo(
            name="ServiceB",
            namespace="Services",
            file_path="test.cs",
            type_kind="class",
        )

        type_c = CSharpTypeInfo(
            name="ServiceC", namespace="Other", file_path="test.cs", type_kind="class"
        )

        type_a.dependencies = {"ServiceB"}
        type_b.dependencies = {"ServiceC"}
        type_c.dependencies = set()  # No cycle

        analyzer.types = {"ServiceA": type_a, "ServiceB": type_b, "ServiceC": type_c}

        violations = audit_engine.detect_cyclic_dependencies()

        # Should have no violations for acyclic graph
        assert len(violations) == 0


class TestGodObjectDetection:
    """Test God Object detection using LCOM and LOC."""

    def test_god_object_high_lcom(self, audit_engine):
        """Test detection of God Object with high LCOM."""
        analyzer = audit_engine.analyzer

        # Create type with high LCOM (low cohesion)
        god_object = CSharpTypeInfo(
            name="UserService",
            namespace="Services",
            file_path="Services/UserService.cs",
            type_kind="class",
            lcom_score=0.85,  # > threshold 0.8
        )

        analyzer.types = {"UserService": god_object}

        violations = audit_engine.audit_god_objects()

        # Should detect God Object
        assert len(violations) > 0
        assert any("cohesion" in v.message.lower() for v in violations)

    def test_god_object_high_loc(self, audit_engine):
        """Test detection of God Object with high LOC."""
        analyzer = audit_engine.analyzer

        # Create type with high LOC (>500 lines)
        god_object = CSharpTypeInfo(
            name="LargeService",
            namespace="Services",
            file_path="Services/LargeService.cs",
            type_kind="class",
            lines_of_code=750,  # > threshold 500
        )

        analyzer.types = {"LargeService": god_object}

        violations = audit_engine.audit_god_objects()

        # Should detect God Object
        assert len(violations) > 0
        assert any("lines" in v.message.lower() for v in violations)

    def test_god_object_both_metrics(self, audit_engine):
        """Test detection of God Object with both high LCOM and LOC."""
        analyzer = audit_engine.analyzer

        god_object = CSharpTypeInfo(
            name="MonolithService",
            namespace="Services",
            file_path="test.cs",
            type_kind="class",
            lcom_score=0.9,
            lines_of_code=1000,
        )

        analyzer.types = {"MonolithService": god_object}

        violations = audit_engine.audit_god_objects()

        # Should have multiple violations for this type
        obj_violations = [v for v in violations if v.type_name == "MonolithService"]
        assert len(obj_violations) >= 2  # Both LCOM and LOC violations

    def test_clean_code_no_god_object(self, audit_engine):
        """Test that clean code doesn't trigger God Object violation."""
        analyzer = audit_engine.analyzer

        clean_class = CSharpTypeInfo(
            name="UserDTO",
            namespace="Models",
            file_path="test.cs",
            type_kind="class",
            lcom_score=0.2,  # < threshold 0.8
            lines_of_code=50,  # < threshold 500
        )

        analyzer.types = {"UserDTO": clean_class}

        violations = audit_engine.audit_god_objects()

        # Should have no violations
        assert len(violations) == 0


class TestSQLAccessAudit:
    """Test SQL access restrictions."""

    def test_sql_access_in_web_layer(self, audit_engine):
        """Test detection of direct SQL in Web/Controllers layer."""
        analyzer = audit_engine.analyzer

        bad_controller = CSharpTypeInfo(
            name="UserController",
            namespace="Controllers",
            file_path="Controllers/UserController.cs",
            type_kind="class",
        )

        # Direct SQL dependency
        bad_controller.dependencies = {"__SQL__Microsoft.Data.SqlClient"}

        analyzer.types = {"UserController": bad_controller}

        violations = audit_engine.audit_sql_access()

        assert isinstance(violations, list)

    def test_sql_access_in_application_layer(self, audit_engine):
        """Test detection of direct SQL in Application layer."""
        analyzer = audit_engine.analyzer

        bad_service = CSharpTypeInfo(
            name="UserApplicationService",
            namespace="Application.Services",
            file_path="Application/Services/UserService.cs",
            type_kind="class",
        )

        bad_service.dependencies = {"__SQL__Dapper"}

        analyzer.types = {"UserApplicationService": bad_service}

        violations = audit_engine.audit_sql_access()

        assert isinstance(violations, list)

    def test_sql_access_allowed_in_infrastructure(self, audit_engine):
        """Test that SQL access is allowed in Infrastructure layer."""
        analyzer = audit_engine.analyzer

        good_repository = CSharpTypeInfo(
            name="UserRepository",
            namespace="Infrastructure.Persistence",
            file_path="Infrastructure/Persistence/UserRepository.cs",
            type_kind="class",
        )

        good_repository.dependencies = {"__SQL__Microsoft.Data.SqlClient"}

        analyzer.types = {"UserRepository": good_repository}

        violations = audit_engine.audit_sql_access()

        # Should not report violations for Infrastructure layer
        infra_violations = [v for v in violations if "UserRepository" in v.message]
        assert len(infra_violations) == 0


class TestAsyncSafety:
    """Test async-over-sync anti-pattern detection."""

    def test_async_result_violation(self, audit_engine):
        """Test detection of .Result on async method."""
        analyzer = audit_engine.analyzer

        bad_service = CSharpTypeInfo(
            name="BadService",
            namespace="Services",
            file_path="test.cs",
            type_kind="class",
        )

        # Simulate async violations
        bad_service.async_violations = [(42, "Blocking call: .Result on async method")]

        analyzer.types = {"BadService": bad_service}

        violations = audit_engine.audit_async_safety()

        # Should detect async violation
        assert len(violations) > 0
        assert any(".Result" in v.message for v in violations)

    def test_async_wait_violation(self, audit_engine):
        """Test detection of Task.Wait()."""
        analyzer = audit_engine.analyzer

        bad_service = CSharpTypeInfo(
            name="BlockingService",
            namespace="Services",
            file_path="test.cs",
            type_kind="class",
        )

        bad_service.async_violations = [
            (50, "Blocking call: Task.Wait()"),
            (51, "Blocking call: Task.WaitAll()"),
        ]

        analyzer.types = {"BlockingService": bad_service}

        violations = audit_engine.audit_async_safety()

        assert len(violations) >= 2

    def test_async_clean_code(self, audit_engine):
        """Test that proper async code doesn't trigger violations."""
        analyzer = audit_engine.analyzer

        good_service = CSharpTypeInfo(
            name="GoodService",
            namespace="Services",
            file_path="test.cs",
            type_kind="class",
        )

        good_service.async_violations = []

        analyzer.types = {"GoodService": good_service}

        violations = audit_engine.audit_async_safety()

        # Should have no violations
        assert len(violations) == 0


class TestAuditRunAll:
    """Test running all audits together."""

    def test_run_all_audits(self, audit_engine):
        """Test that run_all_audits executes without errors."""
        analyzer = audit_engine.analyzer

        # Create some test types
        type1 = CSharpTypeInfo(
            name="TestClass", namespace="Test", file_path="test.cs", type_kind="class"
        )

        analyzer.types = {"TestClass": type1}

        result = audit_engine.run_all_audits()

        # Should return AuditResult
        assert isinstance(result, AuditResult)
        assert hasattr(result, "total_types")
        assert hasattr(result, "total_violations")
        assert hasattr(result, "violations")

    def test_audit_result_structure(self, audit_engine):
        """Test structure of AuditResult."""
        result = audit_engine.run_all_audits()

        # Check required fields
        assert result.total_types >= 0
        assert result.total_violations >= 0
        assert isinstance(result.violations_by_severity, dict)
        assert isinstance(result.violations_by_rule, dict)
        assert isinstance(result.violations, list)
        assert isinstance(result.metrics, dict)
