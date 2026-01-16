"""Integration module for C# Architectural Audit with existing DNA system.

This module bridges the advanced C# audit capabilities with the existing
Architectural DNA pattern extraction and storage system.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import asdict

from models import Pattern, PatternCategory, Language, CodeChunk
from pattern_extractor import PatternExtractor
from csharp_semantic_analyzer import (
    CSharpSemanticAnalyzer,
    CSharpTypeInfo,
    ArchitecturalRole
)
from csharp_audit_engine import CSharpAuditEngine
from csharp_audit_reporter import CSharpAuditReporter

logger = logging.getLogger(__name__)


class CSharpArchitecturalAuditor:
    """
    Main integration point for C# architectural auditing.

    Extends the basic pattern extraction with deep architectural analysis.
    """

    def __init__(self):
        self.pattern_extractor = PatternExtractor()
        self.semantic_analyzer = CSharpSemanticAnalyzer()
        self.audit_engine = CSharpAuditEngine(self.semantic_analyzer)
        self.reporter = CSharpAuditReporter()

    def analyze_csharp_file(
        self,
        file_path: str,
        content: str
    ) -> List[CSharpTypeInfo]:
        """
        Analyze a C# file with full semantic enrichment.

        Args:
            file_path: Path to the C# file
            content: File content

        Returns:
            List of enriched type information
        """
        # Extract basic chunks using pattern extractor
        chunks = self.pattern_extractor.extract_chunks(
            content,
            file_path,
            Language.CSHARP
        )

        types_info = []

        for chunk in chunks:
            # Create type info
            namespace = self._extract_namespace(chunk.context or "")

            type_info = CSharpTypeInfo(
                name=chunk.name or "Unknown",
                namespace=namespace,
                file_path=file_path,
                type_kind=chunk.chunk_type,
                lines_of_code=chunk.end_line - chunk.start_line
            )

            # Extract attributes
            type_info.attributes = self.semantic_analyzer.extract_attributes(
                content,
                chunk.start_line
            )

            # Determine architectural role
            base_types = self._extract_base_types(chunk.content)
            type_info.architectural_role = self.semantic_analyzer.determine_architectural_role(
                type_info.attributes,
                type_info.name,
                base_types
            )

            # Detect partial classes
            type_info.is_partial = "partial" in chunk.content

            # Full semantic analysis
            type_info = self.semantic_analyzer.analyze_type(type_info, chunk.content)

            # Check for async safety issues
            async_violations = self.semantic_analyzer.detect_async_over_sync(chunk.content)
            if async_violations:
                type_info.async_violations = async_violations
                logger.warning(
                    f"Async-over-sync detected in {type_info.name}: "
                    f"{len(async_violations)} violations"
                )

            types_info.append(type_info)

        return types_info

    def analyze_csharp_project(
        self,
        project_path: str,
        include_patterns: List[str] = None
    ) -> Dict:
        """
        Analyze an entire C# project or solution.

        Args:
            project_path: Path to project root or .csproj file
            include_patterns: Optional glob patterns for files to include

        Returns:
            Dictionary with analysis results
        """
        project_root = Path(project_path)
        if project_root.is_file():
            project_root = project_root.parent

        # Find all C# files
        cs_files = list(project_root.rglob("*.cs"))

        if include_patterns:
            cs_files = [
                f for f in cs_files
                if any(f.match(pattern) for pattern in include_patterns)
            ]

        logger.info(f"Analyzing {len(cs_files)} C# files in {project_root}")

        # Analyze each file
        all_types = []
        for cs_file in cs_files:
            try:
                content = cs_file.read_text(encoding='utf-8')

                # Check for Program.cs to extract DI registrations
                if cs_file.name in ["Program.cs", "Startup.cs"]:
                    self.semantic_analyzer.extract_di_registrations(
                        content,
                        str(cs_file)
                    )

                types = self.analyze_csharp_file(str(cs_file), content)
                all_types.extend(types)

            except Exception as e:
                logger.error(f"Error analyzing {cs_file}: {e}")

        # Link DI registrations
        self.semantic_analyzer.link_di_registrations()

        # Aggregate partial classes
        self.semantic_analyzer.aggregate_partial_classes()

        # Run architectural audits
        audit_result = self.audit_engine.run_all_audits()

        return {
            "project_path": str(project_root),
            "files_analyzed": len(cs_files),
            "types_analyzed": len(all_types),
            "types": {t.name: t for t in all_types},
            "audit_result": audit_result
        }

    def generate_reports(
        self,
        analysis_result: Dict,
        output_dir: str
    ):
        """
        Generate all report formats.

        Args:
            analysis_result: Result from analyze_csharp_project
            output_dir: Directory to write reports
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        audit_result = analysis_result["audit_result"]
        types = analysis_result["types"]

        # JSON Report
        json_path = output_path / "audit_report.json"
        self.reporter.generate_json_report(audit_result, str(json_path))
        logger.info(f"JSON report: {json_path}")

        # Markdown Report
        md_path = output_path / "audit_report.md"
        self.reporter.generate_markdown_report(audit_result, types, str(md_path))
        logger.info(f"Markdown report: {md_path}")

        # SARIF Report (for IDE integration)
        sarif_path = output_path / "audit_report.sarif"
        self.reporter.generate_sarif_report(audit_result, str(sarif_path))
        logger.info(f"SARIF report: {sarif_path}")

        # Console summary
        self.reporter.print_console_summary(audit_result)

    def convert_to_dna_patterns(
        self,
        types: List[CSharpTypeInfo]
    ) -> List[Pattern]:
        """
        Convert analyzed types to DNA Pattern format for storage.

        Args:
            types: List of analyzed type information

        Returns:
            List of Pattern objects ready for DNA storage
        """
        patterns = []

        for type_info in types:
            # Only store high-quality patterns
            if type_info.lcom_score > 0.8:  # Skip low-cohesion classes
                continue

            # Map architectural role to pattern category
            category_map = {
                ArchitecturalRole.CONTROLLER: PatternCategory.API,
                ArchitecturalRole.SERVICE: PatternCategory.BUSINESS_LOGIC,
                ArchitecturalRole.REPOSITORY: PatternCategory.DATA_ACCESS,
                ArchitecturalRole.DOMAIN_ENTITY: PatternCategory.ARCHITECTURE,
                ArchitecturalRole.HANDLER: PatternCategory.BUSINESS_LOGIC,
                ArchitecturalRole.MIDDLEWARE: PatternCategory.ARCHITECTURE,
            }

            category = category_map.get(
                type_info.architectural_role,
                PatternCategory.OTHER
            )

            # Create pattern description
            description = self._generate_pattern_description(type_info)

            # Create pattern
            pattern = Pattern(
                title=f"{type_info.architectural_role.value.replace('_', ' ').title()}: {type_info.name}",
                description=description,
                content=f"// Extracted from {type_info.file_path}\n// Namespace: {type_info.namespace}\n\n[Type definition would be here]",
                category=category,
                language=Language.CSHARP,
                quality_score=self._calculate_quality_score(type_info),
                source_repo="csharp_audit",
                source_path=type_info.file_path,
                use_cases=[
                    type_info.architectural_role.value,
                    type_info.type_kind,
                    f"lcom_{type_info.lcom_score:.2f}",
                    f"deps_{len(type_info.dependencies)}"
                ]
            )

            patterns.append(pattern)

        return patterns

    def _extract_namespace(self, context: str) -> str:
        """Extract namespace from context string."""
        for line in context.split("\n"):
            if line.strip().startswith("namespace "):
                return line.strip().replace("namespace ", "").rstrip(";")
        return ""

    def _extract_base_types(self, content: str) -> List[str]:
        """Extract base types/interfaces from class declaration."""
        match = re.search(r':\s*([^{]+)', content)
        if match:
            bases = match.group(1).split(',')
            return [b.strip() for b in bases]
        return []

    def _generate_pattern_description(self, type_info: CSharpTypeInfo) -> str:
        """Generate human-readable pattern description."""
        parts = [
            f"A {type_info.type_kind} from the {type_info.namespace} namespace",
            f"serving as a {type_info.architectural_role.value.replace('_', ' ')}."
        ]

        if type_info.attributes:
            attr_names = [a.name for a in type_info.attributes]
            parts.append(f"Decorated with attributes: {', '.join(attr_names)}.")

        parts.append(
            f"Contains {len(type_info.members)} members with "
            f"LCOM score of {type_info.lcom_score:.2f}."
        )

        if type_info.dependencies:
            parts.append(
                f"Depends on {len(type_info.dependencies)} types."
            )

        return " ".join(parts)

    def _calculate_quality_score(self, type_info: CSharpTypeInfo) -> int:
        """
        Calculate quality score (1-10) based on metrics.

        High cohesion, low coupling, appropriate size = higher score.
        """
        score = 10

        # Penalize low cohesion
        if type_info.lcom_score > 0.8:
            score -= 3
        elif type_info.lcom_score > 0.6:
            score -= 1

        # Penalize high complexity
        if type_info.cyclomatic_complexity > 50:
            score -= 2
        elif type_info.cyclomatic_complexity > 30:
            score -= 1

        # Penalize large size
        if type_info.lines_of_code > 500:
            score -= 2
        elif type_info.lines_of_code > 300:
            score -= 1

        # Penalize high coupling
        if len(type_info.dependencies) > 15:
            score -= 2
        elif len(type_info.dependencies) > 10:
            score -= 1

        # Bonus for good architectural role
        if type_info.architectural_role != ArchitecturalRole.UNKNOWN:
            score += 1

        return max(1, min(10, score))


# Example usage function
def audit_csharp_project_example(project_path: str, output_dir: str):
    """
    Example function showing complete workflow.

    Args:
        project_path: Path to C# project
        output_dir: Where to write reports
    """
    auditor = CSharpArchitecturalAuditor()

    # Analyze project
    print(f"Analyzing C# project at: {project_path}")
    results = auditor.analyze_csharp_project(project_path)

    # Generate reports
    print(f"Generating reports to: {output_dir}")
    auditor.generate_reports(results, output_dir)

    # Convert to DNA patterns for storage
    types = list(results["types"].values())
    patterns = auditor.convert_to_dna_patterns(types)
    print(f"Generated {len(patterns)} DNA patterns for storage")

    return results, patterns
