import base64
import json

def decode_config(b64_str: str) -> dict:
    try:
        # Aggiunge padding se manca
        b64_str += '=' * (-len(b64_str) % 4)
        decoded = base64.b64decode(b64_str).decode('utf-8')
        return json.loads(decoded)
    except Exception:
        return {}

def encode_config(config: dict) -> str:
    json_str = json.dumps(config)
    # Rimuove padding '=' per rendere l'URL più pulito
    return base64.b64encode(json_str.encode('utf-8')).decode('utf-8').replace('=', '')
