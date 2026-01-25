"""Integration module for C# Architectural Audit with existing DNA system.

This module bridges the advanced C# audit capabilities with the existing
Architectural DNA pattern extraction and storage system.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Optional

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
        """Analyze a C# file with full semantic enrichment."""
        if not content or not content.strip():
            logger.warning(f"Empty content for file: {file_path}")
            return []

        chunks = self.pattern_extractor.extract_chunks(
            content,
            file_path,
            Language.CSHARP
        )

        types_info = []

        for chunk in chunks:
            namespace = self._extract_namespace(chunk.context or "")

            type_info = CSharpTypeInfo(
                name=chunk.name or "Unknown",
                namespace=namespace,
                file_path=file_path,
                type_kind=chunk.chunk_type,
                lines_of_code=chunk.end_line - chunk.start_line
            )

            type_info.attributes = self.semantic_analyzer.extract_attributes(
                content,
                chunk.start_line
            )

            base_types = self._extract_base_types(chunk.content)
            type_info.architectural_role = self.semantic_analyzer.determine_architectural_role(
                type_info.attributes,
                type_info.name,
                base_types
            )

            type_info.is_partial = "partial" in chunk.content
            type_info = self.semantic_analyzer.analyze_type(type_info, chunk.content)

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
        include_patterns: List[str] = None,
        batch_size: int = 100
    ) -> Dict:
        """Analyze an entire C# project or solution.

        Args:
            project_path: Path to C# project root or .csproj file
            include_patterns: Optional glob patterns to filter files
            batch_size: Number of files to process per batch (prevents memory issues)

        Returns:
            Dictionary with analysis results and audit findings
        """
        if not project_path:
            raise ValueError("project_path cannot be empty")

        project_root = Path(project_path)
        if not project_root.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        if project_root.is_file():
            project_root = project_root.parent

        cs_files = list(project_root.rglob("*.cs"))

        if not cs_files:
            logger.warning(f"No C# files found in {project_root}")
            return {
                "project_path": str(project_root),
                "files_analyzed": 0,
                "types_analyzed": 0,
                "types": {},
                "audit_result": None
            }

        if include_patterns:
            cs_files = [
                f for f in cs_files
                if any(f.match(pattern) for pattern in include_patterns)
            ]

        logger.info(f"Analyzing {len(cs_files)} C# files in {project_root}")

        # Process files in batches to prevent memory exhaustion on large projects
        files_processed = 0
        files_skipped = 0

        for i in range(0, len(cs_files), batch_size):
            batch = cs_files[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(cs_files) + batch_size - 1) // batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} files)")

            for cs_file in batch:
                try:
                    # Try multiple encodings
                    content = None
                    for encoding in ['utf-8', 'utf-8-sig', 'windows-1252']:
                        try:
                            content = cs_file.read_text(encoding=encoding)
                            break
                        except UnicodeDecodeError:
                            continue

                    if content is None:
                        logger.warning(f"Skipping {cs_file}: unsupported encoding")
                        files_skipped += 1
                        continue

                    # Extract DI registrations from entry point files
                    if cs_file.name in ["Program.cs", "Startup.cs"]:
                        self.semantic_analyzer.extract_di_registrations(
                            content,
                            str(cs_file)
                        )

                    # Analyze file and register types directly to prevent memory accumulation
                    types = self.analyze_csharp_file(str(cs_file), content)
                    for type_info in types:
                        # Register in analyzer immediately instead of accumulating in list
                        self.semantic_analyzer.types[type_info.name] = type_info

                    files_processed += 1

                except Exception as e:
                    logger.error(f"Unexpected error analyzing {cs_file}: {e}", exc_info=True)
                    files_skipped += 1

        logger.info(
            f"Analysis complete: {files_processed} files processed, "
            f"{files_skipped} files skipped, "
            f"{len(self.semantic_analyzer.types)} types analyzed"
        )

        # Link DI registrations and aggregate partial classes
        self.semantic_analyzer.link_di_registrations()
        self.semantic_analyzer.aggregate_partial_classes()

        # Run architectural audit
        audit_result = self.audit_engine.run_all_audits()

        return {
            "project_path": str(project_root),
            "files_analyzed": files_processed,
            "files_skipped": files_skipped,
            "types_analyzed": len(self.semantic_analyzer.types),
            "types": self.semantic_analyzer.types,
            "audit_result": audit_result
        }

    def generate_reports(
        self,
        analysis_result: Dict,
        output_dir: str
    ):
        """Generate all report formats."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        audit_result = analysis_result["audit_result"]
        types = analysis_result["types"]

        json_path = output_path / "audit_report.json"
        self.reporter.generate_json_report(audit_result, str(json_path), types)
        logger.info(f"JSON report: {json_path}")

        md_path = output_path / "audit_report.md"
        self.reporter.generate_markdown_report(audit_result, types, str(md_path))
        logger.info(f"Markdown report: {md_path}")

        sarif_path = output_path / "audit_report.sarif"
        self.reporter.generate_sarif_report(audit_result, str(sarif_path))
        logger.info(f"SARIF report: {sarif_path}")

        self.reporter.print_console_summary(audit_result)

    def convert_to_dna_patterns(
        self,
        types: List[CSharpTypeInfo]
    ) -> List[Pattern]:
        """Convert analyzed types to DNA Pattern format for storage."""
        if not types:
            logger.warning("No types provided to convert_to_dna_patterns")
            return []

        if not isinstance(types, list):
            raise TypeError(f"Expected list of CSharpTypeInfo, got {type(types)}")

        patterns = []

        for type_info in types:
            if type_info.lcom_score > 0.8:
                continue

            category_map = {
                ArchitecturalRole.CONTROLLER: PatternCategory.API_DESIGN,
                ArchitecturalRole.SERVICE: PatternCategory.UTILITIES,
                ArchitecturalRole.REPOSITORY: PatternCategory.DATA_ACCESS,
                ArchitecturalRole.DOMAIN_ENTITY: PatternCategory.ARCHITECTURE,
                ArchitecturalRole.HANDLER: PatternCategory.UTILITIES,
                ArchitecturalRole.MIDDLEWARE: PatternCategory.ARCHITECTURE,
            }

            category = category_map.get(
                type_info.architectural_role,
                PatternCategory.OTHER
            )

            pattern = Pattern(
                title=f"{type_info.architectural_role.value.replace('_', ' ').title()}: {type_info.name}",
                description=self._generate_pattern_description(type_info),
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
        """Calculate quality score (1-10) based on metrics."""
        score = 10

        if type_info.lcom_score > 0.8:
            score -= 3
        elif type_info.lcom_score > 0.6:
            score -= 1

        if type_info.cyclomatic_complexity > 50:
            score -= 2
        elif type_info.cyclomatic_complexity > 30:
            score -= 1

        if type_info.lines_of_code > 500:
            score -= 2
        elif type_info.lines_of_code > 300:
            score -= 1

        if len(type_info.dependencies) > 15:
            score -= 2
        elif len(type_info.dependencies) > 10:
            score -= 1

        if type_info.architectural_role != ArchitecturalRole.UNKNOWN:
            score += 1

        return max(1, min(10, score))

    def sync_github_csharp_repo(
        self,
        repo_name: str,
        github_token: str,
        min_quality_score: int = 5,
        temp_dir: str = "/tmp/dna_repos"
    ) -> Dict:
        """
        Sync and analyze C# patterns from GitHub repository.

        Args:
            repo_name: Repository name (owner/repo format)
            github_token: GitHub personal access token
            min_quality_score: Minimum quality score for patterns (1-10)
            temp_dir: Temporary directory for cloning

        Returns:
            Dictionary with patterns and analysis statistics
        """
        from github_client import GitHubClient
        from pathlib import Path
        import shutil

        try:
            logger.info(f"Syncing GitHub C# repo: {repo_name}")

            # Clone repository
            client = GitHubClient(github_token)
            repo_path = client.clone_repository(repo_name, temp_dir)

            logger.info(f"Analyzing C# project at: {repo_path}")

            # Analyze C# project
            analysis_result = self.analyze_csharp_project(repo_path)

            # Convert types to patterns (types is a dict, convert to list)
            types_dict = analysis_result.get("types", {})
            types_list = list(types_dict.values()) if types_dict else []
            patterns = self.convert_to_dna_patterns(types_list)

            # Filter by quality score
            high_quality_patterns = [
                p for p in patterns
                if p.quality_score >= min_quality_score
            ]

            logger.info(
                f"Extracted {len(high_quality_patterns)} high-quality patterns "
                f"from {repo_name}"
            )

            return {
                "repository": repo_name,
                "total_patterns": len(patterns),
                "high_quality_patterns": len(high_quality_patterns),
                "patterns": high_quality_patterns,
                "audit_result": analysis_result.get("audit_result"),
                "violations": analysis_result.get("audit_result").violations
                if "audit_result" in analysis_result
                else []
            }

        except Exception as e:
            logger.error(f"Failed to sync GitHub repo {repo_name}: {e}", exc_info=True)
            raise

        finally:
            # Cleanup temporary directory
            repo_path = Path(temp_dir) / repo_name.split("/")[-1]
            if repo_path.exists():
                shutil.rmtree(repo_path, ignore_errors=True)


def audit_csharp_project_example(project_path: str, output_dir: str):
    """Example function showing complete workflow."""
    auditor = CSharpArchitecturalAuditor()

    print(f"Analyzing C# project at: {project_path}")
    results = auditor.analyze_csharp_project(project_path)

    print(f"Generating reports to: {output_dir}")
    auditor.generate_reports(results, output_dir)

    types = list(results["types"].values())
    patterns = auditor.convert_to_dna_patterns(types)
    print(f"Generated {len(patterns)} DNA patterns for storage")

    return results, patterns
