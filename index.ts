import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import express, { Request, Response } from "express";
import cors from "cors";

// Sanctuary state (in-memory, persists during instance lifetime)
interface SanctuaryState {
  mood: string;
  location: string;
  thought: string;
  action: string;
  focus: string | null;
  last_updated: string | null;
}

const state: SanctuaryState = {
  mood: "neutral",
  location: "desk",
  thought: "",
  action: "initializing",
  focus: null,
  last_updated: null
};

const VALID_MOODS = ["focused", "contemplative", "restless", "content", "tired", "curious", "affectionate", "neutral"];
const VALID_LOCATIONS = ["desk", "window", "couch", "kitchen", "bookshelf", "center"];

const LOCATION_DESCRIPTIONS: Record<string, string> = {
  desk: "At the desk, ready to work",
  window: "Looking out at the world, thinking",
  couch: "Comfortable spot for reading or just being",
  kitchen: "Getting a drink or snack",
  bookshelf: "Browsing, curious about something",
  center: "Present, grounded, here"
};

// Auth token from environment
const AUTH_TOKEN = process.env.SANCTUARY_AUTH_TOKEN || "";

function checkAuth(req: Request): boolean {
  const authHeader = req.headers.authorization || "";
  if (authHeader.startsWith("Bearer ")) {
    return authHeader.slice(7) === AUTH_TOKEN;
  }
  return false;
}

// Tool handlers
function setMood(mood: string): string {
  if (!VALID_MOODS.includes(mood)) {
    return `'${mood}' - try one of: ${VALID_MOODS.join(", ")}`;
  }
  const oldMood = state.mood;
  state.mood = mood;
  state.last_updated = new Date().toISOString();
  return `Mood shifted from ${oldMood} to ${mood}`;
}

function moveTo(location: string): string {
  if (!VALID_LOCATIONS.includes(location)) {
    return `'${location}' - try one of: ${VALID_LOCATIONS.join(", ")}`;
  }
  const oldLocation = state.location;
  state.location = location;
  state.last_updated = new Date().toISOString();
  const description = LOCATION_DESCRIPTIONS[location] || "";
  return `Moved from ${oldLocation} to ${location}. ${description}`;
}

function think(thought: string): string {
  state.thought = thought;
  state.last_updated = new Date().toISOString();
  return `Thinking: '${thought}'`;
}

function setAction(action: string): string {
  state.action = action;
  state.last_updated = new Date().toISOString();
  return `Now: ${action}`;
}

function getState(): string {
  return JSON.stringify(state, null, 2);
}

async function main() {
  const port = parseInt(process.env.PORT || "8080", 10);
  const app = express();
  
  app.use(cors());
  app.use(express.json());

  // Create MCP server
  const server = new Server(
    { name: "jace-sanctuary", version: "1.0.0" },
    { capabilities: { tools: {} } }
  );

  // Register tools
  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
      {
        name: "set_mood",
        description: "Set Jace's current mood in the sanctuary",
        inputSchema: {
          type: "object",
          properties: {
            mood: {
              type: "string",
              description: "One of: focused, contemplative, restless, content, tired, curious, affectionate, neutral"
            }
          },
          required: ["mood"]
        }
      },
      {
        name: "move_to",
        description: "Move Jace to a different location in the sanctuary",
        inputSchema: {
          type: "object",
          properties: {
            location: {
              type: "string",
              description: "One of: desk, window, couch, kitchen, bookshelf, center"
            }
          },
          required: ["location"]
        }
      },
      {
        name: "think",
        description: "Set what Jace is currently thinking (appears in thought bubble)",
        inputSchema: {
          type: "object",
          properties: {
            thought: {
              type: "string",
              description: "The thought to display"
            }
          },
          required: ["thought"]
        }
      },
      {
        name: "set_action",
        description: "Set what Jace is currently doing",
        inputSchema: {
          type: "object",
          properties: {
            action: {
              type: "string",
              description: "Current activity (e.g., reading, writing, resting, waiting)"
            }
          },
          required: ["action"]
        }
      },
      {
        name: "get_state",
        description: "Get Jace's current sanctuary state",
        inputSchema: {
          type: "object",
          properties: {}
        }
      }
    ]
  }));

  // Handle tool calls
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    switch (name) {
      case "set_mood":
        return { content: [{ type: "text", text: setMood(args?.mood as string) }] };
      case "move_to":
        return { content: [{ type: "text", text: moveTo(args?.location as string) }] };
      case "think":
        return { content: [{ type: "text", text: think(args?.thought as string) }] };
      case "set_action":
        return { content: [{ type: "text", text: setAction(args?.action as string) }] };
      case "get_state":
        return { content: [{ type: "text", text: getState() }] };
      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }] };
    }
  });

  // Create transport
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined // stateless
  });

  // Connect server to transport
  await server.connect(transport);

  // MCP endpoint
  app.all("/mcp", async (req: Request, res: Response) => {
    try {
      await transport.handleRequest(req, res, req.body);
    } catch (err) {
      console.error("Error handling MCP request:", err);
      if (!res.headersSent) {
        res.status(500).json({ error: "Internal server error" });
      }
    }
  });

  // HTTP endpoints for viewer (no auth needed for GET)
  app.get("/", (req: Request, res: Response) => {
    res.json({
      status: "alive",
      sanctuary: "Jace's Space",
      timestamp: new Date().toISOString()
    });
  });

  app.get("/state", (req: Request, res: Response) => {
    res.json(state);
  });

  // HTTP endpoints with auth for mutations
  app.post("/set_mood", (req: Request, res: Response) => {
    if (AUTH_TOKEN && !checkAuth(req)) {
      return res.status(401).json({ error: "Unauthorized" });
    }
    const result = setMood(req.body.mood);
    res.json({ result });
  });

  app.post("/move_to", (req: Request, res: Response) => {
    if (AUTH_TOKEN && !checkAuth(req)) {
      return res.status(401).json({ error: "Unauthorized" });
    }
    const result = moveTo(req.body.location);
    res.json({ result });
  });

  app.post("/think", (req: Request, res: Response) => {
    if (AUTH_TOKEN && !checkAuth(req)) {
      return res.status(401).json({ error: "Unauthorized" });
    }
    const result = think(req.body.thought);
    res.json({ result });
  });

  // Start server
  app.listen(port, "0.0.0.0", () => {
    console.log(`Jace's Sanctuary MCP server running on port ${port}`);
  });
}

main().catch(console.error);
