"""Advanced C# Semantic Analysis for Architectural Intelligence.

This module provides deep architectural analysis including:
- Dependency Injection mapping
- Attribute-based categorization
- Complexity metrics (LCOM, Instability)
- Architectural rule enforcement
"""

import re
import ast
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from collections import defaultdict
from enum import Enum

from models import Language, PatternCategory


class ArchitecturalRole(str, Enum):
    """Architectural roles derived from attributes and patterns."""
    CONTROLLER = "controller"
    SERVICE = "service"
    REPOSITORY = "repository"
    DOMAIN_ENTITY = "domain_entity"
    VALUE_OBJECT = "value_object"
    HANDLER = "handler"
    VALIDATOR = "validator"
    MIDDLEWARE = "middleware"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class CSharpAttribute:
    """Represents a C# attribute."""
    name: str
    arguments: List[str] = field(default_factory=list)
    location: Optional[str] = None


@dataclass
class CSharpMember:
    """Represents a class member (field, property, method)."""
    name: str
    member_type: str  # "field", "property", "method"
    return_type: Optional[str] = None
    accessed_members: Set[str] = field(default_factory=set)
    is_static: bool = False


@dataclass
class DIRegistration:
    """Represents a dependency injection registration."""
    interface_type: str
    implementation_type: str
    lifetime: str  # "Transient", "Scoped", "Singleton"
    location: str


@dataclass
class CSharpTypeInfo:
    """Extended type information for architectural analysis."""
    name: str
    namespace: str
    file_path: str
    type_kind: str  # "class", "interface", "struct", "record", "enum"

    # Architectural metadata
    attributes: List[CSharpAttribute] = field(default_factory=list)
    architectural_role: ArchitecturalRole = ArchitecturalRole.UNKNOWN

    # Dependencies
    dependencies: Set[str] = field(default_factory=set)  # Types this depends on
    dependents: Set[str] = field(default_factory=set)   # Types that depend on this

    # Members for cohesion analysis
    members: List[CSharpMember] = field(default_factory=list)

    # Metrics
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    lcom_score: float = 0.0

    # Partial class tracking
    is_partial: bool = False
    partial_locations: List[str] = field(default_factory=list)


@dataclass
class ArchitecturalViolation:
    """Represents an architectural rule violation."""
    rule_id: str
    severity: str  # "error", "warning", "info"
    message: str
    type_name: str
    file_path: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


