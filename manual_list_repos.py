import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# Suppress FastMCP output just in case
os.environ["FASTMCP_SHOW_CLI_BANNER"] = "false"
os.environ["FASTMCP_LOG_ENABLED"] = "false"

try:
    from dna_server import get_github_client, config
    
    print("--- REPO LISTING START ---")
    
    gh = get_github_client()
    excluded = config.get("github", {}).get("excluded_repos", [])
    
    repos = gh.list_repositories(
        include_private=True,
        include_orgs=True,
        excluded_patterns=excluded
    )
    
    output = f"Found {len(repos)} repositories:\n\n"
    for repo in repos:
        visibility = "[PRIVATE]" if repo.is_private else "[PUBLIC]"
        lang = repo.language or "Unknown"
        desc = repo.description or "No description"
        output += f"**{repo.full_name}** ({visibility})\n"
        output += f"  Language: {lang} | Branch: {repo.default_branch}\n"
        output += f"  {desc}\n\n"
        
    print(output)
    print("--- REPO LISTING END ---")
except Exception as e:
    print(f"Error: {e}")
