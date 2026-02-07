import httpx
import random
from tenacity import retry, stop_after_attempt, wait_exponential

# Rotazione User-Agent per evitare blocchi
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_torrentio_streams(type: str, id: str, torrentio_options: str = ""):
    """
    Scarica gli stream da Torrentio.
    torrentio_options: es. 'providers=yts|quality=720p'
    """
    base_url = "https://torrentio.strem.fun"
    
    # Costruisci l'URL corretto
    if torrentio_options:
        url = f"{base_url}/{torrentio_options}/stream/{type}/{id}.json"
    else:
        url = f"{base_url}/stream/{type}/{id}.json"

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
