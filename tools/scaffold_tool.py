"""Project scaffolding tool for generating new projects from DNA patterns."""

from pathlib import Path

from .base import BaseTool


class ScaffoldTool(BaseTool):
    """Tool for scaffolding new projects using DNA bank patterns."""

    def scaffold_project(
        self,
        project_name: str,
        project_type: str,
        tech_stack: str,
        output_dir: str | None = None,
    ) -> str:
        """
        Scaffold a new project using best practices from the DNA bank.

        Searches for relevant patterns based on the project type and tech stack,
        then generates a complete project structure with files.

        Args:
            project_name: Name for the new project (will be the directory name)
            project_type: Type of project - "api", "cli", "library", or "web-app"
            tech_stack: Comma-separated technologies (e.g., "python, fastapi, postgresql")
            output_dir: Directory to create the project in (defaults to ./generated_projects)

        Returns:
            Path to the created project and summary of what was generated
        """
        try:
            scaffolder = self.get_scaffolder()

            # Parse tech stack
            stack = [t.strip() for t in tech_stack.split(",")]

            # Get output directory
            if output_dir:
                out_path = Path(output_dir)
            else:
                out_path = Path(
                    self.config.get("scaffolding", {}).get(
                        "output_dir", "./generated_projects"
                    )
                )

            self.logger.info(
                f"Scaffolding project: {project_name} "
                f"(Type: {project_type}, Stack: {', '.join(stack)})"
            )

            # Gather relevant patterns from DNA bank
            patterns = scaffolder.gather_patterns(project_type, stack, limit=5)
            self.logger.info(f"Found {len(patterns)} relevant patterns")

            # Generate project structure
            structure = scaffolder.generate_structure(
                project_name=project_name,
                project_type=project_type,
                tech_stack=stack,
                patterns=patterns,
            )

            if not structure:
                return "[ERROR] Failed to generate project structure"

            # Write project to disk
            project_path = scaffolder.write_project(out_path, structure)

            # Build summary
            output = "[OK] Project scaffolded successfully!\n\n"
            output += f"**Location:** `{project_path}`\n\n"
            output += f"**Structure:**\n```\n{project_name}/\n"

            for dir_path in sorted(structure.directories):
                output += f"├── {dir_path}/\n"
            for file_path in sorted(structure.files.keys()):
                output += f"├── {file_path}\n"

            output += "```\n\n"
            output += f"**Files created:** {len(structure.files)}\n"
            output += f"**Based on:** {len(patterns)} patterns from DNA bank"

            return output

        except Exception as e:
            return f"[ERROR] Error scaffolding project: {e}"
