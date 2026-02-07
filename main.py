from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

# Import moduli interni
from utils.encoding import decode_config
from core.torrentio import fetch_torrentio_streams
from core.filter import is_italian_content
from core.debrid import check_realdebrid_cache, check_torbox_cache

app = FastAPI()

# Abilita CORS per Stremio Web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
@app.get("/configure", response_class=HTMLResponse)
async def configure(request: Request):
    return templates.TemplateResponse("configure.html", {"request": request})

@app.get("/{config}/manifest.json")
async def get_manifest(config: str):
    settings = decode_config(config)
    
    # Personalizza il nome in base al servizio
    service_tag = ""
    if settings.get("service") == "realdebrid": service_tag = " [RD]"
    if settings.get("service") == "torbox": service_tag = " [TB]"

    return {
        "id": "org.ita.torrentiofilter",
        "version": "1.0.1",
        "name": f"Torrentio SOLO ITA{service_tag}",
        "description": "Filtra i risultati di Torrentio mostrando solo contenuti in Italiano. Supporta RealDebrid e TorBox.",
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
    options = settings.get("options", "") # Opzioni Torrentio (es. providers=...)

    # 1. Recupera gli stream da Torrentio
    try:
        data = await fetch_torrentio_streams(type, id, options)
        streams = data.get("streams", [])
    except Exception as e:
        print(f"Errore chiamata Torrentio: {e}")
        return {"streams": []}

    # 2. Filtra SOLO ITA
    filtered_streams = []
    hashes_to_check = []

    for stream in streams:
        title = stream.get("title", "")
        filename = title.split("\n")[0] # Spesso il filename è nella prima riga
        name = stream.get("name", "")

        if is_italian_content(name, title):
            # Aggiungi bandiera
            stream["name"] = f"🇮🇹 {name}"
            filtered_streams.append(stream)
            
            # Raccogli hash per il controllo cache
            info_hash = stream.get("infoHash")
            if info_hash:
                hashes_to_check.append(info_hash)

    if not filtered_streams:
        return {"streams": []}

    # 3. Controllo Cache Debrid
    cached_hashes = set()
    if service == "realdebrid" and apikey:
        cached_hashes = await check_realdebrid_cache(hashes_to_check, apikey)
    elif service == "torbox" and apikey:
        cached_hashes = await check_torbox_cache(hashes_to_check, apikey)

    # 4. Formatta Output Finale (Cached vs Download)
    final_streams = []
    for stream in filtered_streams:
        h = stream.get("infoHash", "").lower()
        
        if h in cached_hashes:
            stream["name"] = f"⚡ [RD+] {stream['name'].replace('🇮🇹 ', '')}"
            stream["behaviorHints"] = {"bingeGroup": f"ita-cached-{h}"}
        elif service:
            stream["name"] = f"⏳ [DOWNLOAD] {stream['name'].replace('🇮🇹 ', '')}"
        
        final_streams.append(stream)

    return {"streams": final_streams}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7002)
