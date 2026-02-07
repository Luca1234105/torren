<div align="center">

  <img src="https://i.ibb.co/wfF4j52/Gemini-Generated-Image-mm5p80mm5p80mm5p-Photoroom.png" alt="Torrenthan Logo" width="250" height="250" />

  # Torrenthan 🇮🇹
  
  **Motore di Ottimizzazione P2P & Debrid per Stremio**
  
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-High_Performance-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
  [![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

  <p align="center">
    <b>Torrenthan</b> non è un semplice addon. È un middleware avanzato che intercetta, ottimizza e inietta metadati nei flussi torrent prima di inviarli ai servizi Debrid, garantendo velocità istantanea e massima disponibilità di peer.
  </p>

  <p align="center">
    <a href="#-architettura">Architettura</a> •
    <a href="#-installazione">Installazione</a> •
    <a href="#-configurazione">Configurazione</a> •
    <a href="#-legal--disclaimer">⚖️ Note Legali</a>
  </p>
</div>

---

## ⚡ Introduzione e Filosofia

La maggior parte degli addon per Stremio soffre di un collo di bottiglia fondamentale: cerca di risolvere la disponibilità del file (Cached Check) *prima* di mostrare la lista dei risultati. Questo comporta tempi di attesa dai 5 ai 15 secondi solo per vedere l'elenco dei film.

**Torrenthan inverte il paradigma.**
Utilizza un approccio asincrono "Lazy Loading": restituisce la lista dei possibili stream **istantaneamente** (0 latenza). La risoluzione effettiva del link (comunicazione con le API Debrid, sblocco del file, selezione dello stream video) avviene **solo** nel momento esatto in cui l'utente preme "Play".

---

## 🧠 Architettura Tecnica

Torrenthan introduce due concetti chiave per migliorare la stabilità e la velocità dello streaming in Italia.

### 1. Risoluzione Just-in-Time (Lazy Loading)
Invece di sovraccaricare le API di Real-Debrid/TorBox con centinaia di richieste hash all'apertura del catalogo:
1.  L'addon genera URL "virtuali" che puntano al proprio endpoint `/playback`.
2.  Stremio riceve la lista in millisecondi.
3.  Al click, il server backend esegue la transazione API (Add Magnet -> Select Files -> Unrestrict Link).
4.  L'utente viene reindirizzato con un `HTTP 302` al flusso video finale MP4/MKV.

### 2. Tracker Injection System (TIS)
Molti torrent, specialmente quelli più vecchi o di nicchia italiani, falliscono su Real-Debrid perché il magnet link originale non contiene abbastanza tracker aggiornati.
Torrenthan **inietta dinamicamente** una lista curata di 10+ Tracker UDP ad alte prestazioni in ogni singola richiesta magnet.
> *Risultato:* Anche se il torrent originale ha 0 peer nel file `.torrent`, l'aggiunta dei tracker permette al cloud di trovare fonti alternative nella DHT network.

### 3. Smart Parsing
Il parser analizza i titoli grezzi dei file video per estrarre metadati cruciali che spesso sfuggono agli scraper tradizionali:
* Identificazione codec (HEVC/H.265 vs AVC).
* Riconoscimento Dynamic Range (HDR, Dolby Vision, HDR10+).
* Mapping audio avanzato (TrueHD, DTS-HD MA, Dolby Digital Plus).

---

## 🚀 Features Principali

* **Zero Latency Listing:** Caricamento immediato dei risultati di ricerca.
* **Dual-Provider Support:** Integrazione nativa sia per **Real-Debrid** (API REST) che per **TorBox**.
* **Italian Priority:** Algoritmo di filtro che privilegia tracce audio e sottotitoli in lingua italiana.
* **Fallback Management:** Gestione automatica degli errori di risoluzione API.
* **Secure Stream:** Nessun IP residenziale esposto durante lo streaming (tutto passa tramite Debrid).

---

## 🛠 Installazione e Deploy

### Opzione A: Docker (Raccomandata)

Il metodo più pulito e sicuro per eseguire Torrenthan è tramite container.

1.  **Clona la repository:**
    ```bash
    git clone [https://github.com/tuo-user/torrenthan.git](https://github.com/tuo-user/torrenthan.git)
    cd torrenthan
    ```

2.  **Build dell'immagine:**
    ```bash
    docker build -t torrenthan-server .
    ```

3.  **Avvio del container:**
    ```bash
    docker run -d -p 7002:7002 --restart unless-stopped --name torrenthan torrenthan-server
    ```

### Opzione B: Esecuzione Locale (Python)

Richiede Python 3.10 o superiore.

```bash
# Installazione dipendenze
pip install -r requirements.txt

# Avvio server Uvicorn
python main.py
```
⚙️ Configurazione
Una volta avviato il server, l'addon non richiede modifiche ai file di configurazione manuali. L'interfaccia di configurazione è accessibile via browser:

👉 URL: http://TUO-IP:7002/configure

Da questa pagina potrai:

Selezionare il provider (Real-Debrid o TorBox).

Inserire la tua API Key privata.

Impostare filtri di qualità opzionali.

Generare il link di installazione per Stremio ("Install").

---

---

<div align="center">

[![Legal](https://img.shields.io/badge/LEGAL-DISCLAIMER-red?style=for-the-badge&logo=scale)](https://en.wikipedia.org/wiki/Disclaimer)
[![Education](https://img.shields.io/badge/PURPOSE-EDUCATIONAL-blue?style=for-the-badge&logo=book)](https://opensource.org/)

# ⚖️ LEGAL & DISCLAIMER
### ⚠️ IMPORTANTE: LEGGERE ATTENTAMENTE PRIMA DELL'USO

</div>

### 1. 🧬 Natura del Software
**Torrenthan** è un motore di meta-ricerca e indicizzazione automatizzato. È fondamentale comprendere che questo software:

> * ❌ **NON** ospita, archivia o distribuisce alcun file video, audio o contenuto protetto da copyright.
> * ❌ **NON** possiede un database proprio di contenuti.
> * ✅ **AGISCE** esclusivamente come interfaccia tecnica ("Middleware") tra l'utente, plugin di terze parti (come Torrentio) e servizi di API pubbliche (come Real-Debrid o TorBox).

---

### 2. 👤 Responsabilità dell'Utente
L'utilizzo di questo software è a **totale discrezione e rischio dell'utente finale**.

* È **responsabilità esclusiva dell'utente** assicurarsi di possedere i diritti necessari per visualizzare o scaricare i contenuti accessibili tramite i servizi configurati.
* Gli sviluppatori di Torrenthan **non hanno alcun controllo** sui risultati forniti dagli scraper di terze parti né sui file accessibili tramite i servizi Debrid.

---

### 3. 🛡️ Conformità DMCA / Copyright
Poiché Torrenthan **non ospita contenuti** ma si limita a processare stringhe di testo (hash e magnet link) generate da terze parti:
* Non è tecnicamente possibile rimuovere contenuti dal "software" in quanto il software **non ne contiene**.
* Per richieste di rimozione contenuti (DMCA Takedown), rivolgersi direttamente ai **siti di hosting sorgente** o ai **tracker pubblici** indicizzati.

---

### 4. 🎓 Scopo Educativo
Questo progetto è stato sviluppato a **puro scopo didattico** e di ricerca per:
1.  Analizzare le performance delle librerie `FastAPI` in Python.
2.  Studiare l'interazione asincrona con API REST complesse e protocolli P2P.

> 🚫 **L'autore condanna fermamente la pirateria informatica e incoraggia l'uso di servizi di streaming legali e autorizzati.**

---

<div align="center">
  <sub>Developed with logic & passion.</sub><br>
  <sub><i>Torrenthan Team © 2024</i></sub>
</div>
