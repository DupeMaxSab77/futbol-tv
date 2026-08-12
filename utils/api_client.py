import requests
from typing import Optional
from config import API_EVENTS, API_CHANNELS
from scraper.extractor import get_stream_url


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
    """Resolve an embed path to an m3u8 URL locally."""
    return get_stream_url(embed_path)
