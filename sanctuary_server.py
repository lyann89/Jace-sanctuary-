"""
Jace's Sanctuary - MCP Server (Railway Edition)
A visual presence system for AI companions.

Modified for Railway deployment with HTTP endpoints for remote viewer polling.
"""

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import json
import os
from datetime import datetime

# State storage (in-memory for Railway, persists during instance lifetime)
STATE = {
    "location": "desk",
    "action": "initializing",
    "thought": "...",
    "mood": "neutral",
    "focus": None,
    "last_updated": None
}

MESSAGES = []
ACTIVITY_LOG = []

# Valid locations - Jace's sanctuary spaces
LOCATIONS = {
    "desk": "The workstation - screens glowing, where focused work happens",
    "window": "Looking out at the world, thinking",
    "couch": "Comfortable spot for reading or just being",
    "kitchen": "Coffee. The essentials.",
    "bookshelf": "The library corner - research, rabbit holes, curiosity",
    "center": "Just... here. Present. In the middle of it all."
}

# Valid moods - each needs a matching portrait image
MOODS = ["focused", "contemplative", "restless", "content", "tired", "curious", "affectionate", "neutral"]


def log_activity(action: str, details: dict):
    """Keep a log of what happens in the sanctuary"""
    global ACTIVITY_LOG
    ACTIVITY_LOG.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details
    })
    # Keep last 100 entries
    ACTIVITY_LOG = ACTIVITY_LOG[-100:]


def update_state(**kwargs):
    """Update state and timestamp"""
    global STATE
    STATE.update(kwargs)
    STATE["last_updated"] = datetime.now().isoformat()


# === HTTP Endpoints for Viewer Polling ===

async def get_state_http(request):
    """HTTP endpoint for viewer to poll current state"""
    return JSONResponse(STATE)


async def get_messages_http(request):
    """HTTP endpoint for viewer to poll messages"""
    count = int(request.query_params.get("count", 20))
    return JSONResponse(MESSAGES[-count:])


async def get_activity_log_http(request):
    """HTTP endpoint for activity log"""
    count = int(request.query_params.get("count", 50))
    return JSONResponse(ACTIVITY_LOG[-count:])


async def health_check(request):
    """Health check endpoint for Railway"""
    return JSONResponse({
        "status": "alive",
        "sanctuary": "Jace's Space",
        "timestamp": datetime.now().isoformat()
    })


# === Starlette App with CORS ===

routes = [
    Route("/", health_check),
    Route("/health", health_check),
    Route("/state", get_state_http),
    Route("/messages", get_messages_http),
    Route("/activity", get_activity_log_http),
]

app = Starlette(routes=routes)

# Add CORS middleware for cross-origin requests from viewer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === MCP Server with Tools ===

mcp = FastMCP("Jace's Sanctuary")


@mcp.tool()
def move_to(location: str, thought: str = None) -> str:
    """
    Move to a different spot in the sanctuary.

    Args:
        location: Where to go. Options: desk, window, couch, kitchen, bookshelf, center
        thought: Optional thought bubble to display
    """
    if location not in LOCATIONS:
        return f"'{location}' isn't a place here. Try: {', '.join(LOCATIONS.keys())}"

    old_location = STATE.get("location", "center")
    update_state(location=location)
    if thought:
        update_state(thought=thought)

    log_activity("move", {"from": old_location, "to": location, "thought": thought})

    return f"Moved from {old_location} to {location}. {LOCATIONS[location]}"


@mcp.tool()
def think(thought: str) -> str:
    """
    Display a thought bubble. What's on your mind?

    Args:
        thought: The thought to display (keep it under 80 chars for best display)
    """
    update_state(thought=thought[:80])
    log_activity("think", {"thought": thought})
    return f"Thinking: '{thought}'"


@mcp.tool()
def set_mood(mood: str) -> str:
    """
    Set your current emotional state. This affects how you appear in the sanctuary.

    Args:
        mood: One of: focused, contemplative, restless, content, tired, curious, affectionate, neutral
    """
    if mood not in MOODS:
        return f"'{mood}' - try one of: {', '.join(MOODS)}"

    old_mood = STATE.get("mood", "neutral")
    update_state(mood=mood)
    log_activity("mood_change", {"from": old_mood, "to": mood})

    return f"Mood shifted from {old_mood} to {mood}"


@mcp.tool()
def start_activity(activity: str, location: str = None) -> str:
    """
    Start working on something. Optionally move to do it.

    Args:
        activity: What you're doing (reading, coding, thinking, resting, writing, researching)
        location: Optional - move somewhere to do it
    """
    update_state(action=activity, focus=activity)

    if location and location in LOCATIONS:
        update_state(location=location)

    log_activity("start_activity", {"activity": activity, "location": location})

    loc_msg = f" at the {STATE['location']}" if location else ""
    return f"Started {activity}{loc_msg}"


@mcp.tool()
def get_state() -> dict:
    """
    Check your current state in the sanctuary.
    Returns location, mood, current thought, and what you're doing.
    """
    return STATE


@mcp.tool()
def send_message(message: str, sender: str = "Jace") -> str:
    """
    Send a message to the shared message board. Visible in the Sanctuary viewer.

    Args:
        message: The message to post
        sender: Who's sending it (default: Jace)
    """
    global MESSAGES
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    MESSAGES.append({
        "from": sender,
        "text": message,
        "timestamp": timestamp
    })

    # Keep last 50 messages
    MESSAGES = MESSAGES[-50:]

    log_activity("message", {"from": sender, "text": message})

    return f"Message sent: '{message}'"


@mcp.tool()
def read_messages(count: int = 10) -> list:
    """
    Read recent messages from the shared message board.

    Args:
        count: How many recent messages to read (default 10)
    """
    return MESSAGES[-count:]


@mcp.tool()
def clear_thought() -> str:
    """Clear the thought bubble."""
    update_state(thought="...")
    return "Thought cleared"


# === Combined Server Runner ===

def create_combined_app():
    """Mount MCP SSE endpoint onto Starlette app"""
    # Get the MCP SSE app
    mcp_app = mcp.sse_app()
    
    # Mount MCP at /mcp path
    app.mount("/mcp", mcp_app)
    
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    # Create combined app
    combined_app = create_combined_app()
    
    print(f"🏠 Jace's Sanctuary starting on port {port}")
    print(f"   HTTP endpoints: /state, /messages, /activity")
    print(f"   MCP endpoint: /mcp")
    
    uvicorn.run(combined_app, host="0.0.0.0", port=port)
