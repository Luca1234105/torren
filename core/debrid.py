import httpx

async def check_realdebrid_cache(hash_list: list, api_key: str):
    if not api_key or not hash_list: return set()
    
    # RD API: /instantAvailability/{hash}
    # Dividiamo gli hash in chunk se sono troppi, ma per ora facciamo semplice
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
                    # Se 'rd' è presente nelle varianti, è in cache
                    if variants and "rd" in variants:
                        cached_hashes.add(h.lower())
    except Exception as e:
        print(f"Errore RD Cache: {e}")
        
    return cached_hashes

async def check_torbox_cache(hash_list: list, api_key: str):
    if not api_key or not hash_list: return set()
    
    url = "https://api.torbox.app/v1/api/torrents/checkcached"
    params = {"hash_list": ",".join(hash_list), "format": "list"}
    headers = {"Authorization": f"Bearer {api_key}"}
    cached_hashes = set()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # Torbox ritorna la lista degli hash trovati
                found = data.get("data", [])
                for h in found:
                    cached_hashes.add(h.lower())
    except Exception as e:
        print(f"Errore TorBox Cache: {e}")

    return cached_hashes
