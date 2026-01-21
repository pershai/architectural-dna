"""Advanced C# Semantic Analysis for Architectural Intelligence.

This module provides deep architectural analysis including:
- Dependency Injection mapping
- Attribute-based categorization
- Complexity metrics (LCOM, Instability)
- Architectural rule enforcement
"""

import re
import ast
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from collections import defaultdict
from enum import Enum

from models import Language, PatternCategory
from csharp_pattern_detector import CSharpPatternDetector, DesignPattern
from csharp_constants import CSHARP_CONSTANTS


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

    # Async safety violations (line_number, message)
    async_violations: List[Tuple[int, str]] = field(default_factory=list)

    # Detected design patterns
    design_patterns: List[dict] = field(default_factory=list)  # List of {pattern, confidence, indicators}


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

    def __init__(self, config_path: str = "config.yaml"):
        self.types: Dict[str, CSharpTypeInfo] = {}
        self.di_registrations: List[DIRegistration] = []
        self.config = self._load_config(config_path)
        self.pattern_detector = CSharpPatternDetector()

    def _load_config(self, config_path: str) -> Dict:
        """Load C# configuration from YAML file."""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                    return config.get("csharp_audit", {})
        except Exception:
            pass  # Return empty config on error

        return {}

    def extract_attributes(self, content: str, start_line: int) -> List[CSharpAttribute]:
        """Extract C# attributes from code."""
        attributes = []
        lines = content.split("\n")
        attr_pattern = re.compile(r'^\s*\[(\w+)(?:\(([^]]*)\))?\]')

        search_start = max(0, start_line - CSHARP_CONSTANTS.ATTRIBUTE_SEARCH_LINES_BEFORE)
        search_end = min(len(lines), start_line + CSHARP_CONSTANTS.ATTRIBUTE_SEARCH_LINES_AFTER)

        for i in range(search_start, search_end):
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
        patterns = [
            r'Add(Transient|Scoped|Singleton)<(\w+),\s*(\w+)>\(',
            r'Add(Transient|Scoped|Singleton)<(\w+)>\([^)]*new\s+(\w+)',
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

        field_pattern = re.compile(r'(?:private|public|protected|internal)\s+(?:readonly\s+)?(\w+(?:<\w+>)?)\s+\w+')
        for match in field_pattern.finditer(content):
            dep_type = re.sub(r'<.*?>', '', match.group(1))
            if dep_type and dep_type[0].isupper():
                dependencies.add(dep_type)

        method_pattern = re.compile(r'(?:public|private|protected|internal)\s+(?:async\s+)?(?:Task<)?(\w+)>?\s+\w+\([^)]*\)')
        for match in method_pattern.finditer(content):
            return_type = match.group(1)
            if return_type and return_type[0].isupper() and return_type not in ['Task', 'void']:
                dependencies.add(return_type)

        using_pattern = re.compile(r'using\s+([\w.]+);')
        for match in using_pattern.finditer(content):
            namespace = match.group(1)
            if 'SqlClient' in namespace or 'Dapper' in namespace:
                dependencies.add(f"__SQL__{namespace}")

        return dependencies

    def extract_members(self, content: str) -> List[CSharpMember]:
        """Extract class members for cohesion analysis."""
        members = []

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
        """Calculate Lack of Cohesion in Methods (LCOM4)."""
        methods = [m for m in members if m.member_type == "method" and not m.is_static]
        fields = [m for m in members if m.member_type in ("field", "property") and not m.is_static]

        if not methods or not fields:
            return 0.0

        total_accesses = 0
        for method in methods:
            # Use C# method pattern instead of Python 'def' keyword
            method_pattern = rf'(?:public|private|protected|internal)\s+.*\s+{re.escape(method.name)}\s*\('
            method_match = re.search(method_pattern, content)

            if method_match:
                method_start = method_match.start()
                # Find method end by counting braces
                method_end = self._find_method_end(content, method_start)
                method_region = content[method_start:method_end]

                # Check if this method accesses each field
                for field in fields:
                    if re.search(rf'\b{re.escape(field.name)}\b', method_region):
                        total_accesses += 1
                        method.accessed_members.add(field.name)

        max_accesses = len(methods) * len(fields)
        if max_accesses == 0:
            return 0.0

        lcom = 1.0 - (total_accesses / max_accesses)
        return round(lcom, 3)

    def _find_method_end(self, content: str, start: int) -> int:
        """Find the end of a C# method by counting braces."""
        brace_count = 0
        in_method = False
        i = start

        while i < len(content):
            char = content[i]
            if char == '{':
                brace_count += 1
                in_method = True
            elif char == '}':
                brace_count -= 1
                if in_method and brace_count == 0:
                    return i + 1

            i += 1

        # If we didn't find closing brace, return a reasonable default
        return min(start + CSHARP_CONSTANTS.METHOD_REGION_FALLBACK, len(content))

    def _calculate_cyclomatic_complexity(self, content: str) -> int:
        """
        Calculate cyclomatic complexity by counting decision points.
        Uses regex with word boundaries to avoid matching in comments/strings.
        """
        # Remove single-line comments
        content_no_comments = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)

        # Remove multi-line comments
        content_no_comments = re.sub(r'/\*.*?\*/', '', content_no_comments, flags=re.DOTALL)

        # Remove string literals to avoid false matches
        content_cleaned = re.sub(r'"(?:[^"\\]|\\.)*"', '', content_no_comments)
        content_cleaned = re.sub(r"'(?:[^'\\]|\\.)*'", '', content_cleaned)

        # Count decision points with word boundaries
        decision_patterns = [
            r'\bif\b',
            r'\belse\s+if\b',  # Count else-if as separate decision
            r'\bwhile\b',
            r'\bfor\b',
            r'\bforeach\b',
            r'\bcase\b',  # Each case is a decision point
            r'\bcatch\b',  # Exception handlers add complexity
            r'&&',  # Logical AND
            r'\|\|',  # Logical OR
            r'\?(?!=)',  # Ternary operator (but not null-coalescing ??)
        ]

        complexity = 1  # Base complexity
        for pattern in decision_patterns:
            complexity += len(re.findall(pattern, content_cleaned))

        return complexity

    def detect_async_over_sync(self, content: str) -> List[Tuple[int, str]]:
        """Detect async-over-sync anti-patterns and async best practice violations."""
        violations = []

        # Anti-patterns that block async code
        blocking_patterns = [
            (r'\.Result\b', 'Using .Result blocks the thread (async-over-sync)'),
            (r'\.Wait\(\)', 'Using .Wait() blocks the thread (async-over-sync)'),
            (r'\.GetAwaiter\(\)\.GetResult\(\)', 'Using GetResult() blocks the thread'),
            (r'Task\.Run\([^)]*\)\.Wait\(\)', 'Task.Run().Wait() is async-over-sync anti-pattern'),
            (r'Task\.WaitAll\(', 'Task.WaitAll() blocks the thread, prefer await Task.WhenAll()'),
            (r'Task\.WaitAny\(', 'Task.WaitAny() blocks the thread, prefer await Task.WhenAny()'),
        ]

        # Best practice violations (warnings, not errors)
        best_practice_patterns = [
            (r'async\s+void\s+\w+\s*\([^)]*\)', 'async void should only be used for event handlers'),
            (r'async\s+Task.*\([^)]*\)\s*{(?!.*CancellationToken)',
             'Async method should accept CancellationToken parameter'),
        ]

        for i, line in enumerate(content.split("\n"), 1):
            # Check blocking patterns
            for pattern, message in blocking_patterns:
                if re.search(pattern, line):
                    violations.append((i, message))

            # Check best practices (only for public/internal methods)
            if re.search(r'^\s*(?:public|internal)\s+async', line):
                for pattern, message in best_practice_patterns:
                    if re.search(pattern, line):
                        violations.append((i, f"Best practice: {message}"))

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

        # Calculate cyclomatic complexity with proper regex to avoid false positives
        type_info.cyclomatic_complexity = self._calculate_cyclomatic_complexity(content)

        # Detect design patterns
        if self.config.get("patterns", {}).get("detect_design_patterns", True):
            try:
                patterns = self.pattern_detector.detect_patterns(content, type_info.name)
                type_info.design_patterns = [
                    {
                        "pattern": p.pattern.value,
                        "confidence": p.confidence,
                        "indicators": p.indicators,
                        "description": p.description
                    }
                    for p in patterns
                ]
            except Exception as e:
                # Gracefully skip pattern detection on error
                pass

        # Store in analyzer
        self.types[type_info.name] = type_info

        return type_info

    def calculate_instability(self, namespace: str) -> float:
        """Calculate Instability Index for a namespace (0=stable, 1=unstable)."""
        types_in_namespace = [t for t in self.types.values() if t.namespace == namespace]

        if not types_in_namespace:
            return 0.0

        efferent = set()
        for type_info in types_in_namespace:
            efferent.update(type_info.dependencies)

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

        for type_name, type_info in self.types.items():
            if type_info.is_partial:
                key = f"{type_info.namespace}.{type_info.name}"
                partial_groups[key].append(type_info)

        for key, partials in partial_groups.items():
            if len(partials) <= 1:
                continue

            base = partials[0]
            base.partial_locations = [p.file_path for p in partials]

            for other in partials[1:]:
                base.members.extend(other.members)
                base.attributes.extend(other.attributes)
                base.dependencies.update(other.dependencies)
                base.lines_of_code += other.lines_of_code
                base.cyclomatic_complexity += other.cyclomatic_complexity
