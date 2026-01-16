"""C# Architectural Audit Engine with Rule-Based Validation.

Implements advanced architectural rules for C# projects including:
- MediatR pattern compliance
- Layer dependency rules
- SQL access restrictions
- Cyclic dependency detection
"""

import re
import logging
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from csharp_semantic_analyzer import (
    CSharpSemanticAnalyzer,
    CSharpTypeInfo,
    ArchitecturalViolation,
    ArchitecturalRole
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
    configuration: Dict = field(default_factory=dict)


@dataclass
class AuditResult:
    """Result of an architectural audit."""
    total_types: int
    total_violations: int
    violations_by_severity: Dict[str, int]
    violations_by_rule: Dict[str, int]
    violations: List[ArchitecturalViolation]
    metrics: Dict[str, Any] = field(default_factory=dict)


class CSharpAuditEngine:
    """Advanced architectural audit engine for C# codebases."""

    def __init__(self, analyzer: CSharpSemanticAnalyzer):
        self.analyzer = analyzer
        self.rules: Dict[str, AuditRule] = {}
        self.violations: List[ArchitecturalViolation] = []

        # Initialize default rules
        self._initialize_rules()

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
                "forbidden_dependencies": ["Domain"]
            }
        )

        self.rules["MEDIATR_002"] = AuditRule(
            rule_id="MEDIATR_002",
            name="Controller MediatR Usage",
            description="Controllers must only depend on IMediator, not handlers directly",
            severity="error",
            configuration={
                "controller_allowed_dependencies": ["IMediator"],
                "forbidden_patterns": ["Handler"]
            }
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
                    "System.Data.SqlClient"
                ]
            }
        )

        # Rule 3: Cyclic Dependencies
        self.rules["ARCH_001"] = AuditRule(
            rule_id="ARCH_001",
            name="No Cyclic Dependencies",
            description="Namespaces must not have circular references",
            severity="error"
        )

        # Rule 4: God Object Detection
        self.rules["DESIGN_001"] = AuditRule(
            rule_id="DESIGN_001",
            name="No God Objects",
            description="Classes should maintain reasonable cohesion (LCOM < 0.8)",
            severity="warning",
            configuration={
                "lcom_threshold": 0.8,
                "loc_threshold": 500
            }
        )

        # Rule 5: Async Safety
        self.rules["ASYNC_001"] = AuditRule(
            rule_id="ASYNC_001",
            name="No Async-over-Sync",
            description="Avoid blocking async code with .Result or .Wait()",
            severity="warning"
        )

        # Rule 6: Dependency Direction
        self.rules["ARCH_002"] = AuditRule(
            rule_id="ARCH_002",
            name="Dependency Flow Direction",
            description="Dependencies must flow inward: Web -> Application -> Domain",
            severity="error",
            configuration={
                "layer_hierarchy": ["Domain", "Application", "Infrastructure", "Web"]
            }
        )

        # Rule 7: Repository Pattern
        self.rules["DATA_002"] = AuditRule(
            rule_id="DATA_002",
            name="Repository Interface Usage",
            description="Repositories must implement an interface",
            severity="warning"
        )

        # Rule 8: Attribute Validation
        self.rules["ATTR_001"] = AuditRule(
            rule_id="ATTR_001",
            name="Controller Attribute Validation",
            description="Controllers must have [ApiController] and [Route] attributes",
            severity="warning"
        )

    def audit_mediatr_pattern(self) -> List[ArchitecturalViolation]:
        """Audit MediatR pattern compliance."""
        violations = []
        rule1 = self.rules["MEDIATR_001"]
        rule2 = self.rules["MEDIATR_002"]

        for type_name, type_info in self.analyzer.types.items():
            # Check handlers only access Domain
            if type_info.architectural_role == ArchitecturalRole.HANDLER:
                for dep in type_info.dependencies:
                    dep_type = self.analyzer.types.get(dep)
                    if dep_type:
                        # Check if dependency is outside Domain layer
                        if dep_type.namespace and not any(
                            layer in dep_type.namespace
                            for layer in ["Domain", "Handler", "Common"]
                        ):
                            violations.append(ArchitecturalViolation(
                                rule_id=rule1.rule_id,
                                severity=rule1.severity,
                                message=f"Handler '{type_name}' depends on '{dep}' from {dep_type.namespace} (should only depend on Domain)",
                                type_name=type_name,
                                file_path=type_info.file_path,
                                suggestion="Handlers should only reference Domain entities and value objects"
                            ))

            # Check controllers only use IMediator
            if type_info.architectural_role == ArchitecturalRole.CONTROLLER:
                for dep in type_info.dependencies:
                    if "Handler" in dep and dep != "IMediator":
                        violations.append(ArchitecturalViolation(
                            rule_id=rule2.rule_id,
                            severity=rule2.severity,
                            message=f"Controller '{type_name}' directly depends on '{dep}' (should use IMediator)",
                            type_name=type_name,
                            file_path=type_info.file_path,
                            suggestion="Inject IMediator and send commands/queries instead of calling handlers directly"
                        ))

        return violations

    def audit_sql_access(self) -> List[ArchitecturalViolation]:
        """Audit direct SQL access in non-data layers."""
        violations = []
        rule = self.rules["DATA_001"]

        forbidden_namespaces = rule.configuration["forbidden_namespaces"]
        forbidden_layers = rule.configuration["forbidden_layers"]

        for type_name, type_info in self.analyzer.types.items():
            # Check if type is in a forbidden layer
            in_forbidden_layer = any(
                layer in type_info.namespace or layer in type_info.file_path
                for layer in forbidden_layers
            )

            if in_forbidden_layer:
                # Check dependencies for SQL libraries
                for dep in type_info.dependencies:
                    if dep.startswith("__SQL__"):
                        sql_namespace = dep.replace("__SQL__", "")
                        violations.append(ArchitecturalViolation(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=f"Type '{type_name}' in {type_info.namespace} directly references {sql_namespace}",
                            type_name=type_name,
                            file_path=type_info.file_path,
                            suggestion="Move SQL access to Infrastructure/Repository layer and use interfaces"
                        ))

        return violations

    def detect_cyclic_dependencies(self) -> List[ArchitecturalViolation]:
        """Detect cyclic dependencies between namespaces."""
        violations = []
        rule = self.rules["ARCH_001"]

        # Build namespace dependency graph
        namespace_deps = defaultdict(set)

        for type_info in self.analyzer.types.values():
            source_ns = type_info.namespace

            for dep_name in type_info.dependencies:
                dep_type = self.analyzer.types.get(dep_name)
                if dep_type and dep_type.namespace != source_ns:
                    namespace_deps[source_ns].add(dep_type.namespace)

        # Detect cycles using DFS
        def find_cycle(node, visited, rec_stack, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in namespace_deps.get(node, []):
                if neighbor not in visited:
                    if find_cycle(neighbor, visited, rec_stack, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    violations.append(ArchitecturalViolation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=f"Cyclic dependency detected: {' -> '.join(cycle)}",
                        type_name=node,
                        file_path="Multiple files",
                        suggestion="Refactor to break the cycle using interfaces or moving shared code"
                    ))
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        visited = set()
        for namespace in namespace_deps.keys():
            if namespace not in visited:
                find_cycle(namespace, visited, set(), [])

        return violations

    def audit_god_objects(self) -> List[ArchitecturalViolation]:
        """Detect God Objects using LCOM and LOC metrics."""
        violations = []
        rule = self.rules["DESIGN_001"]

        lcom_threshold = rule.configuration["lcom_threshold"]
        loc_threshold = rule.configuration["loc_threshold"]

        for type_name, type_info in self.analyzer.types.items():
            is_god_object = False
            reasons = []

            # Check LCOM
            if type_info.lcom_score > lcom_threshold:
                is_god_object = True
                reasons.append(f"Low cohesion (LCOM={type_info.lcom_score:.2f})")

            # Check LOC
            if type_info.lines_of_code > loc_threshold:
                is_god_object = True
                reasons.append(f"Too many lines ({type_info.lines_of_code} LOC)")

            # Check number of dependencies
            if len(type_info.dependencies) > 10:
                is_god_object = True
                reasons.append(f"Too many dependencies ({len(type_info.dependencies)})")

            if is_god_object:
                violations.append(ArchitecturalViolation(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    message=f"'{type_name}' is a potential God Object: {', '.join(reasons)}",
                    type_name=type_name,
                    file_path=type_info.file_path,
                    suggestion="Consider splitting into smaller, focused classes with single responsibilities"
                ))

        return violations

    def audit_async_safety(self) -> List[ArchitecturalViolation]:
        """Audit async/await usage for anti-patterns."""
        violations = []
        rule = self.rules["ASYNC_001"]

        for type_name, type_info in self.analyzer.types.items():
            if hasattr(type_info, 'async_violations') and type_info.async_violations:
                for line_num, message in type_info.async_violations:
                    violations.append(ArchitecturalViolation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=message,
                        type_name=type_name,
                        file_path=type_info.file_path,
                        line_number=line_num,
                        suggestion="Use proper async/await instead of .Result, .Wait(), or .GetAwaiter().GetResult()"
                    ))

        return violations

    def audit_dependency_direction(self) -> List[ArchitecturalViolation]:
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
                    violations.append(ArchitecturalViolation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=f"'{type_name}' in {source_layer} depends on '{dep_name}' in {dep_layer} (wrong direction)",
                        type_name=type_name,
                        file_path=type_info.file_path,
                        suggestion=f"Dependencies should flow: {' -> '.join(layer_hierarchy)}. Consider using interfaces or moving code."
                    ))

        return violations

    def audit_repository_interfaces(self) -> List[ArchitecturalViolation]:
        """Audit that repositories implement interfaces."""
        violations = []
        rule = self.rules["DATA_002"]

        for type_name, type_info in self.analyzer.types.items():
            if type_info.architectural_role == ArchitecturalRole.REPOSITORY:
                # Check if there's a corresponding interface
                interface_name = f"I{type_name}"

                if interface_name not in self.analyzer.types:
                    violations.append(ArchitecturalViolation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=f"Repository '{type_name}' does not have a corresponding interface",
                        type_name=type_name,
                        file_path=type_info.file_path,
                        suggestion=f"Create interface '{interface_name}' and inject via DI"
                    ))

        return violations

    def audit_controller_attributes(self) -> List[ArchitecturalViolation]:
        """Audit that controllers have required attributes."""
        violations = []
        rule = self.rules["ATTR_001"]

        required_attributes = ["ApiController", "Route"]

        for type_name, type_info in self.analyzer.types.items():
            if type_info.architectural_role == ArchitecturalRole.CONTROLLER:
                attr_names = [attr.name for attr in type_info.attributes]

                for required in required_attributes:
                    if not any(required in attr for attr in attr_names):
                        violations.append(ArchitecturalViolation(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=f"Controller '{type_name}' is missing [{required}] attribute",
                            type_name=type_name,
                            file_path=type_info.file_path,
                            suggestion=f"Add [{required}] attribute to the controller"
                        ))

        return violations

    def run_all_audits(self) -> AuditResult:
        """Run all enabled audit rules."""
        all_violations = []

        # Run each audit
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
                violations = audit_method()
                all_violations.extend(violations)
            except Exception as e:
                # Log error but continue with other audits
                logger.error(f"Error in {audit_method.__name__}: {e}")

        # Compile results
        violations_by_severity = defaultdict(int)
        violations_by_rule = defaultdict(int)

        for violation in all_violations:
            violations_by_severity[violation.severity] += 1
            violations_by_rule[violation.rule_id] += 1

        # Calculate metrics
        metrics = {
            "total_types": len(self.analyzer.types),
            "avg_lcom": sum(t.lcom_score for t in self.analyzer.types.values()) / len(self.analyzer.types) if self.analyzer.types else 0,
            "avg_dependencies": sum(len(t.dependencies) for t in self.analyzer.types.values()) / len(self.analyzer.types) if self.analyzer.types else 0,
            "types_by_role": defaultdict(int),
            "namespaces_analyzed": len(set(t.namespace for t in self.analyzer.types.values())),
        }

        for type_info in self.analyzer.types.values():
            metrics["types_by_role"][type_info.architectural_role.value] += 1

        return AuditResult(
            total_types=len(self.analyzer.types),
            total_violations=len(all_violations),
            violations_by_severity=dict(violations_by_severity),
            violations_by_rule=dict(violations_by_rule),
            violations=all_violations,
            metrics=metrics
        )
