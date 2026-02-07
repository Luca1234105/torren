from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import asyncio
import os
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# --- HELPER FUNCTIONS ---

def get_hash_from_stream(stream: dict) -> str:
    """Estrae l'hash da infoHash o URL"""
    if stream.get('infoHash'):
        return stream['infoHash'].lower()
    
    url = stream.get('url')
    if url:
        match = re.search(r'btih:([a-fA-F0-9]{40})', url, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        parts = url.split('/')
        if len(parts) > 6:
            potential_hash = parts[6]
            if re.match(r'^[a-fA-F0-9]{40}$', potential_hash):
                return potential_hash.lower()
    return ""

# --- REAL ACTIVE CHECKER ---

async def check_cache_active(stream: dict, api_key: str) -> bool:
    """
    Controllo Cache 'Pesante':
    1. Aggiunge Magnet a RD
    2. Seleziona i file
    3. Controlla se è 'downloaded' (Cached)
    4. Cancella il torrent
    """
    hash_val = get_hash_from_stream(stream)
    if not hash_val: 
        return False

    is_cached = False
    torrent_id = None

    try:
        async with httpx.AsyncClient(timeout=10, headers={'Authorization': f"Bearer {api_key}"}) as client:
            # 1. Aggiungi Magnet
            magnet_response = await rd.add_magnet(client, hash_val)
            if 'id' not in magnet_response:
                return False
            
            torrent_id = magnet_response['id']
            
            # 2. Seleziona tutti i file ("all") per vedere se è pronto
            await rd.select_files(client, torrent_id, "all")
            
            # 3. Controlla Info
            info = await rd.get_torrent_info(client, torrent_id)
            
            if info.get('status') == 'downloaded':
                is_cached = True
            
            # 4. Pulizia Immediata (Non lasciamo tracce)
            await rd.delete_torrent(client, torrent_id)

    except Exception as e:
        print(f"Errore Active Check per {hash_val}: {e}")
        # Tenta pulizia di emergenza se abbiamo un ID
        if torrent_id:
             try:
                 async with httpx.AsyncClient(timeout=5, headers={'Authorization': f"Bearer {api_key}"}) as client:
                    await rd.delete_torrent(client, torrent_id)
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
        "id": "org.ita.torrentiofilter.heavy",
        "version": "2.0.0",
        "name": "Torrentio ITA [Heavy Check]",
        "description": "Filtra ITA e forza il controllo cache su RD.",
        "resources": ["stream"],
        "types": ["movie", "series"],
        "catalogs": [],
        "idPrefixes": ["tt", "kitsu"]
    }

@app.get("/{config}/stream/{type}/{id}.json")
async def get_stream(config: str, type: str, id: str):
    print(f"\n--- STREAM: {type} {id} ---")
    settings = decode_config(config)
    service = settings.get("service")
    apikey = settings.get("key")
    options = settings.get("options", "")

    try:
        data = await fetch_torrentio_streams(type, id, options)
        streams = data.get("streams", [])
    except Exception as e:
        print(f"Errore Torrentio: {e}")
        return {"streams": []}

    final_streams = []
    
    # Filtra solo ITA
    ita_streams = [s for s in streams if is_italian_content(s.get('name', ''), s.get('title', ''))]
    print(f"DEBUG: Trovati {len(ita_streams)} ITA su {len(streams)} totali.")

    # Limitiamo il numero di controlli per non bloccare tutto (Max 15 file)
    ita_streams = ita_streams[:15]

    # Processiamo i file sequenzialmente (o in piccoli gruppi) per non esplodere RD
    for stream in ita_streams:
        base_name = stream['name'].replace('Torrentio', '').strip()
        
        # Se RealDebrid è configurato
        if service == 'realdebrid' and apikey:
            # Esegui il controllo pesante
            is_ready = await check_cache_active(stream, apikey)
            
            if is_ready:
                stream['name'] = f"[⚡RD+] 🇮🇹 {base_name}"
            else:
                stream['name'] = f"[⏳DL] 🇮🇹 {base_name}"
        else:
            stream['name'] = f"[P2P] 🇮🇹 {base_name}"

        final_streams.append(stream)

    # Ordina: Prima i Cached
    final_streams.sort(key=lambda x: "[⚡RD+]" not in x["name"])

    return {"streams": final_streams}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7002)
