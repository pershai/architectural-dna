"""Unit tests for C# Audit Reporter."""

import pytest

from csharp_audit_engine import AuditResult
from csharp_audit_reporter import CSharpAuditReporter
from csharp_semantic_analyzer import ArchitecturalViolation, CSharpTypeInfo


@pytest.fixture
def sample_audit_result():
    """Create a sample audit result for testing."""
    violations = [
        ArchitecturalViolation(
            rule_id="DESIGN_001",
            severity="warning",
            message="Class has low cohesion (LCOM=0.85)",
            type_name="UserService",
            file_path="Services/UserService.cs",
            line_number=42,
            suggestion="Consider splitting into smaller, focused classes",
        ),
        ArchitecturalViolation(
            rule_id="ARCH_001",
            severity="error",
            message="Cyclic dependency detected: Services.A -> B -> A",
            type_name="ServiceA",
            file_path="Services/ServiceA.cs",
            suggestion="Refactor to break the cycle using interfaces",
        ),
        ArchitecturalViolation(
            rule_id="ASYNC_001",
            severity="warning",
            message="Blocking call: .Result on async method",
            type_name="AsyncService",
            file_path="Services/AsyncService.cs",
            line_number=100,
            suggestion="Use await instead of .Result",
        ),
    ]

    return AuditResult(
        total_types=15,
        total_violations=3,
        violations_by_severity={"error": 1, "warning": 2, "info": 0},
        violations_by_rule={"DESIGN_001": 1, "ARCH_001": 1, "ASYNC_001": 1},
        violations=violations,
        metrics={
            "total_types": 15,
            "namespaces_analyzed": 5,
            "avg_lcom": 0.45,
            "avg_dependencies": 3.2,
            "types_by_role": {
                "controller": 3,
                "service": 5,
                "repository": 3,
                "other": 4,
            },
        },
    )


@pytest.fixture
def sample_types():
    """Create sample type information."""
    return {
        "UserService": CSharpTypeInfo(
            name="UserService",
            namespace="Services",
            file_path="Services/UserService.cs",
            type_kind="class",
            lcom_score=0.85,
            lines_of_code=350,
        ),
        "User": CSharpTypeInfo(
            name="User",
            namespace="Models",
            file_path="Models/User.cs",
            type_kind="class",
            lcom_score=0.2,
            lines_of_code=50,
        ),
    }


class TestJSONReportGeneration:
    """Test JSON report generation."""

    def test_json_report_creation(self, tmp_path, sample_audit_result):
        """Test creation of JSON report file."""
        output_path = tmp_path / "audit.json"

        report = CSharpAuditReporter.generate_json_report(
            sample_audit_result, str(output_path)
        )

        # File should be created
        assert output_path.exists()

        # Should be valid JSON
        assert isinstance(report, dict)
        assert "metadata" in report
        assert "summary" in report
        assert "violations" in report

    def test_json_report_structure(self, tmp_path, sample_audit_result):
        """Test structure of JSON report."""
        output_path = tmp_path / "audit.json"

        report = CSharpAuditReporter.generate_json_report(
            sample_audit_result, str(output_path)
        )

        # Check metadata
        assert "generated_at" in report["metadata"]
        assert "tool" in report["metadata"]
        assert "version" in report["metadata"]

        # Check summary
        assert report["summary"]["total_types_analyzed"] == 15
        assert report["summary"]["total_violations"] == 3

        # Check violations
        assert len(report["violations"]) == 3
        assert all("rule_id" in v for v in report["violations"])
        assert all("severity" in v for v in report["violations"])

    def test_json_report_content(self, tmp_path, sample_audit_result):
        """Test content of JSON violations."""
        output_path = tmp_path / "audit.json"

        report = CSharpAuditReporter.generate_json_report(
            sample_audit_result, str(output_path)
        )

        violations = report["violations"]

        # Check first violation details
        assert violations[0]["rule_id"] == "DESIGN_001"
        assert violations[0]["severity"] == "warning"
        assert violations[0]["type"] == "UserService"


class TestMarkdownReportGeneration:
    """Test Markdown report generation."""

    def test_markdown_report_creation(
        self, tmp_path, sample_audit_result, sample_types
    ):
        """Test creation of Markdown report file."""
        output_path = tmp_path / "audit.md"

        report = CSharpAuditReporter.generate_markdown_report(
            sample_audit_result, sample_types, str(output_path)
        )

        # File should be created
        assert output_path.exists()

        # Should return markdown string
        assert isinstance(report, str)
        assert len(report) > 0

    def test_markdown_report_structure(
        self, tmp_path, sample_audit_result, sample_types
    ):
        """Test structure of Markdown report."""
        output_path = tmp_path / "audit.md"

        report = CSharpAuditReporter.generate_markdown_report(
            sample_audit_result, sample_types, str(output_path)
        )

        # Check for key sections
        assert "# C# Architectural DNA Audit Report" in report
        assert "## Executive Summary" in report
        assert "## Violations by Rule" in report
        assert "## Top Architectural Issues" in report
        assert "## Recommendations" in report

    def test_markdown_contains_metrics(
        self, tmp_path, sample_audit_result, sample_types
    ):
        """Test that Markdown report contains metrics."""
        output_path = tmp_path / "audit.md"

        report = CSharpAuditReporter.generate_markdown_report(
            sample_audit_result, sample_types, str(output_path)
        )

        # Check for metrics section
        assert "## Architectural Metrics" in report
        assert "Total Types" in report
        assert "Average LCOM" in report
        assert "Average Dependencies" in report

    def test_markdown_contains_violations(
        self, tmp_path, sample_audit_result, sample_types
    ):
        """Test that Markdown report contains violations."""
        output_path = tmp_path / "audit.md"

        report = CSharpAuditReporter.generate_markdown_report(
            sample_audit_result, sample_types, str(output_path)
        )

        # Check for specific violations
        assert "DESIGN_001" in report
        assert "UserService" in report
        assert "low cohesion" in report.lower()


