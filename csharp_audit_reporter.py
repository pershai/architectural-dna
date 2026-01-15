"""Audit Report Generation for C# Architectural Analysis.

Generates comprehensive audit reports in multiple formats:
- JSON (for tooling integration)
- Markdown (for documentation)
- HTML (for visual dashboards)
"""

import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from csharp_audit_engine import AuditResult, ArchitecturalViolation
from csharp_semantic_analyzer import CSharpTypeInfo, ArchitecturalRole


class CSharpAuditReporter:
    """Generate architectural audit reports in various formats."""

    @staticmethod
    def generate_json_report(result: AuditResult, output_path: str):
        """Generate JSON format audit report."""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "tool": "Architectural DNA - C# Audit Engine",
                "version": "1.0.0"
            },
            "summary": {
                "total_types_analyzed": result.total_types,
                "total_violations": result.total_violations,
                "violations_by_severity": result.violations_by_severity,
                "violations_by_rule": result.violations_by_rule,
            },
            "metrics": result.metrics,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "severity": v.severity,
                    "type": v.type_name,
                    "file": v.file_path,
                    "line": v.line_number,
                    "message": v.message,
                    "suggestion": v.suggestion
                }
                for v in result.violations
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        return report

    @staticmethod
    def generate_markdown_report(result: AuditResult, types: Dict[str, CSharpTypeInfo], output_path: str):
        """Generate Markdown format audit report."""
        md = []

        # Header
        md.append("# C# Architectural DNA Audit Report")
        md.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"\n**Total Types Analyzed:** {result.total_types}")
        md.append(f"\n**Total Violations:** {result.total_violations}")

        # Executive Summary
        md.append("\n## Executive Summary")
        md.append("\n### Violations by Severity")
        for severity, count in sorted(result.violations_by_severity.items()):
            emoji = {"error": "🔴", "warning": "⚠️", "info": "ℹ️"}.get(severity, "📌")
            md.append(f"- {emoji} **{severity.upper()}**: {count}")

        # Metrics Dashboard
        md.append("\n## Architectural Metrics")
        md.append("\n| Metric | Value |")
        md.append("|--------|-------|")
        md.append(f"| Total Types | {result.metrics.get('total_types', 0)} |")
        md.append(f"| Namespaces | {result.metrics.get('namespaces_analyzed', 0)} |")
        md.append(f"| Average LCOM | {result.metrics.get('avg_lcom', 0):.3f} |")
        md.append(f"| Average Dependencies | {result.metrics.get('avg_dependencies', 0):.1f} |")

        # Types by Role
        md.append("\n### Types by Architectural Role")
        md.append("\n| Role | Count |")
        md.append("|------|-------|")
        types_by_role = result.metrics.get('types_by_role', {})
        for role, count in sorted(types_by_role.items(), key=lambda x: -x[1]):
            md.append(f"| {role.replace('_', ' ').title()} | {count} |")

        # Violations by Rule
        md.append("\n## Violations by Rule")
        for rule_id, count in sorted(result.violations_by_rule.items(), key=lambda x: -x[1]):
            md.append(f"\n### {rule_id} ({count} violations)")

            # Group violations by this rule
            rule_violations = [v for v in result.violations if v.rule_id == rule_id]

            for v in rule_violations[:10]:  # Limit to 10 per rule
                md.append(f"\n**{v.type_name}** ({v.severity})")
                md.append(f"- File: `{v.file_path}`")
                if v.line_number:
                    md.append(f"- Line: {v.line_number}")
                md.append(f"- Issue: {v.message}")
                if v.suggestion:
                    md.append(f"- 💡 Suggestion: {v.suggestion}")

            if len(rule_violations) > 10:
                md.append(f"\n... and {len(rule_violations) - 10} more")

        # Top Offenders
        md.append("\n## Top Architectural Issues")

        # Find types with most violations
        type_violation_count = {}
        for v in result.violations:
            type_violation_count[v.type_name] = type_violation_count.get(v.type_name, 0) + 1

        md.append("\n### Types with Most Violations")
        md.append("\n| Type | Violations |")
        md.append("|------|------------|")
        for type_name, count in sorted(type_violation_count.items(), key=lambda x: -x[1])[:10]:
            md.append(f"| {type_name} | {count} |")

        # God Objects
        god_objects = [
            t for t in types.values()
            if t.lcom_score > 0.8 or t.lines_of_code > 500
        ]
        if god_objects:
            md.append("\n### Potential God Objects")
            md.append("\n| Type | LCOM | LOC | Dependencies |")
            md.append("|------|------|-----|--------------|")
            for t in sorted(god_objects, key=lambda x: -x.lcom_score)[:10]:
                md.append(f"| {t.name} | {t.lcom_score:.3f} | {t.lines_of_code} | {len(t.dependencies)} |")

        # Instability Analysis
        md.append("\n## Namespace Stability Analysis")
        md.append("\n| Namespace | Instability | Classification |")
        md.append("|-----------|-------------|----------------|")

        # Calculate instability for each namespace
        from csharp_semantic_analyzer import CSharpSemanticAnalyzer
        analyzer = CSharpSemanticAnalyzer()
        analyzer.types = types

        namespaces = set(t.namespace for t in types.values() if t.namespace)
        for ns in sorted(namespaces):
            instability = analyzer.calculate_instability(ns)
            classification = "Stable" if instability < 0.3 else "Balanced" if instability < 0.7 else "Unstable"
            md.append(f"| {ns} | {instability:.3f} | {classification} |")

        # Recommendations
        md.append("\n## Recommendations")
        md.append("\n### High Priority")

        error_violations = [v for v in result.violations if v.severity == "error"]
        if error_violations:
            md.append(f"\n1. **Fix {len(error_violations)} Critical Errors**")
            for v in error_violations[:5]:
                md.append(f"   - {v.type_name}: {v.message}")

        md.append("\n### Medium Priority")
        warning_violations = [v for v in result.violations if v.severity == "warning"]
        if warning_violations:
            md.append(f"\n1. **Address {len(warning_violations)} Warnings**")
            md.append("   - Focus on God Objects and dependency direction issues")

        md.append("\n### Best Practices")
        md.append("- Maintain LCOM scores below 0.5 for high cohesion")
        md.append("- Keep classes under 300 lines of code")
        md.append("- Limit dependencies to 5-7 per class")
        md.append("- Follow layer dependency rules: Domain ← Application ← Infrastructure ← Web")
        md.append("- Use interfaces for all repositories and services")
        md.append("- Avoid async-over-sync patterns (.Result, .Wait)")

        # Footer
        md.append("\n---")
        md.append("\n*Generated by Architectural DNA C# Audit Engine*")

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md))

        return '\n'.join(md)

    @staticmethod
    def generate_sarif_report(result: AuditResult, output_path: str):
        """
        Generate SARIF format report for IDE integration.

        SARIF (Static Analysis Results Interchange Format) is supported by
        Visual Studio, VS Code, and GitHub Code Scanning.
        """
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Architectural DNA C# Audit",
                            "version": "1.0.0",
                            "informationUri": "https://github.com/yourusername/architectural-dna",
                            "rules": []
                        }
                    },
                    "results": []
                }
            ]
        }

        # Add rules
        rule_definitions = {}
        for v in result.violations:
            if v.rule_id not in rule_definitions:
                rule_definitions[v.rule_id] = {
                    "id": v.rule_id,
                    "name": v.rule_id,
                    "shortDescription": {
                        "text": v.message.split(':')[0] if ':' in v.message else v.message
                    },
                    "fullDescription": {
                        "text": v.message
                    },
                    "help": {
                        "text": v.suggestion or "No suggestion available"
                    },
                    "defaultConfiguration": {
                        "level": "error" if v.severity == "error" else "warning"
                    }
                }

        sarif["runs"][0]["tool"]["driver"]["rules"] = list(rule_definitions.values())

        # Add results
        for v in result.violations:
            result_entry = {
                "ruleId": v.rule_id,
                "level": "error" if v.severity == "error" else "warning",
                "message": {
                    "text": v.message
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": v.file_path
                            }
                        }
                    }
                ]
            }

            if v.line_number:
                result_entry["locations"][0]["physicalLocation"]["region"] = {
                    "startLine": v.line_number
                }

            sarif["runs"][0]["results"].append(result_entry)

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sarif, f, indent=2)

        return sarif

    @staticmethod
    def print_console_summary(result: AuditResult):
        """Print a concise summary to console."""
        print("\n" + "="*80)
        print("  C# ARCHITECTURAL DNA AUDIT REPORT")
        print("="*80)
        print(f"\n📊 Types Analyzed: {result.total_types}")
        print(f"⚠️  Total Violations: {result.total_violations}\n")

        print("Violations by Severity:")
        for severity, count in sorted(result.violations_by_severity.items()):
            emoji = {"error": "🔴", "warning": "⚠️", "info": "ℹ️"}.get(severity, "📌")
            print(f"  {emoji} {severity.upper():8s}: {count:3d}")

        print("\nTop 5 Rule Violations:")
        for rule_id, count in sorted(result.violations_by_rule.items(), key=lambda x: -x[1])[:5]:
            print(f"  • {rule_id}: {count}")

        print("\nMetrics:")
        print(f"  • Average LCOM: {result.metrics.get('avg_lcom', 0):.3f}")
        print(f"  • Average Dependencies: {result.metrics.get('avg_dependencies', 0):.1f}")
        print(f"  • Namespaces: {result.metrics.get('namespaces_analyzed', 0)}")

        print("\n" + "="*80 + "\n")
