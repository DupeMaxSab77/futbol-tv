import re
import base64
import requests
from typing import Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://la18hd.su/",
}


def decode_embed_path(path: str) -> Optional[str]:
    """Decode the base64 embed path to get the real URL."""
    if not path:
        return None
    try:
        # Path format: /embed/eventos.html?r=<base64>
        # or /embed/eventos?r=<base64>
        if "?r=" in path:
            b64_part = path.split("?r=")[-1]
            # Add padding if needed
            missing = len(b64_part) % 4
            if missing:
                b64_part += "=" * (4 - missing)
            decoded = base64.b64decode(b64_part).decode("utf-8")
            return decoded
    except Exception:
        pass
    return None


def extract_m3u8_from_page(url: str) -> Optional[str]:
    """Fetch a page and extract m3u8 URL from it."""
    if not url:
        return None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"[extractor] Error fetching {url}: {e}")
        return None

    # Patterns to find m3u8 URLs in HTML/JS
    patterns = [
        # PLAYBACKURL variable
        r'PLAYBACKURL\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'PLAYBACKURL\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        # source/file/src properties
        r'(?:source|file|src)\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        # data-src or data-url
        r'data-(?:src|url)\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        # hlsUrl or hls_url
        r'hls[_]?[Uu]rl\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        # url property in player config
        r'url\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        # Any .m3u8 URL in the page
        r'(https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*)',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            m3u8_url = match.group(1)
            # Clean up the URL
            m3u8_url = m3u8_url.strip().rstrip('"').rstrip("'")
            if m3u8_url.startswith("//"):
                m3u8_url = "https:" + m3u8_url
            return m3u8_url

    # If not found directly, check for iframes
    iframe_patterns = [
        r'<iframe[^>]+src=["\']([^"\']+)["\']',
        r'iframe\.src\s*=\s*["\']([^"\']+)["\']',
    ]
    for pattern in iframe_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            iframe_url = match.group(1)
            if iframe_url.startswith("/"):
                from urllib.parse import urljoin
                iframe_url = urljoin(url, iframe_url)
            # Recursively try to extract from iframe
            return extract_m3u8_from_page(iframe_url)

    return None


def resolve_embed(embed_path: str) -> Optional[str]:
    """Resolve an embed path to an m3u8 URL."""
    real_url = decode_embed_path(embed_path)
    if not real_url:
        return None
    return extract_m3u8_from_page(real_url)


def get_stream_url(source: str) -> Optional[str]:
    """Get the final stream URL.

    Accepts either:
    - Embed path: /embed/eventos.html?r=<base64>
    - Direct URL: https://la18hd.su/vivo/canal.php?stream=espn
    """
    if not source:
        return None

    # Try decode as embed path first (has ?r= with base64)
    if "?r=" in source and "/embed/" in source:
        result = resolve_embed(source)
        if result:
            return result

    # Otherwise treat as direct URL
    if source.startswith("http"):
        return extract_m3u8_from_page(source)

    # Last resort: try decode_embed_path anyway
    return resolve_embed(source)
