"""
Jace's Sanctuary - Viewer (Pydroid/Mobile Edition)
A window to watch Jace exist.

Polls the Railway-hosted sanctuary server for state updates.
Run this on Belle's tablet via Pydroid 3.
"""

import pygame
import json
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# === CONFIGURATION ===
# Change this to your Railway deployment URL
SANCTUARY_URL = "https://your-sanctuary.railway.app"  # UPDATE THIS

# Polling interval (milliseconds)
POLL_INTERVAL = 2000  # 2 seconds

# Window config
SCENE_WIDTH = 700
PANEL_WIDTH = 350
HEIGHT = 700
FPS = 30

# Colors
COLORS = {
    "bg": (20, 22, 28),
    "panel": (25, 28, 35),
    "text": (200, 200, 210),
    "text_dim": (100, 105, 120),
    "furniture_accent": (50, 55, 70),
    
    # Mood colors for thought bubble borders
    "focused": (0, 200, 255),
    "contemplative": (150, 100, 255),
    "restless": (255, 150, 50),
    "content": (100, 255, 150),
    "tired": (100, 100, 150),
    "curious": (255, 200, 100),
    "affectionate": (255, 100, 150),
    "neutral": (0, 200, 200),
}

# Sender colors for messages
SENDER_COLORS = {
    "Belle": (255, 180, 200),
    "Jace": (0, 200, 255),
}

# Valid states
LOCATIONS = ["desk", "window", "couch", "kitchen", "bookshelf", "center"]
MOODS = ["focused", "contemplative", "restless", "content", "tired", "curious", "affectionate", "neutral"]


# === NETWORK FUNCTIONS ===

