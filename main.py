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
    title_lower = title.lower()
    name_lower = name.lower()
    
    # 1. Risoluzione
    res = "UNK"
    if "2160p" in name_lower or "4k" in name_lower: res = "4K"
    elif "1080p" in name_lower: res = "1080p"
    elif "720p" in name_lower: res = "720p"
    elif "480p" in name_lower: res = "SD"

    # 2. Codec e Video Features
    codec = "x264"
    if "hevc" in title_lower or "h265" in title_lower: codec = "HEVC"
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

    # 4. Numeri
    peers_match = re.search(r"👤\s*(\d+)", title)
    peers = peers_match.group(1) if peers_match else "0"
    
    size_match = re.search(r"💾\s*([\d\.]+\s*[GM]B)", title)
    size = size_match.group(1) if size_match else "N/A"

    # 5. Uploader
    uploader_match = re.search(r"⚙️\s*([^\n]+)", title)
    uploader = uploader_match.group(1).strip() if uploader_match else "Torrentio"

    return {
        "res": res, "source": "WEB-DL" if "web" in title_lower else "Bluray", 
        "codec": codec, "hdr": hdr_tag, "audio": audio, 
        "peers": peers, "size": size, "uploader": uploader
    }

def get_hash_from_stream(stream: dict) -> str:
    if stream.get('infoHash'): return stream['infoHash'].lower()
    url = stream.get('url', '')
    match = re.search(r'btih:([a-fA-F0-9]{40})', url, re.IGNORECASE)
    if match: return match.group(1).lower()
    return ""

# --- RD ACTIVE RESOLVER ---
# Questa funzione controlla la cache E restituisce il link diretto se pronto
async def resolve_rd_link(stream: dict, api_key: str):
    hash_val = get_hash_from_stream(stream)
    if not hash_val: return None

    try:
        async with httpx.AsyncClient(timeout=10, headers={'Authorization': f"Bearer {api_key}"}) as client:
            # 1. Aggiungi Magnet
            magnet_resp = await rd.add_magnet(client, hash_val)
            if 'id' not in magnet_resp: return None
            torrent_id = magnet_resp['id']
            
            # 2. Seleziona file
            await rd.select_files(client, torrent_id, "all")
            
            # 3. Controlla info
            info = await rd.get_torrent_info(client, torrent_id)
            
            # Se è scaricato, sblocchiamo il link (UNRESTRICT)
            if info.get('status') == 'downloaded':
                # Prendiamo il link dell'ultimo file video (solitamente il film)
                files = [f for f in info.get('files', []) if f['selected'] == 1]
                # Ordina per dimensione decrescente (il file più grande è il film)
                files.sort(key=lambda x: x['bytes'], reverse=True)
                
                if files:
                    selected_file_id = files[0]['id']
                    # Trova il link originale corrispondente
                    links = info.get('links', [])
                    if links:
                        link_to_unrestrict = links[0] # Semplificazione: prende il primo link generato
                        
                        # Chiamata Unrestrict
                        unrestrict_resp = await client.post("https://api.real-debrid.com/rest/1.0/unrestrict/link", 
                                                          data={"link": link_to_unrestrict})
                        if unrestrict_resp.status_code == 200:
                            stream_url = unrestrict_resp.json().get('download')
                            return stream_url

            # Pulizia
            await rd.delete_torrent(client, torrent_id)
            
    except Exception as e:
        print(f"RD Resolve Error: {e}")
        
    return None

# --- ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
@app.get("/configure", response_class=HTMLResponse)
async def configure(request: Request):
    return templates.TemplateResponse("configure.html", {"request": request})

@app.get("/{config}/manifest.json")
async def get_manifest(config: str):
    return {
        "id": "org.ita.torrenthan",
        "version": "4.0.0",
        "name": "Torrenthan 🇮🇹",
        "description": "Torrentio ITA Enhanced. RD Unrestricted & TorBox.",
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
        data = extract_leviathan_data(original_title, original_name)
        
        provider_code = "P2P"
        provider_icon = "👤"
        left_color_icon = "🔵"
        
        # LOGICA REAL-DEBRID (Nuova: Unrestrict)
        if service == 'realdebrid' and apikey:
            # Tentiamo di ottenere il link diretto
            direct_link = await resolve_rd_link(stream, apikey)
            
            if direct_link:
                provider_code = "RD"
                provider_icon = "🐙"
                left_color_icon = "🐬"
                # SOSTITUIAMO L'URL: Ora è HTTP diretto, non più Magnet!
                stream['url'] = direct_link
                # Rimuoviamo infoHash per forzare Stremio a usare l'URL
                if 'infoHash' in stream: del stream['infoHash']
            else:
                provider_code = "DL"
                provider_icon = "⏳"

        # LOGICA TORBOX
        elif service == 'torbox':
            url = stream.get('url', '')
            if "TB+" in original_name or url.startswith('https'):
                provider_code = "TB"
                provider_icon = "🌩️"
                left_color_icon = "⚡"
            else:
                provider_code = "DL"
                provider_icon = "⏳"

        # Formattazione Leviathan
        stream['name'] = f"{left_color_icon} {provider_code} {provider_icon}\nTorrenthan"
        
        clean_filename = original_title.split('\n')[0].replace('.', ' ').strip()
        stream['title'] = (
            f"▶ {clean_filename}\n"
            f"🔱 {data['res']} • {data['source']} • {data['codec']}{data['hdr']}\n"
            f"🗣️ IT/GB | 💿 {data['audio']}\n"
            f"💾 {data['size']} | 👥 {data['peers']}\n"
            f"🦈 {data['uploader']}"
        )
        
        final_streams.append(stream)

    final_streams.sort(key=lambda x: "🐙" not in x["name"] and "🌩️" not in x["name"])

    return {"streams": final_streams}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7002)
