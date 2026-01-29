"""Integration module for C# Architectural Audit with existing DNA system.

This module bridges the advanced C# audit capabilities with the existing
Architectural DNA pattern extraction and storage system.
"""

import logging
import re
from pathlib import Path

from csharp_audit_engine import CSharpAuditEngine
from csharp_audit_reporter import CSharpAuditReporter
from csharp_semantic_analyzer import (
    ArchitecturalRole,
    CSharpSemanticAnalyzer,
    CSharpTypeInfo,
)
from models import Language, Pattern, PatternCategory
from pattern_extractor import PatternExtractor

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

    def analyze_csharp_file(self, file_path: str, content: str) -> list[CSharpTypeInfo]:
        """Analyze a C# file with full semantic enrichment."""
        if not content or not content.strip():
            logger.warning(f"Empty content for file: {file_path}")
            return []

        chunks = self.pattern_extractor.extract_chunks(
            content, file_path, Language.CSHARP
        )

        types_info = []

        for chunk in chunks:
            # Try to extract namespace from chunk context first, then from full content
            namespace = self._extract_namespace(chunk.context or "")
            if not namespace:
                namespace = self._extract_namespace(content)

            # Log if no namespace found (valid for file-scoped or global namespaces)
            if not namespace:
                logger.debug(
                    f"No namespace found for {chunk.name} in {file_path}. "
                    f"May use file-scoped or global namespace."
                )

            type_info = CSharpTypeInfo(
                name=chunk.name or "Unknown",
                namespace=namespace or "_global_",  # Use marker for empty namespaces
                file_path=file_path,
                type_kind=chunk.chunk_type,
                lines_of_code=chunk.end_line - chunk.start_line,
            )

            type_info.attributes = self.semantic_analyzer.extract_attributes(
                content, chunk.start_line
            )

            base_types = self._extract_base_types(chunk.content)
            type_info.architectural_role = (
                self.semantic_analyzer.determine_architectural_role(
                    type_info.attributes, type_info.name, base_types
                )
            )

            type_info.is_partial = "partial" in chunk.content
            type_info = self.semantic_analyzer.analyze_type(type_info, chunk.content)

            async_violations = self.semantic_analyzer.detect_async_over_sync(
                chunk.content
            )
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
        include_patterns: list[str] | None = None,
        batch_size: int = 100,
    ) -> dict:
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

        if not isinstance(project_path, str):
            raise TypeError(f"project_path must be string, got {type(project_path)}")

        project_root = Path(project_path)
        try:
            if not project_root.exists():
                raise FileNotFoundError(f"Project path does not exist: {project_path}")

            if not project_root.is_dir() and not project_root.is_file():
                raise ValueError(
                    f"Project path is neither file nor directory: {project_path}"
                )
        except FileNotFoundError:
            raise  # Re-raise FileNotFoundError as-is
        except (PermissionError, OSError) as e:
            logger.error(f"Cannot access project path {project_path}: {e}")
            raise ValueError(f"Cannot access project path: {e}") from e

        if project_root.is_file():
            project_root = project_root.parent

        cs_files = list(project_root.rglob("*.cs"))

        if not cs_files:
            logger.warning(f"No C# files found in {project_root}")
            return {
                "project_path": str(project_root),
                "files_analyzed": 0,
                "types_analyzed": 0,
                "total_types": 0,
                "types": {},
                "audit_result": None,
            }

        if include_patterns:
            cs_files = [
                f
                for f in cs_files
                if any(f.match(pattern) for pattern in include_patterns)
            ]

        logger.info(f"Analyzing {len(cs_files)} C# files in {project_root}")

        # Process files in batches to prevent memory exhaustion on large projects
        files_processed = 0
        files_skipped = 0

        for i in range(0, len(cs_files), batch_size):
            batch = cs_files[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(cs_files) + batch_size - 1) // batch_size

            logger.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} files)"
            )

            for cs_file in batch:
                try:
                    # Try multiple encodings
                    content = None
                    encoding_used = None

                    for encoding in ["utf-8", "utf-8-sig", "windows-1252"]:
                        try:
                            content = cs_file.read_text(encoding=encoding)
                            encoding_used = encoding
                            break
                        except UnicodeDecodeError:
                            continue
                        except (PermissionError, OSError) as e:
                            logger.warning(f"Cannot read {cs_file}: {e}")
                            break

                    if content is None:
                        logger.warning(f"Skipping {cs_file}: failed to decode with any encoding")
                        files_skipped += 1
                        continue

                    # Validate it looks like C# code
                    if not self._looks_like_csharp(content):
                        logger.warning(f"Skipping {cs_file}: content doesn't appear to be C# code")
                        files_skipped += 1
                        continue

                    logger.debug(f"Read {cs_file.name} using {encoding_used} encoding")

                    # Extract DI registrations from entry point files
                    if cs_file.name in ["Program.cs", "Startup.cs"]:
                        try:
                            self.semantic_analyzer.extract_di_registrations(
                                content, str(cs_file)
                            )
                            logger.info(f"Extracted DI registrations from {cs_file}")
                        except Exception as e:
                            logger.warning(
                                f"Failed to extract DI registrations from {cs_file}: {e}. "
                                f"Architectural role detection may be less accurate.",
                                exc_info=True
                            )
                            # Continue - DI mapping is optional, not critical

                    # Analyze file and register types directly to prevent memory accumulation
                    types = self.analyze_csharp_file(str(cs_file), content)
                    for type_info in types:
                        # Register in analyzer immediately instead of accumulating in list
                        self.semantic_analyzer.types[type_info.name] = type_info

                    files_processed += 1

                except Exception as e:
                    logger.error(
                        f"Unexpected error analyzing {cs_file}: {e}", exc_info=True
                    )
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
            "total_types": len(self.semantic_analyzer.types),
            "types": self.semantic_analyzer.types,
            "audit_result": audit_result,
        }

    def generate_reports(self, analysis_result: dict, output_dir: str):
        """Generate all report formats."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        audit_result = analysis_result["audit_result"]
        types = analysis_result["types"]

        json_path = output_path / "audit_report.json"
        self.reporter.generate_json_report(audit_result, str(json_path), types)
        logger.info(f"JSON report: {json_path}")

        md_path = output_path / "audit_report.md"
        self.reporter.generate_markdown_report(
            audit_result, types, str(md_path), self.audit_engine.config
        )
        logger.info(f"Markdown report: {md_path}")

        sarif_path = output_path / "audit_report.sarif"
        self.reporter.generate_sarif_report(audit_result, str(sarif_path))
        logger.info(f"SARIF report: {sarif_path}")

        self.reporter.print_console_summary(audit_result)

    def convert_to_dna_patterns(
        self, types: list[CSharpTypeInfo] | dict, source_repo: str = "csharp_audit"
    ) -> list[Pattern]:
        """Convert analyzed types to DNA Pattern format for storage."""
        # Convert dict to list if needed
        if isinstance(types, dict):
            types = list(types.values())

        if not types:
            logger.warning("No types provided to convert_to_dna_patterns")
            return []

        if not isinstance(types, list):
            raise TypeError(f"Expected list of CSharpTypeInfo, got {type(types)}")

        # Load threshold from configuration
        metrics_config = self.audit_engine.config.get("metrics", {})
        lcom_threshold = metrics_config.get("lcom_threshold", 0.8)

        patterns = []

        for type_info in types:
            # Skip God Objects (low cohesion) using config threshold
            if type_info.lcom_score > lcom_threshold:
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
                type_info.architectural_role, PatternCategory.OTHER
            )

            pattern = Pattern(
                title=f"{type_info.architectural_role.value.replace('_', ' ').title()}: {type_info.name}",
                description=self._generate_pattern_description(type_info),
                content=f"// Extracted from {type_info.file_path}\n// Namespace: {type_info.namespace}\n\n[Type definition would be here]",
                category=category,
                language=Language.CSHARP,
                quality_score=self._calculate_quality_score(type_info),
                source_repo=source_repo,
                source_path=type_info.file_path,
                use_cases=[
                    type_info.architectural_role.value,
                    type_info.type_kind,
                    f"lcom_{type_info.lcom_score:.2f}",
                    f"deps_{len(type_info.dependencies)}",
                ],
            )

            patterns.append(pattern)

        return patterns

    def _looks_like_csharp(self, content: str) -> bool:
        """Quick sanity check that content looks like C# code."""
        upper_content = content.upper()
        return (
            any(keyword in upper_content for keyword in ["CLASS", "NAMESPACE", "USING"])
            or upper_content.count("PUBLIC") > 0
            or upper_content.count("PRIVATE") > 0
        )

    def _extract_namespace(self, context: str) -> str:
        """Extract namespace from context string.

        Returns empty string if no namespace found (file-scoped or global namespace).
        Logs debug message for visibility.
        """
        if not context or not context.strip():
            return ""

        for line in context.split("\n"):
            if line.strip().startswith("namespace "):
                ns = (
                    line.strip()
                    .replace("namespace ", "")
                    .rstrip(";")
                    .rstrip("{")
                    .strip()
                )
                if ns:
                    return ns

        # No namespace found - this is valid for file-scoped or global namespaces
        return ""

    def _extract_base_types(self, content: str) -> list[str]:
        """Extract base types/interfaces from class declaration."""
        match = re.search(r":\s*([^{]+)", content)
        if match:
            bases = match.group(1).split(",")
            return [b.strip() for b in bases]
        return []

    def _generate_pattern_description(self, type_info: CSharpTypeInfo) -> str:
        """Generate human-readable pattern description."""
        parts = [
            f"A {type_info.type_kind} from the {type_info.namespace} namespace",
            f"serving as a {type_info.architectural_role.value.replace('_', ' ')}.",
        ]

        if type_info.attributes:
            attr_names = [a.name for a in type_info.attributes]
            parts.append(f"Decorated with attributes: {', '.join(attr_names)}.")

        parts.append(
            f"Contains {len(type_info.members)} members with "
            f"LCOM score of {type_info.lcom_score:.2f}."
        )

        if type_info.dependencies:
            parts.append(f"Depends on {len(type_info.dependencies)} types.")

        return " ".join(parts)

    def _calculate_quality_score(self, type_info: CSharpTypeInfo) -> int:
        """Calculate quality score (1-10) based on metrics."""
        # Load thresholds from configuration
        metrics_config = self.audit_engine.config.get("metrics", {})
        dependencies_config = self.audit_engine.config.get("dependencies", {})

        lcom_threshold = metrics_config.get("lcom_threshold", 0.8)
        loc_threshold = metrics_config.get("loc_threshold", 500)
        max_dependencies = dependencies_config.get("max_per_class", 7)

        score = 10

        # LCOM penalties (using config thresholds)
        if type_info.lcom_score > lcom_threshold:
            score -= 3
        elif type_info.lcom_score > (lcom_threshold * 0.75):
            score -= 1

        # Cyclomatic complexity penalties (using thresholds derived from config)
        complexity_critical = metrics_config.get("cyclomatic_complexity_limit", 15) * 3
        complexity_warning = metrics_config.get("cyclomatic_complexity_limit", 15) * 2
        if type_info.cyclomatic_complexity > complexity_critical:
            score -= 2
        elif type_info.cyclomatic_complexity > complexity_warning:
            score -= 1

        # LOC penalties (using config thresholds)
        if type_info.lines_of_code > loc_threshold:
            score -= 2
        elif type_info.lines_of_code > (loc_threshold * 0.6):
            score -= 1

        # Dependencies penalties (using config thresholds)
        max_deps_critical = max_dependencies * 2
        max_deps_warning = max_dependencies + 3
        if len(type_info.dependencies) > max_deps_critical:
            score -= 2
        elif len(type_info.dependencies) > max_deps_warning:
            score -= 1

        if type_info.architectural_role != ArchitecturalRole.UNKNOWN:
            score += 1

        return max(1, min(10, score))

    def sync_github_csharp_repo(
        self,
        repo_name: str,
        github_token: str,
        min_quality_score: int = 5,
        temp_dir: str = "/tmp/dna_repos",
    ) -> dict:
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
        import shutil
        from pathlib import Path

        from github_client import GitHubClient

        try:
            logger.info(f"Syncing GitHub C# repo: {repo_name}")

            # Get repository
            client = GitHubClient(github_token)
            try:
                repo = client.get_repository(repo_name)
            except Exception as e:
                logger.error(f"Failed to fetch repository {repo_name}: {e}")
                raise ValueError(
                    f"Repository {repo_name} not found or inaccessible"
                ) from e

            if repo is None:
                raise ValueError(
                    f"Repository {repo_name} returned None from GitHub API"
                )

            repo_path = getattr(repo, "clone_url", None)
            if not repo_path:
                raise ValueError(
                    f"Could not get clone URL for repository {repo_name}. "
                    f"Repository may be empty or inaccessible."
                )

            logger.info(f"Analyzing C# project at: {repo_path}")

            # Analyze C# project
            try:
                analysis_result = self.analyze_csharp_project(repo_path)
            except Exception as e:
                logger.error(f"Failed to analyze project at {repo_path}: {e}", exc_info=True)
                raise ValueError(f"C# project analysis failed: {e}") from e

            if not isinstance(analysis_result, dict):
                raise TypeError(f"analyze_csharp_project returned {type(analysis_result)}, expected dict")

            if "types" not in analysis_result:
                raise ValueError("analyze_csharp_project result missing 'types' key")

            # Convert types to patterns (types is a dict, convert to list)
            types_dict = analysis_result.get("types", {})
            if not isinstance(types_dict, dict):
                raise TypeError(f"'types' in result is {type(types_dict)}, expected dict")
            types_list = list(types_dict.values()) if types_dict else []
            patterns = self.convert_to_dna_patterns(types_list)

            # Filter by quality score
            high_quality_patterns = [
                p for p in patterns if p.quality_score >= min_quality_score
            ]

            logger.info(
                f"Extracted {len(high_quality_patterns)} high-quality patterns "
                f"from {repo_name}"
            )

            audit_result = analysis_result.get("audit_result")
            violations = audit_result.violations if audit_result is not None else []

            return {
                "repository": repo_name,
                "total_patterns": len(patterns),
                "high_quality_patterns": len(high_quality_patterns),
                "patterns": high_quality_patterns,
                "audit_result": audit_result,
                "violations": violations,
            }

        except Exception as e:
            logger.error(f"Failed to sync GitHub repo {repo_name}: {e}", exc_info=True)
            raise

        finally:
            # Cleanup temporary directory with robust error handling
            repo_path = Path(temp_dir) / repo_name.split("/")[-1]
            if repo_path.exists():
                try:
                    shutil.rmtree(str(repo_path))
                    logger.debug(f"Successfully cleaned up: {repo_path}")
                except PermissionError:
                    logger.warning(f"Temp directory locked, retrying: {repo_path}")
                    try:
                        import time
                        time.sleep(0.5)
                        shutil.rmtree(str(repo_path))
                        logger.debug(f"Cleanup succeeded on retry: {repo_path}")
                    except Exception as retry_error:
                        logger.error(f"Failed to clean up {repo_path}: {retry_error}")
                        logger.warning(f"Manual cleanup required: rm -rf {repo_path}")
                except OSError as e:
                    logger.error(f"Cannot clean up {repo_path}: {e}")
                    logger.warning(f"Manual cleanup required: rm -rf {repo_path}")


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
