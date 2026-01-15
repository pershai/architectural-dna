"""Project scaffolding based on DNA patterns."""

import logging
import os
from pathlib import Path
from typing import Optional

from qdrant_client import QdrantClient
from google import genai

from models import ProjectStructure
from utils import parse_json_from_llm_response

logger = logging.getLogger(__name__)


class ProjectScaffolder:
    """Generates project structures based on DNA patterns."""
    
    SCAFFOLD_PROMPT = '''You are a senior software architect. Generate a project structure for a new {project_type} project.

Project Name: {project_name}
Tech Stack: {tech_stack}
Project Type: {project_type}

Reference patterns from the codebase (use these as inspiration for style and structure):

{patterns}

Generate a complete project structure with file contents. Follow these guidelines:
1. Use the patterns above as reference for coding style and architecture
2. Include proper configuration files for the tech stack
3. Add a README.md with setup instructions
4. Include basic error handling and logging
5. Follow the same naming conventions as the reference patterns

Respond with a JSON object (no markdown, just raw JSON):
{{
    "directories": ["list", "of", "directory", "paths"],
    "files": {{
        "path/to/file.py": "file content here",
        "another/file.js": "file content here"
    }}
}}

Generate production-ready scaffolding with proper structure. Include at least:
- Main application entry point
- Configuration handling
- Basic project structure (src/, tests/, etc.)
- Package/dependency file (requirements.txt, package.json, etc.)
- README.md'''

    def __init__(
        self, 
        qdrant_client: QdrantClient, 
        collection_name: str,
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize the scaffolder.
        
        Args:
            qdrant_client: Qdrant client for pattern retrieval
            collection_name: Name of the Qdrant collection
            gemini_api_key: Gemini API key (uses env var if not provided)
        """
        self.qdrant = qdrant_client
        self.collection_name = collection_name
        
        api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self.model = "gemini-2.0-flash"
        else:
            self.client = None
            self.model = None
    
    def gather_patterns(
        self, 
        project_type: str, 
        tech_stack: list[str],
        limit: int = 5
    ) -> list[dict]:
        """
        Retrieve relevant patterns for the project.
        
        Args:
            project_type: Type of project (api, cli, library, web-app)
            tech_stack: List of technologies
            limit: Maximum patterns to retrieve
        
        Returns:
            List of pattern data from Qdrant
        """
        # Build search query from project type and tech stack
        query = f"{project_type} {' '.join(tech_stack)}"
        
        # Add context based on project type
        type_context = {
            "api": "REST API endpoint controller service",
            "cli": "command line argument parser",
            "library": "module package utility",
            "web-app": "web application frontend backend",
        }
        query += " " + type_context.get(project_type, "")
        
        try:
            results = self.qdrant.query(
                collection_name=self.collection_name,
                query_text=query,
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Error querying patterns: {e}")
            return []
    
    def generate_structure(
        self, 
        project_name: str,
        project_type: str,
        tech_stack: list[str],
        patterns: list[dict]
    ) -> Optional[ProjectStructure]:
        """
        Generate project structure using LLM.
        
        Args:
            project_name: Name for the new project
            project_type: Type of project
            tech_stack: Technologies to use
            patterns: Reference patterns from DNA bank
        
        Returns:
            ProjectStructure with directories and files
        """
        if not self.client:
            return self._generate_basic_structure(project_name, project_type, tech_stack)
        
        # Format patterns for the prompt
        pattern_text = self._format_patterns(patterns)
        
        prompt = self.SCAFFOLD_PROMPT.format(
            project_name=project_name,
            project_type=project_type,
            tech_stack=", ".join(tech_stack),
            patterns=pattern_text
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return self._parse_structure(project_name, response.text)
        except Exception as e:
            logger.warning(f"Error generating structure with LLM: {e}, using basic structure")
            return self._generate_basic_structure(project_name, project_type, tech_stack)
    
    def _format_patterns(self, patterns: list[dict]) -> str:
        """Format patterns for inclusion in prompt."""
        if not patterns:
            return "No reference patterns available."
        
        formatted = []
        for i, pattern in enumerate(patterns, 1):
            metadata = pattern.metadata if hasattr(pattern, 'metadata') else {}
            document = pattern.document if hasattr(pattern, 'document') else str(pattern)
            
            title = metadata.get('title', metadata.get('description', f'Pattern {i}'))
            language = metadata.get('language', 'unknown')
            
            formatted.append(f"### Pattern {i}: {title} ({language})\n```\n{document[:500]}...\n```\n")
        
        return "\n".join(formatted)
    
    def _parse_structure(
            self,
            project_name: str,
            response_text: str
    ) -> Optional[ProjectStructure]:
        """Parse LLM response into ProjectStructure."""
        data = parse_json_from_llm_response(response_text)
        if not data:
            return None

        try:
            return ProjectStructure(
                name=project_name,
                directories=data.get("directories", []),
                files=data.get("files", {})
            )
        except (KeyError, TypeError) as e:
            logger.error(f"Error constructing ProjectStructure from data: {e}")
            return None
    
    def _generate_basic_structure(
        self, 
        project_name: str, 
        project_type: str, 
        tech_stack: list[str]
    ) -> ProjectStructure:
        """Generate a basic structure without LLM (fallback)."""
        # Detect primary language
        if "python" in [t.lower() for t in tech_stack]:
            return self._python_structure(project_name, project_type, tech_stack)
        elif any(t.lower() in ["typescript", "javascript", "node"] for t in tech_stack):
            return self._node_structure(project_name, project_type, tech_stack)
        elif "java" in [t.lower() for t in tech_stack]:
            return self._java_structure(project_name, project_type, tech_stack)
        else:
            return self._generic_structure(project_name, project_type, tech_stack)
    
    def _python_structure(self, name: str, ptype: str, stack: list[str]) -> ProjectStructure:
        """Generate Python project structure."""
        dirs = ["src", "tests", "docs"]
        files = {
            "README.md": f"# {name}\n\n{ptype.title()} built with {', '.join(stack)}\n",
            "requirements.txt": "# Project dependencies\n",
            "setup.py": f'''from setuptools import setup, find_packages

setup(
    name="{name}",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={{"": "src"}},
)
''',
            "src/__init__.py": "",
            "src/main.py": f'''"""Main entry point for {name}."""

def main():
    print("Hello from {name}!")

if __name__ == "__main__":
    main()
''',
            "tests/__init__.py": "",
            "tests/test_main.py": '''"""Tests for main module."""

def test_placeholder():
    assert True
''',
        }
        
        # Add FastAPI specifics
        if "fastapi" in [s.lower() for s in stack]:
            files["src/main.py"] = '''"""FastAPI application."""

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
'''
            files["requirements.txt"] = "fastapi>=0.100.0\nuvicorn>=0.23.0\n"
        
        return ProjectStructure(name=name, directories=dirs, files=files)
    
    def _node_structure(self, name: str, ptype: str, stack: list[str]) -> ProjectStructure:
        """Generate Node.js project structure."""
        dirs = ["src", "tests"]
        files = {
            "README.md": f"# {name}\n\n{ptype.title()} built with {', '.join(stack)}\n",
            "package.json": f'''{{
  "name": "{name}",
  "version": "0.1.0",
  "main": "src/index.js",
  "scripts": {{
    "start": "node src/index.js",
    "test": "jest"
  }}
}}
''',
            "src/index.js": f'''// Main entry point for {name}

console.log("Hello from {name}!");
''',
        }
        return ProjectStructure(name=name, directories=dirs, files=files)
    
    def _java_structure(self, name: str, ptype: str, stack: list[str]) -> ProjectStructure:
        """Generate Java project structure."""
        package_path = f"src/main/java/com/{name.replace('-', '').lower()}"
        dirs = [
            "src/main/java",
            "src/main/resources", 
            "src/test/java",
            package_path
        ]
        files = {
            "README.md": f"# {name}\n\n{ptype.title()} built with {', '.join(stack)}\n",
            "pom.xml": f'''<?xml version="1.0" encoding="UTF-8"?>
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.{name.replace('-', '').lower()}</groupId>
    <artifactId>{name}</artifactId>
    <version>0.1.0</version>
</project>
''',
            f"{package_path}/Application.java": f'''package com.{name.replace('-', '').lower()};

public class Application {{
    public static void main(String[] args) {{
        System.out.println("Hello from {name}!");
    }}
}}
''',
        }
        return ProjectStructure(name=name, directories=dirs, files=files)
    
    def _generic_structure(self, name: str, ptype: str, stack: list[str]) -> ProjectStructure:
        """Generate generic project structure."""
        return ProjectStructure(
            name=name,
            directories=["src", "docs", "tests"],
            files={
                "README.md": f"# {name}\n\n{ptype.title()} built with {', '.join(stack)}\n",
            }
        )
    
    def write_project(self, output_dir: Path, structure: ProjectStructure) -> Path:
        """
        Write the generated project to disk.
        
        Args:
            output_dir: Base directory to create project in
            structure: ProjectStructure with dirs and files
        
        Returns:
            Path to the created project directory
        """
        project_dir = output_dir / structure.name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create directories
        for dir_path in structure.directories:
            (project_dir / dir_path).mkdir(parents=True, exist_ok=True)
        
        # Create files
        for file_path, content in structure.files.items():
            full_path = project_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
        
        return project_dir
