---
name: architectural-dna
description: Extract, store, and reuse code patterns from GitHub repositories
tools: ["store_pattern", "search_dna", "list_my_repos", "sync_github_repo", "scaffold_project", "get_dna_stats", "get_embedding_info", "batch_sync_repo", "get_sync_progress", "clear_sync_progress", "recategorize_patterns", "get_category_stats"]
---

# Architectural DNA Skill

Extract architectural patterns from your GitHub repositories, store them in a vector database, and reuse them to scaffold new projects.

## Tool Categories

### Discovery Tools
- `list_my_repos` - See available GitHub repositories
- `get_dna_stats` - Overview of stored patterns
- `get_category_stats` - Pattern distribution by category
- `get_embedding_info` - Current embedding configuration

### Ingestion Tools
- `sync_github_repo` - Sync small/medium repositories
- `batch_sync_repo` - Sync large repositories with resume support
- `store_pattern` - Manually store a single pattern

### Retrieval Tools
- `search_dna` - Find patterns by natural language query
- `scaffold_project` - Generate a new project from patterns

### Maintenance Tools
- `recategorize_patterns` - Re-analyze pattern categories with LLM
- `get_sync_progress` - Check batch sync progress
- `clear_sync_progress` - Reset sync progress to start fresh

---

## When to Use Each Tool

### list_my_repos
**Use when:**
- Starting fresh, need to see available repositories
- User asks "what repos can I sync?"
- Need to verify repository access

**Do NOT use when:**
- You already know the repository name
- User provided the full repo name (e.g., "owner/repo")

---

### sync_github_repo vs batch_sync_repo

| Scenario | Use |
|----------|-----|
| Small repo (<100 files) | `sync_github_repo` |
| Large repo (100+ files) | `batch_sync_repo` |
| Need to resume after interruption | `batch_sync_repo` |
| Quick one-time sync | `sync_github_repo` |
| Repo previously timed out | `batch_sync_repo` |

**sync_github_repo:**
- Simpler, single operation
- No progress tracking
- May timeout on large repos

**batch_sync_repo:**
- Processes in configurable batches
- Tracks progress, supports resume
- Use `get_sync_progress` to monitor
- Use `clear_sync_progress` to reset

---

