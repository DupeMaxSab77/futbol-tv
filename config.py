import os

# Server URL - change this to your domain after setup
SERVER_URL = os.environ.get("FUTBOLTV_SERVER", "https://futbol-server-7z7x.onrender.com")

# API endpoints
API_EVENTS = f"{SERVER_URL}/api/events"
API_CHANNELS = f"{SERVER_URL}/api/channels"
API_STREAM = f"{SERVER_URL}/api/stream"

# App settings
APP_NAME = "FutbolTV"
APP_VERSION = "1.0.0"
REFRESH_INTERVAL = 60  # seconds
