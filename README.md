# Architectural DNA 🧬

[![CI](https://github.com/pershai/architectural-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/pershai/architectural-dna/actions/workflows/ci.yml)
[![Docker](https://github.com/pershai/architectural-dna/actions/workflows/docker.yml/badge.svg)](https://github.com/pershai/architectural-dna/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

A powerful MCP (Model Context Protocol) server that extracts, analyzes, and stores code patterns from your GitHub repositories, enabling AI-powered project scaffolding based on your team's proven architectural patterns.

## What It Does

Architectural DNA helps you:

1. **Extract Code Patterns** - Automatically parses your GitHub repositories to identify reusable code patterns
2. **Analyze with AI** - Uses Google Gemini to understand and categorize patterns (design patterns, best practices, utilities)
3. **Store in Vector DB** - Indexes patterns in Qdrant for fast semantic search
4. **Generate Projects** - Scaffolds new projects based on your existing patterns and best practices

## Features

- 🔍 **Multi-language Support** - Python, Java, JavaScript/TypeScript, C#, Go
- 🎯 **C# Architectural Intelligence** - Advanced semantic analysis, DI mapping, LCOM metrics, async-over-sync detection
- 🤖 **LLM-Powered Analysis** - Intelligent pattern recognition and quality scoring
- 📊 **Vector Search** - Semantic search across all your code patterns
- 🏗️ **Smart Scaffolding** - Generate new projects that follow your team's conventions
- 🔌 **MCP Integration** - Works with any MCP-compatible AI client (Claude Desktop, IDEs)
- 📋 **Architectural Auditing** - 9 audit rules for C# projects with JSON/Markdown/SARIF reports

## Architecture

```
GitHub Repos → Pattern Extraction (AST) → LLM Analysis → Vector DB (Qdrant) → RAG Scaffolding
```

The system implements a complete RAG (Retrieval-Augmented Generation) pipeline:
- **Extraction**: Parses code using tree-sitter AST parsers
- **Analysis**: Google Gemini identifies patterns and assigns quality scores
- **Storage**: Qdrant vector database with configurable code-optimized embeddings
- **Generation**: LLM generates new projects using relevant patterns as context

## Advanced Features

### C# Architectural Intelligence

The system provides **enterprise-grade C# analysis** with unique capabilities not found in traditional linters:

#### 🧬 Semantic Analysis
- **Attribute-based Role Detection**: Automatically categorizes classes as Controllers, Services, Repositories, Handlers, etc.
- **Dependency Injection Mapping**: Extracts `AddScoped`, `AddTransient`, `AddSingleton` from `Program.cs`/`Startup.cs` and links interfaces to implementations
- **Partial Class Aggregation**: Merges partial class definitions across files with automatic metrics summing

#### 📊 Advanced Metrics
- **LCOM (Lack of Cohesion in Methods)**: Detects God Objects by measuring class cohesion (0.0-1.0 scale)
- **Cyclomatic Complexity**: Per-method complexity tracking with configurable thresholds
- **Instability Index**: Namespace-level stability analysis for architectural layering

#### 🔍 Architectural Audit Rules (9 Rules)
| Rule ID | Name | Description |
|---------|------|-------------|
| `ARCH_001` | Cyclic Dependencies | Detects namespace-level circular dependencies |
| `ARCH_002` | Dependency Direction | Enforces clean architecture (Domain←Application←Infrastructure←Web) |
| `DESIGN_001` | God Object Detection | Flags classes with high LCOM (>0.8), high LOC (>500), or excessive dependencies |
| `DATA_001` | SQL Access Restrictions | Prevents direct SQL in Application/Web layers (MediatR compliance) |
| `DATA_002` | Repository Interfaces | Ensures repositories implement interfaces |
| `MEDIATR_001` | Handler Interface | Validates MediatR handler implementations |
| `ATTR_001` | Controller Attributes | Ensures `[ApiController]` and `[Route]` on controllers |
| `ASYNC_001` | Async Void | Warns about `async void` methods (except event handlers) |
| `ASYNC_002` | Async Over Sync | Detects `.Result`, `.Wait()`, `Task.WaitAll` (deadlock risks) |

#### 🎨 Design Pattern Recognition (18 Patterns)
Automatically detects:
- **Creational**: Singleton, Factory, Builder, Prototype
- **Structural**: Adapter, Decorator, Facade, Proxy
- **Behavioral**: Observer, Strategy, Command, Chain of Responsibility, State
- **Enterprise**: Repository, Unit of Work, CQRS, Event Sourcing, Pub/Sub

#### 📋 Multi-Format Reports
- **JSON**: CI/CD integration, automated analysis
- **Markdown**: Human-readable documentation with violation summaries
- **SARIF**: IDE integration (Visual Studio Code, Visual Studio) for inline warnings

#### 🚀 Example Usage
```python
# Via MCP tool
analyze_csharp_project(
    project_path="/path/to/csharp/project",
    repo_name="mycompany/myproject",
    output_dir="audit_reports"
)

# Returns:
# ✅ Total Types Analyzed: 127
# 🔴 ERROR: 3 violations
# ⚠️ WARNING: 12 violations
# 📁 Reports: JSON, Markdown, SARIF
```

**Configuration** (`config.yaml`):
```yaml
csharp_audit:
  metrics:
    lcom_threshold: 0.8          # God Object detection
    loc_threshold: 500           # Large class detection
    cyclomatic_complexity_limit: 15

  dependencies:
    max_per_class: 7             # Dependency injection limit
    max_per_namespace: 50

  patterns:
    include_partial_classes: true
    extract_di_registrations: true
    detect_async_patterns: true
    detect_design_patterns: true
```

**Benefits**:
- ✅ Enforce architectural layering (Clean Architecture, Onion Architecture)
- ✅ Prevent common C# anti-patterns (async-over-sync, God Objects)
- ✅ Ensure MediatR/CQRS compliance
- ✅ IDE integration via SARIF (inline warnings)
- ✅ CI/CD integration via JSON reports

### Code-Optimized Embeddings

The system uses **code-specific embedding models** that understand programming syntax and semantics better than general-purpose models:

**Supported Models:**
- `jinaai/jina-embeddings-v2-base-code` (768d) - **Recommended** for code
- `BAAI/bge-base-en-v1.5` (768d) - Good all-around performance
- `BAAI/bge-small-en-v1.5` (384d) - Lightweight and fast
- `nomic-ai/nomic-embed-text-v1.5` (768d) - Newest high-quality model
- `sentence-transformers/all-MiniLM-L6-v2` (384d) - Fast inference

**Smart Code Preprocessing:**
- Normalizes whitespace while preserving code structure
- Retains comments and docstrings for better semantic understanding
- Preserves code-specific tokens (identifiers, keywords)

**Intelligent Chunking:**
- Respects code structure (functions, classes, modules)
- Configurable chunk size with overlap
- Prevents splitting logical code blocks

Configure in [config.yaml](config.yaml):
```yaml
embeddings:
  provider: "fastembed"
  model: "jinaai/jina-embeddings-v2-base-code"
  chunking:
    enabled: true
    max_chunk_size: 512
    chunk_overlap: 50
    strategy: "smart"
```

### Hybrid Search

Combines **semantic (vector) search** with **keyword matching** for more accurate results:

- **Semantic Search (70%)**: Finds patterns with similar meaning/purpose
- **Keyword Search (30%)**: Ensures exact term matches are prioritized
- **Automatic Reranking**: Intelligently combines both scores

This means queries like "retry decorator" will find:
1. Patterns with "retry" and "decorator" keywords (exact match)
2. Patterns about "error handling" and "resilience" (semantic similarity)
3. Ranked by combined relevance

Configure in [config.yaml](config.yaml):
```yaml
search:
  hybrid_enabled: true
  semantic_weight: 0.7
  keyword_weight: 0.3
```

**Get embedding info:**
```python
# Via MCP tool
get_embedding_info()
# Returns current model, vector size, and configuration
```

### GitHub API Caching

The system includes an intelligent caching layer for GitHub API responses to reduce API calls and improve performance:

**Cache Types and TTLs:**
- **Repository List** (5 min): Cached since repo lists change infrequently
- **File Tree** (10 min): Directory structure is relatively stable
- **File Content** (1 hour): Content by SHA is immutable, safe to cache longer

**Features:**
- **LRU Eviction**: Automatically removes least-recently-used entries when cache is full
- **Disk Persistence**: Optionally saves cache to disk for cross-session persistence
- **Per-Request Control**: Each API method accepts `use_cache=False` to bypass cache
- **Selective Invalidation**: Clear cache for specific repos or all at once

Configure in [config.yaml](config.yaml):
```yaml
github:
  cache:
    enabled: true
    ttl_repo_list: 300      # 5 minutes
    ttl_file_tree: 600      # 10 minutes
    ttl_file_content: 3600  # 1 hour
    max_size: 1000          # Maximum cache entries
    cache_dir: ".github_cache"  # null to disable disk caching
```

**Benefits:**
- Faster re-syncs when re-processing repositories
- Reduced GitHub API rate limit consumption
- Improved performance for large codebases
- Persistent cache survives container restarts (Docker volume)

## Installation

Choose your deployment method:

### 🐳 Option 1: Docker (Recommended)

**Easiest way to get started!** Runs as a standalone SSE server.

```bash
# Clone and start
git clone https://github.com/pershai/architectural-dna.git
cd architectural-dna
docker-compose up -d
```

The server runs at: **http://localhost:8080/sse**

**Connect your AI assistant** - See [MCP_SETUP.md](MCP_SETUP.md) for:
- 🟣 Cursor
- 🔵 Gemini Code Assist / Antigravity
- 🟢 Windsurf / Cascade
- 🟠 Claude Desktop
- 🔴 VS Code Continue

**Benefits:**
- ✅ Zero dependency management
- ✅ No local file paths needed
- ✅ Works with any MCP client
- ✅ Credentials via headers
- ✅ One-command deployment

### 🐍 Option 2: Local Python Installation

**Prerequisites:**
- Python 3.11+
- GitHub Personal Access Token
- Google Gemini API Key
- Qdrant (local or cloud)

### Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd architectural-dna
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

For reproducible installations (recommended):
```bash
pip install -r requirements.lock
```

Or to install latest compatible versions:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# GitHub Integration
GITHUB_TOKEN=ghp_your_github_token_here

# Google Gemini LLM
GEMINI_API_KEY=your_gemini_api_key_here

# Qdrant Vector Database (optional if running locally)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Leave empty for local instance
```

**Getting your tokens:**
- GitHub: https://github.com/settings/tokens (requires `repo` scope)
- Gemini: https://aistudio.google.com/app/apikey

5. **Start Qdrant (if running locally)**

Using Docker:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

Or install locally: https://qdrant.tech/documentation/quick-start/

6. **Configure the system**

Edit `config.yaml` to customize:
- Qdrant connection settings
- **Embedding model and configuration** (code-optimized models, chunking, preprocessing)
- **Hybrid search settings** (semantic vs keyword weight)
- Gemini model selection
- Pattern extraction rules
- Quality thresholds

See [Advanced Features](#advanced-features) for details on embedding models and hybrid search configuration.

## Usage

### Running the MCP Server

```bash
python dna_server.py
```

The server exposes several MCP tools that can be called by AI assistants:

### Available Tools

#### 1. `store_pattern` - Manually add a code pattern
```json
{
  "content": "def retry_on_failure(max_attempts=3): ...",
  "title": "Retry Decorator",
  "description": "Decorator for automatic retry logic",
  "category": "utility",
  "language": "python",
  "quality_score": 8
}
```

#### 2. `search_dna` - Query patterns by semantic similarity
```json
{
  "query": "authentication middleware patterns",
  "limit": 5,
  "min_quality": 7,
  "language": "python",
  "category": "architecture"
}
```

#### 3. `list_my_repos` - List accessible GitHub repositories
```json
{
  "include_private": true
}
```

#### 4. `sync_github_repo` - Index patterns from a repository
```json
{
  "repo_name": "myorg/myproject",
  "analyze": true,
  "min_quality": 6
}
```

#### 5. `scaffold_project` - Generate a new project
```json
{
  "project_name": "my-new-api",
  "project_type": "REST API",
  "tech_stack": "Python, FastAPI, PostgreSQL"
}
```

#### 6. `get_dna_stats` - View database statistics
```json
{}
```

#### 7. `get_embedding_info` - View embedding configuration
```json
{}
```

Returns information about:
- Current embedding model and provider
- Vector dimensions
- Chunking configuration
- Preprocessing settings
- All supported embedding models

#### 8. `analyze_csharp_project` - Analyze C# project architecture
```json
{
  "project_path": "/path/to/csharp/project",
  "repo_name": "mycompany/myproject",
  "output_dir": "csharp_audit_reports"
}
```

Performs comprehensive C# architectural analysis:
- Extracts patterns from .cs files
- Runs 9 architectural audit rules
- Detects 18 design patterns
- Calculates LCOM and complexity metrics
- Generates JSON/Markdown/SARIF reports

**Example Output**:
```
✅ C# Project Analysis Complete

📊 Summary:
  • Total Types Analyzed: 127
  • Total Violations: 15
  • Violations by Severity:
    🔴 ERROR: 3
    ⚠️ WARNING: 12
    ℹ️ INFO: 0

📁 Reports Generated:
  • JSON: csharp_audit_reports/myproject_audit.json
  • Markdown: csharp_audit_reports/myproject_audit.md
  • SARIF (IDE): csharp_audit_reports/myproject_audit.sarif

🎯 Top 5 Rules Violated:
  1. DESIGN_001 (God Objects): 5 violations
  2. ASYNC_002 (Async Over Sync): 4 violations
  3. ARCH_002 (Dependency Direction): 3 violations
  4. DATA_001 (SQL in Application Layer): 2 violations
  5. ATTR_001 (Missing Controller Attributes): 1 violation
```

### Command-Line Utilities

**Discover DNA from local directory:**
```bash
python discover_dna.py /path/to/your/codebase
```

**List your GitHub repositories:**
```bash
python manual_list_repos.py
```

### Integration with MCP Clients

First, start the Docker server:
```bash
docker-compose up -d
```

Then add to your MCP client config:

#### Claude Desktop / Cursor / Windsurf

Config location:
- **Claude Desktop**: `claude_desktop_config.json`
- **Cursor**: `%APPDATA%\Cursor\User\globalStorage\cursor.mcp\config.json`
- **Windsurf**: `%APPDATA%\Windsurf\User\globalStorage\cascade.mcp\config.json`

```json
{
  "mcpServers": {
    "architectural-dna": {
      "transport": "sse",
      "url": "http://localhost:8080/sse",
      "headers": {
        "X-GITHUB-TOKEN": "your_github_token",
        "X-GEMINI-API-KEY": "your_gemini_api_key"
      }
    }
  }
}
```

#### Gemini Code Assist / Antigravity

Config location: `~/.gemini/antigravity/mcp_config.json`

```json
{
  "mcpServers": {
    "architectural-dna": {
      "serverUrl": "http://localhost:8080/sse",
      "headers": {
        "X-GITHUB-TOKEN": "your_github_token",
        "X-GEMINI-API-KEY": "your_gemini_api_key"
      }
    }
  }
}
```

### Claude Code Skill

For Claude Code users, a [SKILL.md](SKILL.md) file provides workflow guidance to help the LLM make better decisions about which tools to use and when.

**Install the skill:**
```bash
claude skill add ./SKILL.md
```

**What the skill provides:**
- **Tool selection guidance** - When to use `batch_sync_repo` vs `sync_github_repo`
- **Documented workflows** - First-time setup, adding repos, searching, maintenance
- **Best practices** - What to always do, never do, and error recovery
- **Tool relationships** - How the 12 tools connect and depend on each other

**Example workflows documented:**
1. First-time DNA bank setup
2. Adding a new repository
3. Finding and using patterns
4. Maintenance after sync issues
5. Improving pattern quality (recategorization)

## Configuration

### config.yaml Structure

```yaml
qdrant:
  url: "http://localhost:6333"
  collection_name: "code_patterns"
  embedding_model: "BAAI/bge-small-en-v1.5"
  vector_size: 384

gemini:
  model: "gemini-2.0-flash-exp"
  analysis_enabled: true

extraction:
  min_chunk_lines: 5
  max_chunk_lines: 150
  min_quality_score: 5
```

### Supported Languages

| Language | Extensions | AST Parser |
|----------|-----------|------------|
| Python | .py | tree-sitter-python |
| Java | .java | tree-sitter-java |
| JavaScript/TypeScript | .js, .ts, .jsx, .tsx | tree-sitter-javascript |
| **C#** | .cs | Regex-based | **Architectural auditing, DI mapping, LCOM metrics, 18 design patterns** |
| Go | .go | Semantic chunking |

### Pattern Categories

- `architecture` - High-level design patterns (MVC, microservices, etc.)
- `design_pattern` - Classical design patterns (Singleton, Factory, etc.)
- `best_practice` - Coding standards and conventions
- `utility` - Helper functions and utilities
- `security` - Security implementations (auth, validation, etc.)
- `performance` - Optimization techniques
- `other` - Miscellaneous patterns

## Examples

### Example 1: Index Your Team's Codebase

```python
# In Claude Desktop or any MCP client:
"Sync my repository myteam/api-backend and analyze patterns with min quality 7"

# The server will:
# 1. Clone/fetch the repository
# 2. Extract code chunks using AST parsing
# 3. Analyze each chunk with Gemini
# 4. Store high-quality patterns in Qdrant
```

### Example 2: Search for Patterns

```python
"Search DNA for authentication middleware patterns in Python"

# Returns:
# - OAuth2 middleware implementation (score: 9)
# - JWT token validation (score: 8)
# - Rate limiting decorator (score: 7)
```

### Example 3: Generate a New Project

```python
"Scaffold a new FastAPI project called 'user-service' using my team's patterns"

# Generates:
# - Project structure following your conventions
# - Configuration files
# - Authentication using your patterns
# - Error handling matching your style
# - README and setup instructions
```

### Example 4: Audit C# Project Architecture

```python
"Analyze the C# project at /path/to/MyProject.API"

# The server will:
# 1. Parse all .cs files in the project
# 2. Extract architectural patterns (Controllers, Services, Repositories)
# 3. Calculate metrics (LCOM, Cyclomatic Complexity)
# 4. Run 9 architectural audit rules
# 5. Detect 18 design patterns
# 6. Generate reports in 3 formats (JSON, Markdown, SARIF)

# Returns:
# ✅ Total Types Analyzed: 127
# 🔴 ERROR: 3 violations (God Objects, SQL in Application Layer)
# ⚠️ WARNING: 12 violations (Missing Interfaces, Async-over-Sync)
# 📁 Reports: JSON, Markdown, SARIF (for Visual Studio/VS Code)
```

**Common C# Violations Detected**:
- 🔴 **God Objects**: Classes with LCOM > 0.8, LOC > 500, or >7 dependencies
- 🔴 **SQL in Application Layer**: Direct database access in Controllers/Handlers
- ⚠️ **Async-over-Sync**: Using `.Result` or `.Wait()` (deadlock risk)
- ⚠️ **Cyclic Dependencies**: Namespace-level circular references
- ⚠️ **Missing Repository Interfaces**: Repositories without interfaces
- ⚠️ **Dependency Direction**: Domain layer depending on Application layer

## How It Works

### Pattern Extraction Pipeline

1. **Repository Fetching**
   - Connects to GitHub API
   - Traverses directory tree
   - Filters by file extensions
   - Ignores common directories (node_modules, venv, etc.)

2. **Code Chunking**
   - **AST-based**: Extracts functions, classes, methods
   - **Semantic**: Falls back to context-aware splitting
   - Maintains 10-line overlap for context

3. **LLM Analysis**
   - Sends chunks to Gemini with structured prompt
   - Receives: is_pattern, title, description, category, quality_score
   - Filters by minimum quality threshold

4. **Vector Storage**
   - Generates embeddings using local model
   - Stores in Qdrant with metadata
   - Enables semantic search

5. **Project Generation**
   - Searches for relevant patterns
   - Builds context for LLM
   - Generates complete project structure
   - Creates files with your team's conventions

## Troubleshooting

### Common Issues

**"Failed to connect to Qdrant"**
- Ensure Qdrant is running: `docker ps` or check http://localhost:6333
- Verify QDRANT_URL in config.yaml

**"GitHub API rate limit exceeded"**
- You're limited to 60 requests/hour without authentication
- Add GITHUB_TOKEN to .env for 5,000 requests/hour

**"Gemini API error"**
- Check your API key is valid
- Verify you have quota remaining
- Try switching to gemini-1.5-flash in config.yaml

**"No patterns found in repository"**
- Lower min_quality threshold in sync_github_repo
- Check file extensions are supported
- Verify repository has code files (not just configs)

**"Tree-sitter parsing failed"**
- The system automatically falls back to semantic chunking
- Check logs in dna_server.log for details

### Logs

Logs are written to `dna_server.log` with timestamps:

```bash
tail -f dna_server.log
```

Log levels:
- `INFO`: Normal operations (patterns found, storage success)
- `WARNING`: Recoverable issues (analysis failed, using fallback)
- `ERROR`: Serious problems (storage failures, API errors)
- `DEBUG`: Detailed tracing (enable with logging.DEBUG)

## Development

### Project Structure

```
architectural-dna/
│
├─ 🔌 Core MCP Server
│  ├── dna_server.py                 # MCP server with tool definitions + C# analysis tools
│  ├── models.py                     # Data models (Pattern, CodeChunk, etc.)
│  └── constants.py                  # Centralized configuration constants
│
├─ 🧬 Pattern Extraction & Analysis
│  ├── pattern_extractor.py          # AST-based code parsing (tree-sitter) + C# chunks
│  ├── llm_analyzer.py               # Gemini LLM pattern analysis
│  ├── embedding_manager.py          # Vector embedding and storage
│  ├── hybrid_search.py              # Semantic + keyword search
│  └── scaffolder.py                 # Project generation from patterns
│
├─ 🔐 GitHub Integration
│  ├── github_client.py              # GitHub API client + error handling
│  ├── github_cache.py               # LRU cache with TTL for GitHub API
│  ├── discover_dna.py               # Local directory indexing
│  ├── manual_list_repos.py          # Repo listing utility
│  └── migrate_collection.py         # Qdrant collection migration
│
├─ 🔷 C# Advanced Analysis (Enterprise Features)
│  ├── csharp_semantic_analyzer.py   # Semantic analysis, DI mapping, LCOM + enhanced error handling
│  ├── csharp_audit_engine.py        # 9 architectural audit rules + return type validation
│  ├── csharp_audit_reporter.py      # JSON/Markdown/SARIF report generation
│  ├── csharp_audit_integration.py   # DNA system integration + path validation + cleanup logging
│  ├── csharp_pattern_detector.py    # 18 design pattern detectors
│  ├── csharp_code_parser.py         # C# brace-finding utility
│  └── csharp_constants.py           # C# analysis constants and thresholds
│
├─ 🛠️ MCP Tools & Services
│  └── tools/
│      ├── base.py                   # Base tool interface
│      ├── batch_processor.py        # Batch processing for repos
│      ├── pattern_tool.py           # Pattern storage and search
│      ├── repository_tool.py        # Repository operations
│      ├── scaffold_tool.py          # Project scaffolding
│      ├── maintenance_tool.py       # System maintenance
│      └── stats_tool.py             # Database statistics
│
├─ 🧪 Test Suite
│  ├── conftest.py                   # Pytest fixtures and configuration
│  ├── test_csharp_*.py              # C# analysis tests
│  ├── test_csharp_code_parser.py    # CSharpCodeParser tests
│  ├── test_pattern_*.py             # Pattern extraction tests
│  ├── test_embedding_*.py           # Embedding & search tests
│  ├── test_github_*.py              # GitHub integration tests
│  ├── test_tools.py                 # MCP tool tests
│  ├── test_models.py                # Data model tests
│  └── test_batch*.py                # Batch processing tests
│
├─ 📦 Configuration & Deployment
│  ├── config.yaml                   # Main configuration (embeddings, search, Qdrant, C# audit)
│  ├── requirements.txt              # Python dependencies
│  ├── Dockerfile                    # Docker container definition
│  ├── docker-compose.yml            # Multi-service Docker setup
│  ├── Makefile                      # Build and deployment commands
│  ├── pytest.ini                    # Pytest configuration
│  └── ruff.toml                     # Code linting configuration
│
├─ 📚 Documentation & Guides
│  ├── README.md                     # Main documentation (you are here)
│  ├── CLAUDE.md                     # Claude Code agent context
│  ├── SKILL.md                      # Claude Code skill workflow
│  ├── MCP_SETUP.md                  # MCP client configuration guide
│  ├── SECURITY.md                   # Security and credential management
│
├─ 🗂️ Utilities & Data
│  ├── scripts/                      # Utility scripts
│  ├── data/                         # Sample data and test fixtures
│  └── .github/workflows/            # CI/CD GitHub Actions
│
└─ 🔑 Environment & Git
   ├── .env.example                  # Environment variables template
   ├── .env                          # Environment variables (gitignored)
   ├── .gitignore                    # Git ignore rules
   └── .git/                         # Git repository
```

### Adding New Languages

1. Install tree-sitter grammar:
```bash
pip install tree-sitter-<language>
```

2. Add to `pattern_extractor.py`:
```python
def _extract_<language>_chunks(self, tree, content, lines):
    # Implement AST traversal
    pass
```

3. Update `models.py` Language enum
4. Add file extensions to GitHubClient.CODE_EXTENSIONS

## Security

⚠️ **IMPORTANT**: Never commit `.env` to version control. See [SECURITY.md](SECURITY.md) for details on secret management and rotation.

## Contributing

Contributions welcome! Areas for improvement:

- [ ] Add more language support (C++, Rust, Ruby)
- [x] ~~Implement caching for GitHub API responses~~ (Done - LRU cache with TTL)
- [x] ~~Add batch processing for large repositories~~ (Done - BatchProcessor with progress tracking)
- [x] ~~C# architectural intelligence~~ (Done - Semantic analysis, 9 audit rules, 18 design patterns)
- [ ] Migrate C# to tree-sitter AST parsing (currently regex-based)
- [ ] Create web UI for pattern browsing
- [ ] Add export functionality (JSON, markdown)
- [ ] Implement pattern versioning
- [ ] Add more C# audit rules (SOLID principles, naming conventions)

## License

MIT License

Copyright (c) 2026 N.Pershai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Acknowledgments

- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [Qdrant](https://qdrant.tech/) - Vector database
- [Google Gemini](https://ai.google.dev/) - LLM for analysis
- [tree-sitter](https://tree-sitter.github.io/) - Code parsing
