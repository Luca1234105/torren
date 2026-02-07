from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import re
from urllib.parse import unquote

# Import moduli interni
from utils.encoding import decode_config
from core.torrentio import fetch_torrentio_streams
from core.filter import is_italian_content
from core import rd

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# --- UTILS DI FORMATTAZIONE ---

def extract_metadata(original_title):
    """Estrae Seeders, Dimensioni e Uploader dal titolo sporco di Torrentio"""
    # Esempio: "👤 167 💾 14.6 GB ⚙️ ilCorSa"
    peers = re.search(r"👤\s*(\d+)", original_title)
    size = re.search(r"💾\s*([\d\.]+\s*[GM]B)", original_title)
    uploader = re.search(r"⚙️\s*([^\n]+)", original_title)
    
    return {
        "peers": peers.group(1) if peers else "0",
        "size": size.group(1) if size else "N/A",
        "uploader": uploader.group(1).strip() if uploader else "P2P"
    }

def get_hash_from_stream(stream: dict) -> str:
    if stream.get('infoHash'): return stream['infoHash'].lower()
    url = stream.get('url', '')
    match = re.search(r'btih:([a-fA-F0-9]{40})', url, re.IGNORECASE)
    if match: return match.group(1).lower()
    return ""

async def check_cache_active(stream: dict, api_key: str) -> bool:
    hash_val = get_hash_from_stream(stream)
    if not hash_val: return False
    is_cached = False
    torrent_id = None
    try:
        async with httpx.AsyncClient(timeout=8, headers={'Authorization': f"Bearer {api_key}"}) as client:
            magnet_response = await rd.add_magnet(client, hash_val)
            if 'id' not in magnet_response: return False
            torrent_id = magnet_response['id']
            await rd.select_files(client, torrent_id, "all")
            info = await rd.get_torrent_info(client, torrent_id)
            if info.get('status') == 'downloaded': is_cached = True
            await rd.delete_torrent(client, torrent_id)
    except:
        if torrent_id:
            try: await rd.delete_torrent(client, torrent_id)
            except: pass
    return is_cached

# --- ENDPOINTS ---

@app.get("/{config}/manifest.json")
async def get_manifest(config: str):
    return {
        "id": "org.ita.torrentio.smart",
        "version": "1.0.0",
        "name": "Torrenthan 🇮🇹",
        "description": "Filtro ITA + Interfaccia Premium con controllo Debrid.",
        "resources": ["stream"],
        "types": ["movie", "series"],
        "idPrefixes": ["tt", "kitsu"]
    }

@app.get("/{config}/stream/{type}/{id}.json")
async def get_stream(config: str, type: str, id: str):
    settings = decode_config(config)
    service = settings.get("service")
    apikey = settings.get("key")
    options = settings.get("options", "")

    # Configurazione Torbox se presente
    if service == 'torbox' and apikey:
        options = f"{options}|torbox={apikey}" if options else f"torbox={apikey}"

    try:
        data = await fetch_torrentio_streams(type, id, options)
        streams = data.get("streams", [])
    except: return {"streams": []}

    final_streams = []
    ita_streams = [s for s in streams if is_italian_content(s.get('name', ''), s.get('title', ''))]
    
    for stream in ita_streams[:15]:
        original_name = stream.get('name', '')
        original_title = stream.get('title', '')
        
        # Estrazione dati
        meta = extract_metadata(original_title)
        
        # Rilevamento Qualità (4K, 1080p, ecc)
        quality = "SD"
        if "4k" in original_name.lower(): quality = "4K 💎"
        elif "1080p" in original_name.lower(): quality = "1080p ✨"
        elif "720p" in original_name.lower(): quality = "720p 📺"

        # LOGICA CACHE E ETICHETTE
        status_tag = "[P2P]"
        icon = "🔗"
        
        if service == 'realdebrid' and apikey:
            if await check_cache_active(stream, apikey):
                status_tag = "[⚡ RD+]"
                icon = "🚀"
            else:
                status_tag = "[⏳ DL]"
                icon = "☁️"
        elif service == 'torbox':
            if "TB+" in original_name or stream.get('url', '').startswith('https'):
                status_tag = "[⚡ TB+]"
                icon = "🔥"
            else:
                status_tag = "[⏳ DL]"
                icon = "☁️"

        # --- TEMPLATE FIGHISSIMO (LEVIATHAN STYLE) ---
        
        # 1. Nome visualizzato nella lista
        stream['name'] = f"{status_tag} {quality}\n🇮🇹 ITA"
        
        # 2. Descrizione dettagliata (quella che vedi nel tooltip)
        # Puliamo il nome del file eliminando i tag di Torrentio
        clean_filename = original_title.split('\n')[0][:50] + "..." 
        
        stream['title'] = (
            f"🎬 {clean_filename}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📦 {meta['size']}   👥 {meta['peers']}   🛰️ {meta['uploader']}\n"
            f"🔊 Audio: Italiano / Multi\n"
            f"✅ Stato: {icon} {'Instant Cache' if '⚡' in status_tag else 'Peer-to-Peer'}\n"
            f"━━━━━━━━━━━━━━━"
        )

        final_streams.append(stream)

    # Ordinamento: Prima i file in Cache
    final_streams.sort(key=lambda x: "[⚡" not in x["name"])

    return {"streams": final_streams}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7002)