class CSharpSemanticAnalyzer:
    """Advanced semantic analyzer for C# architectural patterns."""

    # Attribute patterns for role detection
    ROLE_ATTRIBUTES = {
        ArchitecturalRole.CONTROLLER: [
            r"ApiController", r"Controller", r"RouteAttribute"
        ],
        ArchitecturalRole.SERVICE: [
            r"Service", r"Injectable", r"Transient", r"Scoped"
        ],
        ArchitecturalRole.REPOSITORY: [
            r"Repository", r"DataAccess"
        ],
        ArchitecturalRole.DOMAIN_ENTITY: [
            r"Entity", r"DomainEntity", r"Aggregate"
        ],
        ArchitecturalRole.VALUE_OBJECT: [
            r"ValueObject", r"Immutable"
        ],
        ArchitecturalRole.HANDLER: [
            r"Handler", r"RequestHandler", r"CommandHandler", r"QueryHandler"
        ],
        ArchitecturalRole.VALIDATOR: [
            r"Validator", r"FluentValidation"
        ],
        ArchitecturalRole.MIDDLEWARE: [
            r"Middleware"
        ]
    }

    def __init__(self):
        self.types: Dict[str, CSharpTypeInfo] = {}
        self.di_registrations: List[DIRegistration] = []
        self.violations: List[ArchitecturalViolation] = []

    def extract_attributes(self, content: str, start_line: int) -> List[CSharpAttribute]:
        """Extract C# attributes from code."""
        attributes = []
        lines = content.split("\n")

        # Attribute pattern: [AttributeName] or [AttributeName(args)]
        attr_pattern = re.compile(r'^\s*\[(\w+)(?:\(([^]]*)\))?\]')

        for i in range(max(0, start_line - 10), min(len(lines), start_line + 5)):
            match = attr_pattern.match(lines[i])
            if match:
                attr_name = match.group(1)
                attr_args = match.group(2).split(',') if match.group(2) else []
                attributes.append(CSharpAttribute(
                    name=attr_name,
                    arguments=[arg.strip() for arg in attr_args],
                    location=f"line {i+1}"
                ))

        return attributes

    def determine_architectural_role(
        self,
        attributes: List[CSharpAttribute],
        type_name: str,
        base_types: List[str]
    ) -> ArchitecturalRole:
        """Determine architectural role based on attributes and conventions."""
        # Check attributes first
        for attr in attributes:
            for role, patterns in self.ROLE_ATTRIBUTES.items():
                if any(re.search(pattern, attr.name, re.IGNORECASE) for pattern in patterns):
                    return role

        # Check naming conventions
        if type_name.endswith("Controller"):
            return ArchitecturalRole.CONTROLLER
        elif type_name.endswith("Service"):
            return ArchitecturalRole.SERVICE
        elif type_name.endswith("Repository"):
            return ArchitecturalRole.REPOSITORY
        elif type_name.endswith("Handler"):
            return ArchitecturalRole.HANDLER
        elif type_name.endswith("Validator"):
            return ArchitecturalRole.VALIDATOR

        # Check base types/interfaces
        for base_type in base_types:
            if "Controller" in base_type:
                return ArchitecturalRole.CONTROLLER
            elif "Repository" in base_type:
                return ArchitecturalRole.REPOSITORY

        return ArchitecturalRole.UNKNOWN

    def extract_di_registrations(self, program_cs_content: str, file_path: str) -> List[DIRegistration]:
        """Extract dependency injection registrations from Program.cs or Startup.cs."""
        registrations = []

        # Patterns for DI registration
        patterns = [
            # services.AddTransient<IService, ServiceImpl>()
            r'Add(Transient|Scoped|Singleton)<(\w+),\s*(\w+)>\(',
            # services.AddTransient<IService>(sp => new ServiceImpl())
            r'Add(Transient|Scoped|Singleton)<(\w+)>\([^)]*new\s+(\w+)',
            # services.AddTransient(typeof(IService), typeof(ServiceImpl))
            r'Add(Transient|Scoped|Singleton)\(typeof\((\w+)\),\s*typeof\((\w+)\)',
        ]

        for i, line in enumerate(program_cs_content.split("\n"), 1):
            for pattern in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    lifetime = match.group(1)
                    interface_type = match.group(2)
                    impl_type = match.group(3)

                    registrations.append(DIRegistration(
                        interface_type=interface_type,
                        implementation_type=impl_type,
                        lifetime=lifetime,
                        location=f"{file_path}:{i}"
                    ))

        self.di_registrations.extend(registrations)
        return registrations

    def extract_dependencies(self, content: str) -> Set[str]:
        """Extract type dependencies from C# code."""
        dependencies = set()

        # Extract from field/property declarations
        field_pattern = re.compile(r'(?:private|public|protected|internal)\s+(?:readonly\s+)?(\w+(?:<\w+>)?)\s+\w+')
        for match in field_pattern.finditer(content):
            dep_type = match.group(1)
            # Remove generic parameters for now
            dep_type = re.sub(r'<.*?>', '', dep_type)
            if dep_type and dep_type[0].isupper():  # Type names start with capital
                dependencies.add(dep_type)

        # Extract from method parameters and return types
        method_pattern = re.compile(r'(?:public|private|protected|internal)\s+(?:async\s+)?(?:Task<)?(\w+)>?\s+\w+\([^)]*\)')
        for match in method_pattern.finditer(content):
            return_type = match.group(1)
            if return_type and return_type[0].isupper() and return_type not in ['Task', 'void']:
                dependencies.add(return_type)

        # Extract from using statements (namespace level)
        using_pattern = re.compile(r'using\s+([\w.]+);')
        for match in using_pattern.finditer(content):
            namespace = match.group(1)
            # Check for SQL-related namespaces for architectural rules
            if 'SqlClient' in namespace or 'Dapper' in namespace:
                dependencies.add(f"__SQL__{namespace}")

        return dependencies

    def extract_members(self, content: str) -> List[CSharpMember]:
        """Extract class members for cohesion analysis."""
        members = []

        # Extract fields
        field_pattern = re.compile(
            r'(?:private|public|protected|internal)\s+(?:readonly\s+)?(?:static\s+)?(\w+)\s+(\w+)\s*[;=]',
            re.MULTILINE
        )
        for match in field_pattern.finditer(content):
            members.append(CSharpMember(
                name=match.group(2),
                member_type="field",
                return_type=match.group(1),
                is_static='static' in match.group(0)
            ))

        # Extract properties
        property_pattern = re.compile(
            r'(?:public|private|protected|internal)\s+(?:static\s+)?(\w+)\s+(\w+)\s*\{',
            re.MULTILINE
        )
        for match in property_pattern.finditer(content):
            members.append(CSharpMember(
                name=match.group(2),
                member_type="property",
                return_type=match.group(1),
                is_static='static' in match.group(0)
            ))

        # Extract methods
        method_pattern = re.compile(
            r'(?:public|private|protected|internal)\s+(?:static\s+)?(?:async\s+)?(?:Task<)?(\w+)>?\s+(\w+)\s*\(',
            re.MULTILINE
        )
        for match in method_pattern.finditer(content):
            members.append(CSharpMember(
                name=match.group(2),
                member_type="method",
                return_type=match.group(1),
                is_static='static' in match.group(0)
            ))

        return members

    def calculate_lcom(self, members: List[CSharpMember], content: str) -> float:
        """
        Calculate Lack of Cohesion in Methods (LCOM4).

        LCOM = 1 - (sum of method-field accesses / (methods * fields))
        Higher values indicate lower cohesion (bad).
        """
        methods = [m for m in members if m.member_type == "method" and not m.is_static]
        fields = [m for m in members if m.member_type in ("field", "property") and not m.is_static]

        if not methods or not fields:
            return 0.0

        # Count field accesses in each method
        total_accesses = 0
        for method in methods:
            for field in fields:
                # Simple check: does method body contain field name?
                # In production, use proper AST parsing
                method_start = content.find(f"def {method.name}")
                if method_start == -1:
                    method_start = content.find(f"{method.name}(")

                if method_start != -1:
                    # Look ahead ~200 chars for field reference
                    method_region = content[method_start:method_start+500]
                    if re.search(rf'\b{field.name}\b', method_region):
                        total_accesses += 1
                        method.accessed_members.add(field.name)

        max_accesses = len(methods) * len(fields)
        if max_accesses == 0:
            return 0.0

        lcom = 1.0 - (total_accesses / max_accesses)
        return round(lcom, 3)

    def detect_async_over_sync(self, content: str) -> List[Tuple[int, str]]:
        """Detect async-over-sync anti-patterns (.Result, .Wait())."""
        violations = []

        patterns = [
            (r'\.Result\b', 'Using .Result blocks the thread (async-over-sync)'),
            (r'\.Wait\(\)', 'Using .Wait() blocks the thread (async-over-sync)'),
            (r'\.GetAwaiter\(\)\.GetResult\(\)', 'Using GetResult() blocks the thread'),
        ]

        for i, line in enumerate(content.split("\n"), 1):
            for pattern, message in patterns:
                if re.search(pattern, line):
                    violations.append((i, message))

        return violations

    def analyze_type(self, type_info: CSharpTypeInfo, content: str) -> CSharpTypeInfo:
        """Perform deep analysis on a C# type."""
        # Extract members
        type_info.members = self.extract_members(content)

        # Calculate LCOM
        type_info.lcom_score = self.calculate_lcom(type_info.members, content)

        # Extract dependencies
        type_info.dependencies = self.extract_dependencies(content)

        # Count lines of code (excluding blanks and comments)
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("//")]
        type_info.lines_of_code = len(lines)

        # Simple cyclomatic complexity (count decision points)
        decision_keywords = ['if', 'else', 'while', 'for', 'foreach', 'switch', 'case', '&&', '||', '?']
        type_info.cyclomatic_complexity = sum(
            content.count(keyword) for keyword in decision_keywords
        )

        # Store in analyzer
        self.types[type_info.name] = type_info

        return type_info

    def calculate_instability(self, namespace: str) -> float:
        """
        Calculate Instability Index for a namespace.

        Instability = Ce / (Ca + Ce)
        Where:
        - Ce = Efferent Coupling (outgoing dependencies)
        - Ca = Afferent Coupling (incoming dependencies)

        Range: 0 (stable) to 1 (unstable)
        """
        types_in_namespace = [t for t in self.types.values() if t.namespace == namespace]

        if not types_in_namespace:
            return 0.0

        # Efferent: dependencies going out
        efferent = set()
        for type_info in types_in_namespace:
            efferent.update(type_info.dependencies)

        # Afferent: dependencies coming in
        afferent = set()
        for type_info in types_in_namespace:
            afferent.update(type_info.dependents)

        ce = len(efferent)
        ca = len(afferent)

        if ce + ca == 0:
            return 0.0

        return round(ce / (ce + ca), 3)

    def link_di_registrations(self):
        """Link interfaces to implementations via DI registrations."""
        for reg in self.di_registrations:
            if reg.interface_type in self.types:
                interface = self.types[reg.interface_type]
                if reg.implementation_type in self.types:
                    implementation = self.types[reg.implementation_type]
                    # Create dependency link
                    interface.dependents.add(reg.implementation_type)
                    implementation.dependencies.add(reg.interface_type)

    def aggregate_partial_classes(self):
        """Aggregate data from partial class declarations."""
        partial_groups = defaultdict(list)

        # Group partial classes by name and namespace
        for type_name, type_info in self.types.items():
            if type_info.is_partial:
                key = f"{type_info.namespace}.{type_info.name}"
                partial_groups[key].append(type_info)

        # Merge partial class data
        for key, partials in partial_groups.items():
            if len(partials) <= 1:
                continue

            # Use first as base
            base = partials[0]
            base.partial_locations = [p.file_path for p in partials]

            # Aggregate from others
            for other in partials[1:]:
                base.members.extend(other.members)
                base.attributes.extend(other.attributes)
                base.dependencies.update(other.dependencies)
                base.lines_of_code += other.lines_of_code
                base.cyclomatic_complexity += other.cyclomatic_complexity

            # Recalculate metrics
            # Note: Would need full content to recalculate LCOM properly
