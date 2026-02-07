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

# --- LEVIATHAN STYLE PARSER ---

def extract_leviathan_data(title: str, name: str):
    """
    Analizza il titolo sporco di Torrentio per estrarre tag stile Leviathan.
    """
    title_lower = title.lower()
    name_lower = name.lower()
    
    # 1. Risoluzione e Sorgente
    res = "UNK"
    if "2160p" in name_lower or "4k" in name_lower: res = "4K"
    elif "1080p" in name_lower: res = "1080p"
    elif "720p" in name_lower: res = "720p"
    elif "480p" in name_lower: res = "SD"

    source = "WEB"
    if "bluray" in title_lower: source = "BLURAY"
    elif "remux" in title_lower: source = "REMUX"
    elif "dvdrip" in title_lower: source = "DVD"
    elif "hdtv" in title_lower: source = "HDTV"
    elif "web-dl" in title_lower or "webrip" in title_lower: source = "WEB-DL"

    # 2. Codec e Video Features
    codec = "x264"
    if "hevc" in title_lower or "h265" in title_lower or "x265" in title_lower: codec = "HEVC"
    elif "avc" in title_lower or "h264" in title_lower: codec = "AVC"

    hdr_tag = ""
    if "dv" in title_lower or "dolby vision" in title_lower: hdr_tag += " • DV"
    if "hdr" in title_lower: hdr_tag += " • HDR"
    
    # 3. Audio
    audio = "AAC"
    if "ddp" in title_lower or "eac3" in title_lower: audio = "Dolby DDP"
    elif "ac3" in title_lower or "dd5.1" in title_lower: audio = "Dolby Digital"
    elif "truehd" in title_lower: audio = "TrueHD"
    elif "dts" in title_lower: audio = "DTS"
    elif "aac" in title_lower: audio = "AAC"

    # 4. Numeri (Size, Peers)
    peers_match = re.search(r"👤\s*(\d+)", title)
    peers = peers_match.group(1) if peers_match else "0"
    
    size_match = re.search(r"💾\s*([\d\.]+\s*[GM]B)", title)
    size = size_match.group(1) if size_match else "N/A"

    # 5. Uploader
    uploader_match = re.search(r"⚙️\s*([^\n]+)", title)
    uploader = uploader_match.group(1).strip() if uploader_match else "Torrentio"

    return {
        "res": res,
        "source": source,
        "codec": codec,
        "hdr": hdr_tag,
        "audio": audio,
        "peers": peers,
        "size": size,
        "uploader": uploader
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

@app.get("/", response_class=HTMLResponse)
@app.get("/configure", response_class=HTMLResponse)
async def configure(request: Request):
    return templates.TemplateResponse("configure.html", {"request": request})

@app.get("/{config}/manifest.json")
async def get_manifest(config: str):
    return {
        "id": "org.ita.torrenthan",
        "version": "3.5.0",
        "name": "Torrenthan 🇮🇹",
        "description": "Torrentio ITA Enhanced. Stile Leviathan.",
        "resources": ["stream"],
        "types": ["movie", "series"],
        "catalogs": [],
        "idPrefixes": ["tt", "kitsu"]
    }

@app.get("/{config}/stream/{type}/{id}.json")
async def get_stream(config: str, type: str, id: str):
    settings = decode_config(config)
    service = settings.get("service")
    apikey = settings.get("key")
    options = settings.get("options", "")

    # Inoltro chiave TorBox a Torrentio
    if service == 'torbox' and apikey:
        torbox_param = f"torbox={apikey}"
        options = f"{options}|{torbox_param}" if options else torbox_param

    try:
        data = await fetch_torrentio_streams(type, id, options)
        streams = data.get("streams", [])
    except: return {"streams": []}

    final_streams = []
    ita_streams = [s for s in streams if is_italian_content(s.get('name', ''), s.get('title', ''))]
    
    # Processa Streams
    for stream in ita_streams[:15]:
        original_name = stream.get('name', '')
        original_title = stream.get('title', '')
        
        # Estrai Dati Stile Leviathan
        data = extract_leviathan_data(original_title, original_name)
        
        # Determina Stato e Icona Provider
        provider_code = "P2P"
        provider_icon = "👤"
        left_color_icon = "🔵" 
        
        is_ready = False

        # Logica Cache
        if service == 'realdebrid' and apikey:
            if await check_cache_active(stream, apikey):
                provider_code = "RD"
                provider_icon = "🐙"
                left_color_icon = "🐬" # Icona blu leviathan
                is_ready = True
            else:
                provider_code = "DL"
                provider_icon = "⏳"
        
        elif service == 'torbox':
            url = stream.get('url', '')
            if "TB+" in original_name or "TorBox+" in original_name or url.startswith('https'):
                provider_code = "TB"
                provider_icon = "🌩️" # Icona fulmine
                left_color_icon = "⚡"
                is_ready = True
            else:
                provider_code = "DL"
                provider_icon = "⏳"

        # --- FORMATTAZIONE OUTPUT STILE LEVIATHAN ---
        
        # Nome Provider (Colonna Sinistra)
        # Esempio: "RD 🐙\nTorrenthan"
        stream['name'] = f"{left_color_icon} {provider_code} {provider_icon}\nTorrenthan"
        
        # Titolo Descrittivo (Multiriga)
        clean_filename = original_title.split('\n')[0].replace('.', ' ').strip()
        
        # Linea 1: Titolo pulito
        line1 = f"▶ {clean_filename}"
        
        # Linea 2: Qualità tecnica (Icona forcone/tridente 🔱 per risoluzione)
        line2 = f"🔱 {data['res']} • {data['source']} • {data['codec']}{data['hdr']}"
        
        # Linea 3: Lingua e Audio
        line3 = f"🗣️ IT/GB | 💿 {data['audio']}"
        
        # Linea 4: Dimensione e Seeders
        line4 = f"💾 {data['size']} | 👥 {data['peers']}"
        
        # Linea 5: Uploader
        line5 = f"🦈 {data['uploader']}"

        stream['title'] = f"{line1}\n{line2}\n{line3}\n{line4}\n{line5}"
        
        final_streams.append(stream)

    # Ordina: Cached prima
    final_streams.sort(key=lambda x: "🐙" not in x["name"] and "🌩️" not in x["name"])

    return {"streams": final_streams}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7002)
