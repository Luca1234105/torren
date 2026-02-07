# Usa un'immagine base leggera di Python
FROM python:3.11-slim

# Imposta la directory di lavoro nel container
WORKDIR /app

# Variabili d'ambiente per evitare file .pyc e buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7002

# Copia prima i requirements per sfruttare la cache di Docker
COPY requirements.txt .

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice sorgente
COPY . .

# Espone la porta specificata
EXPOSE 7002

# Comando di avvio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7002"]
