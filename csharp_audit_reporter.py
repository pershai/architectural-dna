"""Audit Report Generation for C# Architectural Analysis.

Generates comprehensive audit reports in multiple formats:
- JSON (for tooling integration)
- Markdown (for documentation)
- HTML (for visual dashboards)
"""

import json
import logging
from datetime import datetime
from typing import Any

from csharp_audit_engine import AuditResult
from csharp_semantic_analyzer import CSharpTypeInfo

logger = logging.getLogger(__name__)


class CSharpAuditReporter:
    """Generate architectural audit reports in various formats."""

    @staticmethod
    def generate_json_report(
        result: AuditResult,
        output_path: str,
        types: dict[str, CSharpTypeInfo] | None = None,
    ):
        """Generate JSON format audit report."""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "tool": "Architectural DNA - C# Audit Engine",
                "version": "1.0.0",
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
                    "suggestion": v.suggestion,
                }
                for v in result.violations
            ],
        }

        if types:
            patterns_section = {}
            for type_name, type_info in types.items():
                try:
                    if not hasattr(type_info, "design_patterns") or not type_info.design_patterns:
                        continue

                    # Validate required attributes exist
                    required_attrs = ["file_path", "namespace"]
                    for attr in required_attrs:
                        if not hasattr(type_info, attr):
                            logger.warning(f"Type '{type_name}' missing required attribute '{attr}'")
                            continue

                    patterns_section[type_name] = {
                        "file": type_info.file_path,
                        "namespace": type_info.namespace,
                        "patterns": type_info.design_patterns,
                    }
                except AttributeError as e:
                    logger.warning(f"Invalid type_info structure for '{type_name}': {e}")
                    continue

            if patterns_section:
                report["design_patterns"] = patterns_section

        try:
            from pathlib import Path
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

            logger.info(f"JSON report written to: {output_path}")
        except PermissionError as e:
            logger.error(f"Permission denied writing to {output_path}: {e}")
            raise ValueError(f"Cannot write report: permission denied at {output_path}") from e
        except (FileNotFoundError, OSError) as e:
            logger.error(f"File system error writing report to {output_path}: {e}")
            raise ValueError(f"Cannot write report: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error generating JSON report: {e}", exc_info=True)
            raise

        return report

    @staticmethod
    def generate_markdown_report(
        result: AuditResult,
        types: dict[str, CSharpTypeInfo],
        output_path: str,
        config: dict | None = None,
    ):
        """Generate Markdown format audit report."""
        # Load thresholds from configuration
        if config is None:
            config = {}
        metrics_config = config.get("metrics", {})
        lcom_threshold = metrics_config.get("lcom_threshold", 0.8)
        loc_threshold = metrics_config.get("loc_threshold", 500)

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
            severity_marker = {
                "error": "ERROR",
                "warning": "WARNING",
                "info": "INFO",
            }.get(severity, "OTHER")
            md.append(f"- **{severity_marker}**: {count}")

        # Metrics Dashboard
        md.append("\n## Architectural Metrics")
        md.append("\n| Metric | Value |")
        md.append("|--------|-------|")
        md.append(f"| Total Types | {result.metrics.get('total_types', 0)} |")
        md.append(f"| Namespaces | {result.metrics.get('namespaces_analyzed', 0)} |")
        md.append(f"| Average LCOM | {result.metrics.get('avg_lcom', 0):.3f} |")
        md.append(
            f"| Average Dependencies | {result.metrics.get('avg_dependencies', 0):.1f} |"
        )

        md.append("\n### Types by Architectural Role")
        md.append("\n| Role | Count |")
        md.append("|------|-------|")
        types_by_role = result.metrics.get("types_by_role", {})
        for role, count in sorted(types_by_role.items(), key=lambda x: -x[1]):
            md.append(f"| {role.replace('_', ' ').title()} | {count} |")

        md.append("\n## Violations by Rule")
        for rule_id, count in sorted(
            result.violations_by_rule.items(), key=lambda x: -x[1]
        ):
            md.append(f"\n### {rule_id} ({count} violations)")
            rule_violations = [v for v in result.violations if v.rule_id == rule_id]

            for v in rule_violations[:10]:
                md.append(f"\n**{v.type_name}** ({v.severity})")
                md.append(f"- File: `{v.file_path}`")
                if v.line_number:
                    md.append(f"- Line: {v.line_number}")
                md.append(f"- Issue: {v.message}")
                if v.suggestion:
                    md.append(f"- Suggestion: {v.suggestion}")

            if len(rule_violations) > 10:
                md.append(f"\n... and {len(rule_violations) - 10} more")

        md.append("\n## Top Architectural Issues")
        type_violation_count: dict[str, int] = {}
        for v in result.violations:
            type_violation_count[v.type_name] = (
                type_violation_count.get(v.type_name, 0) + 1
            )

        md.append("\n### Types with Most Violations")
        md.append("\n| Type | Violations |")
        md.append("|------|------------|")
        for type_name, count in sorted(
            type_violation_count.items(), key=lambda x: -x[1]
        )[:10]:
            md.append(f"| {type_name} | {count} |")

        god_objects = [
            t
            for t in types.values()
            if t.lcom_score > lcom_threshold or t.lines_of_code > loc_threshold
        ]
        if god_objects:
            md.append("\n### Potential God Objects")
            md.append("\n| Type | LCOM | LOC | Dependencies |")
            md.append("|------|------|-----|--------------|")
            for t in sorted(god_objects, key=lambda x: -x.lcom_score)[:10]:
                md.append(
                    f"| {t.name} | {t.lcom_score:.3f} | {t.lines_of_code} | {len(t.dependencies)} |"
                )

        types_with_patterns = [
            t
            for t in types.values()
            if hasattr(t, "design_patterns") and t.design_patterns
        ]
        if types_with_patterns:
            md.append("\n## Detected Design Patterns")
            md.append("\nThe following design patterns were detected in your codebase:")

            for type_info in sorted(types_with_patterns, key=lambda x: x.name):
                md.append(f"\n### {type_info.name} ({type_info.namespace})")
                md.append(f"- **File:** `{type_info.file_path}`")
                md.append(f"- **Type Kind:** {type_info.type_kind}")

                if type_info.design_patterns:
                    md.append("\n#### Patterns Detected:")
                    for pattern in sorted(
                        type_info.design_patterns, key=lambda x: -x["confidence"]
                    ):
                        pattern_name = pattern["pattern"].replace("_", " ").title()
                        confidence_pct = int(pattern["confidence"] * 100)
                        md.append(f"\n- **{pattern_name}** [{confidence_pct}%]")
                        md.append(f"  - {pattern['description']}")
                        if pattern["indicators"]:
                            md.append("  - Indicators:")
                            for indicator in pattern["indicators"]:
                                md.append(f"    - {indicator}")

        md.append("\n## Namespace Stability Analysis")
        md.append("\n| Namespace | Instability | Classification |")
        md.append("|-----------|-------------|----------------|")

        from csharp_semantic_analyzer import CSharpSemanticAnalyzer

        analyzer = CSharpSemanticAnalyzer()
        analyzer.types = types

        namespaces = {t.namespace for t in types.values() if t.namespace}
        for ns in sorted(namespaces):
            instability = analyzer.calculate_instability(ns)
            if instability < 0.3:
                classification = "Stable"
            elif instability < 0.7:
                classification = "Balanced"
            else:
                classification = "Unstable"
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
        md.append(
            "- Follow layer dependency rules: Domain ← Application ← Infrastructure ← Web"
        )
        md.append("- Use interfaces for all repositories and services")
        md.append("- Avoid async-over-sync patterns (.Result, .Wait)")

        # Footer
        md.append("\n---")
        md.append("\n*Generated by Architectural DNA C# Audit Engine*")

        # Write to file
        try:
            from pathlib import Path
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md))

            logger.info(f"Markdown report written to: {output_path}")
        except PermissionError as e:
            logger.error(f"Permission denied writing to {output_path}: {e}")
            raise ValueError(f"Cannot write report: permission denied at {output_path}") from e
        except (FileNotFoundError, OSError) as e:
            logger.error(f"File system error writing report to {output_path}: {e}")
            raise ValueError(f"Cannot write report: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error generating markdown report: {e}", exc_info=True)
            raise

        return "\n".join(md)

    @staticmethod
    def generate_sarif_report(result: AuditResult, output_path: str) -> dict[str, Any]:
        """Generate SARIF format report for IDE integration."""
        sarif: dict[str, Any] = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Architectural DNA C# Audit",
                            "version": "1.0.0",
                            "informationUri": "https://github.com/yourusername/architectural-dna",
                            "rules": [],
                        }
                    },
                    "results": [],
                }
            ],
        }

        rule_definitions = {}
        for v in result.violations:
            if v.rule_id not in rule_definitions:
                short_desc = v.message.split(":")[0] if ":" in v.message else v.message
                level = "error" if v.severity == "error" else "warning"

                rule_definitions[v.rule_id] = {
                    "id": v.rule_id,
                    "name": v.rule_id,
                    "shortDescription": {"text": short_desc},
                    "fullDescription": {"text": v.message},
                    "help": {"text": v.suggestion or "No suggestion available"},
                    "defaultConfiguration": {"level": level},
                }

        sarif["runs"][0]["tool"]["driver"]["rules"] = list(rule_definitions.values())

        for v in result.violations:
            level = "error" if v.severity == "error" else "warning"
            result_entry: dict[str, Any] = {
                "ruleId": v.rule_id,
                "level": level,
                "message": {"text": v.message},
                "locations": [
                    {"physicalLocation": {"artifactLocation": {"uri": v.file_path}}}
                ],
            }

            if v.line_number:
                result_entry["locations"][0]["physicalLocation"]["region"] = {  # type: ignore[index]
                    "startLine": v.line_number
                }

            sarif["runs"][0]["results"].append(result_entry)

        # Write to file
        try:
            from pathlib import Path
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(sarif, f, indent=2)

            logger.info(f"SARIF report written to: {output_path}")
        except PermissionError as e:
            logger.error(f"Permission denied writing to {output_path}: {e}")
            raise ValueError(f"Cannot write report: permission denied at {output_path}") from e
        except (FileNotFoundError, OSError) as e:
            logger.error(f"File system error writing report to {output_path}: {e}")
            raise ValueError(f"Cannot write report: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error generating SARIF report: {e}", exc_info=True)
            raise

        return sarif

    @staticmethod
    def print_console_summary(result: AuditResult):
        """Print a concise summary to console."""
        print("\n" + "=" * 80)
        print("  C# ARCHITECTURAL DNA AUDIT REPORT")
        print("=" * 80)
        print(f"\nTypes Analyzed: {result.total_types}")
        print(f"Total Violations: {result.total_violations}\n")

        print("Violations by Severity:")
        for severity, count in sorted(result.violations_by_severity.items()):
            print(f"  {severity.upper():8s}: {count:3d}")

        print("\nTop 5 Rule Violations:")
        for rule_id, count in sorted(
            result.violations_by_rule.items(), key=lambda x: -x[1]
        )[:5]:
            print(f"  • {rule_id}: {count}")

        print("\nMetrics:")
        print(f"  • Average LCOM: {result.metrics.get('avg_lcom', 0):.3f}")
        print(
            f"  • Average Dependencies: {result.metrics.get('avg_dependencies', 0):.1f}"
        )
        print(f"  • Namespaces: {result.metrics.get('namespaces_analyzed', 0)}")

        print("\n" + "=" * 80 + "\n")
