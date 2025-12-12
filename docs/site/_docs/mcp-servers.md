---
layout: doc
title: MCP Servers
nav_order: 7
---

MCP (Model Context Protocol) servers extend AIPA's capabilities by providing access to external services and tools.

## What are MCP Servers?

MCP servers are standardized interfaces that let Claude interact with:
- APIs (GitHub, Notion, etc.)
- Databases
- File systems
- Cloud services
- Custom tools

## Configuration

MCP servers are configured in `.mcp.json`:

```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

## Built-in Servers

AIPA comes with these servers pre-configured:

### GitHub

```json
{
  "github": {
    "type": "stdio",
    "command": "docker",
    "args": ["run", "-i", "--rm",
      "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
      "ghcr.io/github/github-mcp-server"
    ]
  }
}
```

**Capabilities:**
- Repository management
- File operations
- Pull requests
- Issues

**Required:** `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable

### AWS Documentation

```json
{
  "aws-docs": {
    "type": "stdio",
    "command": "uvx",
    "args": ["awslabs.aws-documentation-mcp-server@latest"]
  }
}
```

**Capabilities:**
- Search AWS documentation
- Read documentation pages
- Get recommendations

### AWS API

```json
{
  "aws-api": {
    "type": "stdio",
    "command": "uvx",
    "args": ["awslabs.aws-api-mcp-server@latest"],
    "env": {
      "AWS_REGION": "ap-southeast-2"
    }
  }
}
```

**Capabilities:**
- Execute AWS CLI commands
- Query AWS services
- Manage resources

**Required:** AWS credentials configured

### Terraform

```json
{
  "aws-terraform": {
    "type": "stdio",
    "command": "uvx",
    "args": ["awslabs.terraform-mcp-server@latest"],
    "env": {
      "AWS_REGION": "ap-southeast-2"
    }
  }
}
```

**Capabilities:**
- Terraform best practices
- Checkov security scanning
- Provider documentation

### Memory

```json
{
  "memory": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-memory"]
  }
}
```

**Capabilities:**
- Persistent knowledge graph
- Cross-session memory
- Entity relationships

## Adding a New Server

### 1. Find the Server

Browse available servers:
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers)

### 2. Add to Configuration

Edit `.mcp.json`:

```json
{
  "mcpServers": {
    "new-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@package/server-name"]
    }
  }
}
```

### 3. Configure Credentials

Add required environment variables to `.env`.

### 4. Test

Restart Claude Code and verify the server is available:

```
/mcp
```

## Popular MCP Servers

| Server | Purpose |
|--------|---------|
| `@modelcontextprotocol/server-memory` | Persistent knowledge |
| `@modelcontextprotocol/server-filesystem` | File operations |
| `@modelcontextprotocol/server-puppeteer` | Browser automation |
| `@modelcontextprotocol/server-postgres` | PostgreSQL access |
| `ghcr.io/github/github-mcp-server` | GitHub integration |
| `@notionhq/notion-mcp-server` | Notion integration |
| `@modelcontextprotocol/server-slack` | Slack integration |

## Creating Custom Servers

For custom integrations, you can create your own MCP server:

1. Use the [MCP SDK](https://github.com/modelcontextprotocol/typescript-sdk)
2. Implement required handlers
3. Package as npm module or Docker image
4. Add to `.mcp.json`

## Best Practices

1. **Minimal servers** - Only enable servers you need
2. **Secure credentials** - Use environment variables, not inline
3. **Monitor context** - Each server adds to context window
4. **Test locally** - Verify servers work before deploying
5. **Update regularly** - Keep servers at latest versions

## Troubleshooting

### Server not starting

```bash
# Debug mode
claude --mcp-debug
```

### Permission errors

Ensure credentials are set:
```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=xxx
```

### High context usage

Disable unused servers:
```bash
/mcp  # View and toggle servers
```
