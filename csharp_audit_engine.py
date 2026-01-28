"""C# Architectural Audit Engine with Rule-Based Validation.

Implements advanced architectural rules for C# projects including:
- MediatR pattern compliance
- Layer dependency rules
- SQL access restrictions
- Cyclic dependency detection
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from csharp_semantic_analyzer import (
    ArchitecturalRole,
    ArchitecturalViolation,
    CSharpSemanticAnalyzer,
)

logger = logging.getLogger(__name__)


@dataclass
class AuditRule:
    """Represents an architectural audit rule."""

    rule_id: str
    name: str
    description: str
    severity: str  # "error", "warning", "info"
    enabled: bool = True
    configuration: dict = field(default_factory=dict)


@dataclass
class AuditResult:
    """Result of an architectural audit."""

    total_types: int
    total_violations: int
    violations_by_severity: dict[str, int]
    violations_by_rule: dict[str, int]
    violations: list[ArchitecturalViolation]
    metrics: dict[str, Any] = field(default_factory=dict)


class CSharpAuditEngine:
    """Advanced architectural audit engine for C# codebases."""

    def __init__(
        self, analyzer: CSharpSemanticAnalyzer, config_path: str = "config.yaml"
    ):
        if not isinstance(analyzer, CSharpSemanticAnalyzer):
            raise TypeError(
                f"Expected CSharpSemanticAnalyzer instance, got {type(analyzer)}"
            )

        self.analyzer = analyzer
        self.rules: dict[str, AuditRule] = {}
        self.violations: list[ArchitecturalViolation] = []

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize default rules
        self._initialize_rules()

    def _load_config(self, config_path: str) -> dict:
        """Load C# audit configuration from YAML file."""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                    return config.get("csharp_audit", {})
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")

        # Return defaults if config not found
        return {
            "metrics": {
                "lcom_threshold": 0.8,
                "loc_threshold": 500,
                "cyclomatic_complexity_limit": 15,
            },
            "dependencies": {"max_per_class": 7, "max_per_namespace": 50},
            "patterns": {
                "include_partial_classes": True,
                "extract_di_registrations": True,
                "detect_async_patterns": True,
            },
        }

    def _initialize_rules(self):
        """Initialize default architectural rules."""

        # Rule 1: MediatR Pattern Compliance
        self.rules["MEDIATR_001"] = AuditRule(
            rule_id="MEDIATR_001",
            name="MediatR Handler Domain Access",
            description="Only Handlers are allowed to depend on the Domain layer",
            severity="error",
            configuration={
                "allowed_roles": ["handler"],
                "forbidden_dependencies": ["Domain"],
            },
        )

        self.rules["MEDIATR_002"] = AuditRule(
            rule_id="MEDIATR_002",
            name="Controller MediatR Usage",
            description="Controllers must only depend on IMediator, not handlers directly",
            severity="error",
            configuration={
                "controller_allowed_dependencies": ["IMediator"],
                "forbidden_patterns": ["Handler"],
            },
        )

        # Rule 2: No Direct SQL Access
        self.rules["DATA_001"] = AuditRule(
            rule_id="DATA_001",
            name="No Direct SQL in Application/Web Layers",
            description="Application and Web layers must not reference SQL libraries directly",
            severity="error",
            configuration={
                "forbidden_layers": ["Application", "Web", "API", "Controllers"],
                "forbidden_namespaces": [
                    "Microsoft.Data.SqlClient",
                    "Dapper",
                    "System.Data.SqlClient",
                ],
            },
        )

        # Rule 3: Cyclic Dependencies
        self.rules["ARCH_001"] = AuditRule(
            rule_id="ARCH_001",
            name="No Cyclic Dependencies",
            description="Namespaces must not have circular references",
            severity="error",
        )

        # Rule 4: God Object Detection
        self.rules["DESIGN_001"] = AuditRule(
            rule_id="DESIGN_001",
            name="No God Objects",
            description="Classes should maintain reasonable cohesion (LCOM < 0.8)",
            severity="warning",
            configuration={"lcom_threshold": 0.8, "loc_threshold": 500},
        )

        # Rule 5: Async Safety
        self.rules["ASYNC_001"] = AuditRule(
            rule_id="ASYNC_001",
            name="No Async-over-Sync",
            description="Avoid blocking async code with .Result or .Wait()",
            severity="warning",
        )

        # Rule 6: Dependency Direction
        self.rules["ARCH_002"] = AuditRule(
            rule_id="ARCH_002",
            name="Dependency Flow Direction",
            description="Dependencies must flow inward: Web -> Application -> Domain",
            severity="error",
            configuration={
                "layer_hierarchy": ["Domain", "Application", "Infrastructure", "Web"]
            },
        )

        # Rule 7: Repository Pattern
        self.rules["DATA_002"] = AuditRule(
            rule_id="DATA_002",
            name="Repository Interface Usage",
            description="Repositories must implement an interface",
            severity="warning",
        )

        # Rule 8: Attribute Validation
        self.rules["ATTR_001"] = AuditRule(
            rule_id="ATTR_001",
            name="Controller Attribute Validation",
            description="Controllers must have [ApiController] and [Route] attributes",
            severity="warning",
        )

    def audit_mediatr_pattern(self) -> list[ArchitecturalViolation]:
        """Audit MediatR pattern compliance."""
        violations = []
        rule1 = self.rules["MEDIATR_001"]
        rule2 = self.rules["MEDIATR_002"]

        for type_name, type_info in self.analyzer.types.items():
            if type_info.architectural_role == ArchitecturalRole.HANDLER:
                for dep in type_info.dependencies:
                    dep_type = self.analyzer.types.get(dep)
                    if (
                        dep_type
                        and dep_type.namespace
                        and not any(
                            layer in dep_type.namespace
                            for layer in ["Domain", "Handler", "Common"]
                        )
                    ):
                        violations.append(
                            ArchitecturalViolation(
                                rule_id=rule1.rule_id,
                                severity=rule1.severity,
                                message=f"Handler '{type_name}' depends on '{dep}' from {dep_type.namespace} (should only depend on Domain)",
                                type_name=type_name,
                                file_path=type_info.file_path,
                                suggestion="Handlers should only reference Domain entities and value objects",
                            )
                        )

            if type_info.architectural_role == ArchitecturalRole.CONTROLLER:
                for dep in type_info.dependencies:
                    if "Handler" in dep and dep != "IMediator":
                        violations.append(
                            ArchitecturalViolation(
                                rule_id=rule2.rule_id,
                                severity=rule2.severity,
                                message=f"Controller '{type_name}' directly depends on '{dep}' (should use IMediator)",
                                type_name=type_name,
                                file_path=type_info.file_path,
                                suggestion="Inject IMediator and send commands/queries instead of calling handlers directly",
                            )
                        )

        return violations

    def audit_sql_access(self) -> list[ArchitecturalViolation]:
        """Audit direct SQL access in non-data layers."""
        violations = []
        rule = self.rules["DATA_001"]

        for type_name, type_info in self.analyzer.types.items():
            in_forbidden_layer = any(
                layer in type_info.namespace or layer in type_info.file_path
                for layer in rule.configuration["forbidden_layers"]
            )

            if in_forbidden_layer:
                for dep in type_info.dependencies:
                    if dep.startswith("__SQL__"):
                        violations.append(
                            ArchitecturalViolation(
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                message=f"Type '{type_name}' in {type_info.namespace} directly references {dep.replace('__SQL__', '')}",
                                type_name=type_name,
                                file_path=type_info.file_path,
                                suggestion="Move SQL access to Infrastructure/Repository layer and use interfaces",
                            )
                        )

        return violations

    def detect_cyclic_dependencies(self) -> list[ArchitecturalViolation]:
        """Detect cyclic dependencies between namespaces and self-references.

        Thread-safe implementation that returns cycle instead of mutating shared state.
        """
        violations = []
        rule = self.rules["ARCH_001"]

        # First, detect type-level self-references
        for type_name, type_info in self.analyzer.types.items():
            if type_name in type_info.dependencies:
                violations.append(
                    ArchitecturalViolation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=f"Cyclic dependency detected: {type_name} -> {type_name}",
                        type_name=type_name,
                        file_path=type_info.file_path,
                        suggestion="Refactor to break the self-reference",
                    )
                )

        namespace_deps = defaultdict(set)
        for type_info in self.analyzer.types.values():
            for dep_name in type_info.dependencies:
                dep_type = self.analyzer.types.get(dep_name)
                if dep_type and dep_type.namespace != type_info.namespace:
                    namespace_deps[type_info.namespace].add(dep_type.namespace)

        def find_cycle(node, visited, rec_stack, path) -> list[str] | None:
            """Find cycle starting from node. Returns cycle path or None."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in namespace_deps.get(node, []):
                if neighbor not in visited:
                    cycle = find_cycle(neighbor, visited, rec_stack, path)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle, return it
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return None

        visited: set[str] = set()
        for namespace in namespace_deps:
            if namespace not in visited:
                cycle = find_cycle(namespace, visited, set(), [])
                if cycle:
                    violations.append(
                        ArchitecturalViolation(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=f"Cyclic dependency detected: {' -> '.join(cycle)}",
                            type_name=cycle[0],
                            file_path="Multiple files",
                            suggestion="Refactor to break the cycle using interfaces or moving shared code",
                        )
                    )

        return violations

    def audit_god_objects(self) -> list[ArchitecturalViolation]:
        """Detect God Objects using LCOM and LOC metrics."""
        violations = []
        rule = self.rules["DESIGN_001"]

        # Load thresholds from configuration
        metrics_config = self.config.get("metrics", {})
        dependencies_config = self.config.get("dependencies", {})

        lcom_threshold = metrics_config.get("lcom_threshold", 0.8)
        loc_threshold = metrics_config.get("loc_threshold", 500)
        max_dependencies = dependencies_config.get("max_per_class", 7)

        for type_name, type_info in self.analyzer.types.items():
            reasons = []

            if type_info.lcom_score > lcom_threshold:
                reasons.append(f"Low cohesion (LCOM={type_info.lcom_score:.2f})")

            if type_info.lines_of_code > loc_threshold:
                reasons.append(f"Too many lines ({type_info.lines_of_code} LOC)")

            if len(type_info.dependencies) > max_dependencies:
                reasons.append(
                    f"Too many dependencies ({len(type_info.dependencies)} > {max_dependencies})"
                )

            if reasons:
                violations.append(
                    ArchitecturalViolation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=f"'{type_name}' is a potential God Object: {', '.join(reasons)}",
                        type_name=type_name,
                        file_path=type_info.file_path,
                        suggestion="Consider splitting into smaller, focused classes with single responsibilities",
                    )
                )

        return violations

    def audit_async_safety(self) -> list[ArchitecturalViolation]:
        """Audit async/await usage for anti-patterns."""
        violations = []
        rule = self.rules["ASYNC_001"]

        for type_name, type_info in self.analyzer.types.items():
            if hasattr(type_info, "async_violations") and type_info.async_violations:
                for line_num, message in type_info.async_violations:
                    violations.append(
                        ArchitecturalViolation(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=message,
                            type_name=type_name,
                            file_path=type_info.file_path,
                            line_number=line_num,
                            suggestion="Use proper async/await instead of .Result, .Wait(), or .GetAwaiter().GetResult()",
                        )
                    )

        return violations

    def audit_dependency_direction(self) -> list[ArchitecturalViolation]:
        """Audit that dependencies flow in the correct direction."""
        violations = []
        rule = self.rules["ARCH_002"]

        layer_hierarchy = rule.configuration["layer_hierarchy"]
        layer_levels = {layer: i for i, layer in enumerate(layer_hierarchy)}

        for type_name, type_info in self.analyzer.types.items():
            # Determine source layer
            source_layer = None
            for layer in layer_hierarchy:
                if layer in type_info.namespace:
                    source_layer = layer
                    break

            if not source_layer:
                continue

            source_level = layer_levels[source_layer]

            # Check each dependency
            for dep_name in type_info.dependencies:
                dep_type = self.analyzer.types.get(dep_name)
                if not dep_type:
                    continue

                # Determine dependency layer
                dep_layer = None
                for layer in layer_hierarchy:
                    if layer in dep_type.namespace:
                        dep_layer = layer
                        break

                if not dep_layer:
                    continue

                dep_level = layer_levels[dep_layer]

                # Check if dependency flows upward (bad)
                if dep_level > source_level:
                    violations.append(
                        ArchitecturalViolation(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=f"'{type_name}' in {source_layer} depends on '{dep_name}' in {dep_layer} (wrong direction)",
                            type_name=type_name,
                            file_path=type_info.file_path,
                            suggestion=f"Dependencies should flow: {' -> '.join(layer_hierarchy)}. Consider using interfaces or moving code.",
                        )
                    )

        return violations

    def audit_repository_interfaces(self) -> list[ArchitecturalViolation]:
        """Audit that repositories implement interfaces."""
        violations = []
        rule = self.rules["DATA_002"]

        for type_name, type_info in self.analyzer.types.items():
            if type_info.architectural_role == ArchitecturalRole.REPOSITORY:
                # Check if there's a corresponding interface
                interface_name = f"I{type_name}"

                if interface_name not in self.analyzer.types:
                    violations.append(
                        ArchitecturalViolation(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=f"Repository '{type_name}' does not have a corresponding interface '{interface_name}'",
                            type_name=type_name,
                            file_path=type_info.file_path,
                            suggestion=f"Create interface '{interface_name}' and inject via DI",
                        )
                    )

        return violations

    def audit_controller_attributes(self) -> list[ArchitecturalViolation]:
        """Audit that controllers have required attributes."""
        violations = []
        rule = self.rules["ATTR_001"]

        required_attributes = ["ApiController", "Route"]

        for type_name, type_info in self.analyzer.types.items():
            if type_info.architectural_role == ArchitecturalRole.CONTROLLER:
                attr_names = [attr.name for attr in type_info.attributes]

                for required in required_attributes:
                    if not any(required in attr for attr in attr_names):
                        violations.append(
                            ArchitecturalViolation(
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                message=f"Controller '{type_name}' is missing [{required}] attribute",
                                type_name=type_name,
                                file_path=type_info.file_path,
                                suggestion=f"Add [{required}] attribute to the controller",
                            )
                        )

        return violations

    def run_all_audits(self) -> AuditResult:
        """Run all enabled audit rules."""
        all_violations = []

        audit_methods = [
            self.audit_mediatr_pattern,
            self.audit_sql_access,
            self.detect_cyclic_dependencies,
            self.audit_god_objects,
            self.audit_async_safety,
            self.audit_dependency_direction,
            self.audit_repository_interfaces,
            self.audit_controller_attributes,
        ]

        for audit_method in audit_methods:
            try:
                all_violations.extend(audit_method())
            except Exception as e:
                logger.error(f"Error in {audit_method.__name__}: {e}")

        violations_by_severity: defaultdict[str, int] = defaultdict(int)
        violations_by_rule: defaultdict[str, int] = defaultdict(int)

        for violation in all_violations:
            violations_by_severity[violation.severity] += 1
            violations_by_rule[violation.rule_id] += 1

        types_by_count = len(self.analyzer.types) if self.analyzer.types else 0
        types_by_role_dict: defaultdict[str, int] = defaultdict(int)
        metrics: dict[str, int | float | defaultdict[str, int]] = {
            "total_types": types_by_count,
            "avg_lcom": sum(t.lcom_score for t in self.analyzer.types.values())
            / types_by_count
            if types_by_count
            else 0,
            "avg_dependencies": sum(
                len(t.dependencies) for t in self.analyzer.types.values()
            )
            / types_by_count
            if types_by_count
            else 0,
            "types_by_role": types_by_role_dict,
            "namespaces_analyzed": len(
                {t.namespace for t in self.analyzer.types.values()}
            ),
        }

        for type_info in self.analyzer.types.values():
            types_by_role_dict[type_info.architectural_role.value] += 1

        return AuditResult(
            total_types=len(self.analyzer.types),
            total_violations=len(all_violations),
            violations_by_severity=dict(violations_by_severity),
            violations_by_rule=dict(violations_by_rule),
            violations=all_violations,
            metrics=metrics,
        )