### search_dna
**Use when:**
- User wants to find patterns ("show me error handling patterns")
- Looking for specific implementations
- Preparing for scaffolding (preview what's available)

**Parameters guidance:**
- `min_quality`: Default 5 is good. Lower to 3 for more results, raise to 7+ for best patterns only
- `limit`: Start with 5-10, increase if user needs more options
- `category`: Use when user specifies (e.g., "security patterns" → category="security")

---

### scaffold_project
**Use when:**
- User wants to create a new project
- Have patterns in the DNA bank to draw from

**Always do first:**
- Run `search_dna` to verify relevant patterns exist
- If no patterns found, suggest syncing a relevant repo first

**project_type values:**
- `api` - REST/GraphQL backend services
- `cli` - Command-line tools
- `library` - Reusable packages
- `web-app` - Frontend applications

---

### recategorize_patterns
**Use when:**
- `get_category_stats` shows many patterns in "other" category
- Patterns were synced without LLM analysis
- Want to improve pattern organization

**Parameters:**
- `from_category="other"` (default) - Only fix uncategorized patterns
- `from_category="all"` - Re-analyze everything (expensive)
- `dry_run=True` - Preview changes without applying
- `batch_size` - Lower if hitting rate limits

**Rate limiting:**
- Uses exponential backoff automatically
- If quota exhausted, wait for reset or reduce batch_size

---

### store_pattern
**Use when:**
- User wants to manually save a specific code snippet
- Adding patterns not from GitHub
- Storing curated examples

**Categories (pick one):**
- `architecture` - Structural patterns, design patterns
- `error_handling` - Exception handling, error recovery
- `configuration` - Config management, environment handling
- `testing` - Test patterns, fixtures, mocks
- `api_design` - API structure, endpoints, contracts
- `data_access` - Database, ORM, data layer patterns
- `security` - Auth, validation, sanitization
- `logging` - Logging, monitoring, observability
- `utilities` - Helper functions, common utilities
- `other` - Uncategorized (avoid if possible)

---

## Common Workflows

### Workflow 1: First-Time Setup

```
User: "Set up DNA bank from my repositories"

1. list_my_repos
   → Show available repos, let user choose

2. sync_github_repo (or batch_sync_repo for large repos)
   → Extract and store patterns

3. get_dna_stats
   → Confirm patterns were stored

4. get_category_stats
   → Check category distribution

5. IF many "other" patterns:
   recategorize_patterns(dry_run=True)
   → Preview recategorization
   recategorize_patterns()
   → Apply fixes
```

### Workflow 2: Adding a New Repository

```
User: "Add patterns from owner/repo-name"

1. sync_github_repo("owner/repo-name")
   OR batch_sync_repo("owner/repo-name") for large repos

2. IF using batch_sync_repo and it's taking long:
   get_sync_progress("owner/repo-name")
   → Check progress

3. get_category_stats
   → Verify patterns were categorized properly
```

### Workflow 3: Finding and Using Patterns

```
User: "Find error handling patterns for Python APIs"

1. search_dna(
     query="error handling API exceptions",
     language="python",
     category="error_handling"
   )
   → Return matching patterns

2. IF user wants to create a project:
   scaffold_project(
     project_name="my-api",
     project_type="api",
     tech_stack="python, fastapi"
   )
```

### Workflow 4: Maintenance After Sync Issues

```
User: "The sync failed halfway through"

1. get_sync_progress("owner/repo-name")
   → Check what was completed

2. IF want to resume:
   batch_sync_repo("owner/repo-name", resume=True)

3. IF want to start fresh:
   clear_sync_progress("owner/repo-name")
   batch_sync_repo("owner/repo-name")
```

### Workflow 5: Improving Pattern Quality

```
User: "Many patterns are uncategorized"

1. get_category_stats
   → Confirm "other" category count

2. recategorize_patterns(dry_run=True)
   → Preview what would change

3. recategorize_patterns(batch_size=5, delay_between_batches=2.0)
   → Process slowly to avoid rate limits

4. get_category_stats
   → Verify improvement
```

---

## Best Practices

### Always Do
- Check `get_dna_stats` before scaffolding to ensure patterns exist
- Use `dry_run=True` before recategorization to preview changes
- Use `batch_sync_repo` for unknown/large repositories
- Specify `language` and `category` filters in `search_dna` when user mentions them

### Never Do
- Run `scaffold_project` without patterns in the bank
- Use `sync_github_repo` on repos that previously timed out
- Run `recategorize_patterns(from_category="all")` without user confirmation (expensive)
- Ignore rate limit errors—reduce batch size or wait

### Error Recovery
- **Sync timeout**: Switch to `batch_sync_repo`
- **Rate limited (429)**: Reduce `batch_size`, increase `delay_between_batches`
- **No patterns found**: Sync a relevant repository first
- **Quota exhausted**: Wait for daily reset, or use `dry_run` to preview

---

## Tool Relationships

```
list_my_repos
      ↓
sync_github_repo ←――→ batch_sync_repo
      ↓                     ↓
      ↓              get_sync_progress
      ↓              clear_sync_progress
      ↓
get_dna_stats ←――→ get_category_stats
      ↓                     ↓
      ↓              recategorize_patterns
      ↓
search_dna
      ↓
scaffold_project
```

**Alternatives:** `sync_github_repo` ↔ `batch_sync_repo`
**Monitoring:** `get_sync_progress` → `batch_sync_repo`
**Verification:** `recategorize_patterns` → `get_category_stats`
**Prerequisite:** `search_dna` or `sync_*` → `scaffold_project`
