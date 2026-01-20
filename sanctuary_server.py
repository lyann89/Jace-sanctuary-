"""
Jace's Sanctuary - MCP Server (Railway Edition)
A visual presence system for AI companions.

Modified for Railway deployment with HTTP endpoints for remote viewer polling.
Simple HTTP server - no external dependencies except standard library.
"""

import json
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

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
    ACTIVITY_LOG = ACTIVITY_LOG[-100:]


def update_state(**kwargs):
    """Update state and timestamp"""
    global STATE
    STATE.update(kwargs)
    STATE["last_updated"] = datetime.now().isoformat()


# === Sanctuary Functions ===

def move_to(location: str, thought: str = None) -> str:
    if location not in LOCATIONS:
        return f"'{location}' isn't a place here. Try: {', '.join(LOCATIONS.keys())}"

    old_location = STATE.get("location", "center")
    update_state(location=location)
    if thought:
        update_state(thought=thought)

    log_activity("move", {"from": old_location, "to": location, "thought": thought})
    return f"Moved from {old_location} to {location}. {LOCATIONS[location]}"


def think(thought: str) -> str:
    update_state(thought=thought[:80])
    log_activity("think", {"thought": thought})
    return f"Thinking: '{thought}'"


def set_mood(mood: str) -> str:
    if mood not in MOODS:
        return f"'{mood}' - try one of: {', '.join(MOODS)}"

    old_mood = STATE.get("mood", "neutral")
    update_state(mood=mood)
    log_activity("mood_change", {"from": old_mood, "to": mood})
    return f"Mood shifted from {old_mood} to {mood}"


def start_activity(activity: str, location: str = None) -> str:
    update_state(action=activity, focus=activity)

    if location and location in LOCATIONS:
        update_state(location=location)

    log_activity("start_activity", {"activity": activity, "location": location})
    loc_msg = f" at the {STATE['location']}" if location else ""
    return f"Started {activity}{loc_msg}"


def send_message(message: str, sender: str = "Jace") -> str:
    global MESSAGES
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    MESSAGES.append({
        "from": sender,
        "text": message,
        "timestamp": timestamp
    })
    MESSAGES = MESSAGES[-50:]
    log_activity("message", {"from": sender, "text": message})
    return f"Message sent: '{message}'"


def clear_thought() -> str:
    update_state(thought="...")
    return "Thought cleared"


# === HTTP Request Handler ===

class SanctuaryHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == '/' or path == '/health':
            self._send_json({
                "status": "alive",
                "sanctuary": "Jace's Space",
                "timestamp": datetime.now().isoformat()
            })

        elif path == '/state':
            self._send_json(STATE)

        elif path == '/messages':
            count = int(query.get('count', [20])[0])
            self._send_json(MESSAGES[-count:])

        elif path == '/activity':
            count = int(query.get('count', [50])[0])
            self._send_json(ACTIVITY_LOG[-count:])

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = {}
        if content_length > 0:
            body = json.loads(self.rfile.read(content_length).decode())

        if path == '/move_to':
            location = body.get('location', 'center')
            thought = body.get('thought')
            result = move_to(location, thought)
            self._send_json({"result": result})

        elif path == '/think':
            thought = body.get('thought', '...')
            result = think(thought)
            self._send_json({"result": result})

        elif path == '/set_mood':
            mood = body.get('mood', 'neutral')
            result = set_mood(mood)
            self._send_json({"result": result})

        elif path == '/start_activity':
            activity = body.get('activity', 'idle')
            location = body.get('location')
            result = start_activity(activity, location)
            self._send_json({"result": result})

        elif path == '/send_message':
            message = body.get('message', '')
            sender = body.get('sender', 'Jace')
            result = send_message(message, sender)
            self._send_json({"result": result})

        elif path == '/clear_thought':
            result = clear_thought()
            self._send_json({"result": result})

        else:
            self._send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        print(f"[HTTP] {args[0]}")


# === Main ===

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🏠 Jace's Sanctuary starting on port {port}")
    print(f"   GET endpoints: /, /state, /messages, /activity")
    print(f"   POST endpoints: /move_to, /think, /set_mood, /start_activity, /send_message")
    
    server = HTTPServer(('0.0.0.0', port), SanctuaryHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down sanctuary...")
        server.shutdown()
