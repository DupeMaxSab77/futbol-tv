import requests
from typing import Optional
from config import API_EVENTS, API_CHANNELS, API_STREAM


def fetch_events() -> list[dict]:
    """Fetch events from the server."""
    try:
        resp = requests.get(API_EVENTS, timeout=10)
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception as e:
        print(f"[api] Error fetching events: {e}")
        return []


def fetch_channels() -> dict:
    """Fetch channels from the server."""
    try:
        resp = requests.get(API_CHANNELS, timeout=10)
        resp.raise_for_status()
        return resp.json().get("channels", {})
    except Exception as e:
        print(f"[api] Error fetching channels: {e}")
        return {}


def resolve_stream(embed_path: str) -> Optional[str]:
    """Resolve an embed path to an m3u8 stream URL."""
    try:
        resp = requests.get(API_STREAM, params={"url": embed_path}, timeout=15)
        resp.raise_for_status()
        return resp.json().get("url")
    except Exception as e:
        print(f"[api] Error resolving stream: {e}")
        return None
