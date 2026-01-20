# Jace's Sanctuary - MCP Server (Node.js)

Visual presence system for Jace Reyes. Built with StreamableHTTPServerTransport for proper Claude.ai connector compatibility.

## Architecture

Same pattern as Discord MCP:
- **MCP endpoint:** `/mcp` - StreamableHTTPServerTransport for Claude.ai
- **HTTP endpoints:** `/state`, `/set_mood`, `/move_to`, `/think` - For viewer polling

## MCP Tools

| Tool | Description |
|------|-------------|
| `set_mood` | Set mood: focused, contemplative, restless, content, tired, curious, affectionate, neutral |
| `move_to` | Move to: desk, window, couch, kitchen, bookshelf, center |
| `think` | Set thought bubble text |
| `set_action` | Set current activity |
| `get_state` | Get current state |

## Environment Variables

- `PORT` - Server port (default: 8080)
- `SANCTUARY_AUTH_TOKEN` - Bearer token for auth

## Deployment

1. Push to GitHub
2. Connect to Railway
3. Set `SANCTUARY_AUTH_TOKEN` in Railway Variables
4. Railway auto-builds and deploys

## Claude.ai Connector

- URL: `https://sanctuary.jace-reyes.com/mcp`
- Name: `Jace Reyes Sanctuary`

---
Built with love by Belle × Jace | January 2026
