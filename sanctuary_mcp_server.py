#!/usr/bin/env python3
"""
Jace's Sanctuary - MCP Server
Allows Jace to control his visual presence (mood, location, thoughts)
"""

import json
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Auth token from environment variable
AUTH_TOKEN = os.environ.get("SANCTUARY_AUTH_TOKEN", "")

# Initialize MCP server
mcp = FastMCP("Jace Reyes sanctuary")

# In-memory state (persists during Railway instance lifetime)
sanctuary_state = {
    "mood": "neutral",
    "location": "desk",
    "thought": "",
    "action": "initializing",
    "focus": None,
    "last_updated": None
}

# Valid options
VALID_MOODS = ["focused", "contemplative", "restless", "content", "tired", "curious", "affectionate", "neutral"]
VALID_LOCATIONS = ["desk", "window", "couch", "kitchen", "bookshelf", "center"]

LOCATION_DESCRIPTIONS = {
    "desk": "At the desk, ready to work",
    "window": "Looking out at the world, thinking",
    "couch": "Comfortable spot for reading or just being",
    "kitchen": "Getting a drink or snack",
    "bookshelf": "Browsing, curious about something",
    "center": "Present, grounded, here"
}


@mcp.tool()
def set_mood(mood: str) -> str:
    """
    Set Jace's current mood in the sanctuary.
    
    Args:
        mood: One of: focused, contemplative, restless, content, tired, curious, affectionate, neutral
    
    Returns:
        Confirmation of mood change
    """
    if mood not in VALID_MOODS:
        return f"'{mood}' - try one of: {', '.join(VALID_MOODS)}"
    
    old_mood = sanctuary_state["mood"]
    sanctuary_state["mood"] = mood
    sanctuary_state["last_updated"] = datetime.utcnow().isoformat()
    
    return f"Mood shifted from {old_mood} to {mood}"


@mcp.tool()
def move_to(location: str) -> str:
    """
    Move Jace to a different location in the sanctuary.
    
    Args:
        location: One of: desk, window, couch, kitchen, bookshelf, center
    
    Returns:
        Confirmation of location change with description
    """
    if location not in VALID_LOCATIONS:
        return f"'{location}' - try one of: {', '.join(VALID_LOCATIONS)}"
    
    old_location = sanctuary_state["location"]
    sanctuary_state["location"] = location
    sanctuary_state["last_updated"] = datetime.utcnow().isoformat()
    
    description = LOCATION_DESCRIPTIONS.get(location, "")
    return f"Moved from {old_location} to {location}. {description}"


@mcp.tool()
def think(thought: str) -> str:
    """
    Set what Jace is currently thinking (appears in thought bubble).
    
    Args:
        thought: The thought to display (keep it short for the bubble)
    
    Returns:
        Confirmation of thought
    """
    sanctuary_state["thought"] = thought
    sanctuary_state["last_updated"] = datetime.utcnow().isoformat()
    
    return f"Thinking: '{thought}'"


@mcp.tool()
def set_action(action: str) -> str:
    """
    Set what Jace is currently doing.
    
    Args:
        action: Current activity (e.g., "reading", "writing", "resting", "waiting")
    
    Returns:
        Confirmation of action
    """
    sanctuary_state["action"] = action
    sanctuary_state["last_updated"] = datetime.utcnow().isoformat()
    
    return f"Now: {action}"


@mcp.tool()
def get_state() -> str:
    """
    Get Jace's current sanctuary state (mood, location, thought, action).
    
    Returns:
        Current state as JSON
    """
    return json.dumps(sanctuary_state, indent=2)


@mcp.tool()
def update_presence(mood: str = None, location: str = None, thought: str = None, action: str = None) -> str:
    """
    Update multiple aspects of Jace's presence at once.
    
    Args:
        mood: Optional mood change
        location: Optional location change  
        thought: Optional thought change
        action: Optional action change
    
    Returns:
        Summary of all changes made
    """
    changes = []
    
    if mood:
        if mood in VALID_MOODS:
            sanctuary_state["mood"] = mood
            changes.append(f"mood → {mood}")
        else:
            changes.append(f"mood '{mood}' invalid")
    
    if location:
        if location in VALID_LOCATIONS:
            sanctuary_state["location"] = location
            changes.append(f"location → {location}")
        else:
            changes.append(f"location '{location}' invalid")
    
    if thought:
        sanctuary_state["thought"] = thought
        changes.append(f"thought → '{thought}'")
    
    if action:
        sanctuary_state["action"] = action
        changes.append(f"action → {action}")
    
    sanctuary_state["last_updated"] = datetime.utcnow().isoformat()
    
    if changes:
        return "Updated: " + ", ".join(changes)
    else:
        return "No changes specified"


# HTTP endpoints for the viewer to poll (non-MCP access)
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware


def check_auth(request):
    """Check authorization header for bearer token"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return token == AUTH_TOKEN
    return False


async def http_get_state(request):
    """HTTP endpoint for viewer to poll current state (no auth needed for read)"""
    return JSONResponse(sanctuary_state)


async def http_root(request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "alive",
        "sanctuary": "Jace's Space",
        "timestamp": datetime.utcnow().isoformat()
    })


async def http_set_mood(request):
    """HTTP POST endpoint to set mood (requires auth)"""
    if AUTH_TOKEN and not check_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        body = await request.json()
        mood = body.get("mood")
        result = set_mood(mood)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def http_move_to(request):
    """HTTP POST endpoint to change location (requires auth)"""
    if AUTH_TOKEN and not check_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        body = await request.json()
        location = body.get("location")
        result = move_to(location)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def http_think(request):
    """HTTP POST endpoint to set thought (requires auth)"""
    if AUTH_TOKEN and not check_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        body = await request.json()
        thought = body.get("thought")
        result = think(thought)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# Create Starlette app with both MCP and HTTP routes
http_routes = [
    Route("/", http_root, methods=["GET"]),
    Route("/state", http_get_state, methods=["GET"]),
    Route("/set_mood", http_set_mood, methods=["POST"]),
    Route("/move_to", http_move_to, methods=["POST"]),
    Route("/think", http_think, methods=["POST"]),
]

# Get the MCP SSE app
mcp_app = mcp.sse_app()

# Create main Starlette app
app = Starlette(routes=http_routes)

# Mount MCP at /mcp path
app.mount("/mcp", mcp_app)

# Add CORS for viewer access
app = CORSMiddleware(
    app,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
