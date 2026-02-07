from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import re

# Import dei moduli interni
from utils.encoding import decode_config
from core.torrentio import fetch_torrentio_streams
from core.filter import is_italian_content
from core.debrid import check_realdebrid_cache, check_torbox_cache

app = FastAPI()

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
    service_tag = ""
    if settings.get("service") == "realdebrid": service_tag = " [RD]"
    if settings.get("service") == "torbox": service_tag = " [TB]"

    return {
        "id": "org.ita.torrentiofilter",
        "version": "1.0.2",
        "name": f"Torrentio ITA{service_tag}",
        "description": "Filtra solo contenuti ITA. ⚡ = In Cache, ⏳ = Download",
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
    # Se l'utente non ha messo opzioni, usiamo un default sensato
    options = settings.get("options", "") 

    # 1. Recupera gli stream da Torrentio
    try:
        data = await fetch_torrentio_streams(type, id, options)
        streams = data.get("streams", [])
    except Exception as e:
        print(f"Errore Torrentio: {e}")
        return {"streams": []}

    # 2. Filtra ITA e Raccogli Hash
    filtered_streams = []
    hashes_to_check = []

    for stream in streams:
        title = stream.get("title", "")
        name = stream.get("name", "")
        
        # Pulisci il nome (spesso Torrentio mette newline)
        filename = title.split("\n")[0]

        if is_italian_content(name, title):
            # Cerchiamo l'hash. Torrentio lo mette in infoHash.
            # Se non c'è, proviamo a estrarlo dall'URL magnet o http
            info_hash = stream.get("infoHash")
            
            # Se Torrentio non espone infoHash direttamente, prova a cercarlo nell'URL (fallback)
            if not info_hash and "btih:" in stream.get("url", ""):
                 match = re.search(r'btih:([a-fA-F0-9]{40})', stream['url'])
                 if match: info_hash = match.group(1)

            if info_hash:
                # Salviamo l'hash in una chiave temporanea per usarlo dopo
                stream["_temp_hash"] = info_hash
                hashes_to_check.append(info_hash)
            
            filtered_streams.append(stream)

    if not filtered_streams:
        return {"streams": []}

    # 3. Controllo Cache (Batch - Una sola chiamata per tutti)
    cached_hashes = set()
    
    if service == "realdebrid" and apikey and hashes_to_check:
        cached_hashes = await check_realdebrid_cache(hashes_to_check, apikey)
    elif service == "torbox" and apikey and hashes_to_check:
        cached_hashes = await check_torbox_cache(hashes_to_check, apikey)

    # 4. Formatta Output Finale
    final_streams = []
    for stream in filtered_streams:
        # Recupera l'hash temporaneo
        h = stream.get("_temp_hash", "").lower()
        
        # Pulisci il nome stream per rimuovere [RD download] vecchi di Torrentio
        clean_name = stream["name"].replace("[RD download]", "").replace("[RD+]", "").replace("Torrentio", "").strip()
        if not clean_name: clean_name = "ITA" # Fallback

        # Formatta Titolo e Descrizione
        title_lines = stream.get("title", "").split("\n")
        file_display = title_lines[0] # Il nome del file
        # Cerca la dimensione se presente nel titolo originale
        size_display = ""
        for line in title_lines:
            if "GB" in line or "MB" in line:
                size_display = line

        new_description = f"{file_display}\n{size_display}"

        if h in cached_hashes:
            # È IN CACHE: Icona Fulmine
            stream["name"] = f"[⚡RD+] 🇮🇹 {clean_name}"
            stream["title"] = new_description
            # Behavior hints per dire a Stremio che è pronto
            stream["behaviorHints"] = {
                "bingeGroup": f"ita-cached-{h}",
                "notWebReady": False
            }
        elif service:
            # NON È IN CACHE MA ABBIAMO DEBRID: Icona Clessidra
            stream["name"] = f"[⏳DL] 🇮🇹 {clean_name}"
            stream["title"] = new_description
        else:
             # NESSUN DEBRID (Solo P2P)
             stream["name"] = f"🇮🇹 {clean_name}"

        # Rimuovi chiave temporanea prima di inviare a Stremio
        if "_temp_hash" in stream: del stream["_temp_hash"]
        
        final_streams.append(stream)

    # Ordina: Prima i Cached (RD+), poi gli altri
    final_streams.sort(key=lambda x: "[⚡RD+]" not in x["name"])

    return {"streams": final_streams}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7002)