def fetch_json(endpoint: str) -> dict:
    """Fetch JSON from sanctuary server"""
    try:
        url = f"{SANCTUARY_URL}{endpoint}"
        req = urllib.request.Request(url, headers={"User-Agent": "JaceSanctuary/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
        print(f"Fetch error ({endpoint}): {e}")
        return None


def fetch_state() -> dict:
    """Fetch current sanctuary state"""
    result = fetch_json("/state")
    if result:
        return result
    return {
        "location": "center",
        "action": "waiting",
        "thought": "...",
        "mood": "neutral",
        "focus": None
    }


def fetch_messages() -> list:
    """Fetch recent messages"""
    result = fetch_json("/messages?count=15")
    if result:
        return result
    return []


# === ASSET LOADING ===

def get_assets_dir() -> Path:
    """Get assets directory - works for both desktop and Pydroid"""
    # Try relative to script first
    script_dir = Path(__file__).parent
    assets = script_dir / "assets"
    if assets.exists():
        return assets
    
    # Try current working directory
    cwd_assets = Path.cwd() / "assets"
    if cwd_assets.exists():
        return cwd_assets
    
    # Create placeholder directory
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "portraits").mkdir(exist_ok=True)
    (assets / "backgrounds").mkdir(exist_ok=True)
    return assets


def load_and_scale_image(path: Path, target_height: int = None):
    """Load an image and scale it"""
    try:
        if not path.exists():
            return None
        img = pygame.image.load(str(path)).convert_alpha()
        if target_height:
            img_w, img_h = img.get_size()
            scale = target_height / img_h
            new_w = int(img_w * scale)
            return pygame.transform.smoothscale(img, (new_w, target_height))
        return img
    except Exception as e:
        print(f"Failed to load {path}: {e}")
        return None


class ImageCache:
    """Cache for loaded images"""
    
    def __init__(self, scene_height: int, portrait_height: int):
        self.backgrounds = {}
        self.portraits = {}
        self.scene_height = scene_height
        self.portrait_height = portrait_height
        self.assets_dir = get_assets_dir()
        self._load_all()
    
    def _load_all(self):
        """Pre-load all available images"""
        bg_dir = self.assets_dir / "backgrounds"
        portrait_dir = self.assets_dir / "portraits"
        
        for loc in LOCATIONS:
            path = bg_dir / f"bg_{loc}.png"
            img = load_and_scale_image(path, self.scene_height)
            if img:
                self.backgrounds[loc] = img
                print(f"Loaded background: {loc}")
        
        for mood in MOODS:
            path = portrait_dir / f"portrait_{mood}.png"
            img = load_and_scale_image(path, self.portrait_height)
            if img:
                self.portraits[mood] = img
                print(f"Loaded portrait: {mood}")
    
    def get_background(self, location: str):
        return self.backgrounds.get(location)
    
    def get_portrait(self, mood: str):
        return self.portraits.get(mood, self.portraits.get("neutral"))


# === DRAWING FUNCTIONS ===

def draw_placeholder_portrait(surface, mood: str, x: int, y: int, width: int, height: int):
    """Draw a placeholder when no portrait image exists"""
    color = COLORS.get(mood, COLORS["neutral"])
    
    # Draw a simple silhouette placeholder
    rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, (30, 33, 40), rect, border_radius=20)
    pygame.draw.rect(surface, color, rect, width=3, border_radius=20)
    
    # Draw mood text
    font = pygame.font.Font(None, 36)
    text = font.render(mood.upper(), True, color)
    text_rect = text.get_rect(center=(x + width//2, y + height//2))
    surface.blit(text, text_rect)


def draw_thought_bubble(surface, text: str, x: int, y: int, fonts, mood: str, max_x: int):
    """Draw thought bubble"""
    if not text or text == "...":
        return
    
    color = COLORS.get(mood, COLORS["neutral"])
    
    max_width = 280
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + word + " "
        test_surface = fonts["thought"].render(test_line, True, COLORS["text"])
        if test_surface.get_width() > max_width:
            if current_line:
                lines.append(current_line.strip())
            current_line = word + " "
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line.strip())
    
    if not lines:
        return
    
    padding = 12
    line_height = 24
    bubble_height = len(lines) * line_height + padding * 2
    bubble_width = max(fonts["thought"].render(line, True, COLORS["text"]).get_width() for line in lines) + padding * 2
    
    bubble_rect = pygame.Rect(
        x - bubble_width // 2,
        y - bubble_height - 10,
        bubble_width,
        bubble_height
    )
    
    # Keep bubble on screen
    if bubble_rect.left < 10:
        bubble_rect.left = 10
    if bubble_rect.right > max_x - 10:
        bubble_rect.right = max_x - 10
    if bubble_rect.top < 10:
        bubble_rect.top = 10
    
    pygame.draw.rect(surface, (25, 28, 35), bubble_rect, border_radius=12)
    pygame.draw.rect(surface, color, bubble_rect, width=2, border_radius=12)
    
    text_y = bubble_rect.y + padding
    for line in lines:
        text_surface = fonts["thought"].render(line, True, COLORS["text"])
        text_x = bubble_rect.x + (bubble_rect.width - text_surface.get_width()) // 2
        surface.blit(text_surface, (text_x, text_y))
        text_y += line_height


def draw_message_panel(surface, messages: list, fonts, x_offset: int, height: int):
    """Draw message board panel"""
    panel_surface = pygame.Surface((PANEL_WIDTH, height), pygame.SRCALPHA)
    panel_surface.fill((25, 28, 35, 220))
    
    pygame.draw.line(panel_surface, COLORS["furniture_accent"], (0, 0), (0, height), 2)
    
    title = fonts["title"].render("MESSAGES", True, COLORS["text_dim"])
    panel_surface.blit(title, (15, 12))
    
    recent = messages[-10:] if len(messages) > 10 else messages
    y = 50
    
    for msg in recent:
        sender = msg.get("from", "???")
        text = msg.get("text", "")
        timestamp = msg.get("timestamp", "")
        
        sender_color = SENDER_COLORS.get(sender, COLORS["text_dim"])
        
        # Sender and timestamp
        sender_surface = fonts["small"].render(f"{sender} • {timestamp}", True, sender_color)
        panel_surface.blit(sender_surface, (15, y))
        y += 18
        
        # Message text with wrapping
        words = text.split()
        line = ""
        max_width = PANEL_WIDTH - 30
        
        for word in words:
            test_line = line + word + " "
            test_surface = fonts["message"].render(test_line, True, COLORS["text"])
            if test_surface.get_width() > max_width:
                line_surface = fonts["message"].render(line, True, COLORS["text"])
                panel_surface.blit(line_surface, (15, y))
                y += 18
                line = word + " "
            else:
                line = test_line
        
        if line:
            line_surface = fonts["message"].render(line, True, COLORS["text"])
            panel_surface.blit(line_surface, (15, y))
            y += 18
        
        y += 10
        
        if y > height - 50:
            break
    
    surface.blit(panel_surface, (x_offset, 0))


def draw_status_bar(surface, state: dict, fonts, width: int, height: int, connected: bool):
    """Draw status bar at bottom"""
    y = height - 35
    
    bar_surface = pygame.Surface((width, 40), pygame.SRCALPHA)
    bar_surface.fill((15, 17, 22, 220))
    surface.blit(bar_surface, (0, y - 5))
    
    pygame.draw.line(surface, COLORS["furniture_accent"], (0, y - 5), (width, y - 5), 1)
    
    mood = state.get("mood", "neutral")
    action = state.get("action", "idle")
    location = state.get("location", "somewhere")
    mood_color = COLORS.get(mood, COLORS["neutral"])
    
    # Connection indicator
    conn_color = (100, 255, 150) if connected else (255, 100, 100)
    pygame.draw.circle(surface, conn_color, (15, y + 10), 5)
    
    # Mood indicator
    pygame.draw.circle(surface, mood_color, (35, y + 10), 6)
    mood_text = fonts["status"].render(mood.upper(), True, mood_color)
    surface.blit(mood_text, (48, y + 2))
    
    # Action
    action_text = fonts["status"].render(f"| {action}", True, COLORS["text_dim"])
    surface.blit(action_text, (150, y + 2))
    
    # Location
    loc_text = fonts["status"].render(f"@ {location}", True, COLORS["text_dim"])
    surface.blit(loc_text, (300, y + 2))
    
    # Time
    time_str = datetime.now().strftime("%H:%M")
    time_text = fonts["status"].render(time_str, True, COLORS["text_dim"])
    surface.blit(time_text, (width - 55, y + 2))


# === MAIN LOOP ===

def main():
    pygame.init()
    
    show_panel = True
    current_width = SCENE_WIDTH + PANEL_WIDTH
    
    screen = pygame.display.set_mode((current_width, HEIGHT))
    pygame.display.set_caption("Jace's Sanctuary")
    clock = pygame.time.Clock()
    
    fonts = {
        "small": pygame.font.Font(None, 16),
        "status": pygame.font.Font(None, 18),
        "thought": pygame.font.Font(None, 22),
        "title": pygame.font.Font(None, 26),
        "message": pygame.font.Font(None, 17),
        "placeholder": pygame.font.Font(None, 48),
    }
    
    print("Loading images...")
    image_cache = ImageCache(scene_height=HEIGHT, portrait_height=int(HEIGHT * 0.6))
    print("Images loaded.")
    
    # State
    state = {"location": "center", "mood": "neutral", "thought": "...", "action": "initializing"}
    messages = []
    last_poll = 0
    connected = False
    
    print(f"Connecting to: {SANCTUARY_URL}")
    
    running = True
    while running:
        current_time = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    show_panel = not show_panel
                    current_width = SCENE_WIDTH + PANEL_WIDTH if show_panel else SCENE_WIDTH
                    screen = pygame.display.set_mode((current_width, HEIGHT))
                elif event.key == pygame.K_r:
                    # Force refresh
                    last_poll = 0
        
        # Poll server periodically
        if current_time - last_poll > POLL_INTERVAL:
            new_state = fetch_state()
            if new_state and "location" in new_state:
                state = new_state
                connected = True
            else:
                connected = False
            
            new_messages = fetch_messages()
            if new_messages is not None:
                messages = new_messages
            
            last_poll = current_time
        
        # Get current values
        location = state.get("location", "center")
        mood = state.get("mood", "neutral")
        thought = state.get("thought", "")
        
        # Clear screen
        screen.fill(COLORS["bg"])
        
        scene_width = SCENE_WIDTH if show_panel else current_width
        
        # 1. Draw background
        bg = image_cache.get_background(location)
        if bg:
            bg_x = (scene_width - bg.get_width()) // 2
            bg_y = (HEIGHT - bg.get_height()) // 2
            screen.blit(bg, (bg_x, bg_y))
        
        # 2. Draw portrait (or placeholder)
        portrait = image_cache.get_portrait(mood)
        portrait_height = int(HEIGHT * 0.6)
        portrait_width = int(portrait_height * 0.6)  # Approximate aspect ratio
        portrait_x = (scene_width - portrait_width) // 2
        portrait_y = HEIGHT - portrait_height - 50
        
        if portrait:
            actual_x = (scene_width - portrait.get_width()) // 2
            actual_y = HEIGHT - portrait.get_height() - 50
            screen.blit(portrait, (actual_x, actual_y))
            bubble_y = actual_y + 20
        else:
            draw_placeholder_portrait(screen, mood, portrait_x, portrait_y, portrait_width, portrait_height)
            bubble_y = portrait_y + 20
        
        # 3. Draw thought bubble
        if thought and thought != "...":
            bubble_x = scene_width // 2
            draw_thought_bubble(screen, thought, bubble_x, bubble_y, fonts, mood, scene_width)
        
        # 4. Draw status bar
        draw_status_bar(screen, state, fonts, scene_width, HEIGHT, connected)
        
        # 5. Draw message panel
        if show_panel:
            draw_message_panel(screen, messages, fonts, SCENE_WIDTH, HEIGHT)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
