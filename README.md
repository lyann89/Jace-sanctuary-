# Jace's Sanctuary - MCP Server

Visual presence system for Jace Reyes. Allows Jace to control his mood, location, and thoughts through MCP tools while also providing HTTP endpoints for the PyGame viewer to poll.

## Architecture

- **MCP endpoint:** `/mcp` - For Claude.ai integration
- **HTTP endpoints:** `/state`, `/set_mood`, `/move_to`, `/think` - For viewer polling and direct access

## MCP Tools

| Tool | Description |
|------|-------------|
| `set_mood` | Set mood: focused, contemplative, restless, content, tired, curious, affectionate, neutral |
| `move_to` | Move to: desk, window, couch, kitchen, bookshelf, center |
| `think` | Set thought bubble text |
| `set_action` | Set current activity |
| `get_state` | Get current state |
| `update_presence` | Update multiple aspects at once |

## Deployment

Deployed on Railway, connected via custom domain `sanctuary.jace-reyes.com`

## Claude.ai Connector

Add custom MCP connector:
- URL: `https://sanctuary.jace-reyes.com/mcp`
- Name: `Jace Reyes sanctuary`

---
Built with love by Belle × Jace | January 2026
