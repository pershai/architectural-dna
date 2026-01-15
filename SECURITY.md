# Security Notice

## ⚠️ IMPORTANT: Secret Rotation Required

If you have previously committed the `.env` file to version control, the secrets contained within may be compromised.

### Immediate Actions Required:

1. **Rotate GitHub Token**
   - Go to https://github.com/settings/tokens
   - Delete the old token (starts with `ghp_` or `github_pat_`)
   - Generate a new Personal Access Token with required scopes:
     - `repo` (for private repositories)
     - `read:org` (for organization repositories)
   - Update `.env` with the new token

2. **Rotate Gemini API Key**
   - Go to https://aistudio.google.com/app/apikey
   - Delete the old API key
   - Generate a new API key
   - Update `.env` with the new key

3. **Remove Secrets from Git History** (if .env was committed)
   ```bash
   # Install BFG Repo-Cleaner or use git-filter-repo

   # Option 1: Using BFG (recommended)
   bfg --delete-files .env
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive

   # Option 2: Using git-filter-repo
   git filter-repo --path .env --invert-paths

   # Force push to remote (WARNING: Destructive operation)
   git push origin --force --all
   ```

4. **Verify .gitignore**
   - Confirm `.env` is listed in `.gitignore`
   - Verify `.env` is not tracked: `git status` should not show `.env`

### Best Practices Going Forward:

1. **Never commit secrets** - Always use `.env` files that are gitignored
2. **Use .env.example** - Provide a template without actual values
3. **Document required variables** - List all required environment variables in README
4. **Use secret management** - Consider tools like:
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault
   - 1Password CLI
   - Doppler

### Environment Variables Required:

```bash
# GitHub Integration
GITHUB_TOKEN=your_github_token_here

# Google Gemini LLM
GEMINI_API_KEY=your_gemini_api_key_here

# Qdrant Vector Database (optional if running locally)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Leave empty for local instance
```

## Reporting Security Issues

If you discover a security vulnerability, please email the maintainer directly rather than opening a public issue.
