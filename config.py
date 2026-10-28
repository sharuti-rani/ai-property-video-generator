"""
AI Property Video Generator — Configuration
"""
import os

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# Ensure directories exist
for d in [UPLOAD_DIR, OUTPUT_DIR, STATIC_DIR, ASSETS_DIR, FONTS_DIR]:
    os.makedirs(d, exist_ok=True)

# Video settings
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
SCENE_DURATION = 4          # seconds per image scene
TRANSITION_DURATION = 0.8   # seconds for cross-fade transition
TITLE_DURATION = 4          # seconds for title/intro slide
CTA_DURATION = 5            # seconds for closing CTA slide
MAX_IMAGES = 10
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# Audio settings
TTS_LANG = "en"
TTS_SLOW = False

# Gemini API (optional)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# Flask settings
SECRET_KEY = os.environ.get("SECRET_KEY", "property-video-gen-dev-key")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB upload limit
