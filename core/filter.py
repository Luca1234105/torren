import re

# Regex ottimizzata per trovare tag italiani
# Include: ITA, Italian, Crew famose (Corsaro, MIRCrew), Audio ITA
REGEX_ITA = re.compile(
    r'\b(ita|italian|accoppialo|audio\s?ita|ita\s?ac3|ita\s?aac|sub\s?ita|multi(?:-|\s)ita)\b',
    re.IGNORECASE
)

# Regex per escludere file spazzatura o non voluti
REGEX_BAD = re.compile(
    r'\b(cam|ts|telesync|workprint|xxx)\b',
    re.IGNORECASE
)

def is_italian_content(title: str, filename: str) -> bool:
    """Ritorna True se il contenuto è identificato come Italiano."""
    # Unisce titolo e filename per una ricerca completa
    full_text = f"{title} {filename}".lower()
    
    # 1. Se contiene parole bandite, scarta
    if REGEX_BAD.search(full_text):
        return False

    # 2. Cerca match positivo ITA
    if REGEX_ITA.search(full_text):
        return True
    
    # 3. Controllo extra per crew italiane note che a volte non mettono "ITA"
    if "ilcorsaronero" in full_text or "mircrew" in full_text or "tntvillage" in full_text:
        return True

    return False
