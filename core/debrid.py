import httpx
import traceback

async def check_realdebrid_cache(hash_list: list, api_key: str):
    if not api_key or not hash_list: return set()
    
    base_url = "https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/"
    hash_path = "/".join(hash_list)
    url = f"{base_url}{hash_path}"
    
    headers = {"Authorization": f"Bearer {api_key}"}
    cached_hashes = set()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for h, variants in data.items():
                    if variants and "rd" in variants:
                        cached_hashes.add(h.lower())
    except Exception as e:
        print(f"Errore RD Cache: {e}")
        
    return cached_hashes

async def check_torbox_cache(hash_list: list, api_key: str):
    if not api_key or not hash_list: return set()
    
    # 1. Pulizia Key e Hash
    api_key = api_key.replace("Bearer ", "").strip()
    
    # Torbox vuole la virgola letterale, non codificata (%2C). 
    # Costruiamo l'URL a mano per sicurezza.
    clean_hashes = [h.strip().lower() for h in hash_list if h]
    if not clean_hashes: return set()

    hashes_str = ",".join(clean_hashes)
    url = f"https://api.torbox.app/v1/api/torrents/checkcached?hash_list={hashes_str}&format=list"
    
    headers = {"Authorization": f"Bearer {api_key}"}
    cached_hashes = set()

    print(f"📡 TORBOX CHECK: Controllo {len(clean_hashes)} hash...")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # Nota: Non usiamo params= qui, usiamo l'URL già costruito
            resp = await client.get(url, headers=headers)
            
            # --- DEBUG BLOCK ---
            if resp.status_code != 200:
                print(f"❌ TorBox Errore {resp.status_code}: {resp.text}")
                return None
            
            try:
                data = resp.json()
            except:
                print(f"❌ TorBox risponde ma non è JSON: {resp.text}")
                return None

            if data.get("success") is False:
                print(f"❌ TorBox API Error: {data}")
                return None
            # -------------------

            found = data.get("data", [])
            
            # Se la lista è vuota ma siamo sicuri che c'è cache, stampiamo per capire
            if not found:
                print(f"⚠️ TorBox: 0 hash trovati su {len(clean_hashes)} richiesti.")
                # Decommenta riga sotto se vuoi vedere quali hash hai chiesto
                # print(f"Richiesti: {clean_hashes}")
            else:
                print(f"✅ TorBox: Trovati {len(found)} file in cache!")

            for h in found:
                # Aggiungiamo in minuscolo per essere sicuri del match
                cached_hashes.add(h.lower())
                
    except Exception as e:
        print(f"❌ Eccezione TorBox: {e}")
        traceback.print_exc()
        return None

    return cached_hashes
