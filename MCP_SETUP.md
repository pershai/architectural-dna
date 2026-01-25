# MCP Client Setup Guide

Complete instructions for connecting Architectural DNA to various AI assistants.

## Prerequisites

1. **Docker** installed and running
2. **API Keys** ready:
   - GitHub Personal Access Token ([create here](https://github.com/settings/tokens))
   - Google Gemini API Key ([get here](https://aistudio.google.com/app/apikey))

## Quick Start

### 1. Start the Server

```bash
# Clone the repository
git clone https://github.com/pershai/architectural-dna.git
cd architectural-dna

# Start with Docker
docker-compose up -d

# Verify it's running
curl http://localhost:8080/sse
```

The server runs at: **http://localhost:8080/sse**

### 2. Configure Your MCP Client

Choose your client below and follow the instructions.

---

## 🟣 Cursor

### Config Location

- **Windows**: `%APPDATA%\Cursor\User\globalStorage\cursor.mcp\config.json`
- **Mac**: `~/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/config.json`
- **Linux**: `~/.config/Cursor/User/globalStorage/cursor.mcp/config.json`

### Configuration

Add to your `config.json`:

```json
{
  "mcpServers": {
    "architectural-dna": {
      "transport": "sse",
      "url": "http://localhost:8080/sse",
      "headers": {
        "X-GITHUB-TOKEN": "ghp_your_github_token_here",
        "X-GEMINI-API-KEY": "your_gemini_api_key_here"
      }
    }
  }
}
```

### Steps

1. Open Cursor
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
3. Search for "Open Settings (JSON)" or navigate to the config file manually
4. Add the configuration above
5. Replace the placeholder tokens with your actual API keys
6. Restart Cursor

---

## 🔵 Gemini Code Assist / Antigravity

### Config Location

- **Windows**: `%USERPROFILE%\.gemini\antigravity\mcp_config.json`
- **Mac/Linux**: `~/.gemini/antigravity/mcp_config.json`

### Configuration

Add to your `mcp_config.json`:

```json
{
  "mcpServers": {
    "architectural-dna": {
      "serverUrl": "http://localhost:8080/sse",
      "headers": {
        "X-GITHUB-TOKEN": "ghp_your_github_token_here",
        "X-GEMINI-API-KEY": "your_gemini_api_key_here"
      }
    }
  }
}
```

> **Note**: Gemini uses `serverUrl` instead of `url`

### Steps

1. Create/edit the config file at the location above
2. Add the configuration
3. Replace placeholders with your actual API keys
4. Restart your IDE or Gemini Code Assist

---

## 🟢 Windsurf / Cascade

### Config Location

- **Windows**: `%APPDATA%\Windsurf\User\globalStorage\cascade.mcp\config.json`
- **Mac**: `~/Library/Application Support/Windsurf/User/globalStorage/cascade.mcp/config.json`
- **Linux**: `~/.config/Windsurf/User/globalStorage/cascade.mcp/config.json`

### Configuration

Add to your `config.json`:

```json
{
  "mcpServers": {
    "architectural-dna": {
      "transport": "sse",
      "url": "http://localhost:8080/sse",
      "headers": {
        "X-GITHUB-TOKEN": "ghp_your_github_token_here",
        "X-GEMINI-API-KEY": "your_gemini_api_key_here"
      }
    }
  }
}
```

### Steps

1. Open Windsurf
2. Navigate to Settings → MCP Servers (or find the config file)
3. Add the configuration above
4. Replace placeholders with your actual API keys
5. Restart Windsurf

---

## 🟠 Claude Desktop

### Config Location

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "architectural-dna": {
      "transport": "sse",
      "url": "http://localhost:8080/sse",
      "headers": {
        "X-GITHUB-TOKEN": "ghp_your_github_token_here",
        "X-GEMINI-API-KEY": "your_gemini_api_key_here"
      }
    }
  }
}
```

### Steps

1. Close Claude Desktop completely
2. Create/edit the config file at the location above
3. Add the configuration
4. Replace placeholders with your actual API keys
5. Restart Claude Desktop

---

## 🔴 VS Code with Continue Extension

### Config Location

- **Windows**: `%USERPROFILE%\.continue\config.json`
- **Mac/Linux**: `~/.continue/config.json`

### Configuration

Add to your Continue `config.json`:

```json
{
  "experimental": {
    "mcpServers": {
      "architectural-dna": {
        "transport": "sse",
        "url": "http://localhost:8080/sse",
        "headers": {
          "X-GITHUB-TOKEN": "ghp_your_github_token_here",
          "X-GEMINI-API-KEY": "your_gemini_api_key_here"
        }
      }
    }
  }
}
```

### Steps

1. Open VS Code
2. Open Continue settings (click the gear icon in Continue panel)
3. Add the MCP server configuration
4. Replace placeholders with your actual API keys
5. Reload VS Code

---

## Supported Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-GITHUB-TOKEN` | Yes | GitHub Personal Access Token for repo access |
| `X-GEMINI-API-KEY` | Yes | Google Gemini API key for LLM analysis |
| `X-QDRANT-URL` | No | Override Qdrant URL (default: internal Docker) |

---

## Available MCP Tools

Once connected, you'll have access to these tools:

| Tool | Description |
|------|-------------|
| `store_pattern` | Save a code pattern to the DNA bank |
| `search_dna` | Search for patterns using hybrid semantic+keyword search |
| `list_my_repos` | List your accessible GitHub repositories |
| `sync_github_repo` | Index patterns from a GitHub repository |
| `scaffold_project` | Generate a new project from stored patterns |
| `get_dna_stats` | View statistics about your DNA bank |
| `get_embedding_info` | Check current embedding configuration |

---

## Example Usage

After setup, try these commands in your AI assistant:

```
"Get my DNA stats"

"Search for authentication patterns in Python"

"List my GitHub repositories"

"Sync patterns from my-username/my-repo"

"Create a new FastAPI project called my-api"
```

---

## Troubleshooting

### "Connection refused"

```bash
# Check if Docker is running
docker-compose ps

# Restart services
docker-compose restart
```

### "Server not responding"

```bash
# Check logs
docker-compose logs -f dna-server

# Verify SSE endpoint
curl http://localhost:8080/sse
```

### "Invalid API key"

- Verify your GitHub token has `repo` scope
- Verify your Gemini API key is valid
- Check for typos in the config

### "Port already in use"

```bash
# Use a different port
MCP_PORT=9090 docker-compose up -d

# Update your client config to use the new port
"url": "http://localhost:9090/sse"
```

### Config file not found

Create the config file manually:

```bash
# Windows (PowerShell)
New-Item -ItemType File -Path "$env:APPDATA\Cursor\User\globalStorage\cursor.mcp\config.json" -Force

# Mac/Linux
mkdir -p ~/.config/Cursor/User/globalStorage/cursor.mcp
touch ~/.config/Cursor/User/globalStorage/cursor.mcp/config.json
```

---

## Docker Commands Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f dna-server

# Restart services
docker-compose restart

# Rebuild after updates
docker-compose build && docker-compose up -d

# Check status
docker-compose ps
```

---

## Security Notes

- **Never commit API keys** to version control
- The `headers` in MCP config are sent with each request
- Keys are used server-side and not stored
- Consider using environment variables for shared team configs

---

## Need Help?

- Check [DOCKER.md](DOCKER.md) for Docker-specific issues
- Review [README.md](../../README.md) for feature documentation
- Open an issue on GitHub for bugs or feature requests
