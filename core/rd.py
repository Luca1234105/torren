import httpx
import asyncio

REQUEST_DELAY = 0.24
api_url = 'https://api.real-debrid.com/rest/1.0'

# Torrents
async def get_torrents(client: httpx.AsyncClient, delay=0):
    await asyncio.sleep(delay)
    response = await client.get(f"{api_url}/torrents")
    return response.json()

async def get_torrent_info(client: httpx.AsyncClient, id: str, delay=0):
    await asyncio.sleep(delay)
    response = await client.get(f"{api_url}/torrents/info/{id}")
    return response.json()

async def delete_torrent(client: httpx.AsyncClient, id: str, delay=0):
    await asyncio.sleep(delay)
    response = await client.delete(f"{api_url}/torrents/delete/{id}")
    # print(f"Delete torrent: {response}")
    return response.status_code

async def add_magnet(client: httpx.AsyncClient, hash: str, delay=0):
    await asyncio.sleep(delay)
    magnet_link = f'magnet:?xt=urn:btih:{hash}'
    payload = {
        'magnet': magnet_link,
        'host': 'rd'
    }
    response = await client.post(f"{api_url}/torrents/addMagnet", data=payload)
    # print(f"Add magnet: {response}")
    return response.json()

async def select_files(client: httpx.AsyncClient, id: str, files: str, delay=0):
    await asyncio.sleep(delay)
    payload = {'files': files}
    response = await client.post(f"{api_url}/torrents/selectFiles/{id}", data=payload)
    # print(f"Select Files: {response}")
    return response


# Downloads
async def get_downloads(client: httpx.AsyncClient, delay=0):
    await asyncio.sleep(delay)
    response = await client.get(f"{api_url}/downloads")
    return response.json()

async def delete_download(client: httpx.AsyncClient, id: str, delay=0):
    await asyncio.sleep(delay)
    response = await client.delete(f"{api_url}/downloads/delete/{id}")
    # print(f"Delete download: {response}")
    return response.status_code