class TestSARIFReportGeneration:
    """Test SARIF report generation."""

    def test_sarif_report_creation(self, tmp_path, sample_audit_result):
        """Test creation of SARIF report file."""
        output_path = tmp_path / "audit.sarif"

        report = CSharpAuditReporter.generate_sarif_report(
            sample_audit_result, str(output_path)
        )

        # File should be created
        assert output_path.exists()

        # Should be valid SARIF
        assert isinstance(report, dict)
        assert "$schema" in report
        assert "version" in report
        assert "runs" in report

    def test_sarif_report_structure(self, tmp_path, sample_audit_result):
        """Test structure of SARIF report."""
        output_path = tmp_path / "audit.sarif"

        report = CSharpAuditReporter.generate_sarif_report(
            sample_audit_result, str(output_path)
        )

        # Check SARIF structure
        assert report["version"] == "2.1.0"
        assert len(report["runs"]) > 0

        run = report["runs"][0]
        assert "tool" in run
        assert "results" in run

        # Check tool info
        tool = run["tool"]["driver"]
        assert tool["name"] == "Architectural DNA C# Audit"
        assert len(tool["rules"]) > 0

    def test_sarif_report_rules(self, tmp_path, sample_audit_result):
        """Test SARIF report rule definitions."""
        output_path = tmp_path / "audit.sarif"

        report = CSharpAuditReporter.generate_sarif_report(
            sample_audit_result, str(output_path)
        )

        rules = report["runs"][0]["tool"]["driver"]["rules"]

        # Should have rule for each violation type
        rule_ids = {rule["id"] for rule in rules}
        assert "DESIGN_001" in rule_ids
        assert "ARCH_001" in rule_ids

    def test_sarif_report_results(self, tmp_path, sample_audit_result):
        """Test SARIF report results."""
        output_path = tmp_path / "audit.sarif"

        report = CSharpAuditReporter.generate_sarif_report(
            sample_audit_result, str(output_path)
        )

        results = report["runs"][0]["results"]

        # Should have results for each violation
        assert len(results) == 3

        # Check result structure
        for result in results:
            assert "ruleId" in result
            assert "level" in result
            assert "message" in result
            assert "locations" in result


class TestConsoleSummary:
    """Test console summary output."""

    def test_console_summary_output(self, capsys, sample_audit_result):
        """Test console summary output."""
        CSharpAuditReporter.print_console_summary(sample_audit_result)

        captured = capsys.readouterr()
        output = captured.out

        # Check for key information in output
        assert "ARCHITECTURAL DNA AUDIT REPORT" in output
        assert "Types Analyzed" in output or "types" in output.lower()
        assert "Violations" in output or "violations" in output.lower()

    def test_console_summary_metrics(self, capsys, sample_audit_result):
        """Test that console summary includes metrics."""
        CSharpAuditReporter.print_console_summary(sample_audit_result)

        captured = capsys.readouterr()
        output = captured.out

        # Check for metrics
        assert "Metrics:" in output or "LCOM" in output
        assert "Dependencies" in output or "dependencies" in output


class TestEmptyViolationsReport:
    """Test report generation with no violations."""

    def test_empty_violations_json(self, tmp_path):
        """Test JSON report with no violations."""
        empty_result = AuditResult(
            total_types=5,
            total_violations=0,
            violations_by_severity={},
            violations_by_rule={},
            violations=[],
            metrics={},
        )

        output_path = tmp_path / "empty.json"
        report = CSharpAuditReporter.generate_json_report(
            empty_result, str(output_path)
        )

        assert report["summary"]["total_violations"] == 0
        assert len(report["violations"]) == 0

    def test_empty_violations_markdown(self, tmp_path):
        """Test Markdown report with no violations."""
        empty_result = AuditResult(
            total_types=5,
            total_violations=0,
            violations_by_severity={},
            violations_by_rule={},
            violations=[],
            metrics={},
        )

        output_path = tmp_path / "empty.md"
        report = CSharpAuditReporter.generate_markdown_report(
            empty_result, {}, str(output_path)
        )

        # Should still generate valid report
        assert "# C# Architectural DNA Audit Report" in report
